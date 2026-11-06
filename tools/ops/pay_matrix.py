#!/usr/bin/env python3
"""Payment test matrix bookkeeping (no requests, no money movement)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = Path("/root/cases")
ROLES = ["anonymous", "user", "merchant", "admin"]
CLASSES = ["create_order", "callback", "query", "refund", "withdraw", "balance"]


def case_dir(name: str) -> Path:
    p = Path(name)
    return p if p.is_absolute() else CASES / name


def load(case: Path) -> dict:
    f = case / "payments.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"endpoints": []}


def main() -> int:
    ap = argparse.ArgumentParser(description="支付面测试矩阵：端点 × 角色 × 测试类")
    ap.add_argument("--case", "-c", help="case name")
    ap.add_argument("--add", help="name:path, e.g. deposit:/api/pay/create")
    ap.add_argument("--role", default="anonymous", choices=ROLES)
    ap.add_argument("--class", dest="klass", default="create_order", choices=CLASSES)
    ap.add_argument("--status", default="untested", choices=["untested", "tested", "blocked"])
    ap.add_argument("--show", action="store_true", help="show matrix")
    args = ap.parse_args()

    if not args.case:
        print("Payment matrix classes:", ", ".join(CLASSES))
        print("roles:", ", ".join(ROLES))
        print("usage: pay_matrix.py --case <case> --add deposit:/api/pay/create --role anonymous")
        return 0

    case = case_dir(args.case)
    case.mkdir(parents=True, exist_ok=True)
    data = load(case)
    if args.add:
        if ":" not in args.add:
            ap.error("--add must be name:path")
        name, path = args.add.split(":", 1)
        data["endpoints"].append({"name": name, "path": path, "role": args.role,
                                  "class": args.klass, "status": args.status})
        (case / "payments.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.show or not args.add:
        print(f"{'endpoint':24} {'role':10} {'class':14} status")
        for e in data["endpoints"]:
            print(f"{e.get('name',''):24} {e.get('role',''):10} {e.get('class',''):14} {e.get('status','')}")
        gaps = [e for e in data["endpoints"] if e.get("status") == "untested"]
        print(f"[pay] endpoints={len(data['endpoints'])} untested={len(gaps)}")
        return 1 if gaps else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
