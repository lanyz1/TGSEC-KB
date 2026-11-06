#!/usr/bin/env python3
"""Binary diff triage: hashes, changed offsets, string deltas."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def strings(data: bytes) -> set[str]:
    return {m.decode("ascii") for m in re.findall(rb"[\x20-\x7e]{6,}", data)}


def main() -> int:
    ap = argparse.ArgumentParser(description="二进制差分")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    a = Path(args.old).read_bytes()
    b = Path(args.new).read_bytes()
    n = min(len(a), len(b))
    diffs = [i for i in range(n) if a[i] != b[i]]
    sa, sb = strings(a), strings(b)
    out = {"old": args.old, "new": args.new,
           "sha_old": hashlib.sha256(a).hexdigest(), "sha_new": hashlib.sha256(b).hexdigest(),
           "size_old": len(a), "size_new": len(b), "changed_bytes": len(diffs) + abs(len(a) - len(b)),
           "first_offsets": [hex(i) for i in diffs[:args.limit]],
           "strings_added": sorted(sb - sa)[:args.limit], "strings_removed": sorted(sa - sb)[:args.limit]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
