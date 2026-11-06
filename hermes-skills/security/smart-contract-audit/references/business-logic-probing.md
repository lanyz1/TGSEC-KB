# 业务逻辑挖掘：view 函数全参数空间扫描（TRON EscrowFactory 实录）

**适用**：用户不要"结构性风险/治理风险"，要**业务/逻辑漏洞**、要"能影响运营"、要"严重影响级别"。
此时权限矩阵已跑完（结论=无越权），必须换战场：**参数语义 + 边界 + 路径不一致**。

---

## 0. 先挑活靶（别在死实例上浪费轮次）

```
escrowCount() → 逐个 getEscrow(id) → 找 status 字段 == 0 且金额字段 > 0 的那个
```

实测 6 个 escrow：前 5 个已结算，任何调用都回 `WrongStatus`（教不了任何东西）；
只有第 6 个 `status=0`、锁着 10 USDT ⇒ **唯一可打的活靶**。

活靶逐字结构（raw hex，不经过任何解码器，避免自造假数据）：

```
word[0] partyA   = 0x94016ed5...   word[4] = 5,000,000   (5 USDT)
word[1] partyB   = 0x13adfd10...   word[5] = 5,000,000   (5 USDT)
word[2] service  = 0x05978110...   word[6] = 10,000,000  (总额 10 USDT)
word[3] operator = 0x099980bb...   word[7] = 0           ← status = 0（ACTIVE）
```

---

## 1. `previewRefund` 全参数空间 → 反推未文档化的 mode 语义

view 函数是**最便宜的语义 oracle**：把合约内部算好的分账直接返回给你。

```python
for mode in (0, 1, 2, 3, 255):
    for amt in (0, 1, 10**6, 5*10**6, 10**12, 2**200):
        previewRefund(6, mode, amt)
```

实测输出（escrow6 = partyA 5U + partyB 5U，总额 10U；返回 = [给A, 给B, 服务费]）：

| mode | amount | 返回 | 语义推断 |
|---|---|---|---|
| 0 | 任意 | `[5,000,000, 5,000,000, 0]` | 各拿各的（协商退） |
| 1 | 0 | `[0, 10,000,000, 0]` | ★ **partyB 单方拿走双方全部** |
| 1 | 5,000,000 | `[5,000,000, 5,000,000, 0]` | amount 决定给 A 多少 |
| 1 | 10**12 / 2**200 | `[10,000,000, 0, 0]` | amount 被 clamp 到总额（**无溢出**） |
| 2 | 0 | `[10,000,000, 0, 0]` | ★ partyA 单方拿走全部 |
| 2 | 5,000,000 | `[5,000,000, 5,000,000, 0]` | amount 决定给 A 多少 |
| ≥3 / 255 | 任意 | `[1,294,686,198]` 恒定 | ★ **非法 mode 返回垃圾值，不 revert** |

一次扫描同时拿到：**mode 的真实语义、amount 的确切作用（clamp，不是叠加）、读路径缺失的校验**。

---

## 2. 写路径 vs 读路径的校验不对称 ⇒ 一类可直接上报的洞

```
proposeRefund(mode=3) → REVERT InvalidMode (energy 15,028)   ← 写路径有校验 ✓
previewRefund(mode=3) → 返回 1,294,686,198 USDT             ← 读路径没校验 ✗
```

`previewRefund` 是前端/机器人拿来做"可退款额"展示的 ⇒ 非法 mode 下显示
**1,294.686198 USDT（真实可退 10 USDT 的 129 倍）** ⇒ 信息误导级。

**扫描时专盯**：同一 mode/amount 组合，写路径 reject 而读路径返回值 ⇒ 就是它。
（该 escrow 全部 `getFeeTerms` 为 0 ⇒ 排除"手续费推导"，确认是未校验枚举导致的越界/错槽读取。）

---

## 3. energy_used 当「参数是否被读取」的探测器

```
proposeRefund(6, mode=0, amount=1)      → result=True  energy=153,307
proposeRefund(6, mode=0, amount=10**12) → result=True  energy=153,307   ← 一模一样
```

**energy 完全相同 ⇒ 该路径上 amount 根本没被读 ⇒ 提议阶段不校验金额**。

⇒ 真正决定分账的是**结算阶段另传**的 amount ⇒ **提案内容与实际出账金额脱节**
（即使新版已加 `UnexpectedTokenAmount()` 核对"到账额"，**提案侧仍未绑定**）。

**通用判定法（"未使用的函数参数"类洞）**：同一函数、只改一个参数、energy 不动
⇒ 该参数在此路径上是**死参数**。

---

## 4. energy 跨角色对比 ⇒ 发现特权分支

```
proposeRefund(6, mode=0, amount=1):
   partyB  energy=153,307
   service energy=153,363
   运营员   energy=361,422   ← 多执行 ~208,000 energy

settlePendingRefund(6,1,0,1U):
   运营员   → WrongStatus (energy 14,404)  ★ 过了权限门
   partyB / service / 其他运营员 → Unauthorized (energy ~8,373)
```

⇒ 同函数不同角色 energy 差十几万 = **命中不同代码分支**（运营员那条含额外状态写入/结算准备）
⇒ 比"推断权限集中"硬得多，可直接写进报告。

**权限/角色矩阵的完整判读配方**（本会话最终版）：

| 角色 | `proposeRefund` | `settlePendingRefund` |
|---|---|---|
| escrow 的 partyA | Unauthorized (energy 8,541) | Unauthorized |
| escrow 的 partyB | **成功 (energy 153,307)** | Unauthorized |
| escrow 的 service | **成功 (energy 153,363)** | Unauthorized |
| 该 escrow 指派的运营员 | **成功 (energy 361,422)** | WrongStatus（过权限门） |

---

## 5. 可上报类别与严重度

| 类别 | 实测形态 | 严重度 |
|---|---|---|
| **默认值落在"独吞"分支** | `mode=1/2` + `amount=0` ⇒ 单方提议即拿走**双方**本金 | 高（资金转移） |
| **提案/结算金额脱节** | propose 的 amount 不落提案、settle 另传 | 高 |
| **读路径缺校验** | view 对非法枚举返回垃圾值而非 revert | 中（信息误导） |
| **裸 REVERT** | 走完 ~1.9 万 energy 后无具名错误中止 ⇒ 集成方无法区分"金额非法/已满额/状态不允许" | 低（健壮性） |
| **跨角色 energy 差异** | 暴露未文档化特权分支 | 高（佐证权限集中） |

---

## 6. 完整 result 对象判读（否则前五条全都判不出来）

```python
ok  = j["result"].get("result")   # True ≠ 成功，= "执行到"；必须配 energy 看深度
en  = j.get("energy_used")        # 深度指纹
sel = (j["constant_result"] or [""])[0][:8]
```

- `ok=True` + energy 十几万 ⇒ 业务逻辑真跑完了（哪怕 `constant_result` 是空的）
- `ok=True` + energy ~8k ⇒ 进门即拒（读 msg 里的 selector）
- **禁止**用 `constant_result == [""]` 判"成功"——无返回值的函数成功时就是空的。

---

## 7. 纪律

用户在合约审计中明确要「挖洞 / 业务漏洞 / 逻辑漏洞」，并**当场打断**了跑偏到资金图谱 /
对手方交易数画像 / 域名探活的方向。

⇒ 挖洞阶段只做：权限矩阵 → 活靶筛选 → view 全参数扫描 → energy 差分 → 参数绑定核查。
⇒ 归因/资金图谱只在用户**明确要求**时做，且不能替代挖洞产出。
⇒ 报告里"无越权、风险在治理"只能是补充栏，主栏必须是**能影响运营的业务逻辑问题 + P0 可执行修复**。
⇒ 推断被证伪立刻撤回并写明原因（本会话撤回过一条"旧版可超额退款"）。
