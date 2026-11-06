# 95306 报名企业核查与枚举(v6 系统,2026-09 实踩)

触发:用户质疑"报名企业数不对 / 只有一家不合理 / 最少N家才能竞价"——判定项目到底几家报名+审核状态。

## 架构必读(防串台,本次大坑)

- **主服** = 128.241.245.73:12971(root + Ed25519 `v6_master_key`):`/data_pool/<projId>/` 数据池 + `/opt/v6/pix_bot_server.py`(bot 进程 677045)+ merger.py
- **采集机** = 8.133.188.178(root 口令):`/opt/v6/collector.py`(37,699B)+ **ST 池 `/tmp/v6_state.json`** + `/tmp/targets/`
- 三层 SSH:本机 → 主服(私钥)→ 采集机(口令)。审计/8515/公告查询从采集机发起可通
- **踩坑:在主服上 ls /opt/v6 看不到 bot 是正常的**(那是采集机视角);数据池只在主服。先确认你在哪台。
- **写三层远程脚本严禁 r''' 嵌套 r'''(内层 ''' 直接截断外层字符串,代码泄漏到本机执行!)。正确姿势:每层一个独立 .py 文件,本机 → sftp → 主服 /tmp/ → sftp → 采集机 /tmp/ → exec。**

## ST 池结构(/tmp/v6_state.json)

- `seen_st`:216 个全部见过的 ST(**全量枚举的数据源**)
- `st_times`:ST → 首次见到时间
- `enroll_ops`:`notice:<公告id>` → `{账号: 时间}`(**谁跳转报名过哪个公告,直接可查**)
- `full_done` / `giveup_st` / `enroll_st` / `retry_st`:全量完成/放弃/报名/重试账号
- **ST 时效远超 30min TTL**:8/31 17:28 的 ST 在 9/1 01:56 仍可用(getBuyPackageList 不严校验)

## 报名企业全量枚举(核心方法)

- **pack_map.json 只是单 ST 视角**(抓包件清单时用了谁的 ST 就记录谁),**不能证明没有其他企业**——本次误判根因
- 正确方法:遍历 `seen_st` 全部 ST,逐个调:

```
GET https://cg.95306.cn/business-proxy/business/supplierPackage/getBuyPackageList?projId={pid}
headers: Authorization: <ST>, Referer: https://cg.95306.cn/bfwz-view/
```

- 返回 `data` 非空 = 该 ST 企业报名了此项目(含 packId/packCode/packName/frontMoney/bidderCheckStatusName 审核状态)
- 216 ST × 0.15s ≈ 1 分钟;仅限低频核查,勿常态化(限频纪律)

## 审计日志技巧

- `/auditLog/page` 不带 ST 直接可调,从日志抓最新票
- **等值条件不生效,必须 like**(`operation_account=zzzdx2` → 0 条;`operation_username like %紫达祥%` → 命中)
- `noticeRedirectToUrl` 的 detail 含**完整跳转 URL(projName + serviceTicket)**——可实锤"公告→项目"归属,防止张冠李戴(案例:71f970ee 实为"10次二次"项目公告,不是 13次;跳转 URL 里 projName 直接可见)
- 审核员(复核/审批)操作 detail 不带 ST → 审批员票拿不到
- 报名"提交"动作在 bfwz 域,不进 cg 审计(审计只记 redirectEnrollUrl 跳转)——跳转 ≠ 提交成功

## 8515 快照表(bid_package_bidder_business23)

- findList 过滤用 **`params` 字段(数组格式),不是 condition**
- 统计验证平台规则:162 项目 / 602 包件,1家竞价 10 个、2家 13 个 → **"最少3家"不是硬规则,1-2 家也能正常开拍**
- `bidder_name` 字段全空(不导出企业名);数据同步滞后(曾停在 8/28);bfwz 新域项目不入此表

## 接口权限矩阵(企业票)

- **500"您没有该功能的操作权限"**(需审批员角色):`/bfwz/bidPackageBidder/packCheckList`、`bidPackage/queryBidPackageDetail`、`bidRecord/selectBidRecordList`、`bidProject/selectBidRecordList`、`bidPackageBidder/selectBidderList`、竞价室 `/bidRoom/*`
- **403 CSRF**(需 session):公开公告接口 `noticeSearch` / `queryNoticeList` / `baseQueryService/*`;GET 打 POST 接口命中 Thymeleaf 模板错误
- findList funcId 枚举业务表名:全部 -1(HTTP 层错误),不可行

## 数据池目录结构(/data_pool/<projId>/)

- `pack_map.json`:`{targetProj, enterprises{账号:{账号/用户/单位/ST/时间/包件[]}}}`
- `包件清单_公告.json`:**含公告id!** → 用 enroll_ops 匹配谁跳转过该公告
- `企业包件表_18列_<projCode>.csv`:企业全称/账号/包件/审核状态/审核时间/报名时间/竞价开始 等 18 列
- `项目信息.json`:`{projName/projCode/bidStarttime/status}`
- `包件清单.json`:`{包件数, 包件[{packCode/packName/保证金/竞价开始/竞价结束}]}`

## 核查流程(按序)

1. 数据池项目目录 → `包件清单_公告.json` 拿公告 id → `enroll_ops` 匹配跳转账号
2. 审计 like 查这些账号的 `redirectEnrollUrl` → detail 里 projName 定项目归属(可能跳的是别的项目!)
3. ST 池全部 ST 查 `getBuyPackageList(projId)` → 非空 = 报名企业(含审核状态)
4. 8515 快照分组统计 → 平台规则参考(1-2 家也正常,用户"最少3家"的预期不一定成立)
