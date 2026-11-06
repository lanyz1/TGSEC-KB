---
name: recon-for-sec
description: >-
  Entry P1 category router for reconnaissance and methodology. Use when mapping
  scope, discovering assets, fingerprinting technology, building endpoint
  inventory, and choosing the first high-value security testing path.（含 87 张归档子卡索引）
---

# Recon and Methodology Router

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 87 张）

- 索引：`references/index.md`
- 加载：`skill_view(name='recon-for-sec', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->


This is the starting router for new targets and unknown attack surfaces.

## When to Use

- You just received a new target and do not yet know what to test first
- You need to begin with asset discovery, tech fingerprinting, endpoint inventory, and test-route planning
- You want to build follow-up testing on structured methodology instead of random payload enumeration

## Skill Map

- [Recon and Methodology](../recon-and-methodology/SKILL.md)
- [Insecure Source Code Management](../insecure-source-code-management/SKILL.md) — .git/.svn/.hg exposure detection
- [Dependency Confusion](../dependency-confusion/SKILL.md) — Supply chain reconnaissance for internal package names

## Recommended Flow

1. First confirm in-scope assets and target type
2. Then perform asset discovery, port/service identification, technology fingerprinting, and endpoint collection
3. Route based on collected findings to [api-sec](../api-sec/SKILL.md), [auth-sec](../auth-sec/SKILL.md), [injection-checking](../injection-checking/SKILL.md), or [business-logic-vuln](../business-logic-vuln/SKILL.md)

