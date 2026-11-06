# 95306 v7.24+ ST 利用率与"进行中全覆盖"实录

## 背景
用户核心目标:进行中项目的企业+精确包件 ID 零缺失。ST(登录票据)是企业包件数据的前置凭证。

## 利用率惨案(4.7%)
- seen_st 一次性标记:ST 失败即永久放弃,哪怕还有 29 分钟 TTL
- 43 个 ST 只成功 2 家(合肥日航 pldwsw / 黑龙江旭荣 XR112233)
- 日志:审计 ST 22, 新 0 —— 全是历史过期票

## 修复(collector 三层机制)
1. 失败票 → retry_st 队列 {st: {acct, tm, tries}},TTL 30min 内每轮重试
2. 成功才永久 seen_st;过期才丢弃
3. 审计窗口 30 分钟内票(含 seen 失败票)每轮补拉(cutoff 比较 operation_time)
4. 审计分页 2→3→5 页(100/页),覆盖竞价日爆量
5. 日志加"识别 N, 重试队列 N"可观测

## 统计口径(bot 搭建以来)
- 抓取去重 = len(seen_st) 4 台相同(审计同源)
- 利用 = 全部尝试过(seen 即尝试)
- 成功 = 日志"  acct (用户名/单位)" 行去重

## 因果实锤(packId 缺失)
- 全局 6247 个项目有 pack_map:6225 非空(历史导入),22 个空 = 全部实时项目
- 无 ST → getBuyPackageList 拉不到 → 企业 packId 缺失
- 反证:有票企业 packId 全有

## 探测结论
- auditlog 无鉴权 200;其他 funcId(11 个)全部"不存在的功能"
- 业务接口 403 "Could not verify the provided CSRF token because your session was not found" = ST 过期(Authorization: ST + Referer cg.95306.cn/bfwz-view/ 是正确头格式)
- GET vs POST 路由差异:getBuyPackageList 用 GET + query string(采集机方式),POST body 会 500/403

## 用户核心观点(策略约束)
"进行中才有价值"——报名期/竞价期实时数据才有决策价值;竞价结束后的公示补拉/兜底补全无价值。策略:专注进行中全覆盖(审计 ST 被动捕获 + 审核员账号主动全覆盖),不做事后补全。

## 时区陷阱(告警误判排查)
- 主服 UTC,采集机北京时间(UTC+8)
- health.json 心跳时间戳是采集机本地(北京),主服 security_watch 按 UTC 算 gap → 告警时间戳看起来"是旧的"
- 排查顺序:先对表主服 `date -u` vs 采集机心跳 ts,再判断 gap 是否真实
