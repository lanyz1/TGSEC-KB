#!/usr/bin/env python3
"""Case board: one-line status for every local case ledger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = Path("/root/cases")


def stats(case: Path) -> dict:
    rows = []
    ledger = case / "ledger.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    hyps = {r.get("id") for r in rows if r.get("type") == "hypothesis"}
    verdicts = {r.get("hypothesis") for r in rows if r.get("type") == "verdict"}
    confirmed = sum(1 for r in rows if r.get("type") == "verdict" and r.get("status") == "confirmed")
    return {"hypotheses": len(hyps), "verdicts": len(verdicts),
            "open": len(hyps - verdicts), "confirmed": confirmed,
            "report": (case / "REPORT.md").exists()}


def main() -> int:
    ap = argparse.ArgumentParser(description="案卷看板")
    ap.add_argument("action", choices=["board"], nargs="?", default="board")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cases = sorted([p for p in CASES.iterdir() if p.is_dir()]) if CASES.exists() else []
    out = []
    for c in cases:
        s = stats(c)
        out.append({"case": c.name, **s})
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"{'case':28} {'H':>3} {'V':>3} {'open':>5} {'conf':>5} report")
        for r in out:
            print(f"{r['case']:28} {r['hypotheses']:3} {r['verdicts']:3} {r['open']:5} {r['confirmed']:5} {r['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
