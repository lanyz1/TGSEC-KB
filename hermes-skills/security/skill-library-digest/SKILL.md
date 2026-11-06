---
name: skill-library-digest
description: >-
  测绘引擎·Use when user asks to learn all installed skills.
owned: true
tier: ops
pack: survey-skill
---

# skill-library-digest（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/skill-library-digest/`

溯源（仅标记）：`hermes/software-development`

---

# Skill Library Digest (技能库学习手册)

## When to Use
- User asks "帮我学习这101个技能" / "学习所有技能" / "整理技能列表" / "生成技能学习手册" — i.e. wants to understand the full local skill library.
- Regenerating the manual after new skills are installed.
- Auditing what's installed (count, categories, sizes).

## Key Facts (this machine, profile sdsd)
- Skills root: `~/AppData/Local/hermes/profiles/sdsd/skills` — one `<category>/<skill-name>/SKILL.md` per skill.
- As of 2026-07-31: 16 categories, **94 SKILL.md files** (~1.27MB total). User says "101" but the measured count is 94 — always report the measured count, never parrot the user's estimate.
- `yuanbao` sits directly at the skills root (its category resolves to "root").
- Existing deliverables live in `~/Desktop/skill_learning/`: `digest.md`, `digest.json`, `技能学习手册.md`, `extract.py`, `generate_manual.py`.
- The 94 skills are managed/bundled/user-owned — do NOT edit them. The digest/manual are separate artifacts you own.

## Workflow
1. **Inventory** — use terminal `find`, NOT search_files:
   ```
   cd ~/AppData/Local/hermes/profiles/sdsd/skills && find . -name 'SKILL.md' | wc -l
   ```
   (search_files(target='files', pattern='SKILL.md', path='...') returned 0 for this path even though the files exist — find is the reliable method here.)
2. **Extract** — run `scripts/skill_digest.py [out_dir]` (defaults to `~/Desktop/skill_learning`). It parses every SKILL.md: frontmatter (name, description) + headings + command-bearing lines → writes `digest.md` + `digest.json`, prints count/categories/size stats.
3. **Read** the digest in chunks (`read_file` with offset, ~1100-line chunks; 4241 lines ≈ 3 passes). Actually read it — manual quality depends on understanding the content, not just parsing it.
4. **Generate manual** — `~/Desktop/skill_learning/generate_manual.py` produces `技能学习手册.md`: overview table + tailored learning paths + per-skill cards (用途/要点/核心命令). The NOTES dict inside is the curated per-skill commentary — extend it when adding coverage.
5. **Verify** — count headings with Python, not grep (git-bash grep fails on emoji-prefixed headers like `## 📂`):
   ```
   python -c "import re;t=open('技能学习手册.md',encoding='utf-8').read();print('h2',len(re.findall(r'^## ',t,re.M)),'h3',len(re.findall(r'^### ',t,re.M)))"
   ```
   Expect: h2 = 19 (title + 总览 + 学习路径 + 分类详解 + 16 category sections), h3 = 100 (94 skills + 6 path tiers).
6. **Deliver** — MEDIA: link to the manual; summarize: measured count vs user's estimate, learning-path tiers, key findings (giant skills worth deep-reading, skills that encode the user's own prior work).

## Tailoring to This User (embedded preferences)
- Manual language: Chinese; reply in Chinese.
- Structure learning paths around the user's real work: P0 security-research (pentest), P1 AI toolchain (CC Switch / Claude Code / Codex), P2 productivity (跨境/文档/翻译), P3 dev quality & debugging, P4 creative/media, P5 platform-mismatch ("了解即可" — e.g. apple-* on Windows).
- Call out skills that encode the user's own prior work (fintech-api-pentest, lottery-platform-api-deconstruction, tampermonkey-spa-automation, api-crypto-analysis reference EC Markets/BFCP patterns) — these are "already yours", not new material.
- Flag giant skills (web-penetration-testing ~99KB, research-paper-writing ~102KB) as deep-read candidates.
- Keep a todo list with progress status during the long run; report structured status tables.

## Pitfalls
- search_files returned 0 for SKILL.md under AppData/Local/hermes → use terminal find for inventory.
- git-bash grep can't match emoji-prefixed headers → verify with Python re, not grep.
- `generate_manual.py`'s NOTES dict: skills without an entry render without a 要点 line — keep the dict in sync with the skill list.
- digest.md is ~180KB / 4241 lines — read in chunks with offset; don't hold it all at once.
- After skill changes, re-run both scripts and re-check the overview-table counts match per-category measurements.

## Files
- `scripts/skill_digest.py` — inventory + frontmatter/key-line extraction (parametrized output dir).
- `~/Desktop/skill_learning/generate_manual.py` — manual generator with curated NOTES + learning paths (session-versioned; the skill points to it rather than duplicating the 94-entry dict).
