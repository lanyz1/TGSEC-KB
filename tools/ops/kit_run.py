#!/usr/bin/env python3
"""Smallest real TGSEC engagement runner.

This is deliberately a thin orchestrator over tools that actually exist on this
host. It does not pretend to implement the 226 historical tools/ops scripts.

Examples:
  python3 tools/ops/kit_run.py check
  python3 tools/ops/kit_run.py list
  python3 tools/ops/kit_run.py run --kit web -u http://127.0.0.1:18080 --case lab --scope 127.0.0.1 --fast
  python3 tools/ops/kit_run.py run --kit recon -d example.com --case eng --scope example.com --dry-run
  python3 tools/ops/kit_run.py report --case lab
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / ".claude/skills/pentest-redteam/scripts/tools"
LEDGER = ROOT / ".claude/skills/pentest-redteam/scripts/case_ledger.py"
WORKSPACE = Path(os.environ.get("TGSEC_CASES", "/root/cases"))
OPS = Path(__file__).resolve().parent
COMMON_WORDLIST = OPS / "wordlists" / "common.txt"

KITS = {
    "web": ["whatweb", "nuclei", "ffuf"],
    "recon": ["subfinder", "nmap", "whatweb"],
}
BINARIES = ["whatweb", "nuclei", "ffuf", "nmap", "subfinder", "sqlmap", "wpscan", "naabu", "katana"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_of(value: str) -> str:
    if "://" not in value:
        value = "http://" + value
    return (urlparse(value).hostname or "").strip().lower().rstrip(".")


def case_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or "/" in name:
        return p
    return WORKSPACE / name


def ensure_case(name: str, target: str, scope_entries: list[str]) -> Path:
    case = case_path(name)
    (case / "artifacts").mkdir(parents=True, exist_ok=True)
    ledger = case / "ledger.jsonl"
    if not ledger.exists():
        ledger.touch()
    scope_file = case / "scope.txt"
    if scope_entries:
        scope_file.write_text("\n".join(scope_entries) + "\n", encoding="utf-8")
    elif not scope_file.exists():
        # Deliberately empty: do not self-authorize the target host.
        scope_file.write_text("", encoding="utf-8")
    if not (case / "metadata.json").exists():
        (case / "metadata.json").write_text(
            json.dumps({"case": case.name, "created_at": now(), "targets": [target]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return case


def scope_ok(case: Path, target: str) -> bool:
    p = subprocess.run(
        [sys.executable, str(OPS / "scope_lint.py"), "--target", target, "--scope-file", str(case / "scope.txt")],
        capture_output=True, text=True,
    )
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    return p.returncode == 0


def run_step(case: Path, name: str, cmd: list[str], timeout: int, dry: bool) -> dict:
    log = case / "artifacts" / f"{name}.log"
    rec = {"name": name, "cmd": cmd, "started": now(), "log": str(log)}
    if dry:
        print("[dry-run]", " ".join(cmd))
        rec.update(returncode=None, dry_run=True, seconds=0)
        return rec
    started = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = p.stdout + p.stderr
        log.write_text(output, encoding="utf-8", errors="replace")
        rec.update(returncode=p.returncode, seconds=round(time.time() - started, 2),
                   tail=output.strip().splitlines()[-5:])
    except subprocess.TimeoutExpired as e:
        out = e.stdout or b""
        err = e.stderr or b""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        output = out + err
        log.write_text(output, encoding="utf-8", errors="replace")
        rec.update(returncode=124, seconds=round(time.time() - started, 2), tail=["TIMEOUT"])
        print(f"[timeout] {name} after {timeout}s", file=sys.stderr)
    except FileNotFoundError:
        rec.update(returncode=127, seconds=0, tail=["MISSING BINARY"])
        print(f"[missing] {name}: {cmd[0]}", file=sys.stderr)
    print(f"[{rec.get('returncode')}] {name} {rec.get('seconds')}s -> {log}")
    if rec.get("tail"):
        print("    " + " | ".join(rec["tail"])[:500])
    return rec


def cmd_web(case: Path, url: str, timeout: int, dry: bool, full: bool) -> list[dict]:
    steps: list[dict] = []
    steps.append(run_step(case, "whatweb", ["whatweb", "--no-errors", "--color=never", url], min(timeout, 60), dry))
    if shutil.which("nuclei"):
        ncmd = ["nuclei", "-u", url, "-ni", "-duc", "-silent", "-nc", "-timeout", "5", "-retries", "0",
                "-t", "http/technologies/tech-detect.yaml"]
        if full:
            ncmd += ["-severity", "critical,high"]
        steps.append(run_step(case, "nuclei", ncmd, timeout, dry))
    else:
        print("[skip] nuclei missing; use tool_get nuclei", file=sys.stderr)
    if COMMON_WORDLIST.exists():
        fcmd = ["ffuf", "-s", "-u", url.rstrip("/") + "/FUZZ", "-w", str(COMMON_WORDLIST),
                "-mc", "200,204,301,302,307,401,403", "-t", "10", "-timeout", "5"]
        steps.append(run_step(case, "ffuf", fcmd, min(timeout, 60), dry))
    else:
        print(f"[skip] wordlist missing: {COMMON_WORDLIST}", file=sys.stderr)
    return steps


def cmd_recon(case: Path, domain: str, timeout: int, dry: bool, full: bool) -> list[dict]:
    steps: list[dict] = []
    if shutil.which("subfinder"):
        steps.append(run_step(case, "subfinder", ["subfinder", "-d", domain, "-silent", "-timeout", "15"], min(timeout, 60), dry))
    if shutil.which("nmap"):
        steps.append(run_step(case, "nmap", ["nmap", "-Pn", "-T4", "--top-ports", "100", "-oN", str(case / "artifacts" / "nmap.txt"), domain], timeout, dry))
    steps.append(run_step(case, "whatweb", ["whatweb", "--no-errors", "--color=never", "http://" + domain], min(timeout, 60), dry))
    return steps


def write_run(case: Path, payload: dict) -> None:
    (case / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Thin TGSEC engagement runner over real local tools")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="show tool/case-ledger availability")
    sub.add_parser("list", help="list kits")

    run = sub.add_parser("run", help="create a case and run a kit")
    run.add_argument("--kit", choices=sorted(KITS), required=True)
    run.add_argument("-u", "--url", help="target URL for web kit")
    run.add_argument("-d", "--domain", help="target domain for recon kit")
    run.add_argument("--case", required=True, help="case name or path")
    run.add_argument("--scope", action="append", default=[], help="scope entry (repeatable; default target host)")
    run.add_argument("--timeout", type=int, default=90, help="per-step timeout seconds")
    run.add_argument("--full", action="store_true", help="include higher-volume checks")
    run.add_argument("--dry-run", action="store_true")

    rep = sub.add_parser("report", help="run case_report.py for a case")
    rep.add_argument("--case", required=True)

    args = ap.parse_args()

    if args.command == "list":
        print("kits:")
        for k, v in KITS.items():
            print(f"  {k:8} {' -> '.join(v)}")
        return 0

    if args.command == "check":
        print("binaries:")
        for b in BINARIES:
            print(f"  {'OK ' if shutil.which(b) else 'MISS'} {b:10} {shutil.which(b) or ''}")
        print(f"  {'OK ' if LEDGER.exists() else 'MISS'} case_ledger {LEDGER}")
        print(f"workspace: {WORKSPACE}")
        return 0

    if args.command == "report":
        p = subprocess.run([sys.executable, str(OPS / "case_report.py"), "--case", args.case])
        return p.returncode

    target = args.url or args.domain
    if not target:
        print("--url or --domain required", file=sys.stderr)
        return 2
    if args.kit == "web" and not args.url:
        print("--kit web requires --url", file=sys.stderr)
        return 2
    if args.kit == "recon" and not args.domain:
        print("--kit recon requires --domain", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"[dry-run] kit={args.kit} target={target} case={case_path(args.case)}")
        # still show the planned commands without creating files
        if args.kit == "web":
            print("[dry-run] whatweb --no-errors --color=never", args.url)
            print("[dry-run] nuclei -u", args.url, "-ni -duc -silent -nc -timeout 5 -retries 0 -t http/technologies/tech-detect.yaml")
            print("[dry-run] ffuf -s -u", args.url.rstrip("/") + "/FUZZ", "-w", str(COMMON_WORDLIST))
        else:
            print("[dry-run] subfinder -d", args.domain, "-silent -timeout 15")
            print("[dry-run] nmap -Pn -T4 --top-ports 100 -oN <case>/artifacts/nmap.txt", args.domain)
            print("[dry-run] whatweb --no-errors --color=never http://" + args.domain)
        return 0

    case = ensure_case(args.case, target, args.scope)
    if not scope_ok(case, target):
        print("[abort] scope gate failed; no active checks sent", file=sys.stderr)
        return 3

    started = now()
    print(f"[case] {case}")
    print(f"[target] {target}  kit={args.kit}  full={args.full}")
    if args.kit == "web":
        steps = cmd_web(case, args.url, args.timeout, False, args.full)
    else:
        steps = cmd_recon(case, args.domain, args.timeout, False, args.full)
    payload = {"case": str(case), "target": target, "kit": args.kit, "started": started,
               "finished": now(), "full": args.full, "steps": steps}
    write_run(case, payload)
    ok = sum(1 for s in steps if s.get("returncode") in (0, None))
    print(f"[done] {ok}/{len(steps)} steps exit 0; run.json written")
    print(f"[next] python3 {OPS/'case_report.py'} --case {case}")
    return 0 if ok == len(steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
