#!/usr/bin/env python3
"""Absorption provenance audit: card text vs imported assets.

Scans every SKILL.md for pack/source metadata, docs/learning/* asset paths,
and tools/ops/* references. Reports which assets were never imported.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SKILLS = Path("/root/.hermes/skills")
OPS = Path(__file__).resolve().parent
STORE_RE = re.compile(r"(docs/learning/[A-Za-z0-9_./-]+)")
OPS_RE = re.compile(r"tools/ops/([A-Za-z0-9_.-]+\.py)")
SRC_RE = re.compile(r"^溯源（仅标记）：\s*(.+)$", re.M)
PACK_RE = re.compile(r"^pack:\s*(.+)$", re.M)
OWNED_RE = re.compile(r"^owned:\s*(.+)$", re.M)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.M)


def front(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        return text[3:end] if end > 0 else ""
    return ""


def exists_rel(ref: str) -> bool:
    for base in (Path("/root"), Path("/root/TGSEC-Qtzuu"), Path("/root/.hermes")):
        target = base / ref
        if target.exists():
            return True
        # Card text sometimes truncates a module path to `11-`; accept a
        # directory prefix match rather than reporting a false missing asset.
        if ref.rstrip("/").endswith("-") and target.parent.is_dir():
            stem = target.name
            if any(child.name.startswith(stem) for child in target.parent.iterdir()):
                return True
    return False


def scan() -> dict:
    cards = []
    store = Counter()
    ops_missing = Counter()
    ops_sources = defaultdict(set)
    by_pack = Counter()
    by_source = Counter()
    for p in SKILLS.rglob("SKILL.md"):
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        fm = front(text)
        nm = NAME_RE.search(fm) or NAME_RE.search(text)
        name = nm.group(1).strip() if nm else p.parent.name
        pm = PACK_RE.search(fm)
        pack = pm.group(1).strip() if pm else ""
        owned = bool(OWNED_RE.search(fm))
        sm = SRC_RE.search(text)
        src = sm.group(1).strip() if sm else ""
        refs = sorted(set(STORE_RE.findall(text)))
        missing = [r for r in refs if not exists_rel(r)]
        for r in missing:
            store[r] += 1
        op_refs = sorted(set(OPS_RE.findall(text)))
        for op in op_refs:
            if not (OPS / op).exists():
                ops_missing[op] += 1
                ops_sources[op].add(name)
        if pack:
            by_pack[pack] += 1
        if src:
            by_source[src] += 1
        cards.append({
            "name": name, "path": str(p), "pack": pack, "owned": owned,
            "source": src, "store_refs": refs, "store_missing": missing,
            "ops_refs": op_refs,
        })
    return {
        "cards": len(cards),
        "packs": by_pack.most_common(),
        "sources": by_source.most_common(),
        "missing_store_paths": store.most_common(),
        "missing_ops": ops_missing.most_common(),
        "ops_sources": {k: sorted(v) for k, v in ops_sources.items()},
        "cards_detail": cards,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="吸收溯源审计")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", help="写 Markdown 报告路径")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()
    r = scan()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2)[:200000])
    else:
        print(f"cards={r['cards']} packs={len(r['packs'])} sources={len(r['sources'])}")
        print(f"missing_store_paths={len(r['missing_store_paths'])} missing_ops={len(r['missing_ops'])}")
        print("packs:", r["packs"][:10])
        print("sources:", r["sources"][:10])
        print("top missing store:")
        for k, v in r["missing_store_paths"][: args.top]:
            print(f"  {v:4d} {k}")
    if args.write:
        lines = ["# 吸收溯源审计", "", f"- 卡总数：{r['cards']}", f"- pack 数：{len(r['packs'])}",
                 f"- 缺失 `docs/learning/*` 路径：{len(r['missing_store_paths'])}",
                 f"- 仍缺失 `tools/ops` 名：{len(r['missing_ops'])}", "", "## Pack 分布"]
        lines += [f"- `{k}`: {v}" for k, v in r["packs"]]
        lines += ["", "## 溯源来源"]
        lines += [f"- `{k}`: {v}" for k, v in r["sources"]]
        lines += ["", "## 缺失资产路径（Top）"]
        lines += [f"- `{k}`: {v} 张卡引用" for k, v in r["missing_store_paths"][:60]]
        lines += ["", "## 缺失 tools/ops（Top）"]
        for k, v in r["missing_ops"][:60]:
            srcs = ", ".join(r["ops_sources"].get(k, [])[:3])
            lines.append(f"- `{k}`: {v} 张卡；例：{srcs}")
        Path(args.write).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[write] {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
