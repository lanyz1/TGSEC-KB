#!/usr/bin/env python3
"""N-day route: product/CVE → local vuln library entries."""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="N-day 路由：产品/CVE → vuln_find")
    ap.add_argument("--product", "-p", help="product name, e.g. pfSense")
    ap.add_argument("--version", "-v", help="optional version")
    ap.add_argument("--cve", "-c", help="exact CVE id")
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()
    if not args.product and not args.cve:
        ap.error("need --product or --cve")

    if args.cve:
        query = args.cve
    else:
        query = " ".join(x for x in (args.product, args.version) if x)
    cmd = ["/usr/local/bin/vuln_find", query, "--top", str(args.top)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
