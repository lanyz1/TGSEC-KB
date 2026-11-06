#!/usr/bin/env python3
"""RCE family routing: query the local vuln DB and print candidate cards."""
from __future__ import annotations

import argparse
import shutil
import subprocess


def main() -> int:
    ap = argparse.ArgumentParser(description="RCE 家族路由")
    ap.add_argument("query")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    exe = shutil.which("vuln_find")
    if not exe:
        print("[err] vuln_find not installed")
        return 127
    return subprocess.call([exe, args.query, "--top", str(args.top)])


if __name__ == "__main__":
    raise SystemExit(main())
