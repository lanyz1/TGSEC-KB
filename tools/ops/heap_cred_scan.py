#!/usr/bin/env python3
"""Heap/dump credential scan: strings + secret-like regex, no execution."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PATTERNS = {
    "urls": re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,300}"),
    "emails": re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "tokens": re.compile(rb"(?i)(?:token|secret|password|passwd|api[_-]?key|authorization)[\"'\s:=]{1,6}[A-Za-z0-9_\-\.]{8,120}"),
    "jwt": re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Heap/dump 凭据扫描：URL/邮箱/token/JWT")
    ap.add_argument("path", help=".hprof/.dmp/heapdump/binary")
    ap.add_argument("--out", "-o", default="heap_creds", help="output directory")
    ap.add_argument("--max-mb", type=int, default=512)
    args = ap.parse_args()
    src = Path(args.path)
    if not src.exists():
        ap.error(f"not found: {src}")
    data = src.read_bytes()[: args.max_mb * 1024 * 1024]
    found = {k: sorted({m.decode("utf-8", errors="replace") for m in pat.findall(data)})[:500]
             for k, pat in PATTERNS.items()}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"source": str(src), "bytes_scanned": len(data),
               "checked_at": datetime.now(timezone.utc).isoformat(), **found}
    (out / "heap_creds.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[heap] urls={len(found['urls'])} emails={len(found['emails'])} tokens={len(found['tokens'])} jwt={len(found['jwt'])}")
    print(f"[heap] {out / 'heap_creds.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
