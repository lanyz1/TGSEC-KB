<!-- archived from /root/.hermes/skills/security/bi-platform-exfiltration/SKILL.md on 2026-10-21 -->

---
name: bi-platform-exfiltration
description: "Use when BI tools (Metabase etc.) found. Bulk DWH export."
version: 0.1.0
tags: [metabase, superset, bi, data-exfiltration, mbql, csv-export]
---

> 归档卡：原目录 `/root/.hermes/skills/security/bi-platform-exfiltration`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/bi-platform-exfiltration/…')`，不要相对 `references/legacy/` 解析。

# BI/分析台 → 数据仓库批量外带（Metabase 实拍为主）

场景：内网/半公开的 BI 台（Metabase / Superset / Tableau…）用任一可用凭据进入。它背后就是数据仓库 → 直接变成批量取数/外带通道。

> Metabase 的**预认证 SQLi（CVE-2026-72898）**入口见用户技能 `metabase-preauth-sqli`（另一条线，勿混）。本技能只管「已认证后的取数/外带全链」。完整 API 配方见 `references/metabase-authed-exfil.md`。

## Metabase 已认证速览（实测链）

- 登录 `POST /api/session {"username","password"}` → `{"id": token}`；后续头 `X-Metabase-Session: <token>`；token 存盘复用，401 时重登。
- 探测：`/api/session/properties`（版本 + setup-token；token=None 即已初始化）、`/api/database`（库清单，非管理员 details=None）、`/api/database/{id}/metadata`（全表+全列+field id，后续 filter/aggregation 全靠它）。
- **`can_create_native_queries=false` 只禁原生 SQL**；MBQL 结构化查询（`POST /api/dataset`）全放开——单表全读没问题。
- 全量导出 = 建卡 + CSV 双跳：`POST /api/card`（**description 必填**，空串 400）→ `POST /api/card/{id}/query/csv`。**单次导出硬上限 1,048,575 行**。
- 绕上限：按数字主键/时间区间切片（半开 `between a, b-1`）；**返回行数恰 1,048,576 = 被截断，必须细分该片**（低位 ID 段密度最高，最常被截）。
- 每片用后即 `DELETE /api/card/{id}`；批量清理 `GET /api/card?f=all` 按名称前缀扫删。

## 数据对账（交付前必做，用户会追问口径）

- Σ(切片行数) == 全表 count；`count vs distinct(唯一键)` 相等 = 零重复零截断。
- 跨源查漏：导第二源唯一键单列（很小，~950k 行 60MB）做本地集合差；差额用 `["in", field, id1, id2, ...]` 过滤补导。
- PII 口径分开：明文 vs 加密存根（如 `v1$$main_key_id_v1$$<hex>` 前缀）——用 starts-with / not-starts-with 两 count 定性。
- **样本 ≠ 全量**：105 万行样本估 45 万手机号，全量实测 340 万（差 7.5 倍）——报数只认全表聚合/全量导出。
- 号码归一：10/11 位变体、前缀位剥离（如带 `1` 前缀）、去重后再报；多 instance/品牌行用 `distinct(USER_UUID)` 做真人口径。
- 报数三档分开讲：仓库总量 / 已导出量 / 样本——别把总量说成已拿到。

## 体量与可行性（规划交付）

- 1M 行支付流水 CSV ≈1.6GB raw（zstd -3 ≈175MB）；1M 行用户 ≈250–275MB raw；zstd 对 ID/数字型 CSV 压缩 7–10x（1M 行→175MB 实拍）。
- 数千万~百亿行表（支付 9 千万、钱包 220 亿+）：全搬不现实 → 给用户三档选择：分段全导（可做，几十 GB）/ 按需切片 / 聚合。先杀“总量”焦虑，再谈交付形式。

## Pitfalls

- 大规模取数前先 count + breakout 聚合定性；千万级以上别拉明细。
- 会话 token 会过期；大任务前 `/api/user/current` 验活。
- `/api/dataset` JSON 路径约 2000 行上限（快查用）；全量只能走卡片 CSV。
- 临时卡命名带统一前缀（如 `ZZ tmp`）便于扫删，别裸名建卡。
