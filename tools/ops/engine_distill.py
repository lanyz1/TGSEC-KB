#!/usr/bin/env python3
"""Engine distillation snapshot: library size, dead refs, unused enabled cards."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

DB = Path("/root/.hermes/arsenal/arsenal.db")
OPS = Path("/root/TGSEC-Qtzuu/tools/ops")
REF = re.compile(r"tools/ops/([A-Za-z0-9_]+\.py)")


def snapshot() -> dict:
    c = sqlite3.connect(DB)
    rows = c.execute("select status,count(*),sum(length(description)+length(coalesce(excerpt,''))) from skills group by status").fetchall()
    total = c.execute("select count(*) from skills").fetchone()[0]
    refs = set()
    for body in Path("/root/.hermes/skills").rglob("SKILL.md"):
        try:
            refs |= set(REF.findall(body.read_text(errors="ignore")))
        except Exception:
            continue
    missing = sorted(r for r in refs if not (OPS / r).exists())
    cases = len(list(Path("/root/cases").glob("*/case_ledger.jsonl"))) if Path("/root/cases").exists() else 0
    return {"skills": total, "by_status": rows, "ops_refs": len(refs), "ops_missing": len(missing),
            "ops_missing_top": missing[:30], "cases": cases}


def main() -> int:
    ap = argparse.ArgumentParser(description="技能库蒸馏快照")
    ap.add_argument("action", choices=["snapshot", "orphans"], nargs="?", default="snapshot")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = snapshot()
    if args.action == "orphans":
        c = sqlite3.connect(DB)
        rows = c.execute("select name,category,use_count from skills where status='enabled' order by coalesce(use_count,0),name limit 30").fetchall()
        data["orphans"] = rows
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"skills={data['skills']} ops_refs={data['ops_refs']} missing={data['ops_missing']} cases={data['cases']}")
        for row in data.get("orphans", []):
            print("  orphan", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
