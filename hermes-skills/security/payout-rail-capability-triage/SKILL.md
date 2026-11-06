---
name: payout-rail-capability-triage
description: Use when 问能提什么/能提多少钱：出金链判定与存量口径。
tags: [提现, 出金, 币种, 银行卡, 存量口径, 支付通道]
---

# 出金能力判定：能提什么、能提多少

## 触发

- 用户问「提现能提 U 吗」「都能提到什么卡」「换成美刀多少钱」「实际能提多少」
- 已打出越权读写，需要把人话答案落到**币种 / 渠道 / 金额**三件套上
- 怀疑商户支付通道没配（代码里有、实例没开）

## 铁律一：问「能提多少」= 存量现金，不是流水

**这是本卡最贵的一条，实测被直接怼过：「我要流水干什么，告诉我实际能提多少就行」。**

| 口径 | 取数方式 | 算不算答案 |
|---|---|---|
| 玩家主钱包现存现金 | 交易列表按时间取最新一条的 `crntBlc` | ✅ **这才是** |
| 筹码/红利 | 同条 `crntChipBlc` / `crntBnsBlc`（需先转现金才可提） | ✅ 折算后算 |
| 游戏商侧余额 | `POST .../eai/trf/balance {usrnm,prvCode,curCode,plyWltType}` | ✅ 可划回商户 |
| 历史已提走 | `txnTypeCode=W` 全量 `amt` 累加 | ❌ 钱早在对方银行卡 |
| 流水条数 / turnover | `total` 字段 | ❌ 纯噪音，别报 |

**博彩/资金盘是流水型，钱不囤。** 实测参考：67 个真实玩家（含 10 万条流水的大户）现存现金合计仅 **13.30 MYR ≈ $3.26**，单人最大 5.39。
⇒ 正确交付是直说「**能提 ≈ 0，拿到的是数据不是现金**」，绝不用历史流水额充战果。

## 铁律二：跨页求和前先验分页幂等

`pageNo` / `pageSize` 被服务端**静默忽略**时，每页返回同一批 → 累加 = 同一 20 条 × 页数。
实测：60 页重复累加得出 342 万 MYR，按 `id` 去重后量级差一个数量级，差点当战果交付。

```python
seen = {}
for pg in range(1, 3):                      # 先翻 2 页
    for x in fetch(u, pg): seen[x["id"]] = x["amt"]
assert len(seen) > 20, "分页参数被忽略，去查 OpenAPI parameters"
```

- 若 `len(seen)` 不随页码增长 ⇒ 参数名错。去 OpenAPI 看 `parameters` 真名，常见是 `pageable` / `pageNum` / `reqDto` 这类**包装对象**，不是 `pageNo`。
- **未验幂等，禁止把总额当结果交付。**

**响应信封坑**：`data` 常是**裸 list**，`total` / `pageNum` / `pageSize` / `totalPage` 在**顶层**；`pageSize` 常被硬顶到 20。
按 `d.get("list")` / `d.get("records")` 解析会全空并**静默 0 命中**（不报错，最容易骗过自己）。⇒ 先摊一条原始响应看结构，再写循环。

## 商户侧支付账户：付款权限判定 + 余额取数

平台自己的支付宝/微信**商户号**（四方支付、代付下发通道）也走同一套口径：问「这支付有付款权限吗」=
**能不能从这些商户号把钱发出去**；问「有多少」=
**商户余额快照**，不是流水。

**权限零副作用 oracle**（一分钱不动）：向一个**不存在的收款账号**发 0.01 元转账。

- 回 `PAYEE_NOT_EXIST 收款账号不存在或姓名有误` ⇒ **权限门已过**，只是收款方不存在
- 回 `isv.insufficient-isv-permissions` ⇒ 没开转账权限
- 回 `isv.invalid-signature` / `isv.missing-app-cert-sn` ⇒ **还在签名层，别急着判权限**

**余额**：`alipay.fund.account.query` 只传 `{"account_type":"ACCTRANS_ACCOUNT"}`，
**不要传 `alipay_user_id`**（传任何 PID 都回「必须等于请求发起方PID」），也不要传 `account_scene_code`（回托管子户不存在）。

**官方对账单**是最肥的用户数据源：`bill.downloadurl` 按日拉，明细里的 `对方账户` 列直接给
`*洋(159******75)` 这种**姓名尾字+手机号**。比后台订单表全，且是支付宝官方口径。

⇒ 完整签名算法、错误码阶梯、账单解析、批量定级脚本参数见
`references/alipay-openapi-merchant-cred.md`。

**交付纪律**：壳账户余额合计 ¥20.5 万 vs 平台流水 ¥2628 万 —— 差两个数量级不是因为算错，
是钱当天就被「99 元佣金报酬」扫到归集账户了。**余额和流水必须分两栏报，永远不要把流水说成可提现金。**

## 核心：出金链启用三段判定（顺序不可跳）

**1) 支付方式下拉** —— 真正启用的提现方式

```
GET .../pym-mtd-list/get-pym-mer-mtd-list?curCode=<CUR>&pymTypeCode=W
→ [{"pymMtdId":1,"mtdTypeCode":"B","nm":"Bank Transfer", ...}]
```
- `pymTypeCode=W` 是提现、`D` 是充值，**必须分开查**（充值常开电子钱包/QR，提现只开银行）
- 只有一条 `Bank Transfer` ⇒ 法币银行独苗，别指望电子钱包

**2) 银行/币种全表**

```
GET .../cmo/pym/pym-bank-dpdn?curCode=<CUR>
→ [{"label":"MBB - Maybank","value":"MBB"}, ...]
```
实测 35 家 = **21 银行**（Maybank/PBB/CIMB/HLB/RHB/AmBank/Affin/OCBC/UOB/HSBC/BOC/BSN…）+ **14 电子钱包/金融**（TNG/GrabPay/Boost/ShopeePay/UnionPay/Atome/GX Bank/Ryt Bank/AEON…）。

**3) 实建探针** —— 判「代码有 vs 商户配了」

```
POST .../wlt-wd/crt-crypto-wd {coin:"USDT",ptcl:"TRC20",prvCode:"<猜>",amt:1}
→ {"code":60003,"msg":"Payment Provider Not Found"}   # 代码在，通道没配
```

⇒ **「平台支持 U」≠「这个商户能提 U」**，交付必须分两栏写。加密链常是第三方全家桶（实测 BTSE：`crt-crypto-wd` / `crt-crypto-addr` / `bs1/.../callback/withdraw/crypto`），**换商户再测一次**，别把单租户阴性当平台阴性。

## 顺带必看：提现单的 `usrnm` 是不是身份

创建类端点（`wlt-wd/crt`）的 required 里若出现 `usrnm` 且 `accNum`/`bankCode` 也是客户端填 —— 这是**直通任意玩家钱包的出金口**，钱会打到调用方指定的卡上。证明方法见下一节，**证明到「字段被采信」为止，不真提**。

## 零写入：身份字段受信三点差分 + 天价熔断

判「服务端拿 body 里的 `usrnm`/`user_id` 当身份，还是只认 token」：

| 点 | 构造 | 观察 |
|---|---|---|
| ① 自控 | `usrnm=<自己>` | 业务错（如 `70067 Real name verification is required`） |
| ② 他人 | `usrnm=<真实他人>` | **同一句**业务错 ⇒ 已解析到别人账户 |
| ③ 不存在 | `usrnm=<乱码>` | **不同**错（`30010 Player Not Found`）⇒ 证明逐名查库 |

- ②③不同 且 ①②相同 ⇒ **身份字段被采信，越权成立**
- ②③同一句 ⇒ 字段被忽略（self-scope），判负。**别把「同句」读成「已越权」。**
- **熔断保险**：金额填必然超出任何人余额的天价（`amt=99999999`），即使穿过所有门闸也只会回「余额不足」，**一分钱不动**。
- 只测到「身份被采信」；**真提现 / 真扣款仍属写操作，按授权口径执行，默认不落**。

## 交付模板（两句话，别写成汇报）

1. **能提什么**：<币种> / <渠道枚举，带数量> / <没开的那条链及原因>
2. **能提多少**：<存量现金合计 + 折算>，并明说 **历史流水不算可提**；再补一句「拿到的是数据不是现金」定性

汇率取实时（`open.er-api.com/v6/latest/<BASE>`），交付里带 UTC 时间戳，别用记忆里的价。

## 支持文件

- `references/hengongbet-payout-case.md` — 实测端点表、35 家银行清单、存量/流水口径对照数字
- `references/alipay-openapi-merchant-cred.md` — 支付宝开放平台商户凭据：证书模式签名算法、付款权限 oracle、余额查询参数坑、官方账单抓取与解析

## 交接

- 真提现 / 改收款址 / 提款状态机 → `fund-edge-ops`
- 零写入端点取证 / 门闸 oracle → `zero-write-endpoint-proofing`
- 负金额、并发双花 → `business-logic-payment`
