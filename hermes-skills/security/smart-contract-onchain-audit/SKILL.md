---
name: smart-contract-onchain-audit
description: Use when auditing a deployed contract or tracing funds.
---

# 链上合约审计（只读仿真 + 字节码对差 + 资金取证）

## 触发
- 用户丢一个合约地址：「审计这个合约」（EVM 或 TVM/TRON 都适用）
- 判断某合约是不是后门 / 资金盘 / 假托管
- 追链上资金流向、部署者画像、对手方定性

## 三条铁律
1. **全程只读**。`eth_call` / `triggerconstantcontract` / `getcontract` 不广播、不改状态。
   **绝不广播交易、绝不移动他人资金**（用户可能要求「走提款流程」，只给只读结论）。
2. **证伪优先于定罪**。每个可疑点都要仿真验证；被拦就把「不成立」明确写进报告。
   一个假洞毁掉整份报告 —— 宁少勿假。
3. **先看有没有源码**。有源码走代码审计，没有走字节码审计（路线 B）。

---

## 路线 A：有源码（verified）
权限修饰符、重入、外部调用先于状态更新、预言机操纵、精度舍入、owner 单点、
`delegatecall` 目标可控性、升级实现可否被换。
报告分「代码问题」与「治理问题」两栏 —— 两者常被混为一谈。

## 路线 B：无源码 → 字节码审计（主力）

### B1 取 ABI + bytecode
- **EVM**：Etherscan 系 `?module=contract&action=getabi|getsourcecode`
- **TVM(TRON)**：TronGrid `POST /wallet/getcontract` `{"value":"<T...>","visible":true}`
  → `bytecode`（部署字节码）、`abi.entrys[]`、`name`、`account_name`
- ⚠️ **交易所给的 ABI 经常不完整**（实测 44 个 dispatcher selector 里漏了 15 个）
  ⇒ **永远以字节码 dispatcher 为准**。

### B2 反汇编：提取真实 selector 分发表
EVM/TVM 分发器模式 = `PUSH4 <sel>`(0x63) 紧跟 `EQ`(0x14)。扫全指令对，配对即得 selector。
与 ABI 对差，差集就是「未标注函数」。**判据（区分后门 vs 内部函数）**：

| 现象 | 判读 |
|---|---|
| 在字节码中出现 **2~5 次**、位置分散 | 内部函数跳转表，被主流程调用 ⇒ 正常 |
| 只出现在分发块 **一次**、无人调用 | 高危，重点逆 |
| keccak 字典反查命中 | 直接定性（`factory()`、`surplusBalance(address)` 实测命中）|

字典反查：常见动词 × 常见参数表（`()`, `(address)`, `(uint256)`, `(bool)`, `(address,address)`, `(uint256,address)`, `(uint256,uint256)`, `(address,address,uint256)`, `(bytes32)` …）暴力比对。
脚本：`scripts/dispatcher_extract.py`（提取 + 对差 + 危险 opcode 普查，一次跑完）

### B3 危险 opcode 普查
| opcode | 含义 | 判读 |
|---|---|---|
| `0xf4` DELEGATECALL | 委托调用 | 存在 ⇒ 可能代理/可升级；查实现地址可否被改 |
| `0xff` SELFDESTRUCT | 自毁 | 存在 ⇒ 高危 |
| `0xf5` CREATE2 | 确定性部署 | 配合 initcode 可预埋后门 |
| `0xf2` CALLCODE | 已废弃 | 存在 ⇒ 老代码，警惕 |
| `0xf1` CALL / `0xf0` CREATE | 转账 / 建合约 | 计数并定位资金出口与子合约 |

**关键推论**：无 `DELEGATECALL` ⇒ **它不是代理**，「`implementation()`」可能只是占位配置。
实测某「代理」合约的 implementation 地址 `account_name` 解码后 = `CreatedByContract`（占位符）⇒ 证伪代理说。

另需专查**可升级函数**（含隐藏的）：
`(setImplementation|upgradeTo|upgrade|setImpl|setService|initialize|init|setFactory)(address)`
逐个算 keccak selector 再回字节码数出现次数，**全为 0 ⇒ 不可升级**（这是可写进报告的正面结论）。

### B4 只读取值：把状态拉出来
所有 view 函数挨个调（owner / pausable / 费率 / 各记录结构 / 余额）。
结构体返回 = 32 字节对齐拼接串，按 64 hex 切块；块内前 24 位为 0 则是 20 字节地址。

---

## 路线 C：权限矩阵仿真 ★ 本方法论的核心杀伤力
把「**全部特权函数 × 全部角色**」做成矩阵一次跑完。

机制（TRON `triggerconstantcontract`）：`owner_address` 字段**就是模拟调用者**。
返回 `result.message = "REVERT opcode executed"`，`constant_result` 前 8 hex = 自定义 error selector。
该接口天然不落链，做权限测试零风险。

**三态判定**（全部价值在此）：
| 返回 | 含义 |
|---|---|
| `Unauthorized()` 类错误 | 权限守住 ✗ |
| **其它**业务错误 | **过了权限检查**，只撞业务前置条件 ★ 强信号 |
| 有返回值 / 无 revert | 完全可执行 ★★ |

错误 selector 反查：把 ABI 里每个 `Error` 条目按 `Name(types)` 算 keccak 建表；
不在表里的错误（实测 `c1ab6dc1`/`8e78f0cb`）来自内联 require 或库，需更大字典或放弃精确命名。

**必做对照**：owner 本人也跑一遍。实测 owner 在 `transferAsset` 上拿到的是
`SafeERC20FailedOperation(address)`（不是 Unauthorized）⇒ **证明 owner 过了权限、只是 token 层失败**，
这是「owner 能扫走资产」的关键证据。只看「有 revert」会误判成「权限守住了」。

---

## 路线 D：资金取证（定性真假托管/资金盘）
1. **入金**：查该地址的 TRC20/ERC20 转入
2. **出金**：务必用 `fromAddress=<合约>` 单查 —— 多数 API 的 `relatedAddress` 只覆盖转入，**会漏掉出金**（漏了就误判「钱还在」）
3. **现值**：直接 call token 的 `balanceOf(合约)`。**链上索引常滞后，合约调用才是真相**：
   实测索引显示 7.17 USDT，`balanceOf` = 0 ⇒ 钱已跑光。两者打架时以 balanceOf 为准。
4. **对手方画像**：EOA 还是 Contract？若「托管双方」全是**同一部署者 CREATE 出来的合约**（余额 0）⇒ **自成交刷量**，链上活跃度是伪造的。
5. **部署者历史**：同 creator 部署多少同类合约 ⇒ 是否批量生产。
6. **经济模型**：`feePerDay` 类日租金 vs 实际入金量。实测日租 1 USDT 而单笔入金 2~3 USDT ⇒ **2~3 天吃光本金** ⇒ 费率陷阱。
7. **定性克制**：结构性证据（自成交、单点控制、资金已出、资金已出且无争议）可直接下判断；
   「这就是诈骗」需要受害人侧证据（域名/客服/App），别越界。

## 红牌清单（真正的高危形态）
- 单 EOA owner + 能 `transferAsset`/sweep/withdraw 全部资产 + 无时间锁无多签
- 存在 ABI 未标注且无人调用的 selector
- `DELEGATECALL` 指向可控地址 / `SELFDESTRUCT` 存在 / 可升级函数存在且无 timelock
- 「托管」的所有 party 都是同一部署者的合约（自成交）
- 资金已全额转出且无对应业务
- 「托管标的」不是标准代币（无 `symbol()/decimals()/totalSupply()`）

## 交付标准（用户明确过的期望）

**只要【外部攻击者可利用（无需内部密钥）且严重影响运营】的洞。**

不要的（会被骂「我要的不是这种漏洞」）：
- 治理风险（单密钥 owner、无多签、运营员自提自批）
- 合规问题（流程图与合约不一致、文档隐瞒出口）
- 信息披露不足

要的：
- 第三方可利用的代码缺陷（重入、溢出、逻辑绕过、授权漏洞）
- 无需内部密钥就能提款/DOS/操纵账面的路径
- 已证实资金盘/自成交且有受害人证据的诈骗定性

**交付前必做**：写 `third_party_attack_surface.py` 用陌生地址仿真全部接口，确认第三方攻击面不为零再报告。如果外部攻击面 = 0（全 `Unauthorized`），**诚实告知合约对外封闭、所有洞需内部密钥**，不要用治理风险凑数。

## 面向不熟悉链上的用户（沟通方式）
用户明说过：不熟的领域（如链上）要**用实证演示（推导 + 正反对比），别只下结论**。所以：
- 每个结论后面跟**它从哪条链上事实推出来**的（引用具体数字 / selector / 地址），别只说「有风险」
- **正反对照**：把「本可以是真的漏洞」与「实测被拦住」并排给他看（例如 owner 拿到的是
  `SafeERC20FailedOperation` 而不是 `Unauthorized` ⇒ 权限过了、token 层失败）
- 结论先给一句人话，再上证据；别拿术语堆砌当深度
- 用户会追问「是不是盗U/骗局」—— 按路线 D 第 7 条定性：结构性证据可下判断，
  「就是诈骗」不下；把「还需要什么证据才能定性」说清楚

## 报告结构
合约定性 → 访问控制审计（矩阵表）→ 风险发现（H1..Hn 按严重度）→
**明确排除项（不报假洞）** → 结论 → 复现资料。
结论优先一句人话（例：「代码没洞，风险在人」），再列证据。

## 坑
- `visible:true` 时地址必须 **base58**；某字段传 hex ⇒ `ParseException: invalid address`
  （报错只给字符偏移，很难认）。统一 base58 或统一 `visible:false`。
- 源码端点（`contract/source-code`、`contract/verify/source/code` 等）未开源时常返回空响应
  ⇒ 试 1~2 个即转字节码路线；别把 `verify_status` 数值当「已开源」用。
- TronGrid 账户查询的 `trc20` 字段是索引、可能滞后；以合约 `balanceOf` 为准。
- 请求统一 `unset` 代理变量 + `curl --noproxy '*'`（本机常驻代理会污染）。
- 标准 USDT(TRON) = `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`，写脚本直接内用。

## 支持文件
- `references/tron-api-recipes.md` —— TronGrid / TronScan 端点实测清单 + selector 速查 + 地址互转工具
- `references/worked-example-escrow-factory.md` —— ★ 完整实务例子（未开源担保合约）：字节码对差、
  权限矩阵真实输出、资金取证、H1..H6 与排除项、报告形状。**下次开工先读这个。**
- `scripts/dispatcher_extract.py` —— 字节码 selector 提取 + ABI 对差 + 危险 opcode 普查
