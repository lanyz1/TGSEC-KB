#!/usr/bin/env python3
"""Split oversized SKILL.md files into a small main card + references/.

The operation is content-preserving: every H2 section is moved verbatim into
`references/split-NN-<slug>.md`, and the main card keeps its frontmatter,
intro, and a section index.  Originals are copied to
`/root/.hermes/skill-backups/20261021-oversized/` before any write.

Usage:
  python3 tools/ops/split_oversized_cards.py                 # dry run
  python3 tools/ops/split_oversized_cards.py --apply
  python3 tools/ops/split_oversized_cards.py --apply --limit 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

SKILLS = Path("/root/.hermes/skills")
BACKUP = Path("/root/.hermes/skill-backups/20261021-oversized")
REPORT = Path("/root/.hermes/arsenal/oversized-split-20261021.json")
MARK = "<!-- split-index -->"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[: i + 1]), "".join(lines[i + 1 :])
    return "", text


def split_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    lines = body.splitlines(keepends=True)
    starts: list[int] = []
    in_fence = False
    fence = ""
    for i, line in enumerate(lines):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            marker = s[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence, fence = False, ""
            continue
        if not in_fence and line.startswith("## "):
            starts.append(i)
    if not starts:
        return body, []
    intro = "".join(lines[: starts[0]])
    sections: list[tuple[str, str]] = []
    for n, a in enumerate(starts):
        b = starts[n + 1] if n + 1 < len(starts) else len(lines)
        title = lines[a][3:].strip().rstrip("#").strip()
        sections.append((title, "".join(lines[a:b])))
    return intro, sections


def slug(title: str, n: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:40]
    return f"split-{n:02d}-{s or 'section'}"


def process(card: Path, apply: bool, min_bytes: int) -> dict | None:
    text = card.read_text(encoding="utf-8", errors="replace")
    if len(text.encode("utf-8")) <= min_bytes or MARK in text:
        return None
    fm, body = split_frontmatter(text)
    intro, sections = split_sections(body)
    if len(sections) < 2:
        return None
    base = card.parent / "references"
    plan = []
    for n, (title, section) in enumerate(sections, 1):
        name = slug(title, n) + ".md"
        dest = base / name
        if dest.exists():
            name = f"split-{n:02d}-{n}.md"
            dest = base / name
        plan.append({"title": title, "name": name, "section": section, "hash": sha(section)})
    index = [MARK, "", "## Section index", ""]
    for item in plan:
        index.append(f"- [{item['title']}](references/{item['name']})")
    main = fm + intro.rstrip() + "\n\n" + "\n".join(index) + "\n"
    result = {
        "card": str(card),
        "before": len(text.encode("utf-8")),
        "after": len(main.encode("utf-8")),
        "sections": [{"title": p["title"], "name": p["name"], "hash": p["hash"]} for p in plan],
        "applied": apply,
    }
    if not apply:
        return result
    rel = card.relative_to(SKILLS)
    backup = BACKUP / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(card, backup)
    base.mkdir(parents=True, exist_ok=True)
    for item in plan:
        (base / item["name"]).write_text(item["section"], encoding="utf-8")
    card.write_text(main, encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="split oversized SKILL.md into references/")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-bytes", type=int, default=30000)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    cards = sorted(SKILLS.rglob("SKILL.md"), key=lambda p: -p.stat().st_size)
    results = []
    for card in cards:
        if args.limit and len(results) >= args.limit:
            break
        if card.stat().st_size <= args.min_bytes:
            continue
        r = process(card, args.apply, args.min_bytes)
        if r:
            results.append(r)
    if args.apply:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if REPORT.exists():
            try:
                existing = json.loads(REPORT.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        by_card = {r["card"]: r for r in existing if isinstance(r, dict) and "card" in r}
        for r in results:
            by_card[r["card"]] = r
        REPORT.write_text(json.dumps(list(by_card.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"matched={len(results)} apply={args.apply}")
    for r in results[:20]:
        print(f"  {r['before']:7d} -> {r['after']:6d}  {Path(r['card']).parent.name}  sections={len(r['sections'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
