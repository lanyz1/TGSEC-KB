#!/usr/bin/env python3
"""Audit skill cards for references to external ops/playbook paths.

Usage:
  python3 audit_external_ops_refs.py [--skills-root DIR] [--repo-root DIR] [--all] [--json]

Default scans active SKILL.md cards only; --all also includes archived cards and
references. Exit 1 if any referenced path is missing; exit 0 if all resolve.
This is deliberately separate from generic reference auditing: a card can be
fully readable yet point at a tools/ops suite that does not exist on this host.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

PATTERN = re.compile(r"(?:tools/ops|docs/playbooks)/[A-Za-z0-9_.\-/]+\.(?:py|md)")


def active_cards(skills_root: str) -> list[str]:
    cfg_path = os.path.join(os.path.dirname(skills_root), "config.yaml")
    try:
        import yaml
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        disabled = set((cfg.get("skills") or {}).get("disabled") or [])
    except Exception:
        disabled = set()
    out = []
    for path in glob.glob(os.path.join(skills_root, "**", "SKILL.md"), recursive=True):
        if os.path.basename(os.path.dirname(path)) in disabled:
            continue
        out.append(path)
    return out


def all_cards(skills_root: str) -> list[str]:
    """Every markdown file under the skills tree, including archived references."""
    return glob.glob(os.path.join(skills_root, "**", "*.md"), recursive=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-root", default="/root/.hermes/skills")
    ap.add_argument("--repo-root", default="/root/TGSEC-Qtzuu")
    ap.add_argument("--all", action="store_true", help="scan all md, not only active SKILL.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cards = all_cards(args.skills_root) if args.all else active_cards(args.skills_root)
    refs: dict[str, int] = {}
    owners: dict[str, set[str]] = {}
    for path in cards:
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for ref in PATTERN.findall(text):
            refs[ref] = refs.get(ref, 0) + 1
            owners.setdefault(ref, set()).add(os.path.basename(os.path.dirname(path)))

    bases = [args.repo_root, os.path.dirname(args.skills_root)]
    missing = sorted(
        ref for ref in refs
        if not any(os.path.exists(os.path.join(base, ref)) for base in bases)
    )
    total_refs = sum(refs.values())
    implemented_refs = sum(count for ref, count in refs.items() if ref not in set(missing))
    coverage_pct = round(100.0 * implemented_refs / total_refs, 1) if total_refs else 0.0
    result = {
        "mode": "all" if args.all else "active",
        "cards": len(cards),
        "unique_refs": len(refs),
        "implemented": len(refs) - len(missing),
        "missing": len(missing),
        "ref_total": total_refs,
        "ref_implemented": implemented_refs,
        "coverage_pct": coverage_pct,
        "missing_refs": missing,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"mode: {result['mode']}  cards: {len(cards)}")
        print(f"unique refs: {len(refs)}  implemented: {result['implemented']}  missing: {len(missing)}")
        print(f"coverage: {implemented_refs}/{total_refs} = {coverage_pct}%")
        for ref in missing:
            print("MISS", ref, "(cited by", ", ".join(sorted(owners.get(ref, [])))[:120], ")")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
