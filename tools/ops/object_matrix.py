#!/usr/bin/env python3
"""Minimum object × role authorization matrix bookkeeping.

Not a scanner. It records which object access was tested so a case cannot
silently claim "IDOR checked" while leaving most roles untested.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ROLES = ["anonymous", "user", "admin"]
VALID = {"tested", "blocked", "untested"}


def case_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or "/" in name:
        return p
    return Path("/root/cases") / name


def load(case: Path) -> dict:
    p = case / "objects.json"
    if not p.exists():
        return {"roles": DEFAULT_ROLES, "objects": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def save(case: Path, data: dict) -> None:
    (case / "objects.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Object × role matrix for BOLA/IDOR coverage")
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init")
    init.add_argument("--case", required=True)
    init.add_argument("--roles", nargs="+", default=DEFAULT_ROLES)

    add = sub.add_parser("add")
    add.add_argument("--case", required=True)
    add.add_argument("--object", required=True)
    add.add_argument("--role", required=True)
    add.add_argument("--status", choices=sorted(VALID), default="tested")
    add.add_argument("--note", default="")

    check = sub.add_parser("check")
    check.add_argument("--case", required=True)
    check.add_argument("--json", action="store_true")
    check.add_argument("--allow-empty", action="store_true")

    args = ap.parse_args()
    case = case_path(args.case)
    if args.cmd == "init":
        case.mkdir(parents=True, exist_ok=True)
        data = {"roles": args.roles, "objects": {}}
        save(case, data)
        print(f"[matrix] {case/'objects.json'} roles={args.roles}")
        return 0

    data = load(case)
    if args.cmd == "add":
        if args.role not in data["roles"]:
            print(f"[matrix] unknown role {args.role}; roles={data['roles']}", file=sys.stderr)
            return 2
        obj = data["objects"].setdefault(args.object, {})
        obj[args.role] = {"status": args.status, "note": args.note}
        save(case, data)
        print(f"[matrix] {args.object} × {args.role} = {args.status}")
        return 0

    # check
    roles = data.get("roles", DEFAULT_ROLES)
    objects = data.get("objects", {})
    gaps = []
    for obj, per_role in objects.items():
        for role in roles:
            status = per_role.get(role, {}).get("status", "untested")
            if status not in ("tested", "blocked"):
                gaps.append(f"{obj}×{role}")
    if not objects and not args.allow_empty:
        gaps.append("(no objects registered)")
    if args.json:
        print(json.dumps({"case": str(case), "roles": roles, "objects": objects,
                          "gaps": gaps, "ok": not gaps}, ensure_ascii=False, indent=2))
    else:
        print(f"case: {case}")
        print(f"roles: {', '.join(roles)}")
        if not objects:
            print("objects: (none)")
        for obj, per_role in objects.items():
            cells = [f"{r}={per_role.get(r, {}).get('status', 'untested')}" for r in roles]
            print(f"  {obj}: " + "  ".join(cells))
        print(f"gaps: {len(gaps)}")
        for g in gaps:
            print("  -", g)
    return 0 if not gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
