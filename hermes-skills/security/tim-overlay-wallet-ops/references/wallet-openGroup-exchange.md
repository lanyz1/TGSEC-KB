# Wallet / openGroup / C2C order money layer

Paths under the platform API prefix (e.g. `/wuquan`). Always send live access_token with the App-Authorization mode that the host accepts (fixed product string **or** raw token — probe both).

## walletInfo

`GET /walletApi/walletInfo` →

- `cnyAmount`, `usdtAmount`
- `payPwd` bool — if false, `POST /paySetApi/initPwd {password, confirmPassword}` once
- `minExchangeAmount`, `exchangeFee`, rates (`cnyUsdtRate`, `usdtCnyRate`, fee rates)
- `address` (TRON deposit)

Token-scoped. Same-user on foreign uid params = blocked, not leak.

## exchangeBalance (the live exchange door)

```
POST /walletApi/exchangeBalance
{ "password": "<paypwd>", "balance": <num>, "from": "CNY", "to": "USDT" }
```

Also supports USDT→CNY by swapping `from`/`to`. Success messages include `兑换成功` / `操作成功`.

**Do not prefer** `/walletApi/cnyToUsdt` or bare `/walletApi/exchange` when they return Cloudflare HTML — many deploys path-whitelist only `exchangeBalance`.

Rules:

- Honor `minExchangeAmount` (often 100).
- One wrong paypwd can lock the wallet: `由于安全原因，您的钱包功能已被暂时锁定.如需解锁，请联系客户团队获取帮助`. Stop sprays immediately.
- Re-read walletInfo after success before openGroup.

## openGroup fee gate

1. `GET|POST /teamApi/getGroupLevelConfig` → tiers `{id, levelName, levelValue, monthlyFee, memberLimit}`.
2. `POST /teamApi/openGroup { "tid": "<groupId>", "levelId": <config id> }`.

Behaviors:

- **No tid ownership check** — any session can target any tid (IDOR-shaped). Business effect still requires fee payment.
- `请选择要开通的群组配置` → missing/wrong `levelId` (try config `id`, not only levelValue).
- `余额不足` → insufficient **billable** balance. Check USDT first when CNY looks large enough for VIP1 fee.
- `群组配置不存在` → levelId 0 / unknown.
- Bill history `trxType=OPEN_GROUP` shows fee amount and post-balance — use it to learn which pool was debited historically.

`renewGroup {tid, levelId}` hits the same fee gate.

## transfer

`POST /walletApi/transferCn` common working shape:

```json
{ "accid": "<peer accid>", "balance": <num>, "password": "<paypwd>" }
```

`amount` alone may answer `请输入转账金额`. Same lock risk as exchange. USDT transfer path names vary (`transferUsdt` / `usdtTransfer`) and are often CF-gated — confirm with a non-HTML business JSON before grinding.

## C2C order surface

| Step | Path | Notes |
|---|---|---|
| list | `GET /orderApi/orderList?pageNum&pageSize` | POST may be method-not-supported |
| detail | `POST /orderApi/orderDetail {id}` | `paymentWay[]`, `tradeOrderList[]` |
| buy | `POST /orderApi/buyCny {id, balance, password}` | qty field = `balance` |
| loan | `POST /orderApi/confirmLoan {id}` | seller JWT; already-loaned → `该订单已经放款` |
| cancel sale | `POST /orderApi/cancelOrder {id}` | blocked if unfinished trade |
| add sale | `POST /orderApi/addOrder` | needs amount + min + max + pay way + password; field names vary — oracle off error text |

Stuck trade diagnosis:

- detail.tradeOrderList entry with `status:"1"` and null finishedTime holds residual quantity.
- cancelOrder → `该订单存在尚未完成的交易，不可取消` until trade is loaned/cancelled/expired.
- buy against residual may still say `购买数量超过订单剩余可出售数量` when a ghost trade holds the full balance.

BFLA seller mint (when edge allows):

`GET /userApi/getUserAccessToken/{sellerUserId}` under token-as-App-Authorization host. 403 SafeLine HTML = path rule; cool rather than dual-egress spray.

## addOrder field oracle (common messages)

- `请选择支付方式` → need `payWayId` / `paymentInfo` / list field that matches an **owned** payment way id from prior sales
- `请填写出售的CN数量` → amount/balance/cnAmount missing or wrong key
- `请填写单笔交易最低金额` / `最高金额` → minBalance/maxBalance (or minAmount/maxAmount)
- `请填写支付密码` → password/payPassword/payPwd

Historical minimal body that sometimes worked on open hosts:

```json
{
  "minBalance": 0.1,
  "maxBalance": 0.1,
  "balance": 0.1,
  "paymentInfo": "支付宝",
  "timeLimit": 15,
  "password": "135790"
}
```

Prefer creating/listing the account's own payment way first when `请选择支付方式` persists across paymentInfo strings.

## Safety

- Marker-size buys only when validating free-CN; never drain unrelated sellers beyond proof.
- Wallet lock is a campaign-stop on that identity — switch account or wait unlock, do not rotate passwords against the lock.
