#!/usr/bin/env python3
"""Read-only plan menu + thin run wrapper for the local kit runner."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

OPS = Path(__file__).resolve().parent
KIT = OPS / "kit_run.py"


def slug(value: str) -> str:
    return value.replace("://", "_").replace("/", "_").replace(":", "_").strip("_")


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan or run the minimal TGSEC web/recon pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="print a plan without sending requests")
    plan.add_argument("-d", "--domain", required=True)
    plan.add_argument("--admin", help="known admin URL (informational)")
    plan.add_argument("--case")

    run = sub.add_parser("run", help="run the local kit runner")
    run.add_argument("-d", "--domain", required=True)
    run.add_argument("--phases", default="0,1", help="0=recon, 1=web (default 0,1)")
    run.add_argument("--case")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--scope", action="append", default=[])
    run.add_argument("--timeout", type=int, default=90)

    args = ap.parse_args()
    domain = args.domain.strip().lower().rstrip(".")
    case = args.case or f"auto_{slug(domain)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    base = f"https://{domain}"

    if args.cmd == "plan":
        print(f"target: {domain}")
        print(f"case:   {case}")
        print("mode:   read-only plan (no requests sent)")
        print("\nPhase 0 — recon (passive/light):")
        print(f"  subfinder -d {domain} -silent -timeout 15")
        print(f"  nmap -Pn -T4 --top-ports 100 -oN <case>/artifacts/nmap.txt {domain}")
        print(f"  whatweb --no-errors --color=never http://{domain}")
        print("\nPhase 1 — web surface (scope-gated):")
        print(f"  whatweb --no-errors --color=never {base}")
        print(f"  nuclei -u {base} -ni -duc -silent -nc -timeout 5 -retries 0 -t http/technologies/tech-detect.yaml")
        print(f"  ffuf -s -u {base}/FUZZ -w tools/ops/wordlists/common.txt -mc 200,204,301,302,307,401,403")
        print("\nPhase 2 — manual, pick from skill/vuln library: SQLi/IDOR/auth/file/AD/cloud.")
        if args.admin:
            print(f"known admin: {args.admin} (pass to manual testing, not auto-probed)")
        print("\nCommands:")
        print(f"  python3 {KIT} run --kit recon -d {domain} --case {case}")
        print(f"  python3 {KIT} run --kit web -u {base} --case {case}")
        print(f"  python3 {OPS/'case_report.py'} --case {case}")
        return 0

    phases = {p.strip() for p in args.phases.split(",") if p.strip()}
    if not phases or not phases.issubset({"0", "1"}):
        print("supported --phases: 0 and/or 1", file=sys.stderr)
        return 2
    commands = []
    if "0" in phases:
        commands.append([sys.executable, str(KIT), "run", "--kit", "recon", "-d", domain, "--case", case,
                         "--timeout", str(args.timeout), *sum((["--scope", x] for x in args.scope), [])])
    if "1" in phases:
        commands.append([sys.executable, str(KIT), "run", "--kit", "web", "-u", base, "--case", case,
                         "--timeout", str(args.timeout), *sum((["--scope", x] for x in args.scope), [])])
    for cmd in commands:
        print("[exec]", " ".join(cmd))
        if args.dry_run:
            continue
        p = subprocess.run(cmd)
        if p.returncode != 0:
            print(f"[stop] phase exited {p.returncode}", file=sys.stderr)
            return p.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
