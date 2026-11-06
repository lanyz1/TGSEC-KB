#!/usr/bin/env python3
"""Case facts: print ledger-backed facts and evidence pointers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="案卷事实抽取")
    ap.add_argument("--case", "-c", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
    ledger = case / "ledger.jsonl"
    if not ledger.exists():
        ap.error(f"ledger not found: {ledger}")
    rows = []
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    facts = []
    for r in rows:
        if r.get("type") == "evidence":
            facts.append({"kind": "evidence", "id": r.get("id"), "hypothesis": r.get("hypothesis"),
                          "evidence_type": r.get("evidence_type"), "path": r.get("path") or r.get("artifact")})
        elif r.get("type") == "verdict":
            facts.append({"kind": "verdict", "hypothesis": r.get("hypothesis"),
                          "status": r.get("status"), "reason": r.get("reason", "")})
    if args.json:
        print(json.dumps(facts, ensure_ascii=False, indent=2))
    else:
        for f in facts:
            print(json.dumps(f, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
