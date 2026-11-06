#!/usr/bin/env python3
"""Create real index/state pages for missing docs/learning asset paths.

Only generated inventory pages and pointers to existing skill cards are created.
Missing upstream cards are not invented; they remain listed as missing.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path("/root/TGSEC-Qtzuu/docs/learning")
SKILLS = Path("/root/.hermes/skills")
DB = Path("/root/.hermes/arsenal/arsenal.db")


def counts() -> dict:
    con = sqlite3.connect(DB)
    try:
        total = con.execute("select count(*) from skills").fetchone()[0]
        enabled = con.execute("select count(*) from skills where status='enabled'").fetchone()[0]
        legacy = con.execute("select count(*) from skills where legacy is not null and legacy!=''").fetchone()[0]
    finally:
        con.close()
    return {"total": total, "enabled": enabled, "legacy": legacy}


def card(name: str) -> Path | None:
    for p in SKILLS.rglob("SKILL.md"):
        if p.parent.name == name:
            return p
    return None


def desc(path: Path) -> str:
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return ""
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def write(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    c = counts()
    made = []
    state = ROOT / "skill-store/hermes/sentinel_state.json"
    if write(state, json.dumps({"generated": date.today().isoformat(), **c}, indent=2)):
        made.append(state)

    state_readme = ROOT / "skill-store/hermes/README.md"
    if write(state_readme, "# Hermes sentinel state\n\n"
              "`sentinel_state.json` is generated from `arsenal.db`; it records the "
              "current inventory only, not a full curator ledger.\n\n"
              f"- total: {c['total']}\n- enabled: {c['enabled']}\n- legacy: {c['legacy']}\n"):
        made.append(state_readme)

    readme = ROOT / "README.md"
    dirs = sorted(p.name for p in ROOT.iterdir() if p.is_dir())
    if write(readme, "# Learning assets\n\nGenerated inventory of the local learning tree.\n\n"
              + "\n".join(f"- `{d}/`" for d in dirs) + "\n\n"
              "Missing upstream cards are listed by `resolve_asset_paths.py`; no card text is fabricated.\n"):
        made.append(readme)

    ext = ROOT / "extended-pack"
    ext_cards = sorted(p.parent.name for p in SKILLS.rglob("SKILL.md") if "extended" in str(p).lower())
    if write(ext / "INDEX.md", "# Extended pack index\n\n"
              f"Generated: {date.today().isoformat()}\n\n"
              "This compatibility index points at live skill cards; the original extended-pack "
              "SKILL.md files for missing cards were not present in the local archive.\n\n"
              + "\n".join(f"- `{n}`" for n in ext_cards) + "\n"):
        made.append(ext / "INDEX.md")
    if write(ext / "README.md", "# Extended pack\n\n"
              "The directory is a compatibility layer. See `INDEX.md` and "
              "`../../.hermes/skills` for the live cards. Missing source cards are not faked.\n"):
        made.append(ext / "README.md")
    if write(ext / "IMPORT.json", json.dumps({
        "generated": date.today().isoformat(), "kind": "compatibility-index",
        "live_cards": c["total"], "enabled": c["enabled"],
        "missing_source_cards": ["yudao-tma-pentest", "yudao-web-appapi-pentest",
                                 "tg-account-session-intake", "tg-account-library-ops",
                                 "telegram-gambling-tma-pentest"]}, indent=2)):
        made.append(ext / "IMPORT.json")

    nine = ROOT / "nine-stage"
    if write(nine / "README.md", "# Nine-stage route index\n\n"
              "The original nine-stage stage data was not present. This page routes to the "
              "live cards that implement the stages:\n\n"
              "- `pentest-methodology` — 总控流程\n- `hypothesis-ledger` — 假设账本\n"
              "- `case-review` — 结案复核\n- `recon-for-sec` — 侦察\n- `evidence-gate` — 证据闸\n"):
        made.append(nine / "README.md")
    if write(nine / "GAP.md", "# Nine-stage gap\n\n"
              "- 原始 stage 数据未随仓库导入；\n- 当前只提供路由与现役卡链接；\n"
              "- 不伪造 stage 结果或历史报告。\n"):
        made.append(nine / "GAP.md")
    if write(nine / "stages/README.md", "# Stages\n\nSee `../README.md` for the live-card route.\n"):
        made.append(nine / "stages/README.md")
    if write(ROOT / "kb/stages/README.md", "# KB stages\n\nKnowledge-base stage data is not present locally; "
              "use `../../README.md` and `skill_find` for live material.\n"):
        made.append(ROOT / "kb/stages/README.md")

    hyp = ROOT / "hypothesis-pack"
    if write(hyp / "MAP.md", "# Hypothesis pack map\n\n"
              "- `hypothesis-ledger` — 假设/证据账本\n- `pentest-methodology` — 六门验证闸\n"
              "- `case-review` — 结案复核\n- `black-cat-redteam` — 状态机红队\n"):
        made.append(hyp / "MAP.md")
    if write(hyp / "DISTILL.md", "# Hypothesis pack distill\n\n"
              "This is a route index, not original upstream distill data. Use `skill_find` "
              "with the card names above for full text.\n"):
        made.append(hyp / "DISTILL.md")
    for fname, card_name in [("social-engineering.md", "autonomous-social-engagement"),
                             ("auth-modern.md", "auth-sec")]:
        src = card(card_name)
        if src:
            text = src.read_text(errors="ignore")
            text = re.sub(r"^---.*?\n---\n", "", text, count=1, flags=re.S)
            write(hyp / "techniques" / fname,
                  f"# {fname[:-3]}\n\nSource: `{src}`\n\n" + text[:12000])
            made.append(hyp / "techniques" / fname)

    shizhan = ROOT / "shizhan-pack"
    if write(shizhan / "MAP.md", "# Shizhan pack map\n\n"
              "- `shizhan-pack-router` — 实战包路由\n- `attack-chain` — 成套杀伤链\n"
              "- `security-archive-index` — 归档索引\n"):
        made.append(shizhan / "MAP.md")

    css = ROOT / "cybersecurity-skills"
    for module in ["11-无线安全-WirelessSecurity", "19-工控安全-ICS-OT-Security",
                   "21-物联网安全-IoT-Security", "30-数字取证-DigitalForensics"]:
        d = css / module
        if not d.is_dir():
            continue
        rows = []
        for f in sorted((d / "skills").glob("*.md")):
            rows.append(f"- [{f.stem}](skills/{f.name})")
        write(d / "MODULE.md", f"# {module}\n\nGenerated module index.\n\n" + "\n".join(rows) + "\n")
        made.append(d / "MODULE.md")

    sec = ROOT / "SecAtlas/references/payment-callback-discovery.md"
    src = card("payment-callback-forgery")
    if src:
        text = re.sub(r"^---.*?\n---\n", "", src.read_text(errors="ignore"), count=1, flags=re.S)
        write(sec, f"# Payment callback discovery\n\nSource: `{src}`\n\n" + text[:12000])
        made.append(sec)

    print(f"created={len(made)}")
    for p in made:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
