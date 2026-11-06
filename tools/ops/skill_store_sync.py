#!/usr/bin/env python3
"""Skill store sync: mirror enabled skill files to a local store."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

SRC = Path("/root/.hermes/skills")


def main() -> int:
    ap = argparse.ArgumentParser(description="技能库同步")
    ap.add_argument("--dest", default="/root/skill_store")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dest = Path(args.dest)
    files = [p for p in SRC.rglob("SKILL.md")]
    copied = 0
    for p in files:
        rel = p.relative_to(SRC)
        target = dest / rel
        if target.exists() and target.read_bytes() == p.read_bytes():
            continue
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        copied += 1
    print(json.dumps({"src": str(SRC), "dest": str(dest), "skills": len(files), "copied": copied, "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
