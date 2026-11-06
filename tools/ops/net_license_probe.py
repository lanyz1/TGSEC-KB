#!/usr/bin/env python3
"""Network-license sample triage: format, XOR recovery, patch plan, mock server."""
from __future__ import annotations

import argparse
import http.server
import json
import re
import socketserver
import sys
from pathlib import Path

CASES = Path("/root/cases")
MARKERS = [b"license", b"expired", b"trial", b"activate", b"machine", b"valid", b"serial"]


def case_dir(name: str | None) -> Path | None:
    if not name:
        return None
    p = Path(name) if Path(name).is_absolute() else CASES / name
    (p / "artifacts").mkdir(parents=True, exist_ok=True)
    return p


def strings(data: bytes) -> list[str]:
    return [m.decode("ascii", "replace") for m in re.findall(rb"[\x20-\x7e]{5,}", data)]


def drive(path: Path) -> dict:
    data = path.read_bytes()
    found = [(m.decode(), data.find(m)) for m in MARKERS if m in data.lower()]
    keys = {}
    for s in strings(data)[:5000]:
        if re.search(r"[A-Z0-9]{4,}(-[A-Z0-9]{4,}){2,}", s):
            keys.setdefault("license_like", []).append(s)
        if re.search(r"-----BEGIN (RSA|PUBLIC|PRIVATE) KEY-----", s):
            keys.setdefault("pem", []).append(s[:80])
    return {"path": str(path), "bytes": len(data), "magic": data[:8].hex(), "markers": found,
            "strings": len(strings(data)), "key_candidates": {k: v[:10] for k, v in keys.items()}}


def xor_key(plain: bytes, cipher: bytes) -> dict:
    n = min(len(plain), len(cipher))
    if n == 0:
        return {"error": "empty input"}
    key = bytes(a ^ b for a, b in zip(plain[:n], cipher[:n]))
    # shortest repeating period
    period = n
    for p in range(1, min(64, n) + 1):
        if all(key[i] == key[i % p] for i in range(n)):
            period = p
            break
    return {"length": period, "key_hex": key[:period].hex(), "key_repr": repr(key[:period]),
            "plain_head": plain[:80].decode("utf-8", "replace")}


def main() -> int:
    ap = argparse.ArgumentParser(description="网络验证/卡密样本探针")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("drive"); d.add_argument("--path", required=True); d.add_argument("--case")
    f = sub.add_parser("format"); f.add_argument("--sample", action="append", default=[])
    x = sub.add_parser("xor"); x.add_argument("--plain", required=True); x.add_argument("--cipher", required=True)
    pp = sub.add_parser("patch-plan"); pp.add_argument("--path", required=True)
    pp.add_argument("--apply", action="store_true"); pp.add_argument("--offset", type=lambda v: int(v, 0))
    pp.add_argument("--hex"); pp.add_argument("--case")
    sv = sub.add_parser("serve"); sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    if args.cmd == "serve":
        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.dumps({"valid": True, "expires": "2099-01-01T00:00:00Z", "code": 0}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        with socketserver.TCPServer((args.host, args.port), H) as srv:
            print(f"[serve] http://{args.host}:{args.port}")
            srv.serve_forever()
        return 0

    if args.cmd == "drive":
        p = Path(args.path)
        if not p.exists():
            ap.error(f"not found: {p}")
        out = drive(p)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        cd = case_dir(args.case)
        if cd:
            (cd / "artifacts/net_license_drive.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    if args.cmd == "format":
        if not args.sample:
            ap.error("--sample required")
        out = []
        for s in args.sample:
            out.append({"sample": s, "length": len(s), "segments": s.count("-") + 1,
                        "charset": "alnum" if s.replace("-", "").isalnum() else "other",
                        "upper": s.upper() == s, "looks_hex": bool(re.fullmatch(r"[0-9a-fA-F-]+", s))})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "xor":
        plain = Path(args.plain).read_bytes()
        cipher = Path(args.cipher).read_bytes()
        print(json.dumps(xor_key(plain, cipher), ensure_ascii=False, indent=2))
        return 0

    p = Path(args.path)
    if not p.exists():
        ap.error(f"not found: {p}")
    data = p.read_bytes()
    plan = []
    for m in MARKERS:
        start = 0
        while True:
            i = data.lower().find(m, start)
            if i < 0:
                break
            plan.append({"marker": m.decode(), "offset": hex(i), "context": data[max(0, i - 16):i + 32].hex()})
            start = i + 1
    out = {"path": str(p), "patches": plan}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.apply:
        if args.offset is None or not args.hex:
            ap.error("--apply requires --offset and --hex")
        new = bytes.fromhex(args.hex)
        mutated = bytearray(data)
        mutated[args.offset:args.offset + len(new)] = new
        dst = p.with_suffix(p.suffix + ".patched")
        dst.write_bytes(mutated)
        print("[patched]", dst)
    cd = case_dir(args.case)
    if cd:
        (cd / "artifacts/net_license_patch_plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
