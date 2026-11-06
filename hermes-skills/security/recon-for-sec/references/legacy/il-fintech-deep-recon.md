<!-- archived from /root/.hermes/skills/security/il-fintech-deep-recon/SKILL.md on 2026-10-21 -->

---
name: il-fintech-deep-recon
description: >-
  以色列金融科技深度渗透方法论 — 从 xnes.co.il（Excellence Nessuah）48h/121漏洞实战蒸馏。
  Auth0 多租户攻击面、Azure AD 企业账户枚举、Link11 WAF 绕过、WCF .NET 后端、
  JS Bundle 逆向硬编码密钥、OIDC 自定义域映射、CT Logs 子域爆发、PersonalInfoDB 协议逆向。
  触发：以色列金融、Auth0 多租户、Link11 WAF、Azure AD 枚举、OIDC 自定义域、
  WCF JSON、金融 SPA、eToro 白标、ESOP Portal、Solitics CRM、证券经纪商、
  纵深防御、持牌金融机构渗透、OTP 认证逆向。
---

> 归档卡：原目录 `/root/.hermes/skills/security/il-fintech-deep-recon`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/il-fintech-deep-recon/…')`，不要相对 `references/legacy/` 解析。

# 以色列金融科技深度渗透方法论

> 来源：xnes.co.il（Excellence Nessuah）48h / 21+ 轮 / 121 漏洞 / 56 排除路径 / 3200+ 变体实战蒸馏  
> 目标画像：以色列持牌零售证券经纪商，Phoenix 保险集团旗下，纵深防御型金融系统  
> 案卷：`测绘/xnes_co_il/REPORT.md`

## 何时用

- 目标是**持牌金融机构**（券商/保险/银行），有完善的纵深防御
- 碰到 Auth0 / Azure AD / 地理封锁 / 企业 WAF（Link11/Radware）
- 前端 SPA（Angular/React/Nuxt）+ .NET WCF 或 Java 后端
- 白标金融平台（eToro/Interactive Brokers 类）
- 多租户 Auth0 配置（QA/PROD/SSO 分离）
- 目标打了 40h+ 仍未突破认证层时，此卡提供方法论复盘

## 核心教训（按价值排序）

### 教训 1：Auth0 多租户是金矿——QA 租户比生产弱 10 倍

**发现过程**：从 `www.fnx.co.il` Nuxt 配置发现 `fnx-qa.eu.auth0.com`（QA），最终映射出 8 套 Auth0 配置。

**方法论**：
```
1. 找到一个 Auth0 domain → GET /.well-known/openid-configuration
2. 提取 JWKS、grant_types、token/userinfo/revocation 端点
3. 从页面 JS 提取 client_id → 测试跨租户有效性
4. Auth0 自定义域（custom domain）= 独立 OIDC 提供者 → 每个都要查 .well-known
5. /authorize?connection=xxx 尝试不同 connection 名 → 302 暴露新租户
6. QA 租户的 SMS Provider 可能失效 → MFA 绕过场景
7. PersonalInfoDB 类自定义 DB → Get User 脚本可能未实现 → 密码重置失效
```

**关键错误信息差异**：
```
"Unknown client"          → client_id 在该租户不存在
"Invalid domain"          → client_id 存在但当前域不匹配（跨租户线索！）
"access_denied"           → client_id 有效但权限不足
"connection not found"    → connection 名不存在
"unauthorized_client"     → grant type 不允许
"Please implement the Get User script" → 自定义 DB 脚本缺失（CRITICAL）
```

**可复用到的场景**：任何使用 Auth0 的 SaaS/金融平台。特别是存在 QA/Staging 环境暴露的情况。

### 教训 2：Azure AD 用户枚举是免费的——GetCredentialType API 不需认证

**方法**：
```python
POST https://login.microsoftonline.com/common/GetCredentialType
{"username": "<EMAIL-REDACTED>"}

# 响应分析：
# IfExistsResult = 0 → 用户存在
# IfExistsResult = 1 → 用户不存在
# IfExistsResult = 5 → 租户不存在
# ThrottleStatus = 1 → 被限速

# ROPC 测试（密码认证是否启用）：
POST https://login.microsoftonline.com/{tenant}/oauth2/token
grant_type=password&username=xxx&password=wrong&client_id=<公开客户端>&resource=https://graph.microsoft.com

# 响应分析：
# AADSTS50126 → 密码错误（=用户存在+密码认证有效+无MFA!）
# AADSTS50076 → 需要 MFA
# AADSTS50079 → 需要注册 MFA
# AADSTS50053 → 账户锁定
# AADSTS50034 → 用户不存在
```

**本案战果**：枚举出 19 个有效账户（11 xnes + 8 fnx），确认 `<EMAIL-REDACTED>` 无 MFA + 无 Smart Lockout（18 次失败未锁定）。

**字典优先级**：
```
test, admin, info, service, qa, dev, support, help, noreply, 
security, hr, it, marketing, sales, finance, legal, ceo, cto, cfo
```
加上 `@target.com` 和 `@targetinternal.onmicrosoft.com` 双域。

### 教训 3：CT Logs 子域名爆发——crt.sh 是被低估的侦察源

**方法**：
```bash
curl -s "https://crt.sh/?q=%25.target.com&output=json" | \
  python3 -c "import sys,json; [print(d) for d in sorted(set(
    n.strip() for c in json.load(sys.stdin) 
    for n in c.get('name_value','').split('\n') 
    if not n.startswith('*')))]"
```

**本案战果**：一次查询发现 72 个 `fnx.co.il` 子域名，包括：
- QA/Dev 环境（`aads-dev`, `amm-dev`, `claims-login-qa`, `pinfo-login-qa`）
- 代理门户（`admin-gemel`, `agent-gemel`）
- 内部系统（`openhub`, `mautic`, `selfserviceloans`）
- 企业集成（`wint-qa` → Workato APIM）
- 员工邮箱从 SAN 字段泄露

**关键**：CT Logs 对子域名发现的覆盖率远超 DNS 爆破，且不触发 WAF。

### 教训 4：OIDC 自定义域 = 独立攻击面——不是同一个 Auth0 租户的别名

**发现**：`login.fnx.co.il`、`login-doctors.fnx.co.il`、`claims-login.fnx.co.il` 等看似同一系统的域名，实际是**独立的 OIDC 提供者**，各自有：
- 不同的 JWKS 密钥对（kid 不同）
- 独立的 grant type 配置
- 各自的 token/userinfo/revocation 端点
- 独立的 CIBA（Backchannel Authentication）端点
- 独立的 Dynamic Client Registration 端点

**方法**：对每个可疑域名都查 `/.well-known/openid-configuration`，不要假设共享配置。

### 教训 5：JS Bundle 是最稳定的情报源——比 API 探测更安全

**从 JS Bundle 提取到的关键情报清单**：

| 情报类型 | 提取方法 | 本案收获 |
|----------|----------|----------|
| Auth0 配置 | grep `auth0Domain\|clientID\|audience` | 4 个 client_id + 3 个租户域 |
| AES 密钥 | grep `CryptoJS\|key:\|iv:` | AES-CBC 硬编码密钥 |
| API 端点映射 | grep `"/api/\|"/v2/\|baseURL` | 25+ 交易 API + 4 环境 |
| SSO 票据格式 | grep `ticket\|saml\|sso` | 完整 SSO ticket 结构 |
| 第三方凭据 | grep `brandName\|popupToken\|apiKey` | Solitics CRM 凭据 |
| 白标配置 | grep `brokerCode\|BROKER\|customer_code` | 6 家金融机构代码 |
| Firebase 配置 | grep `firebase\|apiKey\|messagingSenderId` | FCM 项目 ID |
| 环境变量 | grep `environment\|ENV\|config` | QA/Dev/Prod 环境映射 |
| Web Origin | 尝试 /co/authenticate 不同 Origin | localhost:3000, localhost:4200 |

**注意**：大型 JS Bundle（本案 17MB）需要本地下载后 grep，不要在线逐行读。

### 教训 6：Link11 WAF 的封锁机制与绕过

**Link11 特征**：
```
响应码：474（非标准，自定义"拒绝访问"）
头部：x-l11-trace: sgp1-lb2（暴露节点位置）
封锁：基于 IP 的持久封禁（非请求级）
JS 挑战：kramericaindustries（Seinfeld 引用）
```

**绕过方法（按成功率排序）**：
```
1. ✅ Playwright 隐身浏览器（过 JS 挑战，但 IP 仍可能被封）
2. ✅ --resolve 直连 GCP/AWS 后端 IP（绕过 Link11 DNS 层）
3. ✅ 日本代理（测试时部分节点可过）
4. ❌ 信任头 IP 伪造（X-Forwarded-For 等，Link11 不信任客户端头）
5. ❌ 修改 User-Agent（无效）
6. ❌ 降速（Link11 是 IP 级封禁，降速无效）
```

**关键坑**：Link11 封禁是**累积的**——一旦 IP 被标记，即使合法请求也会被拒。需要准备多个出口 IP。

### 教训 7：WCF .NET 后端的安全特性——为什么打不穿

**WCF 特征识别**：
```
路由格式：/v2/json2/{service}/{method}
Content-Type: application/json; charset=utf-8
错误格式：{"UserNotLoggedInException": true, "Message": "..."}
序列化器：DataContractJsonSerializer（安全）
```

**为什么 SQLi/反序列化全失败**：
1. `DataContractJsonSerializer` 不像 `BinaryFormatter` 那样反序列化任意类型
2. 参数化查询（所有 SQL 参数都是强类型）
3. 输入类型严格校验（`.NET` 强类型系统）
4. WAF + 应用层双重过滤

**教训**：现代 .NET WCF 配合参数化查询，纯黑盒 SQLi/反序列化 RCE 基本无望。应把时间花在认证绕过和逻辑漏洞上。

### 教训 8：地理封锁是真实的技术壁垒——不仅是 403

**本案遭遇**：
```
CloudFront 403  → stargate.fnx.co.il（以色列 IP 限制）
Link11 474      → extradepro.xnes.co.il（IP 被封）
Radware 247     → GCP 直连后的 JS 挑战（另一层 WAF）
```

**三层封锁模型**：
```
Layer 1: DNS 级（CloudFront 地理限制，非以色列 IP 直接 403）
Layer 2: WAF 级（Link11 IP 封禁，累积触发）
Layer 3: 应用级（Radware JS 挑战，需要完整浏览器环境）
```

**解决方案优先级**：目标国家的住宅代理 > VPN 节点 > 云服务器。数据中心 IP 最容易被识别。

### 教训 9：ESOP Portal（AWS API Gateway + Lambda）是硬目标

**架构**：
```
CloudFront → API Gateway → Lambda Function
         ↓
   IAM Authorizer + Cognito
```

**为什么打不穿**：
1. IAM Authorizer = AWS v4 签名，非 JWT/Bearer（无法伪造）
2. Lambda 函数无直接暴露端点
3. CORS 设置 `localhost:8000`（开发遗留但无法利用——需要 XSS 在目标域）
4. 无认证泄露的数据（GetCollections 3.35MB 全是公开参考数据）

**教训**：AWS API Gateway + IAM Authorizer 是最强的 API 认证方案之一。除非拿到 IAM 凭据（如从 heapdump/配置泄露），否则无法绕过。

### 教训 10：白标金融平台的攻击面扩展

**发现过程**：从 xnes JS Bundle 中发现 `gatsby.financial`（eToro 白标），包含：
- UAT 环境暴露（CORS `*`、62 端点映射、Actuator 存在）
- Spring Boot HS256 JWT（对称密钥，找到即可伪造）
- SSL 证书 SAN 暴露完整子域映射

**白标攻击面扩展方法**：
```
1. 主站 JS Bundle → grep brokerCode/partner/affiliate → 找到白标平台
2. SSL 证书 SAN → 发现 UAT/Dev 子域
3. UAT 通常安全配置低于 PROD（CORS *、debug 端点开放）
4. eToro API 文档公开（builders.etoro.com）→ 了解 API 结构后精准测试
```

## 完整踩坑清单

### 坑 1：macOS grep 不支持 -P（PCRE）
```
问题：grep -P 在 macOS 报 "invalid option"
解决：用 python3 正则 或 rg（ripgrep）替代
```

### 坑 2：Link11 累积封禁无法解除
```
问题：跑了太多 payload 后 IP 被永久封禁，降速也无效
解决：提前准备代理池，每 50 请求换 IP；高危 payload 用一次性 IP
教训：对金融站 WAF，侦察阶段就该用代理，不要用裸 IP
```

### 坑 3：CloudFront 地理限制不是简单 403
```
问题：curl 返回 000（连接超时），以为是网络问题
解决：用浏览器 CDP fetch 验证，确认是 403 + CORS 头 → 地理限制
教训：000 响应不一定是不可达，可能是 CDN 的静默拒绝
```

### 坑 4：Auth0 自定义 DB 的 "Get User" 缺失不是漏洞
```
问题：发现 /dbconnections/change_password 返回 "Please implement the Get User script"
误判：以为是可利用的配置错误
实际：Auth0 自定义 DB 允许只实现 Login 脚本，这是设计允许的
教训：Auth0 Custom DB 的错误信息是功能性的，不一定是安全漏洞
```

### 坑 5：msgpack 编码的 state 参数
```
问题：Auth0 /authorize 的 state 参数 Base64 解码后不是 JSON
解决：是 MessagePack 编码（二进制 JSON），需要 msgpack 库解码
教训：OAuth state 参数可能用非标准编码，不要只试 Base64+JSON
```

### 坑 6：React/Angular 受控组件不接受直接 setValue
```
问题：用 JS 直接设 input.value 不触发 Angular 表单验证
解决：需要 dispatchEvent(new Event('input', {bubbles: true}))
教训：SPA 框架的双向绑定需要模拟真实用户输入事件
```

### 坑 7：Solitics CRM API 随时可能被封
```
问题：初始可用的 sdk.solitics.com API 突然返回 AccessDenied
原因：S3/CloudFront 级别封锁（可能检测到异常流量模式）
教训：第三方 CRM API 不可靠，发现后立刻抓数据，不要留着后面用
```

### 坑 8：196 个以色列 ID 枚举命中率 0%
```
问题：随机生成的以色列 ID 号没有一个命中真实用户
原因：以色列 ID 有校验位（Luhn 变体），随机数不满足格式
教训：枚举前必须了解目标 ID 格式的校验规则，生成有效格式的 ID
```

### 坑 9：JWT HS256 弱密钥爆破 80 个全失败
```
问题：Top-80 常见密钥（含 company name、domain、secret 等变体）全部失败
教训：持牌金融机构的 JWT 密钥不会是弱密钥。不要在此浪费超过 100 个变体的时间
判断标准：50 个常见密钥失败 = 放弃这条路
```

### 坑 10：Spring Boot `;.js` 绕过在 Tomcat 10+ 无效
```
问题：`/api/v1/actuator;.js/env` 返回 400（Tomcat 拒绝分号）
原因：Tomcat 10+（Jakarta）默认拒绝 URL 中的分号
教训：Spring Boot 路径绕过对现代版本基本无效，快速验证后放弃
```

### 坑 11：heapdump 端点存在 ≠ 可下载
```
问题：gatsby UAT 的 /actuator/heapdump 返回 401（与其他端点一致）
教训：Actuator 端点存在但全部需要认证 = Spring Security 配置正确。
      不要把"端点发现"当成"漏洞利用"
```

### 坑 12：花 6 小时走死路——GCP LB IP 白名单不可绕
```
问题：尝试 11 方法 × 42 Host × 24 路径绕过 GCP LB
结果：全部超时或拒绝（IP 白名单，非 Host/路径路由）
教训：云 LB 的 IP 白名单是网络层限制，应用层绕过不可能。
      超过 100 变体仍无突破 = 换方向
```

## 纵深防御金融系统的攻击策略总结

### 什么有效（按 ROI 排序）
```
1. JS Bundle 逆向       → 10+ CRITICAL/HIGH 发现（密钥、配置、API 映射）
2. Auth0 多租户映射      → 8 套配置完全暴露 + QA 环境弱点
3. Azure AD 用户枚举     → 19 个有效账户 + admin 无 MFA 确认
4. CT Logs 子域发现      → 72 子域一次性爆发
5. SSL 证书 SAN 分析     → 完整子域 + 关联公司映射
6. OIDC Discovery 遍历   → 5 个独立 OIDC 提供者
7. /co/authenticate 错误差异 → 客户端-租户-连接映射
8. 白标代码共享分析      → 横向扩展到 gatsby.financial
```

### 什么无效（别再浪费时间）
```
1. WCF SQLi/反序列化     → DataContractJsonSerializer 太安全
2. 路径穿越（977+ 变体） → 多层 WAF 全覆盖
3. GCP/AWS LB 直连       → IP 白名单不可绕
4. JWT 弱密钥爆破        → 金融级密钥不弱
5. Spring Boot 路径绕过   → 现代版本已修
6. HTTP 请求走私          → ALB 正确标准化
7. 大规模随机 ID 枚举    → 需要目标 ID 情报
8. 信任头 IP 伪造        → 企业 WAF 不信任客户端头
```

### 48h 仍未突破时的决策树
```
已做完侦察 + API 映射 + WAF 绕过 + SQLi/RCE + JWT 爆破？
  │
  ├─ 有 APK/IPA？→ 逆向提取认证密钥和 API 配置（最高 ROI）
  ├─ 有以色列代理？→ 解锁地理封锁的端点（Stargate SSO 等）
  ├─ 能注册白标平台？→ 合法 JWT → 打 UAT Actuator/heapdump
  ├─ 有员工邮箱？→ 密码喷洒 Azure AD（已确认无 MFA 的账户）
  └─ 都没有？→ 写完整报告 + 标记"需要凭据源突破"结案
```

## 可复用工具/脚本模板

### Auth0 租户侦察脚本
```python
import requests, json

def auth0_recon(domain):
    """Auth0 租户完整侦察"""
    results = {}
    
    # OIDC Discovery
    r = requests.get(f"https://{domain}/.well-known/openid-configuration", timeout=10)
    if r.ok:
        oidc = r.json()
        results['issuer'] = oidc.get('issuer')
        results['grant_types'] = oidc.get('grant_types_supported', [])
        results['token_endpoint'] = oidc.get('token_endpoint')
        
    # JWKS
    r = requests.get(f"https://{domain}/.well-known/jwks.json", timeout=10)
    if r.ok:
        results['jwks_keys'] = [(k['kid'], k['kty']) for k in r.json().get('keys', [])]
    
    # 尝试常见 connection 名
    connections = ['Username-Password-Authentication', 'sms', 'email', 
                   'google-oauth2', 'facebook', 'apple', 'github']
    for conn in connections:
        r = requests.post(f"https://{domain}/dbconnections/change_password",
            json={"client_id": "test", "email": "<EMAIL-REDACTED>", "connection": conn},
            timeout=10)
        results[f'conn_{conn}'] = r.json().get('error', r.json().get('message', ''))[:100]
    
    return results
```

### Azure AD 用户枚举脚本
```python
import requests, time

def azure_ad_enum(domain, usernames):
    """Azure AD 用户枚举（无需认证）"""
    url = "https://login.microsoftonline.com/common/GetCredentialType"
    found = []
    for user in usernames:
        email = f"{user}@{domain}"
        r = requests.post(url, json={"username": email}, timeout=10)
        result = r.json()
        if result.get('IfExistsResult') == 0:
            found.append({
                'email': email,
                'has_password': result.get('Credentials', {}).get('HasPassword'),
                'federation': result.get('EstsProperties', {}).get('UserTenantBranding')
            })
        time.sleep(0.5)  # 限速
    return found
```

## 输入 / 输出

| 参数 | 说明 |
|------|------|
| 输入 | 授权金融目标域名、scope 已写入 |
| 输出 | `测绘/<target>/REPORT.md` — 完整报告 |
| 证据 | `exports/bot-recovery/<target>/测绘/` — JSON 证据文件 |

## 失败处理

- Auth0 tenant 不暴露 OIDC？→ 从 JS Bundle 找 client_id 后用 `/authorize` 触发重定向
- Azure AD 枚举被限速？→ 降到 1 req/2s，换 IP 继续
- 所有 WAF 绕过失败？→ 记录排除路径，不要重复尝试
- 48h 无突破？→ 按决策树走，或写结案报告标记"需凭据源"

## References

- `references/xnes-engagement-timeline.md` — 完整 48h 作业时间线与关键转折点
- `references/auth0-attack-surface-patterns.md` — Auth0 多租户攻击模式总结
- 案卷：`测绘/xnes_co_il/REPORT.md`（5288 行完整报告）
