# 2026-09-11 TQ 停更事故 · 哨兵链与待发弹药

## 事故定性
- tokenrailquery 09-10 ~21:30-23:00 间停止供数；09-11 全天 0（截至 10:01 实测）。
- 影响面体检（池文件新鲜度法）：**仅 TQ 一条通道**——审计(auditlog)/名册同步(plat_enroll_map 10:01 仍在刷新)/索引全照常 → 补漏主线由审计票 + 存量队列支撑，无损。
- 审计流排查：400 行审计抽 23 票**全为 03 供应商**（±死票）→ 审计不是非-03 票源；02/管理票唯一可靠来源 = tokenrailquery。

## 哨兵链（已部署，全自主）
1. **TQ 恢复哨（本机 hermes cron `3ce30bddc345`，每小时）**：
   链 = `scripts/tq_hourly_check.py`（本机）→ 主服 `python3 /opt/v6/tq_probe_runner.py` → 河源 `/opt/v6/tq_health.py`。
   基线文件 `scripts/tq_hourly_state.json`（首跑建基线；片恢复≥1 或放量≥50 才报警，否则静默）。
   **坑（已修）**：runner stderr 含 paramiko 拆除噪音——解析必须**只取 stdout**（stdout 空才回退 stderr）；混入 stderr 会让 json.loads 静默崩 → 脚本 exit 0 且无状态文件（恢复了也永远不报警）。
2. **特权票哨兵（河源 `/opt/v6/priv_tok_watch.py`，crontab `*/20`）**：6h 宽扫收非 03 票 → `/opt/v6/priv_tokens.json` + `priv_watch.log`；双探针验活（user/info + 管理端 loadMenu）。
3. **待发弹药（上海+河源已部署、编译通过）**：
   - `priv_fire.py [token] [projId]` — 特权票到手即打：user/info→login authority→loadMenu→买家接口矩阵（packCheckList / listBidderBy / getSuppliersByReqId / bidMonitor/getSupplier…）。
   - `tq_backfill_sweep.py [start] [end]` — 恢复后补课扫：30min 片全量收票（03+非03），产物 `/opt/v6/tq_backfill_out.json`。

## 恢复后动作序
片恢复提醒 → 补课扫回停更窗 → 02/管理票蓄水（priv_fire 就位）→ 首票出现即打 → 汇入 15% 缺口补齐方案。
