# pakrummy.com 资金面 + 漏洞成果（YonoGames 矩阵）

## 已确认漏洞
### 1. 任意文件上传（无 session）
- 端点：`POST https://service.yonogames.com/index/uploadFile`
- 参数（**form 编码**，非 JSON）：`uid=<任意>&img=data:image/png;base64,<base64>&token=<任意>`
- 漏洞：无 session 验证（假 uid/token 也接受）；按 MIME 前缀判类型（`data:image/png;base64,` 伪装任意内容），不检查实际内容
- 返回：`{"code":200,"msg":"success","url":"https://img.ssafljaoihfugi.com/storage/<日期>/<时间戳>_<uid>.png"}`
- 限制：强制 .png 后缀 + image/png Content-Type（不直接执行脚本）；路径穿越被防护（../、%2F 被拒）
- 价值：确认后端 Go + openresty + CloudFront；活的图片域名 img.ssafljaoihfugi.com

### 2. 短信发送端点（无 session）
- 端点：`GET https://service.yonogames.com/sms/dosend?phone=<PK号>&channel=0&otptype=6`
- 无 session；需有效手机号，否则 code 10027 Send Failed

## 后端技术栈
- 源站 openresty，Go 后端（`runtime error: index out of range` 是 Go panic）
- CloudFront POP SIN3（新加坡），阿里云邮件（mx1.sg.aliyun.com）
- 图片存储 img.ssafljaoihfugi.com（CloudFront+openresty）

## 资金面架构（全走 WebSocket，需 session）
- MsgId：SYNC_COIN=29、RESERVE_COIN=72、DRAW=132（HTTP 8020）、TRANSFER=142（HTTP 8011）
- 银行系统：BANK_ADD_CASH / BANK_VERFY / BANK_WITHDRAW / BANK_TRANSACTIONS / BANK_PAYMENTS
- 代理资金链路错误码：950 account_exist、952 invalid_promoter_code、956 commission_not_enough、958 transfer_failure、959 available_to_upline_and_downline、963 promoter_code_error
- 提现端点（需 session）：draw/alltypes、draw/setpasswd、user/balance、index/config、index/group_icon、sms/index

## 登录协议（完整还原）
- WebSocket `wss://lo.cweubis96s.com/ws`，消息 `[2B len][2B CRC-16(0x70B1)][4B ts秒][msgpack]`
- 响应不对称：ASCII `"00000000"`(8字节) + msgpack body
- 关键字段：app=RummyVIP=19(或YonoGames=17)；language=数字id(EN=2)；client_uuid=deviceid；code=""；bwss=0；dinfo='{"gid":"","sid":"","oper":""}'
- LoginType：Guest=1、WX=2、ACCOUNT=4、REGISTER=5、TOKEN=<REDACTED>
- **卡点**：游客登录被禁，spcode 209 + "auth fail"（通用 Login fail）；所有 appId 均 auth fail；手机号/三方登录需真实凭证

## 关键结论
- xxtea 密钥 `b32a2160-0c63-41`（主/代理 APK 通用）
- CENT-SIGN = md5(body前100 + serverTime + uid)
- geo-block：亚洲代理可连 /ping；WebSocket 登录需支持 CONNECT 隧道的代理，免费代理极不稳
