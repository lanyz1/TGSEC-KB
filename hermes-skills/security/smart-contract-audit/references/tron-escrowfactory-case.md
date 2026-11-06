# TRON EscrowFactory 审计案例（2026-09-27）

白标担保/托管合约审计实操记录。目标未开源，靠只读仿真 + 字节码 + 多实例 diff 完成。

---

## 1. TRON 端点速查表（实测可用 / 不可用）

| 用途 | 端点 |
|---|---|
| 合约元信息（name / verify_status / is_proxy / creator） | `GET https://apilist.tronscanapi.com/api/contract?contract=<A>` |
| 账户（balance / trc20token_balances / totalTransactionCount / date_created） | `GET https://apilist.tronscanapi.com/api/account?address=<A>` |
| **字节码 + ABI** | `POST https://api.trongrid.io/wallet/getcontract` `{"value":"<A>","visible":true}` |
| **只读调用仿真（核心工具）** | `POST https://api.trongrid.io/wallet/triggerconstantcontract`<br>`{"owner_address":"<caller>","contract_address":"<A>","function_selector":"owner()","parameter":"<args hex>","visible":true}` |
| TRC20 转账史（可靠） | `GET https://api.trongrid.io/v1/accounts/<A>/transactions/trc20?limit=100&only_confirmed=true` |
| TRX 转账 | `GET https://apilist.tronscanapi.com/api/transfer?limit=30&start=0&sort=-timestamp&address=<A>` |
| 与某地址相关的 TRC20 | `GET https://apilist.tronscanapi.com/api/filter/trc20/transfers?limit=50&relatedAddress=<A>` |
| 合约的 Approval 事件 | `GET https://api.trongrid.io/v1/contracts/<TOKEN>/events?event_name=Approval&limit=200&min_block_timestamp=<ms>` |
| TRC20 代币搜索 | `GET https://apilist.tronscanapi.com/api/token_trc20/search?keyword=<name>` |

**不可用 / 坑**：

- `token_trc20/transfers?relatedAddress=` 常返回空 ⇒ 改用 `filter/trc20/transfers` + TronGrid `/transactions/trc20`
- `accountv2` 返回 401；源码类端点（`contract/verify/source/code`、`contract/source`、`contract/solidity`）
  对未开源合约全返回 <200 字节（不是报错，是空体 —— 别把它当"接口不存在"）
- `visible:true` 时 `owner_address` **必须**是 base58；`visible:false` 时必须 hex —— 混用报 `invalid address`

## 2. 地址参数编码：正确写法

```python
from Crypto.Hash import SHA256
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def base58_to_hex25(a):            # base58 -> 25 字节 hex（41 + 20 字节地址 + 4 校验）
    n = 0
    for ch in a: n = n * 58 + ALPH.index(ch)
    return n.to_bytes(25, "big").hex()

def arg_addr(a):                   # ★ 调用参数：取 [2:42]
    return "%024x%s" % (0, base58_to_hex25(a)[2:42])

def word_to_base58(word64):        # ★ ABI 64 字符字 -> base58：取 [-40:]
    raw = bytes.fromhex("41" + word64[-40:])
    ck = SHA256.new(SHA256.new(raw).digest()).digest()[:4]
    n = int.from_bytes(raw + ck, "big"); s = ""
    while n > 0:
        n, r = divmod(n, 58); s = ALPH[r] + s
    for b in raw:
        if b == 0: s = "1" + s
        else: break
    return s
```

**事故实录**：先用 `[-40:]` 去做调用参数（取到了含校验和的错误 20 字节）
⇒ `balanceOf` / `allowance` **9/9 全回 0**。
修正为 `[2:42]` 后，对照组（两个大户余额 34333.588579 / 77700.298138 USDT）与 explorer 索引**完全一致**。

## 3. 三实例权限矩阵（同 creator）

| 版本 | 地址 | 字节码 | 交易数 | owner |
|---|---|---|---|---|
| v1 | `TEhD9ZBShvZifvLRnKF37QqmcVGSBUr2me` | 19,278 B | 11 | `TYzxbVnaxc7XaxsYGwYMj5v8nHJqZmyj5F`（根运营方） |
| v2 | `TJ4ziRXoWe6uanTAZytqAMKkKv7RnrbZZD` | 22,666 B | 51 | `TF6TU56W2Np…` |
| v3 | `TJWSdudwK7vv6eTFidK2JuuPWhXPezZBsC` | 22,766 B | 26 | `TF6TU56W2Np…` |

同源判定：三者 `creator` 相同；三者 `implementation()` 均指向**无字节码、0 交易**的占位地址（非代理）。

**矩阵结果（节选）**：

```
陌生人 / 非指派方          : 全部 Unauthorized()
指派给该 escrow 的运营员    : recoverSurplus / cancelEscrow / proposeRefund / approveRefund / settlePendingRefund 全过权限
owner                      : setAdmin / setPause / 改费率 / transferOwnership / transferAsset 全过权限
主运营(单key)              : 可在同一实例内独立完成 propose → approve → settle（无第二人复核）
```

⇒ 结论：**代码无第三方越权面**；严重级全在"单密钥 + 无限授权"的治理层。

⚠️ **但这不是终点**：只交这个结论会被用户打回（"我要这些干什么 我要你挖洞"）。
权限矩阵扫完后**必须继续做业务逻辑扫描**（见 §9 与 `references/business-logic-probing.md`），
用户要的"业务漏洞/逻辑漏洞"在那一条线上。

## 4. 多版本 diff 的杀伤力（本案最高价值手法）

```
v1/v2 有, v3 无:  proposeRefund(uint256,uint8)          previewRefund(uint256,uint8)
                  settlePendingRefund(uint256,uint256,uint8)
v3 有, v1/v2 无:  proposeRefund(uint256,uint8,uint256)   ← 新增 amount
                  previewRefund(uint256,uint8,uint256)
                  settlePendingRefund(uint256,uint256,uint8,uint256)
                  ERR UnexpectedTokenAmount()            ← 新增「到账金额与预期不符」
                  ERR AddressEmptyCode(address) / ERR FailedCall()   ← OZ 5.x SafeERC20 完整实现
```

**读法**：新增参数/新增错误 = 他们**修过**什么。

**但纪律**：这只能说明"新版加固了"，**不能直接推"旧版可利用"**。本案正是靠实测 v1 的
`proposeRefund(1, 3)` 返回新错误 `0x4d2b57f6`（有 mode 校验）而**证伪**了"旧版可超额退款"的推断。

## 5. 真正的实锤：`previewRefund` 越界读

```
v1 previewRefund(uint256,uint8) // 同一 escrow：
  mode=0/1 → 3,000,000 (3.000000 USDT)   ✓ 正确（= 本金）
  mode=2   → 0 | 3,000,000 | 0           ✓ 正确
  mode≥3   → 1,294,686,198               ★ mode=3/4/5/10/50/100/200/255 全部同一垃圾值
```

该 escrow 的 `getFeeTerms` 全为 0 ⇒ 不是手续费推导 ⇒ **未校验枚举导致的越界/错槽读取**。
写路径（`proposeRefund`）已正确校验 ⇒ 等级为**中**（前端/集成方金额显示错误），不造成资金损失。
**如何证伪"是手续费算出来的"**：把 `getFeeTerms` 一起打出来对账 —— 手续费为 0 却出现大额 ⇒ 不是费用逻辑。

## 6. allowance 暴露面（P0 级发现）

```
allowance(主运营 → v1) = 2^256-1  ★无限（v1 已弃用！）
allowance(主运营 → v2) = 2^256-1
allowance(主运营 → v3) = 2^256-1
allowance(运营A  → v2/v3) = 2^256-1
```

⇒ **废弃的 v1 仍持有运营方热钱包的无限提款权** = 把钱包暴露在废代码上。P0 动作：`approve(v1, 0)`。

## 7. 资金闭环（证明链上"活跃度"是自成交）

```
09-26 05:26  TUn4TWU2… → TNhntpwq(service)    +97.500000 USDT   ← 注资起点
09-27 11:33  TNhntpwq   → TDUy1aGf(运营A)       -6.000000 USDT
09-27 11:35  TPDTkzEs(partyA 空壳合约) → TNhntpwq  +2.940000 USDT  ← 托管"退款"回流
09-27 11:45  TNhntpwq   → TAqxyMJP(主运营)      -3.000000 USDT
```

6 笔 escrow 的 `partyA` 全是运营员 `CREATE` 出的空壳地址；出入金全部闭环于运营方自有钱包。
**链上无任何第三方用户资金** ⇒ 典型的"化妆式活跃度"（搭台未开张或纯自成交）。

## 8. 判别要点速记

- 权限门可通过的"业务错误"清单是理解合约的钥匙 —— 把它当**正面证据**用
- `getEscrow(id)` 结构体：**"被指派运营员"字段** + `setAdmin` 交易历史 = 运营方钱包群
- 有活跃大额流水的 `service` 字段地址 = 运营方业务枢纽
  （本案单日数十笔 1 万~9 万 USDT 整额双向进出 = 跑分/代收代付形态）
- `creator` 是归属最强锚点：多实例同一 creator = 同一运营方
- **老钱包 + 159k 交易的垃圾代币持有 = 不是归属证据**（dust 全网撒）；已用 §7 的域名验证反例记下
- 出金/入金方向一定要用 **explorer 原始记录**核对，别信自己解码的 from/to

## 9. R6：业务逻辑专项（活靶 escrow6）★ 本案例最终交付物

活靶筛选：`escrowCount()=6`，前 5 个已结算（任何调用回 `WrongStatus`，无信息量），
只有 **escrow6 `status=0`**、锁着 5U+5U=10U ⇒ 唯一可打的实例。

### 9.1 `previewRefund` 全参数矩阵 → 反推 mode/amount 语义

```
previewRefund(6, mode=0, amount=任意)      → [5,000,000, 5,000,000, 0]  各拿各的
previewRefund(6, mode=1, amount=0)         → [0, 10,000,000, 0]        ★ partyB 独吞全部 10U
previewRefund(6, mode=1, amount=5,000,000) → [5,000,000, 5,000,000, 0]  amount = 给 A 多少
previewRefund(6, mode=1, amount=2**200)    → [10,000,000, 0, 0]        amount 被 clamp（无溢出）
previewRefund(6, mode=2, amount=0)         → [10,000,000, 0, 0]        ★ partyA 独吞全部
previewRefund(6, mode≥3)                   → [1,294,686,198] 恒定      ★ 非法 mode 不 revert
```

### 9.2 写路径 vs 读路径校验不对称（可直接上报）

```
proposeRefund(mode=3) → REVERT InvalidMode (energy 15,028)   ← 写路径有校验 ✓
previewRefund(mode=3) → 返回 1,294,686,198 USDT = 1,294.686198 ← 读路径没校验 ✗
```
前端拿 `previewRefund` 显示"可退款额" ⇒ 非法 mode 下显示真实值（10U）的 **129 倍**。等级：中（信息误导）。

### 9.3 energy 判"参数是否被读取"

```
proposeRefund(6, mode=0, amount=1)      → result=True energy=153,307
proposeRefund(6, mode=0, amount=10**12) → result=True energy=153,307  ← 完全相同
```
⇒ 提议阶段**完全不读 amount** ⇒ 真正分账的是结算阶段另传的 amount ⇒ **提案内容与实际出账脱节**。

### 9.4 energy 跨角色差异 ⇒ 特权分支

```
proposeRefund(6,0,1):  partyB=153,307  service=153,363  运营员=361,422  ★ 多 ~208,000 energy
settlePendingRefund:   运营员→WrongStatus(过权限门,14,404)   其他→Unauthorized(8,373)
partyA 任何调用 → Unauthorized (energy 8,541 = 秒拒)
```

### 9.5 裸 REVERT

```
deposit(6, 1U): partyB/service → result=True + energy≈1.9 万 + REVERT opcode（无具名错误）
```
⇒ 集成方无法区分"金额非法/已满额/状态不允许"。等级：低（健壮性）。

### 9.6 关键教训：`constant_result == [""]` 是歧义的

本会话在"空返回"上反复误判成功/失败。**必须读 `result.result` + `energy_used` 联合判定**：
`ok=True` + energy 十几万 ⇒ 跑完了；`ok=True` + energy ~8k ⇒ 进门即拒。
没有这条，§9.3/§9.4 全都判不出来。
