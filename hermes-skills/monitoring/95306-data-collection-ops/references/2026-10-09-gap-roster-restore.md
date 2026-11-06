# 2026-10-09 补采名册断供：真根因与修复（企业报名缺口恒 0）

## 症状链路（自上而下，逐层实证）
```
采集率见顶 67.1%
  ← 12 台每轮业务量被候选池饿住（shard0 出现 业务 48/0/48/0 振荡）
  ← 采集机 ctx 恒为「名单 18x / 账号 0」
  ← /opt/v6/gap_projects.json「缺口账号数 = 0」
  ← /tmp/bk8_ctx.json  accts len = 0
  ← /data_pool/gaps.json「企业报名缺口 = 0」（自 10-03 起恒 0）
```

## 真根因（两处叠加，全在 master/gaps.py）
1. `_evid_from_box()` 第 130 行：
   `evid_units.setdefault(pid, set()).add(str(m.get("unit") or st_key[:8]))`
   线上 `_buyed_matrix.json` 的 `unit` 字段**存在但值为空串**（655 条证据仅 22 条有单位，3.4%），
   于是退化写入 `st_key[:8]` —— 一个 8 字符十六进制键片段（如 `8945c0b0`）。
2. `_enroll_one()` 第 200 行三重与门：
   `elif unit and pid in evid and unit in evid_units.get(pid, set()):`
   拿审计侧企业全名（「山西家佑商贸有限公司」）去比 8 字符键片段 ⇒ **永不相等** ⇒
   100% 落到 else 分支「疑似仅打开页面」⇒ `企业报名缺口` 结构性恒 0 ⇒ 补采名册断供。
   实测对账前 40 条：33 条 pid 不在 evid，7 条单位拿全名比键片段，**本应算缺口 0 条**。

## 修复（最小可回滚，改完无需重启任何服务）
merge 是**连续循环长进程**，改完要等当前这一轮跑完落盘才生效（约 8-10 分钟），别急着判定失败。
- 备份：`$TREE/master/gaps.py.bak_20261009_evidgate`
- 改 1（第 130 行）：unit 为空时**不再退化塞 st_key[:8]**，只在有真单位时进 evid_units。
- 改 2（第 200 行）：`elif pid in evid and (not evid_units.get(pid) or (unit and unit in evid_units.get(pid, set()) or not unit)):`
  语义：**项目有提交证据 + （无真单位信息 或 单位匹配）** ⇒ 真缺口。保住原「防误报」意图，
  仅在单位证据不可用时放宽到 `pid in evid`。
- 生效判据：`/data_pool/gaps.json` `企业报名缺口 0 → 33`、`疑似仅打开 100 → 67`。

## 验证阶梯（每层都要实测，别跳）
| 层 | 文件/日志 | 修前 | 修后 |
|---|---|---|---|
| ① 证据 | `/data_raw/*/_buyed_matrix.json` | unit 空 655/677 | 不变（源头仍在采集端） |
| ② 差集 | `/data_pool/gaps.json` | 企业报名缺 0 | **33** |
| ③ 名册 | `/opt/v6/gap_projects.json` | 缺口账号数 0 | **30** |
| ④ 下发 | `/tmp/bk8_ctx.json` | accts 0 | **accts 30 / names 189** |
| ⑤ 落地 | 采集机 journal `缺口 ctx` | 名单 19x / 账号 0 | **名单 189 / 账号 30**（乌兰察布 00:40、河源 00:46） |

## 遗留（下一步，未做）
- 另有 **33 个项目不在 `evid`**（采集机没交提交证据）⇒ 这部分仍需采集侧补 `_buyed_matrix.json`。
- 真正的上游修法：**让采集端写 `_buyed_matrix.json` 时填上 `unit`**（现在字段在但空），
  填上后单位比对可恢复严格语义。

## 口径铁律（本轮踩过的坑，勿再犯）
- `main.py:129` 打印的**「请求/业务/数据」是进程生命周期累计值**，重启归零、单调递增 ⇒ **只能差分**
  （相邻轮 Δ业务；跨重启/异常间隔的相邻两条丢弃），**不可跨轮求平均**。
- ★ **更正**：`max_biz_per_round(620) − 预算剩` **不可当业务量代理**（实测与 Δ业务 比值各台 1:1.65~1:3 不定）；
  正确口径 + 名册修复实测（68.5→73.4 业务/台/轮 = **+7.2%**）见
  `references/2026-10-09-gap-roster-gain-and-measurement-pitfalls.md`。
- `probe_limit=48` 只对**候选充足**的台有效（上海2 29→63、北京 39.8→62、乌兰察布 37.1→66.3 翻倍），
  候选饿死的台没变化甚至更差 ⇒ **瓶颈是候选池，不是 probe_limit**。
- merge 是**长循环进程**，不是每次 cron 起新进程 ⇒ 改 master 代码必须等下一轮才生效。
- 判定「补丁没生效」前，先确认是不是**进程还没轮到新代码**，别急着回滚。
