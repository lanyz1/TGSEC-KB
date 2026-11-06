# 2026-09-11/12 v9.15-v9.16 机制状态(12 台全量优化 + 全链路冲突审计结论)

## 版本链(9 月)
v9.7 enroll 全台处理 → v9.8 seen 只锁命中/ROUNDS 8 → v9.9 审计动态页+70s → v9.10 推送降噪 → v9.11 sync buy_time(报名时刻,分层用) → v9.12 cooldown 30min 退避复活 → v9.13 同账号当日≥3 次冷却→次日 00:10 → v9.14 tokenrailquery 深翻页 30 页(截断修复!) → v9.15 orch8b jumpers 动态+密钥优先+ROUNDS=len → v9.16 审计三档/CHECK_LIMIT 1500+重查配额/sync 60 页/bidRoom 分片/stats 看板/磁盘告警/notices 30 天

## 机制现状(2026-09-11/12 快照)

### cron(主服 UTC)
- sync_plat_enroll: `*/10`(30 页→60 页保险,滑动窗 ~1.4 万行)
- orch8b: `2-59/5 * * * *`(5min;ROUNDS=len(BOXES)=12 → 每台 1 窗×30min=6h 覆盖,6h 窗能抓 TTL 天级的长命票,勿缩)
- gen_gap_projects: `8,18,28,38,48,58`(6h 自动重生成 ent_coverage→jumpers 动态推送 12 台,key 优先)

### collector v9.16(12 台,~70s 轮,错峰 SHARD_ID*7.5s)
- 审计三档:档0 6 页(500 行)/ 档1 15 页(60s≥100 条)/ 档2 31 页(60s≥300 条,仅 SHARD_ID%3==0 的台升档——12 台全冗余,1/3 深翻防打爆审计接口)
- 分片:票 md5(st)%12、企业 md5(acct)%12(SHARD_NUM=12,注释"8台"是过时的别信)
- **bidRoom 出价抓取(bid_live,竞价室监控朋友已实现!)每 30min 仅 SHARD_ID%4==0 的 3 台跑**(12 台全跑=无效冗余+同 ST 限流+卡主循环 6min);bid_status.json 每台本地写无害
- 冷却:code=100 → _cool_backoff(30min 退避,cool_st 到期 _cool_restore 复活;同账号当日≥3 次→次日 00:10);401/403=dead 永久;其他失败 2 次 giveup(票在窗内会每轮重来,实际不丢)
- collector 当日统计插桩(audit_pages/ui_ok/ui_fail/cool/bid_req)→ /tmp/v6_cstats.json → merger 拉回 → **/data_pool/collector_budget.json**(与 orch 的 biz_budget.json 并列)
- notices_map 维护:SHARD 0 每 30min 拉公告 30 页(近 30 天)→ /tmp/targets/_notices_map.json → merger 合并主服 notices_map.json

### bk_worker v9.16(orch 分发,主服 /opt/v6/bk_worker.py 动态读取)
- **深翻页 30 页直到 len<500**(v9.14;高峰窗真实 8700 行/h,7 页=3500 截断丢 60%——沈阳鑫地案例)
- CHECK_LIMIT 1500/台/轮 + **重查 15% 保底配额(225)防饥饿**
- seen 只锁命中者;未命中 45min 可重查;seen 文件跨轮持久(/tmp/bk8_seen_N.json)
- 预算看板:orch 每轮写 /data_pool/biz_budget.json(req/hits/cool)

### merger(daemon 120s)
- get_collectors() 优先 jumpers.json;连接 key 优先(~/.ssh/id_ed25519)+密码兜底
- rsync 拉 /tmp/v6_heartbeat.json(含 disk 字段)→ health.json(含 disk_mb;bot 告警 <1GB)
- _merge_cstats 汇总 12 台 cstats → collector_budget.json
- 失败计数:连续 ≥3 轮才告警(_rsync_ok 成功清零)

## 平台认知补充(认证/审计,与 09-11 reference 合并使用)
- 审计接口=实时滚动窗(最近几百行),**不可回溯**;collector 停机窗口由 12 台冗余兜底
- 审计 detail 只有 redirectEnrollUrl 类跳转带 ST(7% 行);批量报名/工作台静默提交无逐条行
- 历史 token 调 user/info 必 404(会话短命)→ **回溯验证只能 username 文本筛,不能靠 user/info**
- 竞价日=收敛窗口:企业 cg 进场触发增强认证 → tokenrailquery 有记录 → orch 补

## 全链路冲突审计结论(2026-09-11,全绿)
1. collector 分片/票分片均 %12 与 12 台一致 ✓
2. ent_coverage 12 台 md5 一致(gen_gap 每 6h jumpers 动态推送)✓
3. stage 过滤 orch8b/gen_gap/bot 统一(报名中/待竞价/竞价中)✓
4. 机器列表 merger/gen_gap/orch8b 全 jumpers 动态 ✓(v9.15 后无死角)
5. v9.12/13(collector)与 v9.14/15/16(orch 系)文件进程独立无交叉 ✓
- 已知限制(记账):cool_cnt 各台独立(跨台协调未做);biz_budget 已双看板(orch+collector);giveup 每轮重置浪费少量请求(不丢票)
