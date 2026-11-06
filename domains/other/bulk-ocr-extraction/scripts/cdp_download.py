#!/usr/bin/env python3
"""Download binary files through a logged-in browser session over CDP.

Use when direct fetches fail (403 / TLS-fingerprint / bot wall) but a real
browser with a valid session can reach the files (auth-walled media, ticket
attachments, private docs). Fires in-page Image loads, captures
Network.responseReceived events, pulls bodies via Network.getResponseBody.

Requires: pip install websocket-client requests; a browser running with
--remote-debugging-port=9222 and a logged-in tab on the target origin.

Usage:
  python3 cdp_download.py --urls urls.txt --out ./dl \\
      [--cdp http://127.0.0.1:9222] [--tab-match app.example.com] \\
      [--workers 8 --worker-id 0] [--min-bytes 500]

One process per --worker-id for parallelism. Resumable via done-set in
<out>/cdp_done_<worker-id>.json.

Pitfalls baked in (why this file exists):
- Prefer getResponseBody over Network.loadNetworkResource + IO.read: the latter
  starts answering {"code":-32000,"message":"Read failed"} after long CDP
  sessions / many loads. getResponseBody keeps working.
- A first IO.read returning empty is NOT EOF (async buffering) - if you must
  use that flow, retry ~5x with small sleeps before giving up.
- Only mark a URL done AFTER a verified non-empty save; failed/empty reads stay
  unmarked so the next run retries them (a broken reader that marks everything
  done while saving nothing drains the backlog silently).
"""
import argparse
import base64
import hashlib
import json
import os
import time

import requests
import websocket

KEEP_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp",
            "pdf", "zip", "csv", "txt", "xlsx", "docx"}
SKIP_EXT = {"mp4", "mov", "webm", "avi", "mkv", "mp3"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    ap.add_argument("--tab-match", default="", help="substring of tab URL to target")
    ap.add_argument("--urls", required=True, help="one URL per line (or JSONL with a 'url' key)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--worker-id", type=int, default=0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--min-bytes", type=int, default=500)
    av = ap.parse_args()

    os.makedirs(av.out, exist_ok=True)
    done_file = os.path.join(av.out, f"cdp_done_{av.worker_id}.json")
    done = set()
    if os.path.exists(done_file):
        try:
            done = set(json.load(open(done_file)))
        except Exception:
            pass

    urls = []
    for ln in open(av.urls):
        ln = ln.strip()
        if not ln:
            continue
        u = ln
        if ln.startswith("{"):
            try:
                u = json.loads(ln)["url"]
            except Exception:
                pass
        urls.append(u)
    mine = [u for i, u in enumerate(urls) if i % av.workers == av.worker_id and u not in done]
    print(f"worker {av.worker_id}/{av.workers}: {len(mine)} urls", flush=True)

    tabs = requests.get(av.cdp + "/json", timeout=15).json()
    pages = [t for t in tabs if t.get("type") == "page" and av.tab_match in t.get("url", "")]
    if not pages:
        pages = [t for t in tabs if t.get("type") == "page"]
    ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
    ws.settimeout(3)
    _id = [0]
    _q = []

    def cmd(method, params=None, timeout=45):
        _id[0] += 1
        mid = _id[0]
        ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                m = json.loads(ws.recv())
            except Exception:
                continue
            if m.get("id") == mid:
                return m
            if m.get("method"):
                _q.append(m)
        return {"error": "timeout"}

    def ev(expr, timeout=20):
        r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                     "awaitPromise": True}, timeout)
        return (r.get("result") or {}).get("result", {}).get("value")

    cmd("Network.enable")
    saved = 0
    for i in range(0, len(mine), av.batch):
        chunk = mine[i:i + av.batch]
        js = ";(() => {" + "".join(
            f"const im{k}=new Image(); im{k}.src={json.dumps(u)}; "
            for k, u in enumerate(chunk)) + "return true; })()"
        ev(js)
        want = set(chunk)
        rid_map = {}
        t0 = time.time()
        while want and time.time() - t0 < 40:
            for m in list(_q):
                if m.get("method") == "Network.responseReceived":
                    p = m.get("params", {})
                    u = p.get("response", {}).get("url", "")
                    if u in want:
                        rid_map[u] = p.get("requestId")
                        want.discard(u)
                _q.remove(m)
            if want:
                try:
                    m = json.loads(ws.recv())
                    if m.get("method") == "Network.responseReceived":
                        p = m.get("params", {})
                        u = p.get("response", {}).get("url", "")
                        if u in want:
                            rid_map[u] = p.get("requestId")
                            want.discard(u)
                except Exception:
                    pass
        for u, rid in rid_map.items():
            name = u.split("/")[-1].split("?")[0]
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
            if ext in SKIP_EXT:
                done.add(u)
                continue
            if ext not in KEEP_EXT:
                ext = "bin"
            fp = os.path.join(av.out, hashlib.sha1(u.encode()).hexdigest()[:20] + "." + ext)
            try:
                rb = cmd("Network.getResponseBody", {"requestId": rid}, timeout=30)
                d = rb.get("result") or {}
                body = d.get("body", "")
                if not body:
                    done.add(u)
                    continue
                b = base64.b64decode(body) if d.get("base64Encoded") else body.encode()
                if len(b) < av.min_bytes:
                    done.add(u)
                    continue
                with open(fp, "wb") as f:
                    f.write(b)
                saved += 1
                done.add(u)
            except Exception:
                pass  # leave unmarked -> retried next run
        done |= want  # never arrived
        if i % (av.batch * 10) == 0:
            json.dump(sorted(done), open(done_file, "w"))
            print(f"[{i}/{len(mine)}] saved={saved}", flush=True)
    json.dump(sorted(done), open(done_file, "w"))
    print(f"WORKER {av.worker_id} DONE saved={saved}", flush=True)


if __name__ == "__main__":
    main()
