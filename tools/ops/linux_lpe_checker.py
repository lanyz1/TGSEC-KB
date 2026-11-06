#!/usr/bin/env python3
"""Linux local privilege-escalation checks: identity, sudo, SUID, cron, groups."""
from __future__ import annotations

import argparse
import json
import os
import platform
import pwd
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], timeout: int = 8) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout + p.stderr).strip()
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Linux 提权面检查（只读）")
    ap.add_argument("--local-only", action="store_true")
    ap.add_argument("--cve-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", "-o")
    args = ap.parse_args()
    me = pwd.getpwuid(os.getuid())
    data = {
        "host": platform.node(), "kernel": platform.release(), "distro": "",
        "user": me.pw_name, "uid": os.getuid(), "gid": os.getgid(),
        "groups": [g.gr_name for g in __import__("grp").getgrall() if me.pw_name in g.gr_mem or g.gr_gid == me.pw_gid],
        "sudo_nopasswd": "", "suid": [], "cron": "", "capabilities": "",
        "docker_sock": Path("/var/run/docker.sock").exists(),
    }
    try:
        data["distro"] = Path("/etc/os-release").read_text(errors="ignore").splitlines()[0:4]
    except OSError:
        pass
    if not args.cve_only:
        data["sudo_nopasswd"] = run(["sudo", "-n", "-l"])
        suid = run(["find", "/", "-xdev", "-perm", "-4000", "-type", "f", "-print"], timeout=15)
        data["suid"] = [x for x in suid.splitlines() if x][:300]
        data["cron"] = run(["sh", "-c", "crontab -l 2>/dev/null; ls -la /etc/cron* 2>/dev/null"])
        data["capabilities"] = run(["getcap", "-r", "/usr", "/bin", "/sbin"], timeout=10) if shutil.which("getcap") else "getcap not installed"
    if args.out:
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"user={data['user']} uid={data['uid']} kernel={data['kernel']}")
        print(f"groups={data['groups']} docker_sock={data['docker_sock']}")
        print(f"sudo_nopasswd:\n{data['sudo_nopasswd'][:800]}")
        print(f"suid_count={len(data['suid'])}")
        print("suid_sample:")
        for x in data["suid"][:20]:
            print("  ", x)
        print(f"capabilities:\n{data['capabilities'][:800]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
