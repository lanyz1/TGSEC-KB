# 2026-09 第二轮运维:收敛闭环/AI 口径/状态机/竞价室侦察

## 1. 缺口收敛双通道(全貌,含断链教训)

补漏实际两条通道,2026-09-03 发现审计联动通道**断链 28h**(gap_projects.json 停在 09-02 03:00):

| 通道 | 组件 | 机制 | cron |
|---|---|---|---|
| token 窗补采 | orch8b → bk_worker | tokenrailquery(登录轨迹)按 30min 窗轮转查漏采企业活跃 token(user_type=03 供应商 token 即 ST,直用不换票)→ user/info 验 dwhz 归属 → getBuyPackageList 拉包件 | 5,35 |
| 审计联动补拉 | gen_gap_projects → gap_projects.json → 8 台 collector | 采集机每轮拉审计,审计行命中缺口 projId/noticeId/**账号** → 该票强制拉包件(企业一动即补,不等 30min 轮) | 15,45 |

**断链原因(两处,均已修)**:
1. gen_gap_projects.py 不在 cron(曾只挂 sync_plat_enroll+orch8b)
2. 它的输入 gaps.json"企业报名缺口"由 merger 生成,merger 停摆后断供 → 输出只剩"项目包件缺口"

**修复**:gen_gap_projects.py 新增 `_plat_diff_ent_gaps()` 自算 plat_enroll_map 名册 vs pack_map 差集(不再依赖 merger 输入);企业名→账号从**进行中项目 pack_map 里同单位映射**(纯新人无账号=物理边界,只靠 orch8b token 窗);cron 注册 15,45(避开 sync 整点与 orch8b 5/35)。
- 验证:gap_projects.json 从 0项目/29账号(死)→58项目/70账号(活);8/8 台推送成功
- collector `load_gap_projects()` **60s 重读一次**,推送后 1 分钟内生效;ent_coverage 300s 重读
- 命中优先级:审计行 projId∈gap_projects > noticeId 映射 > operation_account∈accounts

## 2. AI 工具"总数全量+列表截断"bug 家族(2026-09-03 十堰 18=6+10+2 事件)

症状:AI 答"平台 18 家=采 6+待补 10"漏 2 家。根因 `ai_query.py project_enterprises` 返回 `"pending": pending[:10]` **写死截断**,LLM 拿不到被截部分 → 数量对不上且自洽地答错。
全库审计发现同模式多处,修复原则:
- **凡返回 count/total 字段 + 截断列表,必须两者同返**(LLM 用 total 报数量)
- search_projects/bid_calendar/deadline_alerts:去 break 全量统计 → `{"total": N, "rows": 截断列表}`;消费方(scan_watches 等)同步适配 `hits.get("rows")`
- project_enterprises 加 `ent_total`+`pending_total`;ents/pending 默认 limit 提到 100
- audit_status 已有 total dict 兜底,明细 30→100;notice_search/search_enterprise 10→30/50(IO 重保留 break,纯展示型)
- **ai_agent 工具结果回传 LLM 截断 [:6000]→[:12000]**(函数全量返回后这层才是真瓶颈)
- SYSTEM 加规则:"返回 {total,rows} 时报数量一律用 total,rows 不够建议导出表格"
- 另一个:bot 端菜单/推送里 projName 切片 [:22]/[:28]/[:30] 显示不全 → 统一 [:80];企业名 [:18]/[:22]→[:30/40];CSV/xlsx 导出项目名去截断全名
- **验证教训**:验证脚本打印字段要打全(regEndtime vs sellEnddate 只打一个会误读),单测用构造数据(fake reg=2099 项目)验证门槛分支

## 3. 平台状态滞后 → 时间推导流转(2026-09-04 合肥/成都项目事件)

平台 selectSelfSellList 的 status 流转**滞后**:合肥项目报名截止(regEndtime=202609031700)2h+ 平台仍 status=19(发布中);成都客车项目平台一直 19,靠 regEndtime 推导。**结论:业务侧流转不能等平台,用公告截止时间推导**。

bot `blockable_projects` 规则(现版):
1. stage=报名中 且 regEndtime/sellEnddate 解析值 < now(北京时间 UTC+8!)→ 归 🟡(报名结束未竞价)
2. **放开 DEPLOY_DAY=2026-08-31 部署日过滤**(当时防"部署前公告=报名真空";plat_enroll 名册+orch8b 补漏兜底后已过时,全量纳入)
3. regEndtime 格式两种:`202609031700`(yyyymmddHHMM,公告解析回填)与 `2026-09-03 17:00`;解析 helper `_deadline_dt` 多格式试
4. **时区坑:regEndtime/bidStarttime 是平台北京时间,主服 datetime.now() 是 UTC → 比较必须 +8h**(`_bj_now_dt = datetime.utcnow()+timedelta(hours=8)`);orch8b 加待竞价窗口判断同样要 +8

**采集完成(✅)硬门槛**:`collect_complete_projects` 判定前先查 regEndtime/sellEnddate,未到 → 归 open(不算完成)。防"平台/推导提前切待竞价 → 采集数=名册数 → 误标完成"。
**merger `_stage_of` 保守化(1b)**:报名截止时间缺失(平台接口无+公告解析失败)时,按平台 status 判定:19→报名中,22→待竞价;**绝不直接落"待竞价"**(老逻辑第 4 分支无 sell 就 return 待竞价 = 提前误标源)。
- 平台 status 语义:19=发布中/报名中(滞后!),22=待竞价(报名期~竞价开始混合),13=竞价中,14=已结束;merger stage 纯时间推导只认 14 特判

## 4. 菜单B/数据池读写稳定性

- **原子写**:orch8b/merger 所有 pack_map.json/index.json 写点 → tmp 文件 + os.replace(曾因非原子 open(w) 半写窗口,bot 3min 监控读 json.load 崩 → 整项目归零 → 假推送 23↔21 抖动;菜单B监控日志 `[菜单B监控异常] too many values to unpack` 与假推送同源)
- **tuple 解包 bug**:`for pid, (op0, cu0) in diffs[:4]` 应为 `for pid, op0, cu0`(真实审核变化推送会崩+丢状态)
- merger 由 **bot 周期 subprocess 调**(pix_bot_server L3535 `timeout 180 python3 merger.py`),index.json `updated` 字段每 ~2.5min 变;不是独立 daemon
- **观察器/诊断误读坑**:后台 grep 日志观察器若只匹配关键词,新日志多为用户 CB 操作(不匹配)→ 每轮输出几乎不变 → 误判"异常持续";判定修复效果要看**时间线**(进程重启点前后)+ 完整日志,别信重复的 grep 窗口
- **性能**:`norm_ent_name` 曾线性扫 36.9 万供应商名单(91 项目×每企业×2 遍 = 上亿比较,全库 collect_complete 卡死数分钟)→ 加 `_sup_key_index()` norm-key→全称 dict 索引(600s 缓存)后 O(1);**凡全库循环内调用归一化/匹配函数必须先索引化**

## 5. 竞价室侦察(2026-09-03,半成品)

- 竞价室接口 `bidRoom/initProjInfo?projId=`(cg.95306.cn/business-proxy/business/,Authorization: ST):**非报名企业 ST 一律 HTTP 500**(含"请联系技术支持"业务错误文本,collector 冷却判定已排除该词防误触发);collector try_fetch_bids 因权限墙从未成功过(数据池 0 个 bid_live 样本)
- **竞价系统真身在独立域 `bid.95306.cn/api/execute-server/`**(审计日志 URL 可暴露:skipJoinPage 等);报名跳转 redirectEnrollUrl 响应 data 带 serviceTicket(审计明文可抓)
- 可行监控路线(验证中):用户给 projId → 取该项目报名企业账号(pack_map)→ 采集机盯审计流 → 报名企业竞价时段登录/出价瞬间的新 ST → 用它调竞价室接口(投标人权限)→ 变化推送;企业不活跃=物理边界
- 观测实验模板:候选项目选 bidStarttime∈[now-1h,now+2h] 且 pack_map 非空;观察器 setsid 到采集机本地跑(不依赖主服 SSH 长连接),主服轮询日志文件;脚本输出必须 flush=True(重定向文件时 stdout 全缓冲,进程没退出=文件空,易误判卡死)

## 6. 部署/测试模式沉淀

- 远程改代码:SFTP 整文件上传最稳(write_file 内嵌 python 经 JSON/base64 多层转义反复翻车:`\\n` 双层变字面 \n);文本替换 patch 易毁缩进 → 整函数/整段 patch + py_compile
- import pix_bot_server 测试:主服弱 CPU,import 本身不慢(实测 0.0s),慢点是逻辑里隐藏的全量线性扫;测试脚本 setsid 落盘 + flush 输出 + 轮询文件(exec_command read 超时是惯例假象)
- 时间:主服 UTC,用户/平台北京时间 UTC+8,一切日志对照先换算
