#!/usr/bin/env python3
"""Compat entry: tools/ops/case_ledger.py -> real case_ledger.py."""
import os
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / ".claude/skills/pentest-redteam/scripts/case_ledger.py"
if not target.exists():
    sys.stderr.write(f"[compat] missing: {target}\n")
    raise SystemExit(127)
os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
