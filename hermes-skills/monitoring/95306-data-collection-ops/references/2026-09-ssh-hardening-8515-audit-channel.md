# 12台 SSH 全加固 + 8515 无鉴权审核状态通道(2026-09,体系尾期升级)

## 1. SSH 安全加固(pubkey-only,12/12)

- 采集机 sshd 全部 `PasswordAuthentication no`(前 4 台早已改;沪4-深7/新4台 9 台补改)。
- **服务名坑:阿里云镜像是 `ssh` 不是 `sshd`** → `systemctl restart ssh`(restart sshd.service 报 Unit not found,配置已改但服务没重载=未生效)。
- 12 台 authorized_keys 只认主服 `~/.ssh/id_ed25519`(尾 rpICY4s/... root@jnjjn);本地运维下载副本到 `~/.ssh/95306_ed25519` 供 Windows 侧 paramiko key_filename。
- 改后连锁适配(必查清单,漏一个=那台失联):
  1. merger.py pull_one 连接:key 优先(password 兜底自动失效,key 全通即可)
  2. orch8b conn():key 优先 + 密码兜底(v9.15 已改)
  3. gen_gap push_to_collectors:早已 key 优先 ✓
  4. 本机(Windows)直连后 8 台:改 key_filename;前 4 台安全组只放行主服(本机直连必 WinError 10060)→ 走主服中转 scp/ssh
- 弱口令攻击面:12 台曾全同密码(Ppikesi101./Ppikesi0001./juxingjiba123.)=一处泄露全失守;加固后密钥单点(保管好 95306_ed25519 与 v6_master_key)。

## 2. 8515 快照 = 审核状态无鉴权通道(bid_package_bidder_business23)

- dataplatform findList 无鉴权 funcId `bid_package_bidder_business23`,collector fetch_8515_snapshot 每 6h(SHARD 0)拉近 7 天窗(8 页×100,~800 条/次)→ /tmp/targets/8515_快照/<ts>.json → merger 拉回。
- **原始行字段(全):** proj_id/pack_id/**bidder_name**/bidder_id/buy_time/**status**/**check_peop/check_time**/current_price/current_price_time/phone/dwcode/uuid/valid_or/isblackliststate…(行粒度=企业×包件!)
- **status 码与 getBuyPackageList 的 bidderCheckStatus 同源**(pack_map 实证):01=通过 / 03=拒绝 / 22=中标 / 00=待审。
- 用户记忆核对:"渗透能直接拿包件审核状态,只是看不到具体包件 id" = 该接口有 pack_id(uuid)但无 packCode/packName(给人看的包件编号/名称要 join 包件清单)→ 语义吻合。
- **历史 bug**:merge_8515_snap 只留 proj→pack→{buy_time,status,src}(丢 bidder_name/check_time)→ 通道只喂 check_gaps 缺口核对,审核状态从未回写 pack_map。
- **v9.16 升级**:merge 保留 `bidders:{企业名:{status,check_time}}` 层 + `audit_writeback()`:按 (proj, bidder_name==企业.单位, packId) 匹配回写 pack_map 包件 审核码/审核状态(映射名)/审核时间 → 6h 级全量审核刷新,不依赖 ST/登录,采购类项目也覆盖。
- 对比另一候选接口 `aggregation_bfwz_bfwzpackage_a`(已结束包件含 pack_id)→ 已挂(code=-1 处理异常),别用。

## 3. 包件审核状态获取途径总表(答复"有哪几条途径")

| 途径 | 状态 |
|---|---|
| getBuyPackageList(带 ST 拉包件,含 bidderCheckStatusName) | ✅ 主力,采集时点快照(快照过期:审核动作后不重拉就旧) |
| 被动重拉(榨干/竞价日/再登录顺带刷新) | ✅ 事件驱动,低频不可控(截止后审核集中期恰恰没事件) |
| **bid_package_bidder_business23(无鉴权,8515 快照)** | ✅ v9.16 回写后=6h 全量刷新,最优通道 |
| biddingandsellingsupplier 名册 | ❌ 行无审核字段 |
| 审计通道 | ❌ 平台审核是内部账号操作,无供应商票且滚动窗不可回溯 |
| 审计日志解析审核操作 | ❌ 证伪:只有企业资质审核(变更/复核),无报名包件审核操作 |

## 4. 12 台职责冗余原则(哪些冗余有价值)

- **审计抓取 12 台全冗余 = 特性**:①单台停机不丢行 ②冷却对冲——同票 12 台错峰重试总有台在限流窗外成功(泽盛案例:广州 23:23 成功,上海被冷却 23:52 才成功;没有冗余那张票永久丢)。
- enroll 报名票 12 台全处理(幂等,量小)= 保留。
- **确定性数据全冗余 = 无效冗余 + 限流风险**:bidRoom 出价抓取(同一 ST 拉同一项目,数据相同)曾 12 台全跑 → 改 `SHARD_ID % 4 == 0` 3 台轮值(每台每 30min 还省 6min 卡循环)。
- 分片(普通票/企业/反查 md5%12)+ 定向冗余 = 最优形态:同构简单 + 无单点 + 冷却自愈。

## 5. 其它尾期参数(12 台规模)

- orch8b:BOXES 从 jumpers.json 动态读(v9.15,与 merger/gen_gap 统一,bot 增删机器自动生效);ROUNDS=len(BOXES);cron `2-59/5 * * * *`(5min,错开 sync 0/10/20 与 gen_gap 8/18/28);CHECK_LIMIT=1500 + 重查 15% 配额(225 保底防饥饿)。
- collector 审计三档:audit_lv 0/1/2(60s 内 ≥100 条/≥300 条)→ 页数 6/16/31;档 2(严重)只 `SHARD_ID%3==0` 的台升 31 页(12 台冗余,1/3 深翻即覆盖,防 12 台打爆审计接口)。
- sync 名册翻页 30→60 页(30 天滑动窗 1.4 万行已用 94% 上限)。
- collector 当日统计插桩(STATS/audit_pages/ui_ok/ui_fail/cool/bid_req)→ /tmp/v6_cstats.json → merger _merge_cstats → /data_pool/collector_budget.json(与 orch biz_budget 并列,预算全貌)。
- bot check_health 磁盘告警:heartbeat 自带 disk 字段(早已有)→ 补 <1GB 告警/≥2GB 解除。
- notices_map 公告拉取 8 页(7天)→30 页(30天)。
- 竞价室 bid_live 抓取已部分实现(collector bidRoom/initProjInfo + bid_status 推导;v9.3 skip 失败项目 1h)——朋友 9/8-9/9 加的,交接时别再说"未实现"。
