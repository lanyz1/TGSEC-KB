#!/usr/bin/env python3
"""Hypothesis route: current signal → matching skills + open case hypotheses."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="假设路由：信号 → 技能卡 + 当前案卷开放假设")
    ap.add_argument("--signal", "-s", required=True, help="current signal/phase, e.g. 'actuator env leaked'")
    ap.add_argument("--case", "-c", help="optional case name")
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    p = subprocess.run(["/usr/local/bin/skill_find", args.signal, "--top", str(args.top)],
                       capture_output=True, text=True)
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")

    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        ledger = case / "ledger.jsonl"
        open_hyps = []
        verdicts = set()
        if ledger.exists():
            rows = []
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            verdicts = {r.get("hypothesis") for r in rows if r.get("type") == "verdict"}
            open_hyps = [r for r in rows if r.get("type") == "hypothesis" and r.get("id") not in verdicts]
        print(f"\n[case] {case} open_hypotheses={len(open_hyps)}")
        for h in open_hyps:
            print(f"  {h.get('id')}: {h.get('claim','')}")
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
