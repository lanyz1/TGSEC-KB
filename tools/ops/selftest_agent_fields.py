#!/usr/bin/env python3
"""Self-test for agent_probe.fields against a local mock API (19 checks)."""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
payload = base64.urlsafe_b64encode(json.dumps({"sub": "1", "exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
JWT = "eyJhbGciOiJIUzI1NiJ9." + payload + ".sig"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"data": [{"username": "u1", "password_hash": "x", "token": JWT}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main() -> int:
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_port
    with tempfile.TemporaryDirectory() as td:
        cmd = ["python3", str(HERE / "agent_probe.py"), "fields", "--base", f"http://127.0.0.1:{port}",
               "--scope", "127.0.0.1", "--paths", "/api/game/agent/all-users", "--case", td]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        art = Path(td) / "artifacts/agent_field_audit.json"
        data = json.loads(art.read_text()) if art.exists() else {}
        sens = data.get("sensitive", {})
        toks = data.get("tokens", {})
        checks = [
            p.returncode == 0,
            art.exists(),
            data.get("paths", {}).get("/api/game/agent/all-users", {}).get("status") == 200,
            sens.get("password_hash") == 1,
            "username" not in sens,
            toks.get("total") == 1,
            toks.get("live") == 1,
            toks.get("expired") == 0,
            toks.get("live", 0) + toks.get("expired", 0) == toks.get("total", 0),
            "password" not in json.dumps(data).lower() or sens.get("password_hash") == 1,
            JWT not in json.dumps(data),
            "paths" in data,
            "sensitive" in data,
            "tokens" in data,
            isinstance(sens, dict),
            isinstance(toks, dict),
            "agent_field_audit.json" == art.name,
            len(json.dumps(data)) > 10,
            p.stderr == "",
        ]
        ok = sum(1 for c in checks if c)
        print(f"selftest_agent_fields: {ok}/{len(checks)}")
        if ok != len(checks):
            print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
            print(p.stderr[:500])
        srv.shutdown()
        return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
