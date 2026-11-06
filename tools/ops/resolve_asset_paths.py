#!/usr/bin/env python3
"""Resolve dead docs/learning skill-card paths to local cards.

The historical packs referenced `docs/learning/<pack>/skills/<name>/` (and
`.../SKILL.md`).  Those files were never imported.  When an exact skill-name
match exists under ~/.hermes/skills, create a symlink at the expected path so
the original card links resolve without rewriting the operator's cards.

Only exact directory/file basename matches are linked.  Data files, indexes and
missing non-card assets are reported, never fabricated.

Usage:
  python3 tools/ops/resolve_asset_paths.py            # dry run
  python3 tools/ops/resolve_asset_paths.py --apply    # create symlinks
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

SKILLS = Path("/root/.hermes/skills")
TGSEC = Path("/root/TGSEC-Qtzuu")
PAT = re.compile(r"docs/learning/[^\s`\)\]\}\]<>\"']+")


def skill_index() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in SKILLS.rglob("SKILL.md"):
        out.setdefault(p.parent.name, p.parent)
    return out


def classify(ref: str) -> tuple[str, str] | None:
    """Return (kind, name) for a missing reference, or None if not a skill path."""
    clean = ref.rstrip(".,;:")
    parts = [x for x in clean.split("/") if x]
    if not parts:
        return None
    if parts[-1] == "SKILL.md":
        if len(parts) < 2:
            return None
        return ("dir", parts[-2])
    # A directory reference normally ends in '/', but the regex strips it.
    if len(parts) >= 2 and parts[-2] in {"skills", "redteam", "research"}:
        return ("dir", parts[-1])
    return None


def scan() -> tuple[list[tuple[str, str, Path]], list[str]]:
    idx = skill_index()
    seen: set[str] = set()
    links: list[tuple[str, str, Path]] = []
    unresolved: list[str] = []
    for card in SKILLS.rglob("SKILL.md"):
        text = card.read_text(errors="ignore")
        for match in PAT.finditer(text):
            ref = match.group(0).rstrip(".,;:")
            if "。" in ref or ref.endswith("/。"):
                continue  # malformed prose punctuation, not an asset path
            if ref in seen:
                continue
            seen.add(ref)
            if (TGSEC / ref).exists():
                continue
            cls = classify(ref)
            if not cls:
                unresolved.append(ref)
                continue
            kind, name = cls
            target = idx.get(name)
            if not target:
                unresolved.append(ref)
                continue
            # Preserve a trailing slash as a directory reference.
            links.append((ref, name, target))
    return links, unresolved


def apply(links: list[tuple[str, str, Path]]) -> tuple[int, int]:
    made = skipped = 0
    for ref, _name, target in links:
        dest = TGSEC / ref.rstrip("/")
        if dest.is_symlink() or dest.exists():
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, dest, target_is_directory=True)
        made += 1
    return made, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="docs/learning 死路径 → 本地技能卡 symlink")
    ap.add_argument("--apply", action="store_true", help="实际创建 symlink（默认 dry-run）")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    links, unresolved = scan()
    print(f"resolvable={len(links)} unresolved={len(unresolved)}")
    for ref, name, target in links[: args.top]:
        print(f"  {ref} -> {target}")
    if unresolved:
        print("unresolved sample:")
        for ref in unresolved[: args.top]:
            print(f"  {ref}")
    if args.apply:
        made, skipped = apply(links)
        print(f"created={made} skipped={skipped}")
    else:
        print("dry-run; use --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
