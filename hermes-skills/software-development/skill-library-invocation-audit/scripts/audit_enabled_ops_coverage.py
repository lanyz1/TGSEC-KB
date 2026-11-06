#!/usr/bin/env python3
"""Audit enabled skill cards' tools/ops references (portable stdlib + PyYAML)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SKILLS = Path("/root/.hermes/skills")
CONFIG = Path("/root/.hermes/config.yaml")
OPS = Path("/root/TGSEC-Qtzuu/tools/ops")
PAT = re.compile(r"tools/ops/([A-Za-z0-9_.-]+\.py)")


def disabled_names() -> set[str]:
    try:
        import yaml
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
        return set((cfg.get("skills") or {}).get("disabled") or [])
    except Exception:
        return set()


def main() -> int:
    ap = argparse.ArgumentParser(description="enabled-card tools/ops coverage")
    ap.add_argument("--all", action="store_true", help="include disabled/archived cards")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    dis = set() if args.all else disabled_names()
    rows: dict[str, dict] = {}
    cards = 0
    for p in SKILLS.rglob("SKILL.md"):
        if not args.all and p.parent.name in dis:
            continue
        cards += 1
        text = p.read_text(encoding="utf-8", errors="ignore")
        for name in set(PAT.findall(text)):
            row = rows.setdefault(name, {"refs": 0, "cards": set()})
            row["refs"] += text.count("tools/ops/" + name)
            row["cards"].add(str(p))
    impl = {n: r for n, r in rows.items() if (OPS / n).exists() or (OPS / n).is_symlink()}
    miss = {n: r for n, r in rows.items() if n not in impl}
    refs_total = sum(r["refs"] for r in rows.values())
    refs_impl = sum(r["refs"] for r in impl.values())
    pct = round(100.0 * refs_impl / refs_total, 1) if refs_total else 0.0
    top = sorted(((r["refs"], n) for n, r in miss.items()), reverse=True)[: args.top]
    out = {
        "scope": "all" if args.all else "enabled",
        "cards": cards,
        "unique": len(rows),
        "implemented": len(impl),
        "missing": len(miss),
        "refs_total": refs_total,
        "refs_implemented": refs_impl,
        "refs_missing": refs_total - refs_impl,
        "coverage_pct": pct,
        "top_missing": [{"name": n, "refs": r} for r, n in top],
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"scope={out['scope']} cards={cards} unique={len(rows)} implemented={len(impl)} missing={len(miss)}")
        print(f"refs={refs_impl}/{refs_total} coverage={pct}%")
        for item in out["top_missing"]:
            print(f"  {item['refs']:3} {item['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
