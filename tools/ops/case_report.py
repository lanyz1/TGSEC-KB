#!/usr/bin/env python3
"""Generate a Markdown case report from case_ledger.jsonl + artifacts.

The ledger remains the source of truth. This tool refuses to render unless
`case_ledger.py verify --report` passes, unless --force is explicit.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _case_gate import check as semantic_check

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".claude/skills/pentest-redteam/scripts/case_ledger.py"


def case_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or "/" in name:
        return p
    return Path("/root/cases") / name


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"type": "corrupt", "raw": line})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a case report from the ledger")
    ap.add_argument("--case", required=True)
    ap.add_argument("--force", action="store_true", help="render even if the ledger gate fails")
    ap.add_argument("--json", action="store_true", help="print machine-readable summary")
    args = ap.parse_args()

    case = case_path(args.case)
    ledger = case / "ledger.jsonl"
    if not ledger.exists():
        print(f"[report] missing ledger: {ledger}", file=sys.stderr)
        return 2

    gate = subprocess.run([sys.executable, str(LEDGER), "verify", "--report", str(case)],
                          capture_output=True, text=True)
    gate_out = (gate.stdout + gate.stderr).strip()
    sem_ok, sem_errors, stats = semantic_check(case)
    effective_gate = gate.returncode == 0 and sem_ok
    if not effective_gate:
        print(gate_out, file=sys.stderr)
        if not sem_ok:
            print("[report] semantic gate errors:", file=sys.stderr)
            for e in sem_errors:
                print("  -", e, file=sys.stderr)
        if not args.force:
            stale = case / "REPORT.md"
            if stale.exists():
                stale.unlink()
                print(f"[report] removed stale {stale}", file=sys.stderr)
            print("[report] gate failed; rerun with --force only for a draft", file=sys.stderr)
            return 2
        print("[report] WARNING: rendering with a failed gate (--force)", file=sys.stderr)
    else:
        print(gate_out)

    rows = read_jsonl(ledger)
    hyps: dict[str, dict] = {}
    evs: dict[str, dict] = {}
    verdicts: dict[str, dict] = {}
    for r in rows:
        t = r.get("type")
        if t == "hypothesis":
            hyps[r.get("id", "?")] = r
        elif t == "evidence":
            evs[r.get("id", "?")] = r
        elif t == "verdict":
            verdicts[r.get("hypothesis", "?")] = r

    scope = ""
    sf = case / "scope.txt"
    if sf.exists():
        scope = sf.read_text(encoding="utf-8", errors="replace").strip()
    run = {}
    rp = case / "run.json"
    if rp.exists():
        try:
            run = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            run = {}

    lines: list[str] = []
    lines.append(f"# Case report — {case.name}")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ")
    lines.append(f"Case path: `{case}`  ")
    lines.append(f"Ledger gate: **{'PASS' if effective_gate else 'FAIL'}**")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("```")
    lines.append(scope or "(no scope.txt)")
    lines.append("```")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    confirmed = sum(1 for v in verdicts.values() if v.get("status") == "confirmed")
    lines.append(f"- Hypotheses: {len(hyps)}")
    lines.append(f"- Evidence records: {len(evs)}")
    lines.append(f"- Verdicts: {len(verdicts)} (confirmed: {confirmed})")
    by_status: dict[str, int] = {}
    for v in verdicts.values():
        by_status[str(v.get("status"))] = by_status.get(str(v.get("status")), 0) + 1
    lines.append(f"- Verdict status: {by_status or '{}'}")
    lines.append("")

    lines.append("## Hypotheses and evidence")
    lines.append("")
    if not hyps:
        lines.append("(no hypotheses recorded)")
        lines.append("")
    for hid, h in hyps.items():
        lines.append(f"### {hid} — {h.get('claim', '(no claim)')}")
        lines.append("")
        lines.append(f"- Scope: `{h.get('scope', '')}`")
        lines.append(f"- Disprove if: {h.get('disprove_if', '')}")
        v = verdicts.get(hid)
        lines.append(f"- Verdict: **{v.get('status', 'none') if v else 'none'}**")
        if v:
            lines.append(f"- Reason: {v.get('reason', '')}")
        lines.append("")
        related = [e for e in evs.values() if e.get("hypothesis") == hid]
        if related:
            lines.append("| Evidence | Role | Effect | Summary | Artifact |")
            lines.append("|---|---|---|---|---|")
            for e in related:
                art = e.get("artifact", "")
                sha = str(e.get("sha256", ""))[:12]
                lines.append(f"| {e.get('id')} | {e.get('role')} | {e.get('effect')} | {e.get('summary', '')} | `{art}` {sha} |")
        else:
            lines.append("(no evidence)")
        lines.append("")

    lines.append("## Tool runs")
    lines.append("")
    if run.get("steps"):
        lines.append(f"Kit: `{run.get('kit')}`  Target: `{run.get('target')}`  Full: `{run.get('full')}`")
        lines.append("")
        for s in run["steps"]:
            lines.append(f"- `{s.get('name')}` rc={s.get('returncode')} {s.get('seconds')}s log=`{s.get('log')}`")
    else:
        lines.append("(no run.json; manual case)")
    lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    ad = case / "artifacts"
    if ad.exists():
        for p in sorted(ad.rglob("*")):
            if p.is_file():
                lines.append(f"- `{p.relative_to(case)}` — {p.stat().st_size} bytes")
    else:
        lines.append("(no artifacts directory)")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This report is generated from `ledger.jsonl`; do not hand-edit it.")
    lines.append("- A `confirmed` verdict requires observation + impact + reproduction evidence.")
    lines.append("- Scanner output is an observation, not proof of exploitability by itself.")
    lines.append("")

    out = case / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] {out}")
    if args.json:
        print(json.dumps({"case": str(case), "report": str(out), "gate": effective_gate,
                          "hypotheses": len(hyps), "evidence": len(evs), "verdicts": len(verdicts),
                          "confirmed": confirmed}, ensure_ascii=False))
    return 0 if (effective_gate or args.force) else 2


if __name__ == "__main__":
    raise SystemExit(main())
