# 招标/竞价平台参标方管控接口实测表 — zb.lyc.cn(优智采白标) 2026-09

身份:洛轴采购人 `setest0606`(公司 `b672fa7d-6881-4418-a33b-1352d2b28b6e`,roleId=2 **全部权限**)
网关前缀一律 `https://zb.lyc.cn/gateway`;票:`POST /gateway/evaltool/user/getEvalToolsLogin`
`{userAccount,password,userType:2,captcha:"0000"}` → `data.accessToken`(自带 `Bearer ` 前缀,别再叠一层)。

> 状态标注:**✅实测过** / **⏳接口与鉴权实测、业务写入未执行**(活场未动手)

## 1. 定位(只读,✅ 实测)

| 用途 | 接口 | 结果 |
|---|---|---|
| 列参标方(拿 bidderId) | `GET /supply-bidding/api/interactive/getBidderList/{projectId}` | ✅ 回 `bidderRegistRecordId` / `bidderId` / `bidderName`(公司名) |
| 邀请型参标方 | `GET /supply-bidding/biddingBidder/getInviteBidderList?projectId=` | ✅ 200 |
| 按供应商反查项目 | `POST /supply-web/bidderRecord/queryProjectForBidder` `{bidderId}` | ✅ 200(需 bidderId) |
| 项目详情 | `POST /supply-bidding/biddingProject/viewProject/{projectId}` | ✅ 通(需真 projectId) |
| 项目列表(踩坑) | `POST /supply-web/projectcommon/getPurchaseSearchList`(`companyId`) | ⚠️ 通但**按 creator 过滤**,自建号名下为空 ⇒ 枚举不到别人的项目 |

## 2. 阻断杠杆(接口+鉴权 ✅,业务写入 ⏳)

| 杠杆 | 接口 | 关键字段(来自 api-docs) |
|---|---|---|
| 资格审核驳回 | `POST /supply-bidding/biddingBidder/auditBidder` | `bidderId, projectId, preAuditStatus, preAuditDesc, preAuditTime`(**2=驳回,1=通过**,老轮次实测 `1→2→1` 可还原) |
| 保证金审核 | `POST /supply-bidding/biddingBidder/auditDeposit` | `projectId, companyId, depositAuditStatus, auditDesc` |
| 移出参标人 | `POST /supply-bidding/biddingBidder/deleteManAddBidder` | `projectId, bidderRegistRecordId`(逻辑删/物删**未验证**,动前先在测试项目验证) |
| 改信用/系数 | `POST /supply-bidding/biddingBidder/addCredit` / `saveCommonCoefficient` / `SaveRankingCoefficient` | `bidderId, creditDesc, projectId` 等 |
| 发消息 | `POST /supply-bidding/biddingBidder/sendMessage` | `SendMessageDto` |
| 轮次/淘汰 | `POST /supply-bidding/biddingInfo/initBiddingRound`(`InitBiddingRoundReqVO`) / `endBiddingRound` / `changeBiddingState`(`BiddingResultReqVO`) / `initProjectToBiddingHall` | 规则 `promotionRules=2` 淘汰模式:每轮淘汰 N 名、保留 M 名(前端文案实证) |
| 看密封报价 | `POST /supply-bidding/biddingInfo/viewSealedQuoteInfo` / `GET detailPrice` | 只读情报 |
| 项目级 | `POST /supply-bidding/biddingProject/returnProjectToPool`(退回池)/ `deleteProject` / `updateProject` | 影响大,慎用 |

**鉴权实测**:以上采购人票调用**全部过鉴权**(假 ID 返回的是业务错,如「项目不存在」「参数输入有误」;`initBiddingRound` 甚至回「无法连接到竞价大厅」= 已进业务逻辑)。

## 3. 房间型场子(FastMeeting / 好视通,61.136.78.115:28443)

SOAP `https://61.136.78.115:28443/fmapi/webservice/jaxws?wsdl`,**只靠 keyCode**(`b390926f02356cab099086bc055e8cc7`),共 38 个操作:

```text
kickOutRoomUsers(roomId, userFieldType, userFieldValue, operator, appBackNotify, keyCode)  ← 踢人
cleanRoomUsers(roomId, operator, appBackNotify, keyCode)                                    ← 清场
queryUserOnlineStatus(userName, keyCode) / getCurUserCount / userInRoom
sendMsgToRoomUsers(...)   /   doRoomRightByUserName / editRoomPermission(权限封锁)
batchAddUser / delUser / addRoominfo / editRoomStatus ...
```
- **无上传/命令类操作** ⇒ 拿不到 shell;`/register/toDownload.do`(好视通任意文件读)→ 404(已修/版本不同)
- 房间 10000 密码字段是 MD5,与配置里 `ahyouzhicai2018` 对不上(原文未破)

## 4. 账号级(需更高身份,❌ 业务票打不到)

| 目标 | 接口 | 实测 |
|---|---|---|
| 冻结/解冻账号 | `POST /yzc-upms/sub/freezeSub`、`GET /sub/getFreezeLogByAccountId` | ❌ `{"code":401,"message":"暂未登录或token已经过期"}`(需 UPMS/运营身份) |
| 供应商黑名单 | 门禁配置 `BlacklistCanBid`(存在于 `yzc-tender-platform-web.yaml`/`yzc-deposit.yaml`);校验 `GET /supply-web/member/isInBlackList?addCompanyId=` | 校验 ✅ 可读;**写入接口未定位**(在供应商库/中台,api-docs 返回空) |
| 平台侧无 IP 封禁 | 57 份配置 + 全部 api-docs 里**无 IP 黑白名单业务开关**(唯一 IP 相关是 `yzc-upms-api` 的 `allowIPs` 白名单,给外部回调用) | 要封 IP 只能到 nginx/主机层 |

## 5. 留痕(恢复不了的部分)

- 审核操作记录、操作日志、`getFreezeLogByAccountId` 冻结记录:**长期可查**
- 驳回常触发短信/站内信(平台有 SMS 模板与 `/bidderRecord/initSmsRemindView` 类接口)⇒ **发出去收不回**
- 只有拿到库写面(MySQL/审计表)才可能清痕迹;否则只能恢复"状态"
