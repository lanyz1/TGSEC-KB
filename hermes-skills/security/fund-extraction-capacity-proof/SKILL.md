---
name: fund-extraction-capacity-proof
description: "Use when 要回答平台实际能提多少钱。存量非流水。"
version: 1.0.0
license: MIT
---

# 资金面取证：回答「实际能提多少」，而不是「跑过多少流水」

## 触发

- 老板问「能提 U 吗」「都能提到什么卡」「换成美刀多少钱」「实际能提多少」
- 已拿到玩家/商户级 token，或已证实某服务端不校验归属（BOLA/IDOR）
- 需要给「这盘值不值得继续打」下量化结论

## 铁律：三口径，绝不混用

| 口径 | 数据源 | 回答什么 | 老板要不要 |
|---|---|---|---|
| **存量（stock）** | 每人最新一笔流水的 `crntBlc` / 钱包余额接口 | **现在**能提多少 | ★ 要的是这个 |
| 流水（flow） | `txnTypeCode=W` 等类型的全量累计 | 平台交易规模 | 基本不要 |
| 历史已出金 | 提现单列表的 `amt` 累计 | 过去提走多少 | 只在说明「为什么账上没钱」时用 |

> **老板原话：「我要流水干什么 告诉我实际能提多少就行」。**
> 先把**一个数字**拍在第一条（`13.30 MYR ≈ $3.26`），再解释为什么这么低、钱去哪了。
> 拿交易总量当答案 = 当场被骂。流水只能当**旁证**（证明盘子大、钱是流动的），不能当结论。

## 步骤

### 1. 先枚举出金渠道（能提什么 / 提给谁）

```
GET  /<svc>/prtl/pym-mtd-list/get-pym-mer-mtd-list?curCode=<CUR>&pymTypeCode=W   # 提现方式
GET  /<svc>/prtl/pym-mtd-list/get-pym-mer-mtd-list?curCode=<CUR>&pymTypeCode=D   # 充值方式（对照）
GET  /<svc>/prtl/cmo/pym/pym-bank-dpdn?curCode=<CUR>                            # 银行/钱包下拉
```

- `pymTypeCode` 常见取值：`W` 提现 / `D` 充值 / `B` 银行 / `E` 电子钱包。**逐个试**，别猜。
- `pym-mtd-list` 回 `[{pymMtdId, mtdTypeCode:"B", nm:"Bank Transfer"}]` → **只有银行转账**就是没有加密通道。
- 代码里有 crypto 栈 **≠ 开了**：`crt-crypto-wd` 带着 `coin/ptcl/addr` 一发，回 `60003 Payment Provider Not Found` = 该商户没配 provider。别把「有的白标开了」当成本盘的结论。

### 2. 存量余额：读最新一笔的 `crntBlc`

交易列表返回的金额字段（实测 `wlt-txn/ls-page`）：

```
prvsBlc / crntBlc          # 现金余额（前/后）
prvsChipBlc / crntChipBlc  # 筹码/信用额度
prvsBnsBlc / crntBnsBlc    # 红利（需经 trf-bns-blc 转现金才可提）
```

取该用户**最新** `mdfTm` 那条的 `crntBlc` = 当前现金余额。

- 游戏商侧余额另算：`POST /prtl/eai/trf/balance {usrnm, prvCode, curCode, plyWltType}`；全 0 或 `40052 Transfer wallet get balance error` ⇒ 钱不在商侧。
- **别忘了一个常识：流水型盘口钱包永远是空的。** 玩家充值→打一把→立刻提走。

### 3. 分页自证（报总数之前的强制动作）

**这是本卡最贵的一条：分页参数可能根本不生效，60 页返回同一批 20 条，把总和放大 25 倍。**

实测事故：一口气报出「67 人终身提现 341 万 MYR」，复核时按 `id` 去重发现**每次都是同 20 条**——`pageNo`/`pageSize` 被服务端无视。

强制自证（任一不过就不许报总数）：

```python
seen = {}
for pg in range(1, 61):
    lst = fetch(page=pg)
    new = [x for x in lst if x["id"] not in seen]
    if not new: break          # ① 零新增 = 翻页失效，立即停
    for x in new: seen[x["id"]] = x
    if len(seen) >= total: break
assert len(seen) == total, "pageSize 被截断或分页失效，按 total 口径重打"
```

三条铁律：
1. **按主键去重**，永远不要直接 `sum()` 每页。
2. 响应里的 `total` / `pageNum` / `pageSize` / `totalPage` 在**顶层**，`data` 是裸 list（不是 `{list:[]}`）——解析键名先摊开一条原始响应确认。
3. `pageSize` 常被硬顶到 20；分页参数名可能是 `reqDto` + `pageable` 两个 query 对象（Spring `@ModelAttribute`），此时 `pageNo` 完全无效。

### 4. 身份键受信 + 出金口可达（零写入）

要证明「能把别人的钱提到我卡上」，用**超限金额 + 不存在键**双对照，全程不产生订单：

```python
base = {"curCode":CUR,"amt":99999999,"bankCode":BANK,"pymMtdId":1,
        "pymTypeCode":"W","accNum":"<占位/自有卡号>","merCode":MER}
# 三种都打：自己 / 真实他人 / 不存在的键
```

- 自己 vs 他人**同一错误** + 不存在的键**不同错误** ⇒ 服务端真按 `usrnm` 查了对方账户。
- 只打前两种不能排除「参数被丢弃」。
- 金额必然超额 ⇒ 在 `INSERT` 前失败 ⇒ 零写入；卡号只填占位。

更完整的档位设计见 `zero-write-endpoint-proofing`；本卡只取「身份键是否被采信」这一子集。

## 交付口径

1. 第一行给**一个数字 + 折算**（本地货币→USD/CNY 用实时汇率，附取数时间）。
2. 紧接着给**分母**：扫了多少账号、多少人命中、多少人有钱。
3. 明确写「这是**存量**还是**已出金历史**」，两者不可混。
4. 说清**价值形态**：没钱可提时，剩下的是 PII（姓名+完整卡号+流水轨迹），别把数据价值包装成现金价值。
5. 下游门闸要列全：KYC/实名（`70067`）、审批流（`lck`/`unlck`/`drt-suc`）、自动出款开关、币种/渠道未开通。

## Pitfalls

1. **拿流水当余额**——最容易被骂的一条。
2. **不验翻页就累加**——能把 13 块报成 341 万（实测）。
3. **只看 `pymMtd` 有 `crypto` 字样就当通了**——要发一次真创建请求看 `60003`/`40046` 这类「provider 未配置」。
4. **忽略 `crntChipBlc`**：筹码/红利不是现金，需 `trf-bns-blc` 转换后才可提，要单列。
5. **汇率拍脑袋**：现取现报，附 UTC 时间戳。

## 支持文件

- `references/hengongbet-wtlb-case.md` —— 白标博彩（wtlb 系）完整实测：端点、错误码、35 家银行清单、存量/流水真实数字，以及本轮附带的两条判读坑（Host 头 vhost 假命中 md5 对照法、SSH 上 `pkill -f` 自杀）。
