---
name: external-skill-library-intake
description: "Use when absorbing another agent's skill-library export."
version: 0.1.0
tags: [skills, intake, diff, dedupe, hermes]
---

# 外部技能库导出包入站（差分 → 决策表 → 装）

场景：用户丢来别人（或另一台机）的 Hermes/Claude 技能库导出——几百到几千张 `SKILL.md`，常和战报、源码、数据混在一个 zip 里。硬规则与 `security-kb-ingest` §0 同一道门：**先差分、出决策表、用户拍板，才动 `~/.hermes/skills`**。

## 流程

1. **解包**：中文 Windows zip 需 GBK 修名（见 `large-file-intake/scripts/unzip_gbk.py`）；滤 `..` 防 zip-slip。
2. **归一名差分**：两侧遍历 `SKILL.md`，名字 `lower().replace('-','').replace('_','')` 比对本地库。匹配池用 `os.walk` 直扫，**别拿 terminal stdout 当池**（大输出截断 → 假 MISS）。四桶：`miss` / `same` / `upstream_fat`（包版 >1.1×，升级候选）/ `local_fat`（本地更厚，守住）。
3. **miss 再分级**：CJK 胖卡（>3KB 且中文密度高）= 真金；EN 大卡 >6KB；stub <1.5KB 基本空壳跳过；小杂卡低优先。
4. **同批多包先去重**：Hermes 布局 zip 与九阶段 tar（`skills/01-recon-osint`…`09-comprehensive`，大量 `lab-*`）常是同血统不同切片，按名字/sha 去重再装。
5. **安检是分流不是否决**：安全卡里 `ignore instructions` 之类关键词是**本体**（误报）；`curl|sh` 多是安装指引；PEM 私钥可能是逆向样本 —— 逐条看语境，真凭据走 gh013 消毒。
6. **装**：只装 miss 高价值卡 + 取 upstream_fat 的**新增段**（不覆盖本地既有增量）；装后署名清理 + `skill_view` 抽检。
7. **混杂物料分流**：战报 → case-lessons；数据导出（profiles.csv 等）→ loot 归档，不进技能库；已入过同版本的技能包（gpu/phoenix 等）直接跳。

## 文件

- `scripts/diff_skill_export.py` — 输入 zip/tar/目录，输出四桶统计 + Top 列表 + JSON
- `references/2026-10-17-export-diff.md` — 1146 卡包实测（466 净新 / 85 升级候选）与待拍板状态

## Pitfalls

- 归一化只能抓同名：语义同、名字不同（`2fa-otp-bypass` vs `2fa-bypass`）要靠人眼看 Top 列表。
- 别按目录名判类别，看 `SKILL.md` 体积 + 中文密度。
- 决策表三方案给用户选（全量 / 只安全面 / TOP-N 抽检），选完再动手。
