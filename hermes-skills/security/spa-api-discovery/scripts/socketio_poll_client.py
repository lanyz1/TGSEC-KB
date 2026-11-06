#!/usr/bin/env python3
"""Minimal native Socket.IO v4 (Engine.IO 4) client over HTTP long-polling.

Use when a target's backend is Socket.IO **RPC** rather than REST -- i.e. every
REST path 404s but the client bundle contains /socket.io/ plus an
`rpc:request`-style envelope.  No third-party dependency beyond `requests`.

Requires: pip install requests

Typical use (see references/socketio-rpc-not-rest.md for the full protocol):

    import sys; sys.path.insert(0, '<this dir>')
    from socketio_poll_client import SIO
    B = "https://api.example.com"

    pub = SIO(B)                                  # public / no-token connection
    print(pub.rpc("auth.register",
                  {"name": "qa-tmp", "email": "<EMAIL-REDACTED>",
                   "password": "Str0ng!Passw0rd"}))  # -> {'ok':..,'data':{'accessToken':..}}

    au = SIO(B, token="<accessToken>")            # authenticated connection
    print(au.rpc("auth.me", {}))                  # confirm the session is live
    print(au.rpc("conversations.list", {"page": 1}))

PITFALLS baked into this implementation (all hit in the field):
  * never POST an empty body as a keepalive -- the server treats the illegal
    payload as a protocol violation and drops the Engine.IO session;
  * ack ids go multi-digit fast: slice `part[2:]` then take the leading digit
    run, do NOT hardcode `part[3:]`;
  * do not interleave actions on one socket -- ack replies get mismatched.
    One rpc() call at a time, wait for its ack.
"""
import json
import time

import requests
import urllib3

urllib3.disable_warnings()

H = {"User-Agent": "Mozilla/5.0"}
RS = "\x1e"  # Engine.IO record separator


class SIO:
    """HTTP long-polling Socket.IO v4 client. Polling only -- no websocket upgrade."""

    def __init__(self, base, token=None, ns=None, timeout=20, verify=False):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.verify = verify
        self.ns = ns          # e.g. "/admin"  (appended as &ns=%2Fadmin)
        self.ack = 0
        self.sid = None
        self._handshake()
        if token is not None:
            # namespace auth: token rides in the CONNECT packet, not an HTTP header
            self._post("40" + json.dumps({"token": token}, separators=(",", ":")))

    # ---------------- transport ----------------
    def _url(self):
        u = "%s/socket.io/?EIO=4&transport=polling" % self.base
        if self.sid:
            u += "&sid=" + self.sid
        if self.ns:
            u += "&ns=" + requests.utils.quote(self.ns, safe="")
        return u

    def _post(self, data):
        r = requests.post(self._url(), data=data, headers=H,
                          verify=self.verify, timeout=self.timeout)
        return r.text

    def _poll(self):
        r = requests.get(self._url(), headers=H,
                         verify=self.verify, timeout=self.timeout)
        return r.text

    def _handshake(self):
        txt = self._poll()
        if not txt.startswith("0"):
            raise RuntimeError("handshake failed: %r" % txt[:200])
        self.sid = json.loads(txt[1:])["sid"]
        return self.sid

    # ---------------- frame parsing ----------------
    @staticmethod
    def _parse_ack(part):
        """'43<ackId>[args]' -> (ackId, parsed_args). Handles multi-digit ackId."""
        rest = part[2:]
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        return int(rest[:i]), json.loads(rest[i:])

    def _wait_ack(self, want, wait):
        deadline = time.time() + wait
        while time.time() < deadline:
            try:
                raw = self._poll()
            except Exception:
                break
            if not raw:
                time.sleep(0.2)
                continue
            for part in raw.split(RS):
                if part.startswith("43"):
                    try:
                        got, payload = self._parse_ack(part)
                    except Exception:
                        continue
                    if got == want:
                        return payload
                elif part.startswith("44"):
                    return {"ok": False, "error": {"message": "namespace error: " + part}}
        return None

    def listen(self, seconds):
        """Collect non-ack event frames (42...) for `seconds`. For reconnaissance only."""
        out, deadline = [], time.time() + seconds
        while time.time() < deadline:
            try:
                raw = self._poll()
            except Exception:
                break
            if not raw:
                time.sleep(0.2)
                continue
            for part in raw.split(RS):
                if part.startswith("42") or part.startswith("43"):
                    out.append(part)
        return out

    # ---------------- RPC ----------------
    def rpc(self, event, payload=None, wait=8.0, envelope="rpc:request"):
        """Emit the RPC envelope and block for its ack.

        Returns ack payload -- normally {"ok":bool,"data":...,"error":{...}} --
        or None on timeout.  `event` is a "<root>.<verb>" action string.
        """
        self.ack += 1
        a = self.ack
        stamp = "%d-%s" % (int(time.time() * 1000), event[:8])
        req = {
            "requestId": stamp,
            "eventName": event,
            "payload": payload or {},
            "idempotencyKey": stamp,
            "attempt": 0,
        }
        self._post("42" + str(a) + json.dumps([envelope, req], separators=(",", ":")))
        return self._wait_ack(a, wait)


# Read-only verb matrix: safe to enumerate. Write verbs are deliberately absent.
READ_VERBS = ["get", "list", "listByUser", "feed", "messages", "history", "comments",
              "discover", "lobby", "matches", "search", "me", "find", "next"]


def probe_readonly(sio, roots, my_id=None, wait=4.0, pause=0.6):
    """Enumerate <root>.<readverb> and report which actions actually exist.

    Prints 'OK <action> -> <shape>' for actions returning ok=True, and returns
    the list of valid action names.  Never sends a write verb.
    """
    valid = []
    for rt in roots:
        for vb in READ_VERBS:
            act = "%s.%s" % (rt, vb)
            pl = {"page": 1}
            if my_id and vb in ("get", "listByUser"):
                pl["userId"] = my_id
                pl["id"] = my_id
            try:
                r = sio.rpc(act, pl, wait=wait)
            except Exception:
                continue
            if isinstance(r, dict) and r.get("ok"):
                d = r.get("data")
                shape = ({"count": len(d), "keys": (list(d[0].keys())
                          if d and isinstance(d[0], dict) else None)}
                         if isinstance(d, list) else d)
                print("OK  ", act, "->", json.dumps(shape)[:300])
                valid.append(act)
            time.sleep(pause)
    print("VALID:", valid)
    return valid


if __name__ == "__main__":
    import sys
    base = sys.argv[1]
    tok = sys.argv[2] if len(sys.argv) > 2 else None
    s = SIO(base, token=tok)
    print("connected sid=%s" % s.sid)
    print("auth.me ->", json.dumps(s.rpc("auth.me", {}))[:600])
