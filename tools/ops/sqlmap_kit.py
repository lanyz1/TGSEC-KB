#!/usr/bin/env python3
"""Scoped sqlmap wrapper: saves output under the case directory."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="sqlmap 案卷化包装")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case")
    ap.add_argument("--data")
    ap.add_argument("--cookie")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--risk", type=int, default=1)
    ap.add_argument("--technique", default="BEUSTQ")
    ap.add_argument("--extra", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    exe = shutil.which("sqlmap")
    if not exe:
        print("[err] sqlmap not installed; tool_get sqlmap")
        return 127
    cmd = [exe, "-u", args.url, "--batch", "--level", str(args.level), "--risk", str(args.risk),
           "--technique", args.technique, "--smart"]
    if args.data:
        cmd += ["--data", args.data]
    if args.cookie:
        cmd += ["--cookie", args.cookie]
    out = None
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        out = case / "artifacts/sqlmap"
        out.mkdir(parents=True, exist_ok=True)
    if out:
        cmd += ["--output-dir", str(out)]
    if args.extra:
        cmd += args.extra
    print("[run]", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
