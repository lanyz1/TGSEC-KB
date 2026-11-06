---
name: smart-contract-audit
description: Use when auditing a deployed contract without source.
version: 1.1.0
tags: [smart-contract, audit, tron, evm, bytecode, readonly-simulation, permission-matrix, version-diff, allowance]
---

# 已部署智能合约审计（无源码场景）

触发词："审计这个合约" / "有没有洞" / "能影响运营的漏洞" / 白标担保托管合约。
目标通常**未开源**，手里只有链上字节码 + explorer 给的（不完整）ABI。

核心不是读源码，而是：

- **只读调用仿真**反推权限边界（不广播、不改状态、不碰钱）
- **字节码 dispatcher 差分**找出 ABI 漏报 / 隐藏函数
- **多实例 / 多版本 diff** 找出运营方"修过什么" ⇒ 旧版"缺什么"
- **allowance 核验**找常备提款权（尤其废弃旧合约上未回收的无限授权）

Related（交叉引用）：`crypto-drainer-farm-pentest`（钓鱼页/drainer 归属）· `oss-version-patch-diffing`（同源 diff 思路，源码场景）· `pentest-finding-verification`（结论纪律）

## When to load

- 用户给合约地址（TRON `T...` / EVM `0x...`）要求审计 / 找洞 / 判断"能影响运营"
- 目标未开源（`verify_status != 1`，源码端点全空）
- 疑似白标担保/托管/资金盘（函数名含 `Escrow`、`deposit`/`depositFor`、`proposeRefund`、`createEscrow` 等）
- 被问"是不是盗U / 谁在运营 / 链上拿了多少"，需要先定性再归因

## 铁律：只读仿真 是审计主力

`triggerconstantcontract`（TRON）/ `eth_call`（EVM）**不广播、不改状态**，却会真实执行权限检查：
对「N 个函数 × M 个角色」逐格跑一遍，看每格返回的错误 selector，就能画出**完整权限边界**。

**判读表（关键）**：

| 返回 | 含义 |
|---|---|
| `Unauthorized()` | 权限门拦住 |
| 业务错误（`WrongStatus`/`InvalidAmount`/`InvalidToken`/`EscrowNotFound`/`InvalidParticipants`） | **已通过权限门**，只是业务规则拦住 |
| `SafeERC20FailedOperation(address)` | **权限门已通过并走到 token 转账层**（仿真禁止状态变更所以 revert）⇒ **该角色确实拥有此能力的最强证据** |
| `ReentrancyGuardReentrantCall()` | 有重入保护 |
| `constant_result == [""]` | ⚠️ **歧义！函数无返回值时"成功"也长这样**。禁止据此判成功，见下节 |

例：判"owner 能否扫空合约"时，owner 得 `SafeERC20FailedOperation` 而陌生人得 `Unauthorized`
⇒ **owner 的扫空能力成立**。不能因为看到 revert 就写成"不可利用"。

## ★ 判真伪：必须读完整 result 对象（本方法论最易翻车处）

只看 `constant_result` 会在"空返回"上反复误判（本会话烧掉整轮）。**每次调用取四样东西**：

```python
ok  = j["result"].get("result")                 # 是否执行到
en  = j.get("energy_used")                      # ★ 执行深度指纹
msg = j["result"].get("message", "")            # "REVERT opcode executed" 等
sel = (j["constant_result"] or [""])[0][:8]      # 自定义错误 selector
```

- `ok=True` + **energy 十几万级** ⇒ 业务逻辑真的跑完了（哪怕没有返回值）
- `ok=True` + **energy ~8k** ⇒ 进门即被拒（读 msg 里的 selector 定性）
- `ok=True` + energy ~1.4 万 + selector ⇒ 卡在某个前置状态检查

**energy_used 同时是「代码路径探测器」**：同一函数、不同角色，energy 相同 ⇒ 同一条路径；
差出十几万 ⇒ **走了不同分支**。实测 `proposeRefund` 在 partyB 身上 153,307、在运营员身上 361,422
（多 20.8 万）⇒ 运营员命中特权分支 —— 这比推断"权限集中"硬得多，可直接写进报告。

## ★ 找业务逻辑洞：view 函数全参数空间扫描

权限矩阵跑完（结论=无越权）之后，**战场必须转到参数语义与边界**，否则只剩"治理风险"可写。

1. **先挑活靶**：`escrowCount()` → 逐个 `getEscrow(id)` → 取 **status 字段 == 0 且金额 > 0** 的那个。
   实测 6 个托管里 5 个已结算（任何调用都回 `WrongStatus`，教不了你任何东西），只有第 6 个
   `status=0`、锁着真金 ⇒ **唯一可打活靶**。在死实例上做参数扫描 = 白烧轮次。
2. **view 函数 = 最便宜的语义 oracle**：把内部算好的分账直接返回给你。
   `previewRefund(id, mode, amount)` 扫 `mode ∈ {0,1,2,3,255} × amount ∈ {0,1,1e6,1e12,2^200}`，
   一次拿到三样东西：**mode 的真实语义、amount 的确切作用、读路径缺失的校验**。详见 references。
3. **写路径 vs 读路径校验不对称 ⇒ 可直接上报**：写路径 `reject(InvalidMode)` 而读路径返回
   垃圾值（实测非法 mode 回 1,294.686198 USDT = 真实可退额的 129 倍）⇒ 前端展示"可退款额"被误导。
4. **energy 判"参数是否被读取"**：同一函数只改一个参数，**energy 完全不动 ⇒ 该参数在此路径上是死参数**。
   实测 `proposeRefund(amount=1)` 与 `proposeRefund(amount=1e12)` energy 完全相同 ⇒ 提议阶段不校验金额
   ⇒ 真正分账的是**结算阶段另传**的 amount ⇒ **提案内容与实际出账金额脱节**（即使新版加了
   到账额核对 `UnexpectedTokenAmount()`，提案侧仍未绑定）。
5. **常见可上报类别**：①默认值落在"独吞"分支（`mode=1/2`+`amount=0` ⇒ 单方提议即拿走**双方**本金）；
   ②提案/结算金额脱节；③读路径缺校验；④走完上万 energy 后**裸 REVERT 无具名错误**（集成方无法区分失败原因）；
   ⑤跨角色同函数 energy 差异暴露未文档化特权分支。

## ★ 挖洞阶段 vs 归因阶段（用户当场纠正过）

用户在合约审计中明确要「挖洞 / 业务漏洞 / 逻辑漏洞」，并**当场打断了跑偏**——本会话曾滑向
资金图谱、对手方交易数画像、域名探活，被一句「我要这些干什么」叫停。

⇒ **挖洞阶段的动作集合固定为**：权限矩阵 → 活靶筛选 → view 全参数扫描 → energy 差分 → 参数绑定核查。
⇒ 资金图谱/归属/域名探活只在用户**明确要求**时做，且**不能用它替代挖洞产出**。
⇒ 用户要的是"能影响运营的洞"和"严重影响级别"，报告里"风险在治理"最多只能是补充栏。
⇒ **顺着线索走到运营方的网站/后台/SaaS 同样算跑偏**。本会话由账实缺口牵出运营方钱包 → 其业务站
   → 其白标 SaaS（公共 S3 桶 / APP 客户端 / API 密钥），中途被一句
   「我让你审计合约的漏洞啊 你怎么搞这些啊」叫停。**线索是真的，错的是交付槽位**：
   合约审计会话里合约结论必须是脊柱；平台侧那条线**另开一轮、并先说明"这是另一个标的"**再动手
   （平台类取证见 `white-label-platform-recon`）。

## ★ 先定商业模式，再打它"兑现不了的承诺"（用户当场纠正过）

本会话把担保平台的**设计机制**当成洞上报过一次（`mode=1`+`amount=0` ⇒ 单方提议即请求双方本金），
被用户一句话打回：**「这他吗本来就是人家的运营模式」「他们是一个担保平台」**。

⇒ **动参数扫描之前，先写下商业模式与它的核心承诺**：
- 担保/托管平台：核心承诺 = **「钱一定兑得出」**（不是"我方无越权"）
- 它的"单方申请→运营裁决""运营员一把钥匙"都是**设计**，报出来只会被当外行
⇒ **攻击点应落在「实现能否兑现这个承诺」**：账实是否相符、池子够不够付、记账能否脱离资金。
⇒ 拿不准一个机制是设计还是洞时，先问"这是不是平台赖以收费的业务流"；是 ⇒ 换个面打。

## ★ 账实对账（担保/托管类合约的最高价值一击）

权限矩阵 + 参数扫描跑完往往只剩"治理风险"可写 —— **此时切到账实对账**。本会话靠它拿到唯一一个
真正"影响运营"的严重级 finding（详见 `references/accounting-vs-onchain-reconciliation.md`）。

1. **账面**：`getEscrow(i)` 类 view 逐个取内部记账字段（押金 / 应付 / 总额）
2. **实收**：`GET /v1/accounts/<合约>/transactions/trc20?limit=200&only_confirmed=true`
   全量事件，筛 `to == 合约`（入）/ `from == 合约`（出）
3. **算术证明**：若 `Σ流入 == 当前余额` 且 `流出 == 0` ⇒ **合约一生只收过这么多钱**
   ⇒ 账面超过这个数的部分**都是没有资金背书的记账**
4. **兑付可行性**：`previewRefund` 类 view 返回的应付额 vs 合约实有余额 ⇒ 应付 > 实有
   ⇒ **结算必然失败 ⇒ 核心承诺被证伪**（可直接写进报告的硬结论）

**找记账注入面**：对 `depositFor(id, party, amount)` 逐角色跑 energy 差分 ——
运营员记 partyB 得 **112,029**，记 partyA/陌生人被 `InvalidParticipants` 拦（8,571），
其余角色 `Unauthorized`（8,437）⇒ **运营员走独立分支，可指定任意 party / 任意 amount 写入账面**。
（旁证：新版新增 `UnexpectedTokenAmount()` = 开发者已知"到账额与记账额不符"，但加固未覆盖全部记账路径。）

## 坑（全部踩过，按事故率排序）

## 六步法

1. **定性** — explorer 元信息 + 字节码/ABI（端点速查见 references）
2. **权限矩阵** — 见上（**动手前先读「坑 1」地址编码**）
3. **dispatcher 差分** — 从字节码提 `PUSH4 <sel> EQ`，与 ABI 计算结果对差（**ABI 会漏函数**）
4. **多实例/多版本 diff** — 由 `creator` 找同源实例；**ABI 差异 = 他们修过什么**
5. **allowance / 授权核验** — 无限授权 = 常备提款权；重点查**已弃用旧合约**上未回收的授权
6. **资金图谱 + 归属** — 运营方钱包群、闭环资金（自成交伪造活跃度）、`owner()`/`service` 字段、`setAdmin` 历史

## 坑（全部踩过，按事故率排序）

### ★1 地址参数编码方向相反（最高频事故）
- base58 → 调用参数：`n.to_bytes(25,'big').hex()` 取 **`[2:42]`**（字节 1~20，去版本位与校验和）
- ABI 64 字符字 → base58：取 **`[-40:]`**（字节 24~44）

**两个方向相反，混用 ⇒ 所有带地址参数的 view 全回 0/假结果**（本案 9/9 假阴性，白烧一轮）。

### ★2 读路径必须先自检（不回检就会报假阴性）
1. 先跑**无参 view** 做对照：`symbol()` / `decimals()` / `totalSupply()` 必须正常
2. 再用**已知持币地址**的 `balanceOf` 与 explorer 索引**对账**（数值必须一致）

**回 0 时先怀疑编码，再怀疑链上。** 无参 view 正常但带参 view 全 0 ⇒ 100% 是参数编码问题。

### ★3 朴素 opcode 计数 = 假阳性
逐字节数 `DELEGATECALL(0xf4)` / `SELFDESTRUCT(0xff)` 会把 **PUSH 数据里的字节**数进去
（本案曾误报 `SELFDESTRUCT=179`，逐指令走实为 0）。必须**逐指令走并跳过 push 数据**：
```python
op = int(bc[i:i+2],16); i += 2
if 0x60 <= op <= 0x7f: i += (op - 0x5f)*2      # 跳过 PUSHn 的立即数
```

### ★4 revert selector 的位置
在 `constant_result[0]` 的**前缀**，不在 `result.data`。（只读 `result.data` 会永远拿不到错误 selector）

### 5 `is_proxy=true` 可能是假阳性
若 `implementation()` 指向的地址**无字节码、0 笔交易、0 创建**，且自身字节码里 **`DELEGATECALL` 计数为 0**
⇒ **不是代理**，那个 implementation 只是占位/装饰地址。别据 `is_proxy` 就断言存在升级后门。

### 6 数据源会降级（高频调用后）
explorer / RPC 在调用量上来后会返回**不可信数值**（本案同一 `allowance` 查询一次回 `2^256-1`、一次回 `2^40`）。
⇒ 关键数值**跨源交叉**（explorer 索引 vs 链上调用）+ 对照组合；**数值结论只采信"带对照验证通过"的那一轮**；
权限类（categorical）结论多轮交叉一致即可采信。

### 7 域名/代币名类归属证据要先验证
dust/垃圾代币名称常带域名（`xxx.fun`、`Authorize at <site>`）。**先 `dig` + HTTP 探活再声称**——
本案四个域名全为停放/已死（Afternic / Hostinger parking / AWS 加速 IP），**不构成归属证据**。

### 8 旧版合约仍在链上且仍持授权
版本迭代后必须查：**旧实例的 allowance 是否还在**。本案运营方对三个实例都给了 `2^256-1`，
其中 v1 已弃用却仍持无限提款权 ⇒ 这才是最该立刻修的暴露面（P0：`approve(old, 0)`）。

### ★9 `transactions/trc20` 里混着 Approval 事件（会污染一切余额算术）
TronGrid 的 `/v1/accounts/<addr>/transactions/trc20` **既返回 Transfer 也返回 Approval**。
Approval 的 `value` 是授权额（无限授权时 ≈ 2^256），当成转账会把 `Σ流入` 算成 1e77 级天文数字。
**判据**：数值在 `1e77` 量级 ⇒ 那是 Approval，不是转账（实测 4 条混在 8 条里）。
**副作用（好事）**：这些 Approval 事件是**无限授权最权威的证据源** —— 比仿真 `allowance()` 可靠，
高频调用后 `allowance()` 会返回 2^40 这类垃圾值（见坑 6），而事件不会。

### ★10 同名函数的多重载：调错元数会**返回垃圾数据**而不是 revert（本会话报错一次）

同一合约族里同名函数常以**不同元数跨版本并存**（v1 `previewRefund(uint256,uint8)` vs
v3 `previewRefund(uint256,uint8,uint256)`）。**元数调错时它可能不 revert**，而是走 fallback /
错位取参后把一段存储当返回值吐出来 —— 数字看着像模像样，于是写进报告又被迫撤回。

本会话实录：同一个 `previewRefund(1, …)` 先后吐出 `3.000000 USDT` → `1,294,686,198`（=1,294.686198 USDT）；
最后确认**两个值来自两个不同元数的调用**，只有与该实例配对正确的那次才算数。

⇒ **规矩：任何返回数字进报告之前，先对「该实例」确认这个 selector 存在**，判据三件套：
1. `energy_used` 是否落在该函数的正常区间（实测合法 mode 4,499~4,916，错路径仅 1,636）
2. 用**合法入参**能否返回**期望量级**（真实入金 3 USDT 的托管不该算出 1,294 USDT）
3. 拿一个**明确不存在的签名**做负对照，看它是否也「成功」返回数据
⇒ 每个数字都要能回答「它是从这个元数、这条 energy 路径上来的」，答不出就不进报告。

## 判读纪律（本用户极看重）

- 结论**必须分离【已证明】与【推断】**；推断被证伪就**立刻撤回**，并在报告里写明"撤回"及原因
- **"新版新增了某校验/参数" ≠ "旧版存在可利用漏洞"** —— 前者是加固证据，不是漏洞证明
  （本案 v3 给退款加了 `amount` + `UnexpectedTokenAmount`，一度让我推断 v1 可超额退款；
   实测 v1 的 `proposeRefund` 有 mode 校验 ⇒ **推断证伪、撤回**）
- 合约"无第三方越权漏洞"也是结论，不要为好看编洞；此时把严重级**落到密钥/授权治理**（多签、timelock、授权回收）
- 区分"代码漏洞"与"治理/密钥风险"：报告要说明**攻击面在代码还是在人的密钥保管**

## 输出规范（本用户）

- **不停下问**：连续深挖，除非用户说停/切目标；每轮产出即落盘
- 报告分层逐轮落盘：`AUDIT_REPORT_R<N>_<主题>.md`（定性 → 权限矩阵 → 版本 diff → 资金图谱 → 修复）
- 结论**必须能落地到 P0 可执行动作**（如"立刻对 v1/v2 执行 `approve(old, 0)`"），不要只说"存在风险"
- 每条 finding 附**复现脚本路径**；脚本落在案卷目录下
- 全程**只读**：`approve`/`settle`/`transfer` 类写操作只在仿真里跑，报告里明确声明"未广播任何交易"

## References / Scripts

- `references/tron-escrowfactory-case.md` — 完整案例：TRON 端点速查表 / 三实例权限矩阵 / 版本 diff 杀伤力 / 地址编码 bug 实录 / 资金闭环
- `scripts/dispatcher_selectors.py` — 字节码 dispatcher 提取 + 与 ABI 对差（逐指令跳过 push data，内置 keccak 自检）
- `scripts/readonly_role_matrix.py` — 只读「角色 × 函数」权限矩阵仿真（TRON `triggerconstantcontract`；EVM 换 `eth_call`）
- `scripts/view_param_sweep.py` — **view/写函数全参数空间扫描**：网格枚举 + 三态判读 + energy 分组（自动标出"参数未影响路径"）
- `references/business-logic-probing.md` — ★ **业务逻辑挖洞详解**：活靶筛选 / previewRefund 实测全矩阵 / 读-写路径校验不对称 / energy 作死参数探测 / 可上报类别与严重度
- `references/accounting-vs-onchain-reconciliation.md` — ★★ **账实对账详解**：账面 vs 事件级实收对账法 / Approval 事件过滤 / `depositFor` 记账注入面 energy 矩阵 / 担保兑付缺口实测数字与报告写法
