# 存款地址端点 → 链上取证（收款地址即资金链入口）

适用：目标平台自己暴露「充值/收款地址」接口（白标赌场、drainer 前端、支付 SaaS）。
这类端点通常是**链上资金链的唯一入口** —— 拿到它就能把「平台数据库」和「公开链上数据」接起来。

## 1. 先找端点，再拿地址

- 命名候选：`/api/user/deposit/address`、`/api/user/deposit/addresses`、`/api/user/deposit/wallet`、
  `/api/user/payment/address`、`/api/user/wallet/deposit`。
- **签名极常见：只接受 POST + JSON body；GET（或 GET 带 query）回 `500 INTERNAL_ERROR`。**
  实测 `GET /api/user/deposit/address?currency=USDT&network=TRC20` 与裸 GET **都回同一个 500 信封**，
  而 `POST` + `{"currency":"USDT","network":"TRC20"}` 立刻 200。
  ⇒ 看到「路由看起来存在但恒 500」，**先换方法换 body，别判死**（与 SKILL.md「Spring 系 404 vs 500」同族）。
- 参数字段名用**错误文案 oracle** 一步问出来：
  ```
  POST {}                                    → {"error":"invalid_currency"}   ⇒ 需要 currency
  POST {"currency":"DAI","network":"ERC20"} → "invalid_currency"              ⇒ 币种白名单
  POST {"currency":"ETH"}                    → "invalid_network"                ⇒ 还缺 network
  POST {"currency":"ETH","network":"ERC20"} → 200 {"address":"0x…","dest_tag":null,…}
  ```
  响应结构一般是 `{address, dest_tag, currency, network}` —— **`dest_tag` 字段本身就在暗示「memo 型收款链」**。

## 2. 地址模型：先判「每用户 HD 派生」还是「固定钱包 + memo」

这决定后续能查到什么。判定法：**同一 session 重复请求 + 跨 session 请求，看地址是否漂移**。

| 观察 | 模型 | 含义 |
|---|---|---|
| 同 session 恒定、跨 session 变化 | **HD 派生的每用户地址** | 新地址通常零交易；**归集地址要靠链上回溯，不能靠派生推算**（没有 xpub） |
| 地址恒定、`dest_tag` 每账号 +1 | **固定平台主钱包 + 每用户 memo** | ★ 金矿：主钱包有全站流水，memo 直接标出是哪个用户 |

实测同一平台两种模型并存：`ERC20/BEP20/BASE/USDC/ETH/BNB` **共用同一个 EVM 地址**（跨链同地址），
`TRC20/SOL/BTC/LTC/XRP/DOGE` 每 session 一换，而 **TON 恒定 + `dest_tag` 逐号递增**（`10000002139` → `10000002140`）。
⇒ **枚举时优先打「会是固定钱包」的那条链（常是 TON/TRX 这类带 memo 的）**，它才是全量流水的入口。

## 3. 链上查询（全部免费、无需 API key）

```
TON   https://tonapi.io/v2/accounts/<addr>
      https://tonapi.io/v2/accounts/<addr>/events?limit=100&before_lt=<lt>   ← 分页
      https://tonapi.io/v2/accounts/<addr>/jettons
TRON  https://apilist.tronscanapi.com/api/account?address=<addr>
      https://apilist.tronscanapi.com/api/account/tokens?address=<addr>&start=0&limit=20
      https://apilist.tronscanapi.com/api/token_trc20/transfers?limit=30&start=0&relatedAddress=<addr>
EVM   https://eth.blockscout.com/api/v2/addresses/<addr>
      https://eth.blockscout.com/api/v2/addresses/<addr>/transactions
BTC   https://blockchain.info/rawaddr/<addr>?limit=20
SOL   POST https://api.mainnet-beta.solana.com  {"method":"getSignaturesForAddress",
        "params":["<addr>",{"limit":20}]}   (JSON-RPC)
```

TON 的 `events` 是**已解析好的结构化事件**（比自己去解 raw tx 省一个数量级）：
每个 event 有 `timestamp` / `actions[]`，action 里 `TonTransfer{amount, comment, sender, recipient}`
或 `JettonTransfer{amount, jetton:{symbol,decimals}, comment}`，另带 `simple_preview.description` 可直接当摘要。
分页用上一个 event 的 `lt` 作 `before_lt`。

## 4. 资金流切分（入金 vs 归集）

拿 `ME = 平台钱包 raw 地址` 做方向判定，**不要靠 `simple_preview` 的描述文案**：

```python
if act_type == "JettonTransfer":
    s = jetton["sender"]["address"]; r = jetton["recipient"]["address"]
    v = jetton["amount"] / 10**jetton["jetton"]["decimals"]
    if r == ME and s != ME: inflow[s]  += v      # 受害充值方
    if s == ME and r != ME: outflow[r] += v      # 归集去处
```

产出四件套：**受害充值方排行**（地址 + 累计 + 笔数）、**归集地址排行**、金额总量（分币种）、原始事件落盘。

## 5. ★ 链上会残留平台内部标识 —— 这是「链↔库」的天然关联键

很多平台把内部 ID **当转账备注直接写在链上**（TON 的 `comment` 字段尤其常见），实测拿到：

```
10000001913 / 10000002004 / 10000002140   ← 平台 dest_tag（用户流水号，与接口返回的 dest_tag 同构）
id=fff470e8-683b-4c91-9f6a-5d829862683d   ← 平台订单 UUID，明文
@laveshka   "Crypto-fiat wallet non-KYC & lower commission"   ← 免 KYC 洗钱通道
@TonFloodingBot                                                ← 拉人头/轰炸服务
Call: 0x6a5229ae                                              ← 合约方法签名
```

**价值：不需要进后台，就能把每一笔链上资金归因到具体平台账户** —— 这把「链上交易」和「平台 DB」在证据层面钉死，
也是把报告从「猜」提升到「可提交交易所/执法冻结」的关键。
**做法：把全部 event 的 `comment` 抽出来单独过一遍，别只看金额。**

## 6. 纪律与交付

- **充值方地址 = 受害者数据。** 只做统计与归档，不接触资金、不发任何转账；报告里标明这是受害者地址清单。
- 交付物是**证据集**：`events.json`（原始）+ `flow_analysis.json`（入/出/合计）+ 地址清单（`deposit_addresses.json`）。
- 报告要写清「这**不是**私钥」——它解决的是「链上锚点 / 资金链取证」，私钥仍只在平台后端。别让用户以为拿到了私钥。
- 与 `crypto-drainer-farm-pentest` 的分工：那个管 drainer 前端/授权面，这里管「收款地址 → 链上」。

## 7. 附：这个动作会触发平台风控（实测）

对一个**有余额的测试号**做密集 API 调用（提交 seed、反复提现、批量枚举）后：
```
POST /api/auth/login  {email,password}          → {"status":"error","error":"banned"}   ← 账号被封
POST /api/auth/register {…}                      → {"error":"multi_account_detected"}     ← 出口 IP 被标记
```
且被封后**部分端点仍可读**（`/api/user/balance` 200 而 `/api/user/profile` 401）——
**别把「一半 200 一半 401」当成路由差异，先怀疑账号状态。**
换新出口（Tor 每请求随机 `--proxy-user`）重新注册即可继续；把「何时该换号」写进战役计划。
