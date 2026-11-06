#!/usr/bin/env python3
"""Resolve a skill name to its local card and next executable step."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = Path("/root/.hermes/skills")


def find_card(name: str) -> Path | None:
    exact = list(SKILLS.rglob(f"{name}/SKILL.md"))
    if exact:
        return exact[0]
    hits = [p for p in SKILLS.rglob("SKILL.md") if p.parent.name == name]
    return hits[0] if hits else None


def description(card: Path) -> str:
    text = card.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip('"') if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="实战包路由：技能名 → 本地卡 + 下一步")
    ap.add_argument("--name", "-n", help="技能目录名，如 whitelabel-gambling-pentest")
    ap.add_argument("--hint", help="模糊提示，走 skill_find")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.name and not args.hint:
        ap.error("need --name or --hint")

    if args.name:
        card = find_card(args.name)
        if card:
            data = {"name": args.name, "card": str(card), "description": description(card),
                    "next": f"python3 tools/ops/core_web_surface_probe.py --url <授权URL> --case <案卷>"}
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"[route] {args.name}")
                print(f"card: {card}")
                print(f"description: {data['description']}")
                print(f"next: {data['next']}")
            return 0

    query = args.name or args.hint
    p = subprocess.run(["/usr/local/bin/skill_find", query, "--top", "5"], capture_output=True, text=True)
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
