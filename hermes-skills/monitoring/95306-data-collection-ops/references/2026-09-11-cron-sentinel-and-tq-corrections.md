# 2026-09-11 增补修正: TQ 延迟模型 / Hermes cron 哨兵配置 / 特权线现状

> 对 -tq-outage-sentinels-ammo.md 与 -priv-token-loop-and-blindspot-solution.md 的增补; 若与原两份冲突, **以本文为准**。

## 1. TQ "停更" → 延迟混合态（13:00 实测定稿）
- 行**延迟 ~2-3h 到货**；**TTL(2-4h) 内到货的窗票活**（10:04 窗实测抽 5 票 3 活），迟到窗里的票已死。
- 判据 = **票鲜度**：主服 `tq_liveness.py`（frontier + 逐票 user/info）→ 本机哨兵 v2 `tq_hourly_check.py`（状态迁移才报）。
- 补扫纪律：**只扫"含活票的新鲜窗"**；迟到窗/旧窗票已死，扫 = 无用功。

## 2. Hermes cron 哨兵配置（本机，2026-09-11 实测）
- schedule 写 `every 30m`（循环）—— 只写 `30m` 会落成**一次性**；
- **deliver 必须显式 `origin`**（默认 local = 输出只存不投递，人看不到）；
- repeat 设大数（如 9999）；
- no_agent 脚本**空输出 = 静默** —— 哨兵正合适（无变化不打扰，有命中才响）。
- 实例：特权票命中哨 `63b9aff57605` 按此配置；TQ 哨 `3ce30bddc345`（每小时）。

## 3. 特权线现状（取代 sentinels-ammo 第 2 节）
- 蓄水 = 主服常驻 `priv_loop.py`（8min 循环：收割 → 验活 → 会话交换 → loadMenu → 10 端点矩阵）；命中存 `/opt/v6/priv_hits.json`。
- `priv_fire.py` 修复留档：函数内 `import urllib.parse` 会遮蔽全局名 → UnboundLocalError；修复 = 顶部统一 `import urllib.parse`。

## 4. 待补 SKILL.md 指针（本轮隔离守卫阻写，下次前台会话/维护时补进 SKILL.md）
- 「数据流与权威基准」节追加一行：
  `- 记录溯源(用户常问「这批记录是哪条ST抓的」): pack_map 条目字段=通道身份证 — 带ST无"来源"=采集机collector / 来源=backfill8=补漏worker(ST空) / 01三态+映射链=历史导入; 直查方法见 references/2026-09-11-st-provenance-forensics.md`
- 「通用部署坑」节追加：
  `6. **Hermes cron 哨兵配置**: schedule 用 `every 30m`(循环) — 只写 `30m` 曾落成一次性; deliver 必须显式 `origin`; repeat 设大数; no_agent 空输出=静默。`
