#!/usr/bin/env python3
"""Adopt skills from a local store without overwriting existing cards."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

DEST = Path("/root/.hermes/skills")


def main() -> int:
    ap = argparse.ArgumentParser(description="从本地技能商店收编")
    ap.add_argument("--src", default="/root/skill_store")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    src = Path(args.src)
    files = list(src.rglob("SKILL.md")) if src.exists() else []
    added = skipped = 0
    for p in files:
        rel = p.relative_to(src)
        target = DEST / rel
        if target.exists():
            skipped += 1
            continue
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        added += 1
    print(json.dumps({"src": str(src), "dest": str(DEST), "found": len(files), "added": added, "skipped": skipped, "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
