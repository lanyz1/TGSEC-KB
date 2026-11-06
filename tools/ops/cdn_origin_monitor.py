#!/usr/bin/env python3
"""Origin/CDN drift monitor: current DNS vs baseline, flag IP changes."""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path


def a_records(domain: str) -> list[str]:
    try:
        return sorted({str(x[4][0]) for x in socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)})
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="CDN/源站 IP 漂移监控")
    ap.add_argument("domain")
    ap.add_argument("--baseline", help="baseline JSON from a previous --save")
    ap.add_argument("--save", help="write current records to this JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    current = a_records(args.domain)
    old = []
    if args.baseline and Path(args.baseline).exists():
        old = json.loads(Path(args.baseline).read_text()).get("ips", [])
    added = sorted(set(current) - set(old))
    removed = sorted(set(old) - set(current))
    out = {"domain": args.domain, "ips": current, "added": added, "removed": removed,
           "changed": bool(old) and (bool(added) or bool(removed))}
    if args.save:
        Path(args.save).write_text(json.dumps({"domain": args.domain, "ips": current}, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"{args.domain}: {', '.join(current) or 'NXDOMAIN'}")
        if added:
            print("  +", ", ".join(added))
        if removed:
            print("  -", ", ".join(removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
