#!/usr/bin/env python3
"""Audit absolute /root paths referenced by skill markdown files."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PATH_RE = re.compile(r"(?<![\w./-])(/root/[^\s`'\"<>|*?()\[\]{}]+)")
TRIM = ".,;:)]}`'\""
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
DEFAULT_SKIP = (
    "不存在",
    "没这个目录",
    "没有此目录",
    "旧路径",
    "旧仓",
    "历史",
    "迁移",
    "Formerly",
    "勿按",
)


def scan(root: Path, keep_history: bool = False) -> tuple[int, list[dict]]:
    missing: list[dict] = []
    scanned = 0
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            if not keep_history and any(mark in line for mark in DEFAULT_SKIP):
                continue
            for match in PATH_RE.finditer(line):
                candidate = match.group(1).rstrip(TRIM)
                if not candidate.startswith("/root/") or candidate == "/root":
                    continue
                if any(ch in candidate for ch in "<>*?$%{}|\\"):
                    continue
                if os.path.exists(candidate):
                    continue
                missing.append(
                    {
                        "path": candidate,
                        "file": str(path),
                        "line": lineno,
                        "text": line.strip()[:180],
                    }
                )
    missing.sort(key=lambda item: (item["file"], item["line"], item["path"]))
    return scanned, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path.home() / ".hermes" / "skills"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep-history", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    scanned, missing = scan(root, keep_history=args.keep_history)
    if args.json:
        print(json.dumps({"root": str(root), "scanned_files": scanned, "missing_count": len(missing), "missing": missing}, ensure_ascii=False, indent=2))
    else:
        print(f"scanned {scanned} markdown files; missing {len(missing)} paths")
        for item in missing:
            print(f"{item['file']}:{item['line']}: {item['path']}")
            print(f"  {item['text']}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
