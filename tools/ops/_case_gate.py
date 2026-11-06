#!/usr/bin/env python3
"""Semantic evidence gate on top of case_ledger.py's structural verify.

The ledger's own verify checks record integrity. This adds the engagement
rule: every hypothesis needs a verdict, and a confirmed verdict needs the
observation + impact + reproduction evidence triangle with real artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REQUIRED_CONFIRMED_ROLES = {"observation", "impact", "reproduction"}


def read_rows(case: Path) -> tuple[list[dict], list[str]]:
    ledger = case / "ledger.jsonl"
    rows: list[dict] = []
    errors: list[str] = []
    if not ledger.exists():
        return rows, [f"missing ledger: {ledger}"]
    for i, line in enumerate(ledger.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON: {e}")
    return rows, errors


def check(case: Path, require_all_verdicts: bool = True) -> tuple[bool, list[str], dict]:
    rows, errors = read_rows(case)
    hyps: dict[str, dict] = {}
    evs: dict[str, dict] = {}
    verdicts: dict[str, dict] = {}
    for r in rows:
        if r.get("type") == "hypothesis":
            hyps[str(r.get("id"))] = r
        elif r.get("type") == "evidence":
            evs[str(r.get("id"))] = r
        elif r.get("type") == "verdict":
            verdicts[str(r.get("hypothesis"))] = r

    if not hyps:
        errors.append("no hypotheses recorded")
    if require_all_verdicts:
        for hid in hyps:
            if hid not in verdicts:
                errors.append(f"{hid}: no verdict")

    for hid, v in verdicts.items():
        if v.get("status") != "confirmed":
            continue
        cited = [str(x) for x in v.get("evidence", [])]
        roles = {evs[x].get("role") for x in cited if x in evs}
        missing = REQUIRED_CONFIRMED_ROLES - roles
        if missing:
            errors.append(f"{hid}: confirmed verdict missing roles: {', '.join(sorted(missing))}")
        for eid in cited:
            if eid not in evs:
                errors.append(f"{hid}: verdict cites missing evidence {eid}")

    # artifact integrity for every evidence record
    for eid, e in evs.items():
        art = e.get("artifact")
        if not art:
            errors.append(f"{eid}: no artifact")
            continue
        p = (case / art).resolve()
        try:
            p.relative_to(case.resolve())
        except ValueError:
            errors.append(f"{eid}: artifact escapes case dir: {art}")
            continue
        if not p.exists() or not p.is_file():
            errors.append(f"{eid}: artifact missing: {art}")
            continue
        want = str(e.get("sha256", ""))
        if want:
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != want:
                errors.append(f"{eid}: artifact sha256 mismatch: {art}")

    stats = {"hypotheses": len(hyps), "evidence": len(evs), "verdicts": len(verdicts),
             "confirmed": sum(1 for v in verdicts.values() if v.get("status") == "confirmed"),
             "errors": len(errors)}
    return (not errors), errors, stats
