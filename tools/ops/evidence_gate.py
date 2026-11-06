#!/usr/bin/env python3
"""Evidence gate wrapper around case_ledger.py verify --report."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _case_gate import check as semantic_check

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".claude/skills/pentest-redteam/scripts/case_ledger.py"


def case_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or "/" in name:
        return p
    return Path("/root/cases") / name


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail unless the case ledger passes its evidence gate")
    ap.add_argument("--case", required=True)
    ap.add_argument("--repair-tail", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    case = case_path(args.case)
    if not (case / "ledger.jsonl").exists():
        print(json.dumps({"ok": False, "error": "missing ledger", "case": str(case)}) if args.json
              else f"[gate] FAIL missing ledger: {case}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(LEDGER), "verify", "--report", str(case)]
    if args.repair_tail:
        cmd.insert(3, "--repair-tail")
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    sem_ok, sem_errors, stats = semantic_check(case)
    ok = p.returncode == 0 and sem_ok
    if args.json:
        print(json.dumps({"ok": ok, "case": str(case), "exit": p.returncode,
                          "structural": out, "semantic": {"ok": sem_ok, "errors": sem_errors, **stats}},
                         ensure_ascii=False))
    else:
        print(out)
        if not sem_ok:
            print("[gate] SEMANTIC FAIL:")
            for e in sem_errors:
                print("  -", e)
        print(f"[gate] {'PASS' if ok else 'FAIL'} {case}  "
              f"(hypotheses={stats['hypotheses']} evidence={stats['evidence']} verdicts={stats['verdicts']})")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
