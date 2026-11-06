---
name: fund-edge-ops
description: >-
  会员资金面边缘越权：wallet_id 旁路、双路径资金 API、展示层充值地址劫持、
  幽灵单/消息神谕、提款 saga/fundsn 状态机、玩家票打 init2/turnWaterInit/task-center。
  用户提到 wallet_id、展示层地址、双路径 bypass、幽灵单、工单回单号、
  fundsn、turnWaterInit、task-center、提款状态机、FPS 客服改址时使用。
  假支付走 payment-callback-forgery；链上 from 归属走 usdt-deposit-attribution-hijack；
  换 userId 走 object-matrix-authz / idor-bola-chain。仅授权范围。
tags: [提现, 提现审核, 出金, 出金审核, 绕过审核, 钱包越权, 资金面, 提款]

---

# 会员资金面边缘越权

**前提**：目标在 `config/scope*.json`。先有会员票；没有先注册 / `auth-brute`。

**成功口径（按档，禁止跳级）**

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 双路径差分 / 换 `wallet_id` 响应变 / 玩家票打到 config | 只发现字段名 |
| L2 | A 票读到 B 的地址/余额/流水，或 B 的展示址变成 A 的 | 200 空 JSON；只读自己 |
| L3 | 自控小额按错误展示址入账，或自控单 saga 跳步 | 先问；禁止动他人余额 |

## 何时启用

- 已有会员票，资金 API 出现 `wallet_id` / `fundsn` / `recvAddress`
- 同一动作两条 path（wallet vs fund / pay vs finance）
- 充值地址来自 init / 消息 / 工单，而不是唯一建单口
- 提现多步带流水号；`user_id` IDOR 已阴

**不要走这张卡**

| 指纹 | 走 |
|------|-----|
| 无会话 | `auth-brute` / 开放注册 |
| 只换 uid 读 `/me` | `object-matrix-authz` |
| 共享收款 + 绑 from | `usdt-deposit-attribution-hijack` |
| notify / submit | `payment-callback-forgery` |
| resetPassword code 任意 / BOLA / 提现密无旧密 / 绑址 / minWithdraw | `gambling-password-reset-ato` · `ato_reset_withdraw_probe.py` |
| 负金额 / 单接口竞态 | `business-logic-payment` |
| 绑卡凭证伪造 | `gambling-deposit-chain-pentest` |
| 低权打管理角色 | `rbac-bypass-authz` |

## 强制行为

1. 先填 `测绘/object_matrix.md`（自己 vs 他人 × 钱包/地址/流水/消息）。  
2. `user_id` 阴性必须换 `wallet_id` + 双路径 + 消息神谕，禁止写「无越权」。  
3. 默认只 GET / 换键读。真提现、改他人收款址、耗余额 **先问**。  
4. 展示层与 USDT 归属**并行**；一张阴不算资金面结案。  
5. 只取 A/B 自控号证明，禁止枚举真实用户钱包。

## 最短命令

```bash
python3 tools/ops/fund_edge_ops_probe.py doctor

python3 tools/ops/fund_edge_ops_probe.py matrix \
  --base https://授权站 --case <案卷> \
  --token-a "$TOKEN_A" --token-b "$TOKEN_B" \
  --wallet-b "$WALLET_B" \
  --prefix /prod-api --cookie "$SID"

python3 tools/ops/fund_edge_ops_probe.py wallet-swap \
  --base https://授权站 --case <案卷> \
  --token-a "$TOKEN_A" --wallet-b "$WALLET_B" \
  --place query,body,header

python3 tools/ops/fund_edge_ops_probe.py cors \
  --base https://授权站 --case <案卷> --token "$TOKEN_A" \
  --origin https://另一租户域

python3 tools/ops/object_matrix.py check --case <案卷> --strict
```

## 六层（缺一层不准结案）

```text
① 会话票
② wallet_id ≠ user_id
③ order_id / fundsn
④ 双路径
⑤ 消息/工单神谕
⑥ 玩家票 init/turnWater/task-center/tenant
```

## 交接

- 链上 from 绑表入账 → `usdt-deposit-attribution-hijack`
- HTTP 回调 → `payment-callback-forgery`
- 换 uid 读 hash / 给他人加款 → `object-matrix-authz`
- 垂直管理 API → `rbac-bypass-authz`
- 负金额/并发双花 → `business-logic-payment` · `logic_vuln_probe.py`

## 真源

- 手法：`docs/playbooks/会员资金面边缘越权与状态机手法.md`
- 工具：`python3 tools/ops/fund_edge_ops_probe.py --help`
- 矩阵：`测绘/object_matrix.md` · `object_matrix.py check --strict`

## 内部钱包对接 API 未授权（2026-10 B8Casino 实锤）
- `/openapi.json` 230 路由零鉴权 → `/transfer/deposit`、`/transfer/withdraw-all`、`/game/launch-url` 免密进游戏
- 双账本判定（游戏钱包 ≠ 现金钱包），`/diag/egress` 泄出口白名单
- 细节见 `internal-wallet-transfer-unauth`

## 红包 handsel + 余额写 + 充值地址改写（2026-09 osaka web3 实战）
- 管理 API `P0 BALANCE WRITE` / `P0 HANDSEL` 均无二次校验：直接改余额、发红包
- 展示层充值地址被改写后，用户充值进攻击者地址（服务端不校验地址归属）
- 提现队列 `pending withdraws` 可读可改状态
- 判据：写 1 分钱自测 + 读回余额一致；红包发出后到账
