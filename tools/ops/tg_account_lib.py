#!/usr/bin/env python3
"""Telegram session library inventory (no network, no secrets printed)."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOTS = [Path("/root"), Path.home() / ".hermes"]


def sessions() -> list[Path]:
    seen = set()
    for root in ROOTS:
        if root.exists():
            for p in root.rglob("*.session"):
                if p.is_file():
                    seen.add(p)
    return sorted(seen)


def info(p: Path) -> dict:
    out = {"path": str(p), "bytes": p.stat().st_size}
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        names = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
        out["tables"] = names
        if "sessions" in names:
            out["sessions"] = c.execute("select count(*) from sessions").fetchone()[0]
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TG 号库盘点")
    ap.add_argument("action", choices=["list", "stats"], nargs="?", default="list")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = [info(p) for p in sessions()]
    if args.action == "stats":
        data = {"total": len(rows), "bytes": sum(r["bytes"] for r in rows)}
    else:
        data = rows
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
