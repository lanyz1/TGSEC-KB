# 登录流水采集通道：20 分钟窗 + 补采 301 静默空（2026-10-09 实测）

## 一句话
企业报名票只靠"捡平台上任意账号的活 token"，而采集端只看**最近 20 分钟**流水且**补采通道因 `base=http` 长期静默查空** ⇒ 错过窗口即永久缺口。

## 通道架构（两个互补腿，互不重叠）
| 腿 | 实现 | 窗口 | 账号类型 | 职责 |
|---|---|---|---|---|
| 采集端 | `collector/tickets.py:98`（日志 `rail 流水: N 页 / M 账号 → 本机票…`） | `[rail] window_min=20`，`every_sec=360` 滚动 | `user_types=03,3`（**只认企业**） | 捡企业票 → 采报名包件 |
| 哨兵 | `master/priv_watch.py`（`priv_tok_watch_v3.py`） | `watch_windows=12 × 30min = 6h` 宽扫 | `watch_skip_types=03,3`（**主动跳过企业**） | 高权接口探测 |

⇒ **企业账号只有 20 分钟窗**；6h 宽扫能力存在但对企业账号关闭 ⇒ 错过即永久缺。
`[rail]` 自带警告原文：「窗口 >= 周期 才能无缝覆盖，**漏一个周期就漏票**」。`[relay]` 有切片回补（`chunk_h=6/max_chunks=32/first_backfill_d=7`），`[rail]` **没有**。

## ★ 301 静默坑（一行配置毁一条通道）
`conf/master.ini` 注释原文：`referer = https://cg.95306.cn/bfwz-view/  ; http 会 301 ⇒ urllib 把 POST 降级成 GET ⇒ 静默查空`
- 错组合（补采 ctx 现状）：`base=http://cg.95306.cn` + `referer=https://cg.95306.cn/`
- 对组合：`base=https://cg.95306.cn` + `referer=https://cg.95306.cn/bfwz-view/`
- ctx 由 `master/backfill.py:66-69` 从 master.ini `[api]` 取：`gs("api","base","http://cg.95306.cn")` / `gs("api","referer","")`

## 单变量 A/B（同 30 分钟窗，采集机出口）
| base | referer | 行数 |
|---|---|---|
| http:// | 站点根 | **0** |
| https:// | bfwz-view | **3000**（触顶） |
| http:// | bfwz-view | **0** |
⇒ 症结在 **base=http**，referer 不救。修 `[api] base` + `[api] referer`（或让其继承 `[site] base_url/referer_biz`）。

## 旁证
- 主路径正常：`rail 流水: 6 页 / 1119 账号 → 本机票 106（新增 40）→ 池 1009`
- 补采常年空转：`bk8_bf_stats_N.json = {"checked":0,"hits":0,...}`、`bk8_bf_result_N.json = {}`（2B；10-02/10-08/10-09 三次全空）
- 截断可达：`[rail] pages=6 × page_size=500 = 3000` 上限实测正好打满；`pick_cands` 取票**不按名册缺口优先** ⇒ 缺口票被挤掉
- 票寿命：`ttl_max_min=360`（6h）；`ttl_min=45` 注释警告「按 45min 淘汰= 白扔票 2/3 寿命」

## 探针纪律（踩过的坑）
- 别用 `Worker.post()` 从采集机**直连** `http://cg.95306.cn`：返回 `code=-2 appId不存在`，不是权限问题而是 301 降级。
- 主控侧正解 = `RelayExec(conf).post_json(url, body)`（ssh 到采集机执行，带 UA+`bfwz-view` referer）；`[priv] url_findlist` 是 https。
- **必须用唯一变量 A/B**（base / referer 各改一次），否则会把"探针自己坏了"误判成"平台真空窗"。
- 采集机 `current -> /opt/v6/lib/v6rel_202610080354`，主控 `current -> v6rel_202610081757`（**版本分裂**，读代码要指明是哪一边）。
