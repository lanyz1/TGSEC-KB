#!/usr/bin/env python3
"""OOB capture: local HTTP listener + callback payload generation."""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
from datetime import datetime


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        line = f"{datetime.utcnow().isoformat()}Z {self.client_address[0]} {self.path}\n"
        print(line, end="", flush=True)
        with open("/tmp/oob_hits.log", "a", encoding="utf-8") as f:
            f.write(line)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="OOB 回调捕获")
    ap.add_argument("action", choices=["serve", "payload"], nargs="?", default="serve")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--public", help="public host/url for payload")
    args = ap.parse_args()
    if args.action == "payload":
        base = args.public or f"http://{args.host}:{args.port}"
        print(f"{base.rstrip('/')}/oob?d=DATA")
        return 0
    with socketserver.TCPServer((args.host, args.port), H) as srv:
        print(f"[oob] listening {args.host}:{args.port}; log=/tmp/oob_hits.log")
        srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
