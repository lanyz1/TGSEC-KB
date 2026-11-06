#!/usr/bin/env python3
"""Small, lockout-aware auth probe wrapper (hard cap on passwords)."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPRAY = ROOT / ".claude/skills/pentest-redteam/scripts/tools/password_spray.py"


def main() -> int:
    ap = argparse.ArgumentParser(description="认证面小规模探测（默认最多 20 个密码）")
    ap.add_argument("--target", "-t", required=True, help="login URL")
    ap.add_argument("--users", "-U", required=True, help="username file")
    ap.add_argument("--passwords", "-P", required=True, help="password file")
    ap.add_argument("--user-field", default="username")
    ap.add_argument("--pass-field", default="password")
    ap.add_argument("--max-attempts", type=int, default=20, help="hard cap, default 20")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()
    cap = max(1, min(args.max_attempts, 50))
    src = Path(args.passwords)
    if not src.exists():
        ap.error(f"password file not found: {src}")
    words = [x for x in src.read_text(encoding="utf-8", errors="replace").splitlines() if x][:cap]
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        f.write("\n".join(words) + "\n")
        tmp = f.name
    cmd = [sys.executable, str(SPRAY), "-t", args.target, "-U", args.users,
           "-P", tmp, "--user-field", args.user_field, "--pass-field", args.pass_field,
           "--delay", str(args.delay)]
    print(f"[auth] attempts={len(words)} hard_cap={cap} delay={args.delay}s")
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
