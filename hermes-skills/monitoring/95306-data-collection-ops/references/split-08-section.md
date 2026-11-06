## 数据流与权威基准

```
平台(findList 无鉴权通道)→ sync_plat_enroll(30min)→ plat_enroll_map.json(权威报名名单,近14天公告)
collector(12台 systemd v6collector,SHARD 0-11,90s轮询审计 ST)→ /data_raw → merger(实时)→ index.json/pack_map
orch8b(主服 cron 每5分钟;v9.21 起补漏目标=进行中+已结束≤30天)→ 12台并行 worker → pack_map
bot 菜单B = index.json + pack_map + plat_enroll_map 三源
```

- **plat_enroll_map.json = 唯一权威基准**("确定没人报名吗"只信它):biddingandsellingsupplier 必须带 params startDate/endDate(无参返 0)
- 审计 ST 仅覆盖跳转式报名(~25%);tokenrailquery 供应商(user_type=03)token 即 bfwz ST(TTL>2h),集团公司 02 无权限
- **tokenrailquery 必须带时间窗**:`params:[{key:"startDate",value:…},{key:"endDate",value:…}]`,**缺窗直接返 0 行 —— 那是调用错误,不是通道失效,别据此判"金矿不存在"**。实测 60min 窗 = 5.4k 行 / 4.3k 不同 userid / 2.5k+ 可用供应商票(`login_status==1 and user_type=="03"`),连续 11 页翻页零限流;行内含 `userid`(登录账号名) ⇒ 不必先 `user/info` 就能建账号→企业映射。通道是平台级可见(12 台看到同一批行),**只需一台拉**。产量比采集消费高约 10^2 倍 ⇒ 产能问题一律不要归因"没票"。
- ⚠️ TQ 可见性模型(已修正,以此为准):行**延迟~2-3h 到达**非停更;迟于 TTL 的行票死;判据=票鲜度。哨兵 v2 `tq_hourly_check.py`→主服 `tq_liveness.py`。详见 references/2026-09-11-tq-model-correction.md 与 -delayed-visibility-verdict.md、-miss-set-recompute-and-gap-scope.md
- 特权会话线(站内直报/批量报名盲区解法): 主服 `/opt/v6/priv_loop.py` 每8min 蓄水非03票+会话交换+端点矩阵实弹(命中存 priv_hits.json, 本地哨兵 63b9aff57605 报)。**★实测该线自建线至今零命中（2026-10-08 已定位真因 = 3 处代码 bug + 认证模型，**「不要按最近坏了去修」的旧结论已作废**，改后见 references/2026-10-08-priv-line-verdict-and-bug-chain.md）；同批盘点 pack_map 覆盖率与缺口归因法（**含 `acct_map.json` 必须用 `map` 反查的坑**）见 references/2026-10-08-packmap-coverage-and-gaps.md**：`priv_cov.json` 的 `命中计数` 恒 `{}`、`票据总数 206`/`命中票数 0`，归档副本 `priv_archive_*` 里同样为 0 ⇒ **不要按「最近坏了」去修**。**三重墙（2026-10-08 全部重核，结论大改）**：①~~票全过期~~ ⇒ **已推翻：真因是 `priv_tok_watch_v3.py` 的 `post`/`_relay_post` 名字错配 + `except Exception: break` 静默吞，致票源断奶一个月（mtime Sep 13 铁证）；修复后活票充足——企业票 5236 张、内部票 80/80 ALIVE**。②~~蓄水器断粮（`NEWTOK 0`，平台近月无非企业新登录，我方不可控）~~ ⇒ **已推翻：平台流水充足（`USER_TYPE {'02':556,'03':907}`、`PASS_FILTER 479` ≈160 张/30min）；`NEWTOK 0` 是上述代码 bug 的产物；另 `watch_cmd` 内层 `timeout 200` 过短（每票 2 次中继探测 ~1.5s）致票簿永不落盘**。③**权限链不足（成立且加强）**：`[priv]` 矩阵打的是**门户 `business-proxy` 端点，需要门户会话**，而票池里的票是 **bfwz ST（供应商视角）** ⇒ 用错端点打不动；实测内部票(02) ⇒「您没有该数据的访问权限」，顶级权限票横跨 14 个路局 **56/56 全部 `HTTP500 您没有该功能的操作权限`（功能点级缺失）**，企业票(03) ⇒ `401 您未登录`；`serviceTicket` 换票一律「登录失败」（票 token ≠ CAS ST），`pack_map` 里的真 CAS ST 已过期且一次性+绑会话 ⇒ **有 auth ≠ 有权**。**`hits=0` 的真因 = 认证模型 + 配置 `pids` 空致 `matrix()` 首行 `return`（不是没权限，是压根没打）**。四处 bug 链与对照实验见 references/2026-10-08-priv-line-verdict-and-bug-chain.md诊断任意一条腿走 `references/leg-health-diagnosis.md`；机制细节见 references/2026-09-11-priv-token-loop-and-blindspot-solution.md
- 竞价室 bid_live(💰实时出价): v9.27 修复"选票(参与方)+静默+merger搬运(需全局sweep)"三断点; 详见 references/2026-09-11-bidlive-capture-v927-fix.md
- 全量待补 miss 复算产物 `/data_pool/miss_current.json`(records/uniq/proj_miss/miss_all)
- 全量历史 22.5 万行企业包件在 /data_pool/汇总/全量_历史_企业包件_18列.csv

