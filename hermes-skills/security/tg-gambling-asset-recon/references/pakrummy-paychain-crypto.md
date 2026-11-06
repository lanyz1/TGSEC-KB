# YonoGames/bdrummy 支付链与响应加密破解（基础设施接管战）

## 响应加密完整破解（关键突破）
支付 API `service.fwui238929sh.com/v1/*` 所有响应是 `{data, timestamp, signature}` 加密格式：
- **uncompile() 是差分解码**：首字符 `charCodeAt(0)-length`，后续 `charCodeAt(i)-前一个解密字符`（不是简单 unescape！）
- P_K/P_AK 定义在 Global（project.js），URL-encoded 密文，uncompile 后是明文 key：
  - P_K（HMAC-SHA256 key，32B）= `rbK2RR#PFn7H4vu0!EKaElnWQkOcKU_z`
  - P_AK（AES-GCM key，32B）= `j39qexkacw7gtnzrnnlwuibjnd494xhw`
- 验签：`HMAC-SHA256(data_b64 + str(timestamp), P_K)` == signature（hex）
- 解密：`AESGCM(P_AK).decrypt(base64前12字节=IV, 后=密文)`，key 用 UTF-8 编码（TextEncoder）

## 资金 API 端点（/v1/ 前缀，sendPayServer 自动附 uid+token）
- GET 带 `?uid=&token=<REDACTED> body form-urlencoded
- `user/balance`（充值渠道，参数 cat/coin/paypop）、`order/pay`（在线支付，参数 amount/id/title）、`order/bank`（银行转账，参数 id/amount/utrnum/pic）
- `draw/alltypes`（提现，dcoin/typelist min100 max50000）、`draw/order`、`kyc/bind`（cat/account/cnic）、`user/editCard`（id/cardnum/cnic）
- `index/uploadFile`（参数 uid/img/token，需 CENT-SIGN 头 md5(img[:100]+serverTime+uid)）

## 支付网关（tfpay88.com，第三方）
- order/pay 成功返回 `payurl=https://tfpay88.com/bkh5/bkof.html?orderNo=BKxxx&amount=500&payType=bkash_office&account=01xxxxxxxxx`
- **收款账户（Bkash 手机号）轮换泄露**：01633909042、01836350724 等
- 支付 API：`api.tfpay88.com/tjl-cashier/searchOrder`（查单，参数 orderNo+account）、`api.tfpay88.com/tjl_fee/api/submitOrder`（提交 UTR，参数 orderId+trxId）
- 前端 Angular，`tfpay88.com/v2/ui/payment.js` 泄露 API

## 防御结论（都拦住了）
- 金额篡改 → code 542（服务器端范围校验）
- SQL 注入 → code 400（参数化查询/类型校验）
- IDOR → code 403 session expired（token 绑定 uid）
- 支付回调伪造 → submitOrder 返回 success 但**不到账**（人工审核 UTR）
- 文件上传 → "upload file type not allowed"（加强校验）
- 源站双 CDN（Cloudflare DNS + CloudFront），阿里云新加坡（MX 泄露 mail.sg.aliyun.com）
- 支付后台 pay.247easygamespay.com 已下线（DNS 无记录）

## 充值渠道（孟加拉）
Bkash / Nagad 移动支付，服务商：Tfpay、Passpay、Starpago、Ttkpay、Gtpay、DayPay、Wifipay、Wenpay