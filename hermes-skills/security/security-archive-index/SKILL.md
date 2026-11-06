---
name: security-archive-index
description: "长尾安全卡归档总索引：624 张已合并卡按字母查，含原文路径。"
version: 1.0.0
---

# security-archive-index

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 624 张）

- 索引：`references/index.md`（624 张，分 21 片，每片 ≤12KB）
- 加载：`skill_view(name='security-archive-index', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->


本卡是**归档目录**，不是执行卡：先看索引，再按需加载子卡原文。

## 用法
1. 打开 `references/index.md`（先选片，再读分片）。
2. 找到子卡名后：`skill_view(name='security-archive-index', file_path='references/legacy/<name>.md')`。
3. 子卡依赖的脚本/字典仍在原目录 `/root/.hermes/skills/<category>/<name>/`，可直接 `read_file`/`terminal` 使用。
4. 本目录只做路由，不替代子卡的判据与 payload。

