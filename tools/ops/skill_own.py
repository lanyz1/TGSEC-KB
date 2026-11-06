#!/usr/bin/env python3
"""Look up ownership/location of a skill in the local arsenal DB."""
from __future__ import annotations

import argparse
import sqlite3

DB = "/root/.hermes/arsenal/arsenal.db"


def main() -> int:
    ap = argparse.ArgumentParser(description="技能归属查询")
    ap.add_argument("name")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    c = sqlite3.connect(DB)
    row = c.execute("select name,category,status,path,use_count from skills where name=? or name like ?",
                    (args.name, "%" + args.name + "%")).fetchone()
    if not row:
        print("not found")
        return 1
    print(row if args.json else "\n".join(str(x) for x in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
