#!/usr/bin/env python3
"""Local host IR snapshot: identity, listeners, cron, recent logins."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone


def run(cmd: list[str]) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return (p.stdout + p.stderr).strip()
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="本机 IR 快照：身份/监听/计划任务/登录")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "uname": run(["uname", "-a"]),
        "id": run(["id"]),
        "listeners": run(["ss", "-lntup"]),
        "processes": run(["ps", "-eo", "pid,user,comm,args", "--sort=-etime"]).splitlines()[:80],
        "cron": run(["crontab", "-l"]),
        "recent_logins": run(["last", "-n", "15"]),
        "passwd_tail": run(["getent", "passwd"]),
        "env_interesting": sorted(k for k in os.environ if any(x in k.upper() for x in ("TOKEN", "KEY", "SECRET", "PASS"))),
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"uname: {data['uname']}")
        print(f"id: {data['id']}")
        print("listeners:")
        print(data["listeners"][:2000])
        print("cron:")
        print(data["cron"][:1000])
        print(f"env_interesting: {data['env_interesting']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
