#!/usr/bin/env python3
"""Session artifact scan: cookie/token names with redacted fingerprints."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CASES = Path("/root/cases")
PATTERNS = {
    "cookie": re.compile(rb"(?i)(cf_clearance|sessionid|session|PHPSESSID|JSESSIONID|csrftoken|auth_token)"),
    "bearer": re.compile(rb"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"),
    "jwt": re.compile(rb"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "api_key": re.compile(rb"(?i)(api[_-]?key|secret|access[_-]?token)[\"'\s:=]{1,6}[A-Za-z0-9._-]{12,}"),
}


def scan_file(p: Path) -> dict:
    try:
        data = p.read_bytes()[:50 * 1024 * 1024]
    except Exception:
        return {}
    out = {}
    for name, rx in PATTERNS.items():
        found = rx.findall(data)
        if found:
            raw = b"|".join(found[:100])
            out[name] = {"count": len(found), "fingerprint": hashlib.sha256(raw).hexdigest()[:12]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Cookie/Token 会话工件扫描")
    ap.add_argument("action", choices=["scan", "doctor"], nargs="?", default="scan")
    ap.add_argument("--path", "-p", required=True)
    ap.add_argument("--case")
    ap.add_argument("--max-files", type=int, default=5000)
    args = ap.parse_args()
    root = Path(args.path)
    if not root.exists():
        ap.error(f"not found: {root}")
    if args.action == "doctor":
        print("scan is read-only; values are never printed, only counts + sha256 prefixes")
        return 0
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()][:args.max_files]
    hits = {}
    for p in files:
        r = scan_file(p)
        if r:
            hits[str(p)] = r
    print(json.dumps({"root": str(root), "files": len(files), "hits": len(hits), "by_file": hits}, ensure_ascii=False, indent=2)[:8000])
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/session_scan.json"
        out.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
