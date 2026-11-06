# OAuth / OIDC 配置缺陷（企业第三方登录面）

> 深化 `oauth-jwt-test.md`：OAuth/OIDC 的攻击面集中在**回调校验、状态绑定、账户映射**三处。遇第三方登录（微信/Google/企业 IdP）先按本文档过。全部授权测试手法。

## 一、流程地形与配置陷阱

```
授权码流程: 客户端 → 授权端点 → (用户登录) → 回调(带 code) → token 端点 → 资源
隐式流程:   客户端 → 授权端点 → 回调(带 access_token)  ← token 在 URL fragment（高危配置）
PKCE:       客户端生成 verifier+challenge → 授权 → 回调(code) → token(需 verifier)
```

| 配置陷阱 | 后果 |
|---------|------|
| 用隐式流程（token 在 fragment） | token 泄露进浏览器历史/日志/Referer |
| 无 PKCE | code 窃取后可兑换（公共客户端） |
| redirect_uri 校验宽松 | token/code 被导走 |
| state 缺失/未校验 | 登录 CSRF（账户绑定攻击） |
| nonce 缺失/未校验（OIDC） | ID token 重放 |
| 账户映射用未验证 email | 预接管/账户接管 |

## 二、redirect_uri 校验全分类（逐级试）

| 校验级别 | 绕过 |
|---------|------|
| 精确匹配 | 无法绕过（换个面打） |
| 前缀匹配（`/callback` 开头） | `/callback.evil.com/`（路径拼接）、`/callback?redirect=//evil` |
| 包含匹配（含 target.com） | `https://evil.com/target.com`、`target.com.evil.com` |
| 正则宽松 | `http://` 不强制 https、没锚定结尾 |
| 域名匹配但允许开放重定向 | 目标自己的 `/redirect?url=evil` 链（token 搭便车） |
| 无校验 | 直接改 `redirect_uri=https://attacker/` → code 到手 |

**验证**：把 redirect_uri 改成自己可控域 → 回调收到 code/token = 漏洞成立。code 不能直接换 token（Public client 需 client_secret 时打 PKCE 缺失面）。

## 三、state / nonce / PKCE 缺失

| 缺陷 | 攻击 | 影响 |
|------|------|------|
| state 缺失 | 攻击者用自己的已登录会话发起登录，诱使受害者点"登录"完成绑定 | 受害者账户被绑定到攻击者第三方账号 = **账户接管** |
| nonce 缺失（OIDC） | 重放受害者 ID token | 会话冒充 |
| PKCE 缺失（公共客户端） | 窃取 code 后直接兑换 | token 获取 |

## 四、Token 面（audience / issuer）

- **aud 不校验**：用 A 应用的 token 调 B 应用（跨应用越权）
- **issuer 不校验**：自建 IdP 签发的 token 被接受（idp 混淆，类似 SAML）
- **算法混淆**：RS256（公钥验签）→ HS256（把公钥当 HMAC 密钥签名）——`jwt-tool` 一键切换
- **RFC 8707 resource indicator**：resource 参数指定错资源 → 越权 scope

## 五、账户绑定与预接管（最真实的接管点）

```
# 预接管（经典链）
1. 攻击者在 IdP 注册 <EMAIL-REDACTED>（IdP 可能不验证邮箱）
2. 攻击者用「Login with IdP」登录 target.com
3. target 看到 IdP 邮箱=<EMAIL-REDACTED>，本地无账号 → 自动创建并绑定
4. 受害者真登录时 → 已存在账号（攻击者控制）

# 绑定劫持（state 缺失时）
攻击者可控制绑定目标 → 把受害者账号绑定到自己的 IdP 身份

# 邮箱替换绑定（已登录用户改绑）
受害者已绑 A 邮箱 → 攻击者诱导改绑到攻击者 IdP 身份 → 接管
```

**验证**：用自己可控 IdP 身份重复注册流程（同一 email）→ 若能绑入已存在账号 = 预接管成立。

## 六、动态客户端注册（DCR）与 scope

- **DCR 开放**：任意注册新 client → 拿到 `client_id/secret` → 以该 client 身份发起流程（redirect_uri 自己可控）
- **scope 过度授权**：请求 `openid profile email` → 拿到多余用户数据（信息泄露面，中危起）
- **scope 混淆**：窄 scope 请求被服务端宽放行

## 七、快速测试流程（遇第三方登录）

```
1. 抓完整 OAuth 流程（authorize → callback → token → userinfo）
2. redirect_uri 变异矩阵逐级试（精确→前缀→包含→重定向链→无校验）
3. state/nonce/PKCE 缺失验证（重放与绑定攻击）
4. 预接管测试：自己 IdP 身份注册同 email → 能否绑已有账号
5. token 面：aud/issuer/算法混淆（jwt-tool）
6. DCR 开放探测（POST /register 无鉴权）
7. scope 越权（请求宽 scope 看是否放行）
```

**差分即证据**：进受害者账户（header 变受害者）/拿到他人 token = 才写；仅配置看起来松但利用不成 = 不写或低危。

## 八、红线
- 预接管测试用自己可控 IdP 身份，不碰真实用户邮箱
- 绑定攻击测试后恢复（自己账号解绑）
- token 只验证 scope/aud（读），不做资源操作