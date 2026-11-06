#!/usr/bin/env python3
"""N-day family probe: vuln library lookup + optional web surface pass."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "tools/ops"
CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="N-day 家族探针：漏洞库定位 + 可选 Web 面")
    ap.add_argument("--family", required=True, help="product/family, e.g. gitea, pfSense")
    ap.add_argument("--base", help="authorized base URL for optional surface pass")
    ap.add_argument("--case", help="case name (required with --base)")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--lookup-only", action="store_true", help="only query vuln_find")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.base and not args.case:
        ap.error("--base requires --case")

    lookup = subprocess.run(["/usr/local/bin/vuln_find", args.family, "--top", str(args.top)],
                            capture_output=True, text=True)
    print(lookup.stdout, end="")
    if lookup.stderr:
        print(lookup.stderr, file=sys.stderr, end="")
    if lookup.returncode != 0:
        return lookup.returncode
    if args.lookup_only or not args.base:
        return 0

    host = urlparse(args.base).hostname
    if not host:
        ap.error("--base has no hostname")
    if args.dry_run:
        print(f"[dry] core_web_surface_probe --url {args.base} --case {args.case} --scope {host}")
        return 0
    case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
    case.mkdir(parents=True, exist_ok=True)
    (case / "artifacts").mkdir(exist_ok=True)
    (case / "artifacts/nday_family_lookup.txt").write_text(lookup.stdout, encoding="utf-8")
    cmd = [sys.executable, str(OPS / "core_web_surface_probe.py"), "--url", args.base,
           "--case", str(case), "--scope", host]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
