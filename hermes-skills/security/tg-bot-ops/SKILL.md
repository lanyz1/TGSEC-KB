---
name: tg-bot-ops
description: "TG数据推送bot开发运维: 菜单/状态机/交互陷阱。触发: tgbot, 推送助手, bot功能。"
---

# TG 数据推送 Bot 开发与运维(TG Bot Ops)

## 适用场景
用 Python + long polling 开发/迭代数据推送 bot(数据池 → TG 查询/下载/推送),典型形态:采集机产数据 → 主服合并 → bot 读取文件系统提供查询/下载/订阅推送。本技能沉淀完整可复用的 bot 工程模式与用户明确要求的交付规范。

## 用户交付规范(明确纠正过,必须遵守)
1. **更新公告只推本次内容**——push_update(version, changes) 只含本次新增/优化/修复,绝不重复之前版本推过的条目;CHANGELOG.md 同步只记本次。
2. **静默重启**——bot 重启/内部操作**不推"已上线"消息**(无信息量);启动只写日志。推送 = 更新公告/每日汇总/周报/订阅事件/健康告警。
3. **下载要"随心所欲"**——不接受固定文件下载,必须支持:条件筛选(路局×物资×状态×时间)→ 勾选项目(分页)→ 挑字段(全字段/精简/仅项目/仅企业/仅包件)三级挑选。
4. **所有功能可点击**——用户中心仪表盘(/start)= 动态数据总览 + 全功能 inline 按钮;☰ 输入框菜单按钮用 setMyCommands + setChatMenuButton。
5. **管理员自主服务**——授权管理/跳板机新增更换等操作管理员在 bot 内自助完成,不找助手。

## 核心架构模式

### 菜单/回调体系
- 用户中心 `/start`:动态统计(项目/包件/企业/加速器状态/订阅数)+ 全功能按钮矩阵。
- 回调 data 命名:`main/pool/bidday:0/1/2/3/qryset:bureau:2/proj:<36位pid>/qrydl:sel`。
- **callback_data 64 字节限制**:完整 36 位 UUID 可以放(proj:xxx=44B),不要用前缀截断(前 20 位有 ~2% 冲突概率)。
- 分页导航:`bidday:{mode}:{page}`、`qrypage:{n}` 格式,页码进回调。

### 状态机输入(PENDING_INPUT[cid] = 模式)
文本输入流:collect(收集项目)/ addauth(添加授权)/ jumpadd(新增跳板机)/ jumpswap:{old_name}(更换)。
- 回调设置模式 → 提示输入格式(带示例)→ handle_text 优先检查 PENDING_INPUT → 处理完 pop。
- `/cancel` 或"取消"必须可退出。
- 模式值可携带参数:`jumpswap:{old_name}` 用 startswith 匹配。

### 定时线程(daemon 线程,不阻塞主循环)
- `daily_checker`:每日 20:00 汇总 + 周日 20:30 周报(用 last_day/last_week 去重)。
- `sub_checker`:每 60s 检查订阅项目变化(新报名/审核状态变化/竞价开始结束)→ broadcast。
- `health_checker`:每 5min 检查采集机心跳,异常推送告警(alerted 文件防重复)。
- 状态文件无锁读写(sub_state.json/health_alert.json)——低频小文件可接受,异常全 try/except。

### 权限分层
- `ADMIN_IDS`(硬编码)+ `users.json`(动态):admins + allowed。
- 鉴权函数 `is_allowed(uid)` 实时读文件(新增授权立即生效,无需重启)。
- 管理功能按钮仅 is_admin(cid) 可见;**回调处理内也要二次校验**(伪造回调防护)。
- broadcast 目标 = admins + allowed(新授权用户自动进广播)。

### 数据池对接(文件系统即数据库)
- `/data_pool/<projId>/{项目信息.json, pack_map.json, 包件清单.json, bid_status.json, bid_live.json}` + `index.json`(全量索引,带 live 标记)+ `汇总/` + `企业档案/` + `供应商/`。
- bot 读 index.json 内存缓存(30s)+ 按需读项目文件夹;13K 项目内存 dict 可行。
- **merger 写 index/pack_map 必须"读旧值合并",不能整体覆盖**——否则历史导入的数据(8515/08文件)会被实时数据挤掉(实测坑)。

## 交互陷阱清单(两轮审查成果——"看似能实现、操作困难"的暗坑)
1. **主线程重活卡 bot**:遍历 13K 项目读文件(排行)→ 缓存 10 分钟;CSV 生成/文件发送 → threading 后台,完成自动发。
2. **大文件超 TG 50MB**:生成后检查大小,超限提示缩小范围;下载前限制项目数(>1500 提示加条件)。
3. **分页刷屏**:翻页必须 editMessageText 编辑原消息(记录 msg_id);**edit 失败(超48h/被删)自动降级为新消息**,否则内容消失。
4. **固定 sleep 等待远程命令**:用 exit_status_ready() 轮询等真实完成,否则超时误报"失败"。
5. **假成功**:加速器 4 台切换必须逐台报告 ✅/✗,失败计数并警告,不能笼统"已切换"。
6. **列表无分页**:任何"还有 N 个..."提示都是失败设计——必须翻页按钮。
7. **顺序随机**:os.listdir 顺序不定,企业搜索先精确匹配再模糊。
8. **无反馈按钮**:noop 等占位回调要 answer_cb 提示"暂无更多"。
9. **Markdown 注入**:项目名/企业名含 `_*[]` 等 → send_msg 400;失败自动降级纯文本重发(parse_mode 弹出重试)。

## 跳板机自助管理(管理员闭环)
- 配置 `jumpers.json`:collectors[{name,ip,port,pwd,role,ts}] + master。
- 状态页 = health.json(merger 汇总各机心跳):✅正常(gap<300s)/⚠️异常(gap≥300)/🚫封禁(WAF blocked)/❌无心跳。
- **WAF 封禁探测**:采集机每轮复用审计请求的状态码(403/429/5xx → heartbeat 标 blocked)——零额外请求。
- 新增/更换流程(bot 内状态机):输入"名称 IP 端口 口令 角色"→ 后台线程 SSH 验证 → 上传 collector.py → pkill+setsid 启动 daemon → 写 jumpers.json → 提示"≤5min 心跳上报"。
- 更换 = 部署新机 + 旧机标记 disabled(数据保留)。
- 操作权限:状态页所有人可见,新增/更换仅管理员。

## 推送格式规范
- 更新公告:`🔔 **<bot名> <version> 更新公告**` + 分区(🆕新增/🔧优化/🐛修复/📊状态)+ `👉 发送 /start 查看用户中心`。
- 订阅事件:`🔔 **<项目名>**` + 事件(🏢新报名/📋审核变化/⚡竞价开始/🏁竞价结束)。
- 告警:`🚨 **采集机告警: <机名>**` + 状态/心跳,dedupe 文件防重复轰炸。

## 参考案例
- `auditlog-ticket-harvesting` 技能 references/95306-session10-v6-tgbot-v3.md — 95306 数据池 bot 全量部署实录(采集/合并/推送链路)。
- `remote-daemon-ops` 技能 — daemon 部署/pkill 自杀/setsid 保活/双调度(pkill 自杀的 [x] 技巧与杀启分离必须遵守)。
