#!/usr/bin/env python3
"""Hermes skill-library sentinel: read-only inventory, ledger tail, report.

This is the local monitoring entrypoint, not the intake/ingest tool. It reads
arsenal.db and Hermes curator ledgers; it never writes Hermes profile files.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path("/root/.hermes/arsenal/arsenal.db")
SKILLS = Path("/root/.hermes/skills")
LEDGERS = [Path("/root/.hermes/skills/.curator_ledger.jsonl"),
           Path("/root/.hermes/profiles/bot2/skills/.curator_ledger.jsonl"),
           Path("/root/.hermes/profiles/bot3/skills/.curator_ledger.jsonl")]
STATE = Path("/root/.hermes/arsenal/sentinel_state.json")
REPORT = Path("/root/TGSEC-Qtzuu/docs/learning/skill-store/hermes/sentinel_report.md")


def counts() -> dict[str, int]:
    if not DB.exists():
        return {"total": 0, "enabled": 0, "disabled": 0, "legacy": 0}
    con = sqlite3.connect(DB)
    try:
        rows = dict(con.execute("select status, count(*) from skills group by status").fetchall())
        total = con.execute("select count(*) from skills").fetchone()[0]
        legacy = con.execute("select count(*) from skills where legacy is not null and legacy != ''").fetchone()[0]
    finally:
        con.close()
    return {"total": total, "enabled": rows.get("enabled", 0),
            "disabled": rows.get("disabled", 0), "legacy": legacy}


def ledger_rows(limit: int) -> list[dict]:
    rows: list[dict] = []
    for path in LEDGERS:
        if not path.exists():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()[-limit:]
        except OSError:
            continue
        for line in lines:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                item["_ledger"] = str(path)
                rows.append(item)
    return rows[-limit:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Hermes skill-library sentinel (read-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--json", action="store_true")
    p.add_argument("--exit-on-new", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("ledger")
    p.add_argument("--n", type=int, default=30)
    p = sub.add_parser("report")
    p = sub.add_parser("sync")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("watch")
    p.add_argument("--interval", type=int, default=1800)
    p = sub.add_parser("install")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    if args.cmd == "ledger":
        rows = ledger_rows(args.n)
        for row in rows:
            action = row.get("action") or row.get("event") or "?"
            path = row.get("path") or row.get("file_path") or ""
            if not path and isinstance(row.get("evidence"), dict):
                path = row["evidence"].get("file_path") or ""
            if not path:
                path = row.get("skill") or ""
            session = row.get("session_id") or ""
            if not session and isinstance(row.get("evidence"), dict):
                session = row["evidence"].get("session_id") or ""
            print(f"{action}\t{path}\t{session}")
        return 0

    if args.cmd == "status":
        data = {"counts": counts(), "db": str(DB), "ledgers": [str(p) for p in LEDGERS if p.exists()],
                "state": str(STATE), "state_exists": STATE.exists()}
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else
              f"total={data['counts']['total']} enabled={data['counts']['enabled']} "
              f"disabled={data['counts']['disabled']} legacy={data['counts']['legacy']} "
              f"ledgers={len(data['ledgers'])}")
        return 0

    if args.cmd in ("sync", "watch", "install"):
        print(f"[sentinel] {args.cmd} is not automated in this read-only entrypoint; "
              "run tools/ops/hermes_intake.py and skill_index.py for intake.")
        return 2 if args.cmd != "watch" else 0

    if args.cmd == "report":
        data = counts()
        rows = ledger_rows(20)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# Hermes skill sentinel report", "",
                 f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
                 f"- total: {data['total']}", f"- enabled: {data['enabled']}",
                 f"- disabled: {data['disabled']}", f"- legacy: {data['legacy']}",
                 "", "## recent ledger", ""]
        for row in rows:
            lines.append(f"- {row.get('action','?')}: {row.get('path') or row.get('file_path') or ''}")
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[report] {REPORT}")
        return 0

    data = counts()
    last = None
    if STATE.exists():
        try:
            last = json.loads(STATE.read_text())
        except Exception:
            last = None
    delta = data["total"] - int(last.get("total", data["total"])) if isinstance(last, dict) else 0
    if args.exit_on_new and delta > 0:
        print(f"[sentinel] new cards={delta}")
        return 10
    if args.json:
        print(json.dumps({"counts": data, "delta_total": delta}, ensure_ascii=False, indent=2))
    elif delta or args.verbose:
        print(f"[sentinel] total={data['total']} enabled={data['enabled']} delta={delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
