#!/usr/bin/env python3
"""Coverage gate: every tools/ops reference must resolve to a real file.

Scope=all scans every skill markdown file. Scope=active scans each enabled
card's SKILL.md plus its direct references/*.md (split-out sections are part
of the card), so the metric follows content moved by the oversized-card split.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

SKILLS = Path("/root/.hermes/skills")
OPS = Path(__file__).resolve().parent
DB = Path("/root/.hermes/arsenal/arsenal.db")


def active_paths() -> set[str]:
    if not DB.exists():
        print(f"[gate] missing {DB}; cannot evaluate --active", file=sys.stderr)
        raise SystemExit(2)
    con = sqlite3.connect(DB)
    try:
        return {str(Path(row[0]).resolve()) for row in con.execute("select path from skills where status='enabled'")}
    finally:
        con.close()


def scan(active_only: bool = False) -> dict:
    allowed = None
    active_files: set[str] = set()
    if active_only:
        allowed = active_paths()
        for card in allowed:
            card_path = Path(card)
            active_files.add(str(card_path.resolve()))
            ref_dir = card_path.parent / "references"
            if ref_dir.is_dir():
                for rp in ref_dir.glob("*.md"):
                    active_files.add(str(rp.resolve()))
    refs: dict[str, set[str]] = {}
    for p in SKILLS.rglob("*.md"):
        if active_files and str(p.resolve()) not in active_files:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for name in re.findall(r"tools/ops/([A-Za-z0-9_.-]+\.py)", text):
            if name == "xxx.py":
                continue  # documentation placeholder, not an ops entrypoint
            refs.setdefault(name, set()).add(str(p))
    implemented = {n: len(v) for n, v in refs.items() if (OPS / n).exists()}
    missing = {n: len(v) for n, v in refs.items() if not (OPS / n).exists()}
    return {
        "scope": "active" if active_only else "all",
        "unique": len(refs),
        "implemented": implemented,
        "missing": missing,
        "implemented_refs": sum(implemented.values()),
        "missing_refs": sum(missing.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="tools/ops 覆盖率门禁")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--active", action="store_true", help="only enabled cards from arsenal.db")
    ap.add_argument("--strict", action="store_true", help="missing>0 时 exit 1")
    args = ap.parse_args()
    r = scan(active_only=args.active)
    total_refs = r["implemented_refs"] + r["missing_refs"]
    pct = 100.0 * r["implemented_refs"] / total_refs if total_refs else 0.0
    if args.json:
        print(json.dumps({**r, "ref_pct": round(pct, 1)}, ensure_ascii=False, indent=2))
    else:
        print(f"scope={r['scope']} unique={r['unique']} implemented={len(r['implemented'])} missing={len(r['missing'])}")
        print(f"refs implemented={r['implemented_refs']} missing={r['missing_refs']} coverage={pct:.1f}%")
        print("top missing:")
        for n, c in sorted(r["missing"].items(), key=lambda x: -x[1])[: args.top]:
            print(f"  {c:4d}  {n}")
    return 1 if args.strict and r["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
