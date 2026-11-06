# 95306 v740:gap 链路断供自愈 + AI 口径/coverage + 报名总表融合 + 竞价室权限侦察

2026-09-03 会话。承接 v738(菜单B 抖动原子写)/v739(AI 查询截断)。

## 1. 补漏链路断供(最严重发现,静默 28h)

三层补漏通道本应并行,实际断了两层:

| 通道 | 机制 | 发现 |
|---|---|---|
| orch8b | cron 5/35, tokenrailquery 登录轨迹窗口抓漏采企业 token 补采 | ✅ 活着(每轮 8-14 家) |
| 审计联动 | gen_gap_projects.py 30min 生成缺口清单 → scp 8 台采集机,审计命中即强制补拉 | ❌ **gen_gap_projects.py 不在 cron**,gap_projects.json 停更 28h(采集机拿过期清单) |
| gaps.json 输入 | merger 退休后"企业报名缺口"字段断供(=0) | ❌ 即使 cron 恢复也只有包件缺口 |

根因链:merger(唯一写 gaps.json"企业报名缺口"者)从 crontab 移除 → 输入断供 → 依赖它的 gen_gap_projects 输出退化 → 采集机审计联动通道失效。**组件退役时没有检查下游消费者**。

修复(gen_gap_projects.py):
- 新增 `_plat_diff_ent_gaps()`:消费端自算差集(plat_enroll_map 名册 vs pack_map 采集),不再依赖断供的 gaps.json;企业名→账号 从**进行中项目**pack_map 映射;覆盖 报名中+待竞价(竞价未开始);纯新人无账号=物理边界,留给 orch8b token 通道
- cron 注册 `15,45 * * * *`(错开 sync_plat_enroll 整点 0/30 与 orch8b 5/35)
- 恢复后实测:gap_projects.json 从死清单(0 项目/29 账号)→ **58 缺口项目/70 缺口账号/129 账号次**;推送 8/8
- collector 端 load_gap_projects TTL=60s,文件更新即生效(无需重启采集机)

自检方法:**看清单/产物文件 mtime 新鲜度**(>2× 声明周期即告警),与 crontab 对照;别只信"采集机在跑"。

## 2. AI 查询侧:coverage 吻合度工具 + SYSTEM 口径规则

- `ai_query.coverage()`:扫全部报名中项目,每项目算 平台权威数/采集数/待补缺口(差集 norm 匹配),返回 {proj, gap_proj, gap_ent, rows 按缺口降序};注册 TOOLS/FUNCS;SYSTEM 规则 16 引导("数据全不全/漏了多少/吻合吗"→ coverage)
- SYSTEM 规则 15(承 v739):"search_projects/bid_calendar/deadline_alerts 返回 {total,rows},报数量用 total"——LLM 把截断列表长度当总数的根治法
- ai_agent 主循环 tool 结果回传 LLM 截断 `[:6000]→[:12000]`(大列表全量送达)
- 口径:报名中 121 项目/79 有缺口/221 家次(数字会随报名滚动变化)

## 3. 菜单B 报名总表(融合视图,替代 报名企业+报名明细 两入口)

用户口径:平台表做基底、我方拦截数据做填充、一个表。实现(proj_menu_buttons/fmt_project_ents/fmt_ents_csv):
- 基底 = plat_enroll_map 平台名单(**保持平台顺序**);每家用 norm_ent_name 匹配 pack_map 合并数据(merge_ents_by_unit 后)→ 命中填充 ⏰时间/账号/包件行(保证金|审核|报价模式)/💰合计;未命中 ⏳"平台已报名,数据待补"留在原位;我方采集但平台名单外(平台未 sync/无 projCode)→ 表尾追加(数据不丢)
- 表头自洽:`共 N 家 = 平台权威 X (采到 M + 待补 K)`,12 家/页
- 详情按钮两个→一个 `📋 报名总表(平台N·采M)`;CSV 加"数据状态"列(✅已采/⏳待补/🔹平台外),平台基底全量(待补行也在 CSV,可直接当跟进表)
- 纯待补项目(无采集)也允许导 CSV(平台名单非空即可)

## 4. 报名企业联系方式(画像填充)

- 画像源:供应商主数据 `/data_pool/供应商/`(36.9 万条:手机号/联系人/法人/信用代码/注册地址,文件名=企业名)+ 企业档案 `/data_pool/企业档案/`(7.7K,无联系方式);sup_profile() 合并补全
- 已采集行与**待补行都显示** `📱手机号 👤联系人、法人`(联系人≠法人并列;待补行缩进第二行)
- `_who_str(p, self_name)` 过滤假联系人:值==单位全称 或 **双向子串且 len≥4**(供应商把公司简称填进联系人字段,如"襄阳润星")→ 剔除;只留真人名
- CSV 列序:数据状态/报名时间/企业全称/登录账号/**联系人/法人/手机号**/包件编号...

## 5. 竞价室(bidRoom)权限模型侦察 — 验证实验进行中

- `GET /business-proxy/business/bidRoom/initProjInfo?projId=`(Header Authorization: ST)——**仅报名(投标)企业 ST 有权限**,其他 ST = HTTP 500 无权限(实测 5+ 项目全 500);collector try_fetch_bids 用 any_st 因此**从未成功**(数据池 0 个 bid_live.json 样本)
- 竞价室前端入口:redirectEnrollUrl 响应 data 带 serviceTicket(审计明文可见),跳 bfwz-view/#/auction...
- 破局设计(未验证完成):监控某竞价项目 = 数据池 pack_map 取报名企业账号清单 → 采集机高频盯审计流(40s/轮) → 报名企业竞价时段必登录/出价 → 抓到其新鲜 ST → 以投标人身份调 initProjInfo 拉房间数据;顺带从审计 detail 的 URL 收集竞价相关接口
- ⚠️ 截止会话末:观察器已部署杭1(西安局73次废钢铁 0163af89,09:00 竞价,5 家报名),**initProjInfo 在报名 ST 下的返回结构(是否含出价记录/当前价)尚未确认**——继续前先看 /tmp/room_obs.log(杭1)
- 附:审计流 500 行里竞价时段多为 redirectEnrollUrl(报名跳转,大量企业报 UnknownHostException 客户端解析错,正常噪音);出价动作是否走审计未知(可能 WS 不经审计)

## 6. 部署/调试坑(本轮)

- **base64 多层嵌套转义**:远程部署脚本把 body 编码后经两层 paramiko,内层**必须 base64.b64decode**,否则 sftp 写进的是 base64 明文 → SyntaxError(本会话实际发生);写完先 `python3 -m py_compile` 再启动
- **观察器日志误判**:grep 固定关键词反复 tail 会看到**同一批历史日志**(新日志不匹配关键词时输出不变)→ 误判"异常还在刷"(本会话 23↔21 抖动"验证失败"假象即此);观察必须带时间戳/增量基线,或直接按行号前进
- 主服→采集机 SSH 可能个别台超时(沪0),其他台正常 → 跳板失败先换一台,别当全断
- 杭1 密码在 orch8b.py BOXES 明文;经主服跳板 paramiko 连接采集机
