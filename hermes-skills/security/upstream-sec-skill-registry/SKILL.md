---
name: upstream-sec-skill-registry
description: Use when 要拉上游安全技能仓库补库。38 源索引+内容级去重闸。
---

# 上游安全技能源索引与增量收割

本库 security 卡基线 **913 张** / 全库 **1054** 张（2026-09，含 Hi-FullHouse 一轮 +10）。**领域名重合 ≠ 缺口**，建卡前必过内容级去重闸。

## 收割流程

1. 克隆：`git clone --depth 1 <url> D:/skills4redteam/<name>`
2. 清点：`find . -name SKILL.md` —— 数量为 0 ⇒ 索引型仓库（只有 README），只抽仓库表。
3. **去重闸（不可跳）**：`python3 scripts/dedupe_gate.py --src <dir>`
   命中 ≥1 张 ⇒ 已有覆盖，**不建卡**。
4. 只吸增量：真缺口 → `skill-creator` 建家族卡；片段增量 → `patch` 已有卡。
5. 归档：仓库留 `D:/skills4redteam`，结论写本卡 references/。

### 大仓库（100+ 卡）的两层证据法

单看 `dedupe_gate` 的 token 级 HOLE 会大面积误判——大仓库的 HOLE 多是 ATT&CK ID / 工具名 / JSON 字段，**不构成域级缺口**。真正定缺口要用两层：

1. **名称级**：本库卡名逐名核对（`ls -d */` 后按域关键词过滤）——某一整个域（如 Sigma/SOAR/SIEM、ZTNA/微隔离、SBOM、DLP、等保、MISP/STIX）**零命中**才算缺口。
2. **内容级**：写一次性扫描器比对上游卡 vs 本库全部 SKILL.md，出模块级覆盖率排序（只读、落盘报告）。**avg 最低带 = 优先补卡方向；avg 最高带（本库已超越的域）= 明确不建卡**。

报告要按卡级与模块级两层排序，并记录「哪些域本轮判定不建卡」，否则下一轮会重复评估。

### 落卡纪律（大仓库抽取）

- 上游卡**原文直接落 `references/`**（保留出处与 MIT 许可），SKILL.md 自己写触发/工作流/Pitfalls——不把上游方法论重写一遍（重写=蒸馏失真）。
- 每个子代理产出一律配 `references/provenance-and-unverified.md`（原样搬自上游 / 本次补充【补】/ 未验证清单三栏）；上游排雷结论（杜撰 GUID、不存在的参数与子命令、拼接式 ID）同步写进 SKILL.md 的 Pitfalls，防止下次照抄。
- 子代理**只准写 `out/<卡名>/`**，不得直接碰技能库；落卡由主控做 `mkdir + cp`，避开长内容截断。
- 落卡后必查三项：① frontmatter `name` 与目录名一致；② `grep -o "references/[a-z0-9.-]*\.md"` 逐条 `[ -f ]` 验证**无悬空引用**；③ `skill_view` 抽查一张确认可被发现（cp 落卡也能被 linked_files 解析）。

## 判定铁律

- 上游这类卡多为 1.5–3KB 方法论摘要 ⇒ 本库深卡通常已超越它，**照搬 = 造重复卡**。
- **占位空壳卡**（正文 = description 复制，加载即空转）是库内高频坑：一律转成**重定向卡**（保留触发词 + 指向真卡），不要在同一域再补第二份内容；无真卡可指的才填真内容。
- 建卡/改卡后**必须校验 frontmatter YAML**：`description` 含裸冒号（`Trigger: x`、`Security: y`）会让整卡解析失败，必须整行加引号 —— 本库一次扫出 26 张（含 `full-crack`/`crack-keygen` 等常用卡）。
- 真缺口判定到**工具/术语级**：领域名 100% 重合仍可能有工具名空缺（如 Flawfinder/Cloudsplaining/Stowaway/Teku），这类只往宿主卡补行，不新建卡。
- 「已覆盖」必须以 grep 命中的卡名为证，不凭印象；单词命中可能误撞（如 wps → wpscan），要看上下文。
- 六门闸 / 范围先行 / 证据导向 / 断点续跑已在 `pentest-methodology`（同源且更完整），禁止再建重复总控卡。
- 目标仓库若混有「爬虫 / 建站 / 加固」等非安全卡，按域分流，不进 security。

## 索引与工具

| 文件 | 内容 |
|------|------|
| `references/registry-38repos.md` | 38 仓库全表：分区 / URL / 更新时间 / 覆盖面 / 值得拉什么 |
| `references/harvest-log.md` | 已收割记录 + 逐卡比对结论与证据 |
| `references/pentest-skill-map.md` | **渗透角度整理图谱**：上游卡→本库归属→本轮动作、空壳重定向表、库健康修复、收割纪律 |
| `scripts/dedupe_gate.py` | 内容级覆盖/缺口闸，可跑 |

## 交接

`skill-creator`（建卡） · `skill-engineering`（写卡规范） · `intel-ingest`（常态情报） · 知识库类走 `surveyengine-knowledge-pack`。
