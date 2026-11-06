# 大卡拆分收口（2026-10-21）

## 结论

92 张 `SKILL.md` 曾 >30KB；用 `tools/ops/split_oversized_cards.py` 做**内容保持**拆分：

- 原文件先复制到 `/root/.hermes/skill-backups/20261021-oversized/<category>/<card>/SKILL.md`。
- 主卡保留 YAML frontmatter、H2 之前的引言，并追加 `## Section index`（带 `<!-- split-index -->` 标记）。
- 每个 H2 节原文移入 `references/split-NN-<slug>.md`；不重写、不摘要、不改语义。
- 结果：92 张主卡合计 **5,140,169 → 219,325 bytes**；**0 张 >30KB**，最大 **29,815 bytes**（`aig-agent-redteam`）。
- 仍留 **279 张 >15KB**，不继续拆；避免每张卡多一层 `skill_view` 间接。

## 校验

对 92 张逐张核对：

- 备份文件存在；
- `frontmatter` 原样保留；
- `intro + 所有 H2 节` 与原 body 字节一致；
- 每个 `references/split-*` 的 sha256 与拆分时记录的节哈希一致；
- 主卡包含每个 reference 的相对链接；
- 无缺失文件、无断链。

结果：**92/92，0 错误**。报告：`/root/.hermes/arsenal/oversized-split-20261021.json`。

## 检索层适配（关键）

只拆文件会让 `skill_find` 搜索不到被移出的正文，因此同时改了：

- `arsenal_build.py`：`headings`/`excerpt` 由 `SKILL.md` + 卡目录下**直接** `references/*.md` 组成；不递归 `references/legacy/`，避免归档卡互相污染。
- `skill_find.py`：`card_text()` 读取 `body_path` + 直接 references，deep scan 仍能命中拆分后的节。
- 重建后：`total=2173`、`enabled=374`、`disabled=1799`、`legacy=1856`；`selftest.py` **30/30**。

## 拆分后必须同步的三处（否则指标假回归）

1. `arsenal_build.py` 的 `headings`/`excerpt` 和 `skill_find.py` 的 `card_text()` 都要读 `SKILL.md + 直接 references/*.md`。只拆文件不改索引，deep scan 搜不到被移出的正文。
2. `coverage_gate.py --active` 若只认 `SKILL.md`，拆分会把引用从主卡移走，active 覆盖会从 116/107 掉到 115/106，看起来像真实回归；必须把启用卡目录下的直接 `references/*.md` 一并计入。全库 scope 同样要重跑后再写文档，不要抄拆分前快照。
3. 拆分报告要合并已有 JSON：`--apply` 第二次只记录新拆的卡，否则第一张的 before/after/sha256 会从报告里消失。

## 复跑

```bash
cd /root/TGSEC-Qtzuu
python3 tools/ops/split_oversized_cards.py                 # dry run
python3 tools/ops/split_oversized_cards.py --apply --limit 1
python3 tools/ops/split_oversized_cards.py --apply          # 会跳过已有 split-index 标记
python3 /root/.hermes/arsenal/arsenal_build.py
python3 /root/.hermes/arsenal/selftest.py
```

## 注意

- 禁用卡的 `body_path` 仍是 `references/legacy/<name>.md`；拆分只改主卡，不改变归档加载路径。
- 已拆过的卡有 `<!-- split-index -->`，再次运行不会重复拆。
- 拆分是“主卡瘦身”，不是“知识删除”；全文仍在 references 与备份中。
