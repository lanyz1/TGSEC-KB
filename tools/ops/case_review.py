#!/usr/bin/env python3
"""Read-only case review: semantic gate + report presence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ops"))
from _case_gate import check  # noqa: E402

CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="案卷只读复核")
    ap.add_argument("--case", "-c", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
    ok, errors, stats = check(case)
    result = {"case": str(case), "ok": ok, "stats": stats, "errors": errors,
              "report": (case / "REPORT.md").exists()}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"case={case} ok={ok} stats={stats} report={result['report']}")
        for e in errors:
            print("  -", e)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
