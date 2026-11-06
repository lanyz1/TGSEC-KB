#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventory + digest the Hermes skill library.

Usage: python skill_digest.py [out_dir]
  out_dir defaults to ~/Desktop/skill_learning

Reads every <skills_root>/<category>/<skill>/SKILL.md, extracts frontmatter
(name, description) plus headings and command-bearing lines, and writes:
  <out_dir>/digest.md   — human-readable digest (one section per skill)
  <out_dir>/digest.json — structured data for downstream manual generation
Prints: total skill count, per-category counts, estimated digest size.
"""
import json, re, os, sys
from pathlib import Path
from collections import Counter

SKILLS_ROOT = Path(os.path.expanduser("~/AppData/Local/hermes/profiles/sdsd/skills"))
OUT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/skill_learning"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_frontmatter(text):
    """Return (frontmatter_dict, body_text)."""
    fm = {}
    body = text
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if m:
        raw = m.group(1)
        body = text[m.end():]
        for line in raw.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip().lower()] = v.strip().strip('"\'')
    return fm, body


def extract_key_lines(body, max_lines=40):
    """Headings + code-block snippets + list items containing backticks."""
    out = []
    lines = body.splitlines()
    in_code = False
    code_buf = []
    code_count = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith('```'):
            if in_code:
                for cl in code_buf[:3]:
                    out.append('  ' + cl)
                if len(code_buf) > 3:
                    out.append(f'  ... (+{len(code_buf)-3} 行)')
                code_count += 1
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(s)
            continue
        if s.startswith('#'):
            out.append(s)
        elif (s.startswith('- ') or s.startswith('* ')) and '`' in s:
            out.append(s[:200])
    # de-dup, preserve order
    seen = set()
    dedup = []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup[:max_lines]


skills = []
for skill_md in sorted(SKILLS_ROOT.rglob('SKILL.md')):
    rel = skill_md.relative_to(SKILLS_ROOT)
    parts = list(rel.parts[:-1])
    category = parts[0] if len(parts) > 1 else 'root'
    name = parts[-1] if parts else 'unknown'
    text = skill_md.read_text(encoding='utf-8', errors='replace')
    fm, body = parse_frontmatter(text)
    desc = fm.get('description', '') or ''
    if not desc:
        body_lines = body.splitlines()
        desc = body_lines[1][:200] if len(body_lines) > 1 and body_lines[0].startswith('# ') else (
            body_lines[0][:200] if body_lines else '')
    key_lines = extract_key_lines(body)
    skills.append({
        'name': name,
        'category': category,
        'path': str(skill_md),
        'size': len(text),
        'description': desc[:500],
        'key_lines': key_lines,
    })

cat_count = Counter(s['category'] for s in skills)
print(f"技能总数: {len(skills)}")
print(f"分类数: {len(cat_count)}")
for c, n in sorted(cat_count.items()):
    print(f"  {c}: {n}")
print(f"digest 预估大小: {sum(len(s['description']) + sum(len(l) for l in s['key_lines']) for s in skills)} chars")

with open(OUT_DIR / 'digest.md', 'w', encoding='utf-8') as f:
    f.write(f"# 技能学习 Digest(共 {len(skills)} 个技能)\n\n")
    for s in skills:
        f.write(f"## [{s['category']}] {s['name']}\n\n")
        f.write(f"**描述**: {s['description']}\n\n")
        f.write(f"**路径**: {s['path']} ({s['size']}B)\n\n")
        if s['key_lines']:
            f.write("**要点/命令**:\n")
            for kl in s['key_lines']:
                f.write(f"- {kl}\n")
        f.write("\n---\n\n")

with open(OUT_DIR / 'digest.json', 'w', encoding='utf-8') as f:
    json.dump(skills, f, ensure_ascii=False, indent=1)

print(f"已写入: {OUT_DIR / 'digest.md'}, {OUT_DIR / 'digest.json'}")
