#!/usr/bin/env python3
"""Consolidate missing docs/playbooks refs from live skill cards.

Creates a real playbook page for each referenced-but-missing path. Content is
copied excerpts from the cards that reference it, with source links; no new
attack semantics are invented and existing files are never overwritten.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import date
from pathlib import Path

DB = Path("/root/.hermes/arsenal/arsenal.db")
SKILLS = Path("/root/.hermes/skills")
OUT = Path("/root/TGSEC-Qtzuu/docs/playbooks")
PLACEHOLDERS = {"*.md", "<组件>手法.md", "CVE日报-YYYY-MM-DD.md"}


def active_files() -> list[Path]:
    con = sqlite3.connect(DB)
    try:
        cards = [Path(r[0]) for r in con.execute("select path from skills where status='enabled'")]
    finally:
        con.close()
    files: list[Path] = []
    for card in cards:
        files.append(card)
        ref = card.parent / "references"
        if ref.is_dir():
            files.extend(ref.glob("*.md"))
    return files


def strip_front(text: str) -> tuple[str, str]:
    title = ""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            m = re.search(r"^name:\s*(.+)$", fm, re.M)
            if m:
                title = m.group(1).strip().strip("\"'")
            body = text[end + 4 :]
    return title, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-sources", type=int, default=6)
    ap.add_argument("--max-chars", type=int, default=4500)
    args = ap.parse_args()

    refs: dict[str, set[Path]] = {}
    for f in active_files():
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        for name in re.findall(r"docs/playbooks/([^\s`'\"）)]+\.md)", text):
            if name in PLACEHOLDERS:
                continue
            refs.setdefault(name, set()).add(f)

    missing = [n for n in refs if not (OUT / n).exists()]
    print(f"refs={len(refs)} missing={len(missing)} apply={args.apply}")
    made = 0
    for name in sorted(missing):
        sources = sorted(refs[name], key=lambda p: (len(p.parts), str(p)))
        chunks = []
        for src in sources[: args.max_sources]:
            try:
                text = src.read_text(errors="ignore")
            except OSError:
                continue
            title, body = strip_front(text)
            body = body.strip()
            if len(body) > args.max_chars:
                body = body[: args.max_chars].rstrip() + "\n\n…（截断，全文见来源卡）"
            if not body:
                continue
            chunks.append(f"### {title or src.parent.name}\n\n来源：`{src}`\n\n{body}")
        if not chunks:
            continue
        content = (
            f"---\ntitle: \"{name}\"\ngenerated: {date.today().isoformat()}\n"
            "kind: consolidated-playbook\n"
            "note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤\n---\n\n"
            f"# {name}\n\n"
            "> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；"
            "不要把它当成独立的新打法。\n\n"
            "## 来源卡\n\n"
            + "\n".join(f"- `{p}`" for p in sources[: args.max_sources])
            + "\n\n## 汇总内容\n\n"
            + "\n\n".join(chunks)
            + "\n"
        )
        if args.apply:
            path = OUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        made += 1
    if args.apply:
        idx = OUT / "INDEX.md"
        lines = [f"# Playbooks index", "",
                 f"Generated: {date.today().isoformat()}",
                 f"Consolidated: {made} missing references", "",
                 "These pages are generated from live skill cards; source paths are on each page.", ""]
        for name in sorted(refs):
            lines.append(f"- [{name}]({name})")
        idx.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"would_write={made}" if not args.apply else f"written={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
