#!/usr/bin/env python3
"""Skill catalog checks against the local arsenal DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DB = Path("/root/.hermes/arsenal/arsenal.db")


def con() -> sqlite3.Connection:
    if not DB.exists():
        raise SystemExit(f"missing {DB}; run arsenal_build.py")
    return sqlite3.connect(DB)


def main() -> int:
    ap = argparse.ArgumentParser(description="技能目录 list/validate/doctor")
    ap.add_argument("action", choices=["list", "validate", "doctor"], nargs="?", default="list")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    c = con()
    if args.action == "list":
        rows = c.execute("select category,status,count(*) from skills group by category,status order by category,status").fetchall()
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for cat, status, n in rows:
                print(f"{cat or '-':28} {status:9} {n}")
    elif args.action == "validate":
        rows = c.execute("select name,path from skills").fetchall()
        missing = [(n, p) for n, p in rows if not Path(p).exists()]
        dup = c.execute("select name,count(*) c from skills group by name having c>1").fetchall()
        print(f"skills={len(rows)} missing_paths={len(missing)} duplicate_names={len(dup)}")
        for x in missing[:20]:
            print("  missing", x)
        for x in dup[:20]:
            print("  dup", x)
        if missing or dup:
            return 1
    else:
        checks = []
        for table in ("skills", "fts"):
            checks.append({"table": table, "exists": bool(c.execute("select 1 from sqlite_master where name=?", (table,)).fetchone())})
        count = c.execute("select count(*) from skills").fetchone()[0]
        print(json.dumps({"db": str(DB), "skills": count, "checks": checks}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
