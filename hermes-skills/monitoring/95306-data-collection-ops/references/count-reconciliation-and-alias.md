# 三口径对账（平台侧 / 采集 / 表格）与简称→全称归一

用户报「平台侧 N 家、采集 M 家、点进表格 K 家，三个数打架」时走本文件。
**先定源、再算数**，不许拿项目名当键，一律按 projCode。

## 1. 三源各归其位

| 口径 | 数据源 | 键/手法 |
|---|---|---|
| 平台权威报名名单 | `/data_pool/plat_enroll_map.json` | `projs[projCode]["企业"]`（家数）+ `["报名时刻"]`（{企业全称: "YYYY-MM-DD HH:MM"}，秒级消歧用）；同一项目名可对多条 projCode ⇒ 统计带 projCode |
| 池内实际采集 | `<池目录>/pack_map.json` → `enterprises` | 去重家数；`单位` 是显示名、`报名时间_平台` 是对撞用；池目录查 `/data_pool/index.json` 的 `projects` |
| 表格行数 | 主控 `ai_query.project_enterprises` → `plat_total/ent_total/pending_total` | `ai_agent` 把 `pending` 行并进企业表 ⇒ 行数 = 采集 + 待补 |

**行数 ≠ 家数**：报名总表是「每包件一行」，`已采 = 家数 × 包件数`。报数时必须同时给行数与去重家数，并注明口径，否则两个都对却看着打架。

## 2. 一家两算（最常见根因）

池内 `单位` 存简称（「帆辰」）、平台名单存全称（「河南帆辰物资回收有限公司」）⇒ 归一函数只做「去空白」时，同一家**既进 pending 又被当「平台外」**，表格虚增 2。
决定性证据：池内 `报名时间_平台` 与平台 `报名时刻` 秒级吻合（如 `14:37:13` ↔ `14:37`），账号缩写也对得上（hn+fc=河南+帆辰）。

## 3. 保守归一算法（`match_plat_units` / `plat_alias_match` / `_alias_units`）

优先级，逐步收紧：
1. 精确同名
2. 唯一互相包含（简称 ⊂ 全称）
3. 多候选时用平台 `报名时刻` 秒级对撞取唯一
4. **都对不上就不匹** —— 宁可留着「待补」，也不许瞎认一家

合并顺序决定成败：先把归一结果并进 `have`（平台全称集合）再算 `pending`；`extra`（名单外）必须用「归一后仍不在平台名单」判定，否则被归一的那家会被重复计入 extra。
归一要**两处闭环**：主控 `ai_query.py` 与 新树 `bot/render.py` ↔ `bot/pool.py` ↔ `bot/regcsv.py`；只改一边 ⇒ 口径继续打架。

## 4. 口径自洽判据

- `plat_total = matched_total + pending_total` **必须成立**
- `ent_total = matched_total + extra_total`
- 汇报文案里不许出现 `平台 = 采集 + 待补` 这种等式：数学不成立时模型会「凑」出一个行数（把 `50 + 3` 硬说成 `53`）。
- prompt 里硬编码了错误等式 ⇒ **改代码不够，必须同时改 prompt 规则行**（否则重启后 AI 照旧凑数）。

## 5. 展示层字段缺失

卡片读 `proj_detail.info` 的字段（如 `packCount`），而新树 `项目信息.json` 没这个键 ⇒ 恒显 0，同屏其他视图却是真值。
修法：展示值以**池内明细**为准（`len(packs)` fallback），别信 `info`；`index.json` 里有同名字段不代表 `proj_detail.info` 有。

## 6. 缺口链路盲区

`gaps.json` 的「企业报名缺口」不认「平台名单有、池内没有」这类差集（已结束项目尤其如此）⇒ 这类缺口**不会自动补**。
只能：① 按报名名单跑定向 `v6m.py backfill`；或 ② 把「平台名单 vs 池内采集」的企业级差分接进 gapgen。别指望重跑采集循环会自愈。

## 7. 主控侧单文件（不在发布树里）怎么改

`ai_query.py` / `ai_agent.py` 位于主控 `/opt/v6/` 根，**不随发布树走**（发布树只含 `bot/ collector/ tools/ deploy/ conf/`）。流程：
1. 本机镜像 `md5sum` 与线上 `md5sum` **比对一致**再动手（不一致就以线上为准）
2. 本地用 heredoc python 精确改，`py_compile` 过
3. 线上 `cp -a <f> <f>.bak_<ts>_<tag>` 备份
4. `scp` 回传，现场 `python3 -c` 用**真池真码**复现数字
5. bot 重启后才生效（模块已加载进内存）

## 8. 验收清单（改完不许只看代码）

- 活树（`/opt/v6/current`）+ 真池**只读**复算：打印 `plat_total / matched_total / pending_total / extra_total / ent_total` + `pending / extra / alias` 明细 + 表行数（`ents + pending`）
- `md5sum` 核「落盘物 == 沙箱被测物」（活树文件 vs `/tmp` 对拍树）
- 夹具函数同样受 ≤50 行结构闸约束 ⇒ 超限拆 helper（`_reg_fixture` 拆 `_reg_suppliers`、`chk_regcsv` 拆断言 helper），别放长函数过闸
