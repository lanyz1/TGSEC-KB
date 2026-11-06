# 吸收对账：md5 内容级比对与全文归档（2026-10-22 实测）

## 背景

一个 608MB 报告包（156 份报告 + 915 张同名技能卡 + 415MB 同行技能包）在收敛时，按**体积**粗筛「908 张同名卡有没有增量」，结论是「只有 1 张有增量」。被质问「闭环了吗」后改做 md5 内容级比对，实测 **93 张**包内更全。差了两个数量级。

## 四分类实测数字

| 分类 | 数量 | 处置 |
|---|---|---|
| md5 完全相同 | 697 | 跳过 |
| 包内更大且内容不同 | **93** | 取全文（归档 references/full.md） |
| 本地更大 | 125 | 保本地（10-21 并库时重构过） |
| 包内独有 | 0 | 走新建 |

包内 915 个卡名 / 本地 2,177 张。最大单卡 554KB（`offensive-windows-boundaries`），第二 530KB（`offensive-windows-mitigations`），第三 409KB（`offensive-crash-analysis`）。

## 为什么体积法会漏

本地卡在并库时被**重构压成索引**：`shiro-exploitation` 本地 2.4KB、包内 54KB；`log4shell-exploitation` 2.3KB vs 56KB；`incident-response` 2.1KB vs 58KB。体积法只看「包内是否更大」，这类是「本地更小但更完整（索引）」——恰恰是包内更大，但前一轮用 SKILL.md 单文件字节比对时被 references 计入口径搅乱，漏了。

**正确口径：md5 比对（判是否同一份）+ 包内独有行数（判增量实际多大）。** 唯一行数排除了「只改了排版/日期」的假增量。

## 全文归档处置

- 路径：`<skill>/references/full.md`（`shutil.copy2` 保时间戳）
- 主卡指引：在 frontmatter 第二个 `---` 之后插
  `> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：skill_view(name='<name>', file_path='references/full.md')`
- 幂等：已有 full.md / 正文已含该路径 / 已手工拆分（partN）→ 跳过
- 结果：93 张 → **75 归档**、18 已有、1 手工跳过、**0 失败**、共 5.37MB

## 为什么不能塞正文

- 530KB 塞进 SKILL.md：单卡加载就吃掉上下文预算，`skill_find` 的 excerpt/headings 被稀释，检索排序被教材正文挤占
- 索引卡 + 全文切片的形状：主卡保持 2–10KB 可检索摘要，深挖时按需 `file_path` 取全文
- 归档后必须重建 arsenal（`arsenal_build.py`）+ `selftest.py` 30/30，否则新内容的 headings/tags 不进索引

## 闭环缺口（同一会话被抓出的两个）

1. 体积法漏判 93 张 —— 「同名卡都看过了」这种结论必须附 md5 数、唯一行数、抽样内容
2. `git status --porcelain` 挂着 89 个未跟踪文件（87 个生成的 `docs/playbooks/*.md` + `tools/` 探针 298 个 + `docs/learning/` 原料 3.6MB）—— 处理：playbooks 与 tools 入库、learning 进 .gitignore，仓才清零
