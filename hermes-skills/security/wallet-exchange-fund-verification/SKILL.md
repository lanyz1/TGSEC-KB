---
name: wallet-exchange-fund-verification
description: "资金面验证: 伪造JWT读钱包资产、链上热钱包TRON/BSC查余额、资金盘定性。触发: 钱包, 热钱包, 资金盘。"
---

# 钱包/交易所资金面验证(伪造token读资产 + 链上热钱包查余额)

对钱包/交易所/资金盘平台,完成"读取全部资金面"并诚实判定"能否转走真实资金"。QQLink/KbitPay 实战验证(2026-09)。

## 何时使用

- 已拿到某平台 OpenAPI/凭据,要回答"里面有多少钱、能不能转走"
- 用户问: 真实资金在哪 / 热钱包是不是真的 / 能转走吗
- 平台特征: 用户余额(DB)、提现卡单、代付/热钱包、多链(TRON/BSC)

## 第 1 步: 内账 vs 链上(先定性,别先打)

- 内账 = DB 余额表(如 wallet_account: uid/chain_name/coin_symbol/balance/frozen/available)
- 链上 = 热钱包真实 USDT。**判断"热钱包空了/轮换了"前必须实际查链上余额**,不能只看一个地址的旧数据或浏览器页面(JS 渲染抓不到 from/to)
- 内账百万级 vs 全链热钱包合计个位数 USDT = 资金盘/跑路前状态(热钱包抽干,只留 gas)

## 第 2 步: 伪造 token 读任意用户资产

注册一个测试用户(第三方应用凭据)→ 拿 wallet_token → **base64 解码 payload 看 JWT 结构**:
```json
{"alg":"HS256","userId":123,"apiKey":"...","userSecret":"64hex","exp":...,"nbf":...,"iat":...}
```
- signing-key 泄露(GVA getSystemConfig)/ 短弱密钥(如 `J05KlCa` 7字节)→ 伪造**任意 userId** 的 token
- 已登录接口 `GET /v1/asstes/getUserAssets?symbol=USDT` → 任意用户余额/冻结/可用全量
- **签名密钥 ≠ 业务 secretKey**: 伪造 token 的 userSecret 必须 = 目标用户当前 secretKey, 否则 `签名验证失败`
- **实时 secretKey 查 Redis** hash `user_signature_secret`(uid→64hex); **DB 值可能过期**(查出的值签名失败 → 切 Redis 重取)
- 批量盘点: DB 余额表找高余额 uid → 逐个伪造 token + Redis secret 查真实资产
- **getUserAssets 慢**(代理到交易所/聚合), 单用户超时给足 50-60s, 分批跑(一次 5 个)

## 第 3 步: 出金链路与热钱包定位

出金链路: 用户提现 → 扣内账 → 审核(state=3 小额自动过) → 平台以商户身份调代付 API → 热钱包链上打币 → 回调写 tx_hash

- DB 成功提现行的 `tx_hash` → 链上反查 `from`(ownerAddress)= 热钱包
- 代付配置里也有热钱包线索(案卷/前端 SDK/回调数据)
- 状态机: state=3 大量无 tx = 代付通道断/配置指向测试线 = "提不出钱"是资金结构问题

## 第 4 步: 链上余额验证(TRON/BSC RPC)

### TRON(TronGrid 公开 API `api.trongrid.io`)
- `wallet/getaccount`(查 TRX)+ `wallet/triggerconstantcontract`(查 USDT balanceOf)
- **visible=true 时地址传 base58**(传 hex 必报 `ParseException : 1:19 invalid address`)
- `parameter` = 32 字节对齐: `"000000000000000000000000" + 40hex地址`
- USDT 合约 base58: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- b58 解码坑: 前导 '1' 补零字节(`zeros = len(s)-len(s.lstrip("1"))`), 否则地址错位
- tronscan API 要 key(401); 交易历史用 `apilist.tronscanapi.com/api/token_trc20/transfers?relatedAddress=<addr>`(拿完整地址,列表显示截断)

### BSC
- `bsc-dataseed.binance.org` 常不通/超时 → 用 `https://bsc-dataseed.bnbchain.org` / `https://bsc.publicnode.com`(免 key 实测通)
- `eth_getBalance` 查主链币; `eth_call` + `balanceOf(address)` 查 USDT:
  - USDT 合约 `0x55d398326f99059ff775485246999027b3197955`
  - data = `0x70a08231` + 32字节 padded 地址
- 出金 tx input 常见 `0x23b872dd`(transferFrom)= 代付从热钱包划走

### 归集追踪(资金去哪了)
- 热钱包交易历史: 入金方(充值入口)、小额出金到用户、**大额转出 = 归集目标**(主资金池/已提走)
- 归集目标地址再查余额; 若也接近 0 → 资金不在链上(托管账户或已抽离)

## 第 5 步: 诚实结论(资金结构 vs 渗透能力)

- "能转走钱吗"的完整答案: 能改 DB 数字(内账操纵), 但链上没钱 → 转不走真实资金
- 热钱包抽干特征: USDT=0 但留少量主链币(BNB ~0.97 / TRX 微量)当 gas = 资金已归集/提走, 不是"没开过"
- 这是资金结构结论, 不是渗透能力不足 —— 向用户明说, 别粉饰
- 只读验证不做写操作(改余额/转账属红线, 先确认再动)

## 用户偏好(强制)

- 所有网络操作走跳板机/主服 SSH, 本机仅写脚本; 禁止本机直连目标/链上 API
- 链上 API/交易所调用低频小批量(公共 RPC 易限流), 连接耗尽(Cannot assign requested address)时等待释放
- 判断资金"空了/轮换"必须先链上验证, 用户会纠正过早结论

## 关联

- goframe-api-pentest(信封/JWT/GVA 后台)、webapp-api-crypto-reverse(Vite 前端协议逆向)
- 白名单绕过(GET 接口绕过 POST-only 中间件)见 webapp-api-crypto-reverse references/vite-rsa-envelope-signing.md 第 4 节
