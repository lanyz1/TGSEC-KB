#!/usr/bin/env python3
"""Forward a legacy tools/ops name to the real TGSEC stdlib tool.

This is an adapter, not a reimplementation. The underlying tool's CLI is
unchanged; run `python3 <name> -h` for its real arguments.
"""
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / ".claude/skills/pentest-redteam/scripts/tools"
OPS = Path(__file__).resolve().parent


def run(target_name):
    target = TOOLS / target_name
    if not target.exists():
        # Some compatibility entries point at real scripts in tools/ops itself.
        target = OPS / target_name
    if not target.exists():
        sys.stderr.write(f"[adapter] missing target: {target}\n")
        raise SystemExit(127)
    if target.resolve() == Path(sys.argv[0]).resolve():
        sys.stderr.write(f"[adapter] self-loop refused: {target}\n")
        raise SystemExit(127)
    os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])


def main():
    # Direct symlinks (e.g. tools/ops/jwt_attack.py) forward to the same name.
    name = Path(sys.argv[0]).name
    run(name)


if __name__ == "__main__":
    main()
