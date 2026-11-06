# 福利来钱包 — 身份层 vs 资金层分离案例

> @fllqb TG USDT 钱包 bot — 身份层打穿但资金层绑死 token 的经典边界

## 核心发现

**身份/安全层**和**资金层**使用不同的鉴权机制：

| 层 | 鉴权方式 | IDOR 结果 |
|----|---------|----------|
| safe/get_verify_info | `tg_id` 参数（无归属校验）| ✅ 越权读 TRON 地址 |
| safe/change_pwd | `user_id` 参数（无归属校验）| ✅ 越权改任意 PIN |
| safe/2verify_* | `user_id` 参数 + 旧安全答案 | ⚠️ 需旧答案才能改 |
| safe/withdrawal | `token`（TG 会话绑定）| ❌ 无 IDOR |
| trade/web/user/info | `token` | ❌ 无 IDOR |
| trade/web/order/* | `token` | ❌ 无 IDOR |

## 资金边界分析

```
┌─────────────────────────────────┐
│  身份层（IDOR 可打穿）            │
│  ├─ PIN 管理 → user_id          │
│  ├─ 安全提示 → tg_id            │
│  └─ 2FA 设置 → user_id          │
├─────────────────────────────────┤
│  资金层（IDOR 打不穿）            │
│  ├─ 余额查询 → token only       │
│  ├─ 提现 → token + PIN + 地址   │
│  ├─ 买卖U → token + 实名        │
│  └─ 订单 → token + order_no     │
└─────────────────────────────────┘
```

## 双路径评估

即使 ATO 了身份层（改掉 PIN），仍需评估：

1. **提现路径**：`withdrawal` 绑 token → 需对方 TG 会话，ATO PIN 不够
2. **改 TRON 地址劫持**：`2verify_set_hit_answer` 需旧安全答案 → 被挡
3. **找回账户重绑**：`2verify_bind` 需 bind_tg_id + 安全答案 → 被挡
4. **市场挂单**：需实名认证（姓名+手机+短信码）→ 被挡

**结论**：身份接管 ≠ 资金接管。本案 wallet_id / TRON 地址只能读不能改，资金路径被 token 封死。

## 对照 fund-edge-ops 方法论

本案在对象矩阵中的定位：

| 维度 | 自己账号 | 他人账号 |
|------|---------|---------|
| 读余额 | ✅ token | ❌ token 绑定 |
| 读 TRON 地址 | ✅ | ✅ **IDOR via tg_id** |
| 改 PIN | ✅ | ✅ **IDOR via user_id** |
| 提现 | ✅ token+PIN | ❌ 需对方 token |
| 改收款地址 | ✅ 需旧答案 | ❌ 需旧答案 |
| 挂买卖单 | ✅ 需实名 | ❌ 需实名+token |

**wallet_id 层（展示层充值地址）**：本案通过 `get_verify_info(tg_id)` 可读任意用户 TRON 地址，但只是展示层读取，不能修改绑定。
