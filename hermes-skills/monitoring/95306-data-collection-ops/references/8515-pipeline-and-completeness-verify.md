# 8515 快照链路巡检与「有没有漏」的权威核验配方（2026-09-29 实测基线）

## 链路（主控侧，全部在 /opt/v6）

```
fetch_8515_inc.py  cron */30 + flock /tmp/v8515.lock → /tmp/v8515.log
  ↳ funcId=bid_package_bidder_business23，按平台「内部更新时间」窄窗拉
    params=[{start_time},{end_time}]，pageNum/pageSize 分页
  ↳ 窄窗 = 35 分钟、每 30 分钟一跑（5 分钟重叠，落在池里是重复行，不是重复入账）
  ↳ 不走主服直连：RELAYS=[上海0, 杭州1, 广州2, 蓉5] 轮询 ssh 中继（架构红线：主服不直连目标）
  ↳ 只在新行才落盘 /data_raw/m_snap/8515_快照_m<MMDD>_<HHMMSS>_<MMDDHH>.json
  ↳ state /opt/v6/8515_inc_state.json = {"last": "抓取时刻"}（每 30 分钟推进）

其他两个 8515 cron（别漏看）：link8515.py（:13 * * * *）/ arch8515.py（:3 * * * *）

merger.py（daemon 每 120s）
  merge_8515_snap() → /data_pool/8515_快照/index.json
  audit_diff()      → /data_pool/audit_changed.json（审核变更项目）
  apply_8515_results() → pack_map["包件结果"]（决标/成交价/审核时间回写）
  → bot 菜单B 监控读同一批 → 推送（三处项目数应对得上）
```

## 数据结构与**对账键**（踩过：用错键会 0 命中 → 误判「全丢」）

- `8515_快照/index.json`：`index[proj_id][pack_id] = {buy_time, status, check_time, price, src}`
  ⇒ **对账键 = (proj_id, pack_id)**。用 `uuid` / `bidder_id` 对账必然全 miss（`bidder_id`/`dwcode` 在 8515 行里恒 None，行是匿名的）。
- 聚合规则（`merge_8515_snap` 内）：`_rank = {22已决标:3, 01通过:2, 03拒绝:1, 00待处理:0}`，同级取 `check_time` 最新；
  `buy_time = buy_time or current_price_time`；`price = current_price or price`。
  ⇒ 同包多行（bidder 级匿名行）不会互相覆盖成错状态（历史 bug：已决标被 01 行覆盖回「竞价中」）。
- 行字段：`proj_id, pack_id, uuid, buy_time, check_time, hereor_time, current_price_time, status, single_price_list, valid_or, hereor, memo, bidder_id(None), dwcode(None)`。

## 核验配方（用户问「8515 更新正常吗 / 是不是漏了」时照此跑）

1. **管道面**：`crontab -l | grep 8515` + `tail /tmp/v8515.log`（每轮 `[窗] rows=N` + `8515 增量完成: N 条`）+ `cat /opt/v6/8515_inc_state.json`（last 是否当前半小时内）+ `ls -lt /data_raw/m_snap/ | head`。
2. **合并面**：`grep 8515 /tmp/v6_merge.log | tail` ⇒ 应有 `8515 快照合并: +N 变更` / `audit_diff: N 个项目` / `8515 结果回写 pack_map: N 项目`。
   **池文件 mtime 不能当证据**：合并器幂等，零变更不重写；mtime 动了 = 真有变更。
3. **逐包件对账（最关键）**：
   - A) m_snap **全量 ∪**（179 文件 15,538 行）→ 按 (proj_id, pack_id) 取 rank 最高的行 → 与池比对 ⇒ `池中缺 / 状态·时间不一致` 必须都是 **0**。
   - B) **平台独立宽窗查询**：`start_time=cutoff, end_time=now`，pageSize=100 翻页（>800 行说明平台在动）→ 同键对账 ⇒ 缺 **0**。
   - 交叉口径：宽窗返回的行是「平台**更新**过的行」，其业务日期可能很旧（平台在刷新历史行）⇒ 别拿行内日期当「平台没动」的证据。
4. **时间字段 max 交叉**：池内 `check_time/buy_time/hereor_time/current_price_time` 各自 max vs 平台侧同字段 max —— 一致即无滞后。

## 2026-09-29 实测基线（可作之后对比的锚点）

- m_snap 全量 15,538 行 → 去重 **2,194 包件** → 池中缺 **0**、状态/时间不一致 **0**。
- 平台宽窗 09-25 00:00 → 09-29 09:16：**1,200 行**（12 页×100 仍然满页）→ 去重 **196 包件** → 池中缺 **0**。
- 池：52,287 项目 / **149,350** (proj,pack) 对（上轮 149,343 ⇒ 在涨）；池内 `check_time` max = **2026-09-24 09:47:34**，>09-24 条目 = **0**。
- 平台侧独立确认：09-25 起更新的 1,200 行里，`check_time` max 09-23、`hereor_time` max **09-24 15:11**、`current_price_time` max **09-24 15:44** ⇒ **平台侧 09-25 之后没有新业务日期**（中秋+周末后未推进新审核，仍在刷新历史行）⇒ 池停在 09-24 属平台节奏，**不是我们漏采**。
- 端到端闭环实证（三处数字对得上）：`[09-29 01:05:34] 8515 快照合并: +11 变更` → `audit_diff: 6 个项目` → `8515 结果回写 pack_map: 6 项目` → bot 菜单B 推送列 **6 个项目**（凯里工务段/北京局废电子电器/…）。

## link8515.py（cron `:13`，日志 `/tmp/lk95.log`）= 8515 匿名行 → 报名企业名 关联

- **坑（2026-09-29 已修）**：`A2[k]=sorted(set(rows))` 里 rows 是 tuple 且可能含 `None` ⇒ `TypeError: '<' not supported between instances of 'str' and 'NoneType'`，**挂在写盘之前**（358 轮里 9 次）⇒ 那一轮关联不落库（旧版文件保留，不脏数据）。
  修法（最小）：`_nrm=lambda t: tuple('' if x is None else str(x) for x in t)` + `sorted(set(rows), key=_nrm)`；备份 `link8515.py.bak_lk95fix_0929_0151`（`bb3cddba…` → `73bafa65…`）。
- 健康一轮必须打到 `L95Z DONE`：`L95A DONE` → `KEYS_D/ROWS_D` → `P1 U2N … CONF` → `P2 ELIM … LEFT` → `RESULT pids/pairs/links` → `WR {...}` → `GOLD ...`。**只到 `L95A DONE` + Traceback 就是挂了**。
- 验证方式：`cd /opt/v6 && flock -n /tmp/lk95.lock python3 -X utf8 link8515.py >> /tmp/lk95.log 2>&1`（flock 与 cron 互斥，安全）。

## 全链体检脚本（本机 → 主控，只读）

- `renew/ms_fleetchk.py` — 主控本地 + 12 台机队逐台：ACT/md5/SHARD/启动时间/磁盘/SEEN/DRAIN/PEND/冷却/今日轮询·入队·榨干/state·targets mtime/最后轮询时刻。后台跑落 `/tmp/fleetchk*.out` 再分片读。
- `renew/ms_fleetchk2.py` — 子任务日志新鲜度 + 异常计数 + `hf_*` 批拉 + `/data_raw` 回流新鲜度 + 池活跃度 + 目录体积。
- `renew/lk95_fix.py` — 就地修复模板（md5 基线 + 备份 + 唯一命中断言 + py_compile + 上下文回显），可复用到其它脚本。
- **常见假警报（别误报）**：①**目录 mtime ≠ 新鲜度**（append 日志不改父目录 mtime；写子目录亦然）②0 B 的 `*_cron.log`（脚本自己另写日志，stdout 无输出）③`*冗余`/杭州/上海3 等**已退役**机目录天然陈旧 —— 判据用 `fleet_gc` 的「机队 N 台/失败 0/待摘除 0/孤儿 0」+ jumpers.json 名单，**不用目录时间**④`m_snap` 目录 20–30 分钟不动属正常（只在有新行才落盘，cron `*/30`）⑤历史 traceback（09-15/09-21 的 paramiko banner timeout、杭州 `121.43.97.73` 失联）**先看日期再判死活**。

## 判读坑

- m_snap 文件是**单行 JSON**（无结尾换行）⇒ `wc -l` 恒 0，行数必须 JSON 解析。
- 抓取器夜间多轮 `rows=0` = 平台无动作（正常），不是抓取故障；只在有新行时才落盘 ⇒ 文件之间出现十几小时空档属正常。
- `m_snap` 在 merger 的 `NON_MACHINE_DIRS = {"m_snap", "95306_full"}` 里（防被当成采集机目录报假「无心跳」告警）。
- 本轮探针脚本（本机）：`renew/ms_8515chk{,2,3,4,5,7}.py`（在 `C:/Users/Administrator/AppData/Local/Temp/renew/`），经 `mrun.py` 投主控跑。
