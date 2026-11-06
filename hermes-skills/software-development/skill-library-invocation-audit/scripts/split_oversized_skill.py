#!/usr/bin/env python3
"""Split an oversized SKILL.md into references/ parts by H2 blocks, with verification.

Usage:
  python3 split_oversized_skill.py <skill_dir> [--max-part-kb 80] [--keep-blocks 4]
                                     [--original PATH] [--dry-run]

Safety rules (learned the hard way):
  * --max-part-kb is a legacy name: the value is a CHARACTER budget, not bytes
    (Chinese text ≈3 bytes/char). Default 12 = ~12K chars per part.
  * Refuses to run when references/part-*.md already exists, unless --original is
    supplied: re-splitting an already-split SKILL.md silently drops the blocks that
    were moved on the first pass.
  * Copies the source SKILL.md to /tmp/<skill>_SKILL.orig.md before writing.
  * Verifies every original H2 block appears exactly once across the new SKILL.md
    plus reference files (Counter equality, whitespace-normalized).
  * Restores SKILL.md and removes newly written parts if verification fails.
"""

import argparse
import collections
import re
import shutil
import sys
from pathlib import Path

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return "", text
    return text[: m.end()], text[m.end() :]


def split_blocks(body: str):
    """Return (preamble, [h2 blocks]) preserving exact text."""
    lines = body.split("\n")
    idx = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not idx:
        return body, []
    preamble = "\n".join(lines[: idx[0]])
    blocks = []
    for n, start in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        blocks.append("\n".join(lines[start:end]))
    return preamble, blocks


def norm_block(block: str) -> str:
    return "\n".join(line.rstrip() for line in block.strip("\n").splitlines())


def slugify(title: str) -> str:
    s = title.lstrip("# ").strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s).strip("-")
    return (s or "section")[:60].strip("-")


def block_title(block: str) -> str:
    return block.splitlines()[0].lstrip("# ").strip()


def counter_for(parts):
    c = collections.Counter()
    for text in parts:
        _, blocks = split_blocks(text)
        for b in blocks:
            c[norm_block(b)] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir")
    ap.add_argument("--max-part-kb", type=int, default=12,
                    help="packing budget in CHARACTERS (legacy name); 12 = ~12K chars, Chinese ≈36KB bytes")
    ap.add_argument("--keep-blocks", type=int, default=4,
                    help="number of leading H2 blocks to keep in SKILL.md")
    ap.add_argument("--original", help="original SKILL.md to use (required if already split)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"ERROR: {skill_md} not found", file=sys.stderr)
        return 2

    refs_dir = skill_dir / "references"
    existing = sorted(refs_dir.glob("part-*.md")) if refs_dir.exists() else []
    source = Path(args.original).resolve() if args.original else skill_md
    if existing and not args.original:
        print(
            "REFUSED: references/part-*.md already exists.\n"
            "Re-splitting a split SKILL.md loses blocks moved on the first pass.\n"
            "Restore the original SKILL.md (e.g. from a tar backup) and pass --original PATH.",
            file=sys.stderr,
        )
        return 3

    original_text = source.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(original_text)
    preamble, blocks = split_blocks(body)
    if not blocks:
        print("ERROR: no H2 blocks to split", file=sys.stderr)
        return 2

    keep_n = max(0, min(args.keep_blocks, len(blocks)))
    keep = blocks[:keep_n]
    moved = blocks[keep_n:]
    if not moved:
        print("Nothing to move: every H2 block is kept in SKILL.md.")
        return 0

    max_chars = args.max_part_kb * 1024
    parts = []  # list[list[str]]
    cur, cur_len = [], 0
    for b in moved:
        if cur and cur_len + len(b) > max_chars:
            parts.append(cur)
            cur, cur_len = [], 0
        cur.append(b)
        cur_len += len(b)
    if cur:
        parts.append(cur)

    backup = Path("/tmp") / f"{skill_dir.name}_SKILL.orig.md"
    backup.write_text(original_text, encoding="utf-8")

    new_skill = fm + preamble.rstrip("\n") + "\n\n" + "\n\n".join(keep)
    index_lines = ["\n## 分册索引（按需加载，不要一次全读）\n"]
    new_parts = []
    for n, group in enumerate(parts, 1):
        name = f"part-{n:02d}-{slugify(block_title(group[0]))}.md"
        content = "\n\n".join(group) + "\n"
        new_parts.append((refs_dir / name, content))
        for b in group:
            kb = max(1, round(len(b.encode("utf-8")) / 1024))
            index_lines.append(f"- [{block_title(b)}](references/{name}) — {kb} KB")
    new_skill = new_skill.rstrip("\n") + "\n" + "\n".join(index_lines) + "\n"

    # Verify against the original blocks before touching anything.
    want = collections.Counter(norm_block(b) for b in blocks)
    got = counter_for([new_skill] + [c for _, c in new_parts])
    # The synthesized index heading is an extra H2 block; drop it.
    index_norm = norm_block("## 分册索引（按需加载，不要一次全读）")
    got[index_norm] -= 1
    if got[index_norm] <= 0:
        got.pop(index_norm, None)
    missing = want - got
    extra = got - want
    if missing or extra:
        print(f"VERIFY FAILED: missing={sum(missing.values())} extra={sum(extra.values())}")
        for k in list(missing)[:3]:
            print("MISSING:", k.splitlines()[0][:100])
        for k in list(extra)[:3]:
            print("EXTRA:", k.splitlines()[0][:100])
        return 4

    print(f"source: {source} ({len(original_text.encode('utf-8'))/1024:.0f} KB)")
    print(f"SKILL.md: {len(new_skill.encode('utf-8'))/1024:.0f} KB, keep {len(keep)} blocks")
    print(f"parts: {len(new_parts)} -> {', '.join(p.name for p, _ in new_parts)}")
    print("verify: missing=0 extra=0")
    if args.dry_run:
        print("dry-run: no files written")
        return 0

    try:
        refs_dir.mkdir(exist_ok=True)
        written = []
        for path, content in new_parts:
            path.write_text(content, encoding="utf-8")
            written.append(path)
        skill_md.write_text(new_skill, encoding="utf-8")
        for path in existing:
            if path not in [p for p, _ in new_parts]:
                path.unlink()
        print(f"backup of original: {backup}")
    except Exception:
        skill_md.write_text(original_text, encoding="utf-8")
        for path in written:
            if path.exists():
                path.unlink()
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
