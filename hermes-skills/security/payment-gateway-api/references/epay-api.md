# Epay（epay.com 易派支付）API 速查

## Epay 1.0（经典）
- 收款接口: `https://api.epay.com/paymentApi/merReceive`
- 查流水接口: `https://api.epay.com/paymentApi/getTransactionRecords`
- 认证: `V2_HASH = md5(account . ":" . apikey)`
  - 查流水参数: `PAYER_ACCOUNT` + `V2_HASH`
- 返回 JSON `TRAN_LIST`，字段: `TYPE`（1=收款）、`STATUS`（10=处理中 / 1=完成）、`AMOUNT`、`CURRENCY`、`PAYMENT_ID`、`CREATE_TIME`、`PAYEE`
- **无转账/代付接口**（只有收款 + 查流水）

## Epay 2.0（新版，capi/openapi）
- 接口前缀: `http://api.epay.com/capi/openapi/payinApi/`
  - `sendTransaction`（发交易/收款）、`queryTransaction`（查交易）、`channelList`、`getBankList`、`calculateAmount`、`getRequiredField`
- **签名算法**（PHP 实现可逆出）：
  1. `ksort` 参数按键排序，值为空跳过，数组值递归排序后用 `{}` 包裹
  2. 拼接 `key=value&key=value&...&key=<apikey>`
  3. `sign = strtoupper(hash("sha256", sign_str))`
- 请求体: `{"param": {...}, "sign": "..."}`，POST JSON
- **代收/代付**：`getRequiredField` 的 `type` 参数 = `RECEIVE`（代收）/ `PAYMENT`（代付）。平台业务默认只配 RECEIVE。
- 错误 `code=1001 "Invalid IP, please contact Epay team"` = **IP 白名单限制**，必须从白名单内源 IP 发起（目标服务器 IP 不一定在白名单，需实测）。

## 关键陷阱
- Epay 1.0 和 2.0 是两套独立 API、凭据格式不同，别混用。
- IP 白名单会拦掉不在白名单的请求，本地和服务器都要试；账户 `deleted=1`/`status=0` 代表通道已废弃。
