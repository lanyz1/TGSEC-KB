#!/usr/bin/env python3
"""Skill index build/search compatibility entry."""
from __future__ import annotations

import argparse
import shutil
import subprocess


def main() -> int:
    ap = argparse.ArgumentParser(description="技能索引 build/find")
    ap.add_argument("action", choices=["build", "find"], nargs="?", default="find")
    ap.add_argument("query", nargs="*")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    if args.action == "build":
        p = "/root/.hermes/arsenal/arsenal_build.py"
        print("[run]", p)
        return subprocess.call(["python3", p])
    exe = shutil.which("skill_find")
    if not exe:
        print("[err] skill_find missing")
        return 127
    return subprocess.call([exe, " ".join(args.query), "--top", str(args.top)])


if __name__ == "__main__":
    raise SystemExit(main())
