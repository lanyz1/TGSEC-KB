#!/usr/bin/env python3
"""Thin web surface probe: delegate to the local kit_run web kit.

This is the high-frequency entry point used by many imported cards. It does
not reimplement scanning; whatweb + nuclei tech-detect + small ffuf run.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "tools/ops/kit_run.py"


def main() -> int:
    ap = argparse.ArgumentParser(description="Web surface probe (whatweb + nuclei tech + ffuf)")
    ap.add_argument("--url", "-u", required=True, help="authorized URL")
    ap.add_argument("--case", "-c", required=True, help="case name under /root/cases")
    ap.add_argument("--scope", action="append", help="allowed host/CIDR; default: URL host")
    ap.add_argument("--full", action="store_true", help="include subfinder/nmap where applicable")
    ap.add_argument("--timeout", type=int, default=45, help="per-step timeout seconds")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    host = (urlparse(args.url).hostname or "").strip()
    if not host:
        ap.error("URL has no hostname")
    scopes = args.scope or [host]
    cmd = [sys.executable, str(KIT), "run", "--kit", "web", "-u", args.url,
           "--case", args.case, "--timeout", str(args.timeout)]
    for s in scopes:
        cmd += ["--scope", s]
    if args.full:
        cmd.append("--full")
    if args.dry_run:
        cmd.append("--dry-run")
    p = subprocess.run(cmd)
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
