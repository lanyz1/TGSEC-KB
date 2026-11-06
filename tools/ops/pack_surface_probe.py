#!/usr/bin/env python3
"""Compat: pack_surface_probe drive --name <card> --case <case> --base <URL>."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tools/ops/gambling_family_probe.py"


def main() -> int:
    ap = argparse.ArgumentParser(description="实战包表面探针（兼容入口）")
    ap.add_argument("action", choices=["drive"], nargs="?", default="drive")
    ap.add_argument("--name", required=True, help="card/family name")
    ap.add_argument("--base", "--url", dest="base", required=True, help="authorized base URL")
    ap.add_argument("--case", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cmd = [sys.executable, str(TARGET), "--family", args.name, "--base", args.base,
           "--case", args.case]
    if args.dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
