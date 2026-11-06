# 金融/券商系统专项（Spring Actuator 检测 + 外汇 IB API 探测模式）

> 摘自 `web-penetration-testing` 主体（2026-09 拆分，主体原 122K 撞 100K 硬限）；references 按需加载。

---

## 🥇 Spring Boot Actuator 信息泄露检测（金融/券商系统）

**适用场景**：遇到返回 401 的 Spring Boot 应用时（所有路径统一 401 而非 404 = Spring Security 全局过滤器）。

**自动检测命令**：
```bash
# 1. 快速确认 Spring Boot
curl -sk "https://target.com/actuator/health"  # 200 = Spring Boot
curl -sk "https://target.com/actuator/info"     # 200 = app info

# 2. 批量检查其他端点
for ep in health info env beans mappings configprops metrics \
           loggers httptrace threaddump heapdump conditions \
           scheduledtasks caches prometheus; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com/actuator/$ep")
  echo "$code /actuator/$ep"
done

# 3. 查找 Swagger API 文档
for path in /swagger /swagger-ui.html /swagger.json /swagger/v1/swagger.json \
            /api-docs /v2/api-docs /v3/api-docs /openapi.json; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com$path")
  echo "$code $path"
done
```

**响应码诊断**：
| 码 | 含义 |
|:---|:------|
| 200 | **完全公开** — 立即抓取内容分析 |
| 401 | **存在但受保护** — 记录为后续目标 |
| 404 | 不存在或Spring Security隐藏 |
| 503 | 应用池停止（如 IIS ASP.NET 的 admin 面板） |

**公开端点的价值**：
```json
// /actuator/health → 数据库信息泄露
{"db":{"status":"UP","components":{
  "ec1DataSource":{"database":"PostgreSQL"},
  "traderEvolutionDataSource":{"database":"PostgreSQL"}
}}}

// /actuator/info → 应用信息
{"app":{"name":"EC1 Backend","version":"1.0.0"},"environment":"prod"}
```

**已知绕过技术（全部失败）**：
| 尝试 | 结果 |
|:-----|:-----|
| 路径遍历 `/actuator;.html` / `..;/actuator/env` | 400/401 |
| 头部注入 X-Forwarded-For / X-Real-IP / X-Original-URL | 401 |
| Cookie 注入 JSESSIONID/SESSION=test | 401 |
| Spring Boot 2.x 特定绕过（/;/actuator/） | 400 |
| 方法覆盖（PUT/DELETE/PATCH） | 405/401 |
| Accept header 变化 | 401 |

**原则**：401 ≠ 404。如果 Swagger/Actuator 都返回 401 而非 404，说明应用池正在运行但 Spring Security 全量保护。重点关注 `/actuator/health` 和 `/actuator/info` 是否有公开意外暴露。

## 🥇 外汇券商/金融 IB 系统 API 探测模式

**区别于博彩站**：金融券商系统（如 EC Markets）使用专业 CDN（CloudFront/Cloudflare）、JWT 认证、Spring Boot/ASP.NET 架构，防护水平通常显著高于博彩站。

### Commission Chain (佣金链) Analysis

EC Markets IB 后台佣金链页面通过 `/api/ib/user/relationship/page` API 展示代理关系树结构：
- **Relation 列**：以 `listitem [level=1]` 树形导航显示父级链
- **筛选**：Relation(直接/间接/全部)、Email/Phone、Name/Alias、KYC状态
- **My Data 按钮**：聚焦当前用户的链
- **已知限制**：`parentAgentUserId` 永远为 null，即使佣金关系存在

### Browser Login Flow for SPA

当 API 直调登录失败（返回 "Not logged in"）：
1. 导航至 `https://ib.ecmarkets.com.au/` → 服务端渲染的登录表单
2. 填写 email/password → 点 Login → AJAX 登录 → cookie 自动设置
3. SPA 重定向至 `/en-US/dashboard`
4. 从 cookie 提取 token：`document.cookie.match(/token=([^;]+)/)[1]`

### Known Limitations (EC Markets IB)

1. `parentAgentUserId` 永远为 null（即使佣金关系存在）
2. Invite code 属主无法通过任何公开 API 查询
3. `agentSearch` 不能搜索 invite code
4. 管理员后台 `admin.ecmarkets.co.uk` 返回 503（IIS 应用池停止）

**API 发现方法论**：前端 Network 标签 → 提取请求 URL/Header → 用相同 token 重构 curl 调用。注意前端 Umi.js/React SPA 的 API 调用可能在 `ib.ecmarkets.com.au` 域名下发（返回 405），实际 API 端点在 `api.ecmarkets.com.au`。完整 16+ 端点列表见 `references/ecmarkets-ib-api-endpoints.md`（含认证方式、字段参考、已知限制）。

**认证头格式（非标准）**：
```bash
# ❌ 博彩站常见：Authorization: Bearer <token>
# ✅ 金融 IB 系统实际：自定义 header
token: eyJhbGciOiJSUzI1NiJ9...   # JWT in custom header
platform: IB                       # 平台标识（必须）
x-api-version: 2.44.0             # API 版本（必须）
lang: zh-CN                       # 语言（必须）
browserfingerprint: 1073981       # 用户ID（部分API需要）
```

**API 响应码诊断**：
| 码 | 含义 |
|:---|:------|
| 200 JSON | 有效请求，解析响应数据 |
| 200 SPA HTML | 请求未到达 API（前端路由捕获了路径） |
| 401 | 需要有效 token |
| 405 Method Not Allowed | 端点存在但 HTTP 方法错误，检查 Allow header |
| 503 | IIS 应用池停止（管理员面板常见） |
| **000 空响应** | **需要 SNI 或客户端证书** — 与 HTTP 错误不同 |

**三层系统架构识别**（从响应码模式推断）：

| 响应模式 | 系统类型 |
|:---------|:---------|
| 所有路径返回 401（统一错误页） | Spring Boot + Spring Security |
| 所有路径返回 200 SPA（Vue/React app） | 前端 SPA 应用（API 在另一域名/端口） |
| 混合：部分 200 JSON + 部分 200 SPA | ASP.NET Core + Vue SPA（API 在前端域名下） |
| 所有路径返回 503 | IIS 应用池停止（维护/宕机） |

**Token 获取方法**（通过浏览器）：
```javascript
// 1. Cookie 中的 JWT
var token = <REDACTED>;]+)/)[1];

// 2. API 调用方式
fetch('/api/ib/user/current/info', {
  headers: {
    'token': token,           // 自定义 header，不是 Bearer
    'platform': 'IB',         // 必须
    'x-api-version': '2.44.0', // 必须
    'lang': 'zh-CN'           // 建议
  }
}).then(r=>r.json()).then(console.log);
```

**Browser自动化登录**（免去手动复制token）:
```bash
# 步骤（中文版比英文版稳定）:
# 1. browser_navigate("https://ib.ecmarkets.com.au/zh-CN/userSign/login")
# 2. browser_type(ref=e14, text="邮箱")
# 3. browser_type(ref=e16, text="密码")
# 4. browser_click(ref=e10)  # "登 录"按钮
# 5. 登录后cookie自动设置，可直接在浏览器内导航菜单
# 注意：SPA在无头浏览器中可能渲染失败，但API调用不受影响
```

### 已知有效登录凭证
```bash
# 下级列表（可查到 users 但 pagination 可能有限制）
GET /api/ib/user/relationship/page?userId={userId}&pageNum=1&pageSize=10

# 搜索代理（只能搜到已有关系的用户）
GET /api/ib/user/agentSearch/field?field={uid}

# 邀请码无法反查属主
# 80+ API 测试后确认：金融 IB 系统不暴露 invite code -> user 的接口
```

**项目隔离原则（重要！）**：
```
❌ BFCP 必发彩票（博彩站）和 EC Markets（外汇券商）是不同项目
   - 不同系统架构（Vue+Vite vs React+Umi）
   - 不同 API 协议（AES加密 vs JWT token）
   - 不同 CDN（jkydns vs CloudFront）
   - 不同目标（博彩站渗透 vs 金融系统API调用）
```


```python
import subprocess, time, urllib.request, json

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_dir = r"C:\Users\Administrator\Desktop\chrome_debug"

cmd = [
    chrome_path,
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",  # 必须加此参数，否则websocket-client连接被403拒绝
    f"--user-data-dir={user_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "https://target.com/lottery/K3/SG31K3"
]
subprocess.Popen(cmd)
time.sleep(5)

# 检查调试端口
req = urllib.request.Request("http://127.0.0.1:9222/json")
with urllib.request.urlopen(req, timeout=5) as resp:
    tabs = json.loads(resp.read().decode())
    for t in tabs:
        print(f"{t.get('title','')} | {t.get('webSocketDebuggerUrl','')}")
```

**注意**：
- `--remote-allow-origins=*` 是**必需的**——不加此标志时，websocket-client 库连接 CDP 会返回 403 Forbidden（"Rejected an incoming WebSocket connection..."）
- Chrome 启动后通过 `http://127.0.0.1:9222/json` 获取标签页列表和 WebSocket 调试 URL
- CDP WebSocket 连接成功后，可通过 `Runtime.evaluate` 在页面中执行 JavaScript（包括 fetch API 调用、localStorage 读取、DOM 操作等）

**登录 API 403（即使从浏览器内调用）**：某些站点会基于 IP/地理位置限制登录。即使通过 CDP 在浏览器中执行 `fetch('/tools/_ajax/login', ...)` 也可能返回 HTTP 403，因为服务器检测到客户端 IP 不在允许区域。

**Vue 3 Pinia store 数据提取**：通过 CDP 控制已登录的浏览器后，可直接从 Vue 的 Pinia store 提取游戏配置、用户信息、当前期号等数据，无需调用 API：

**浏览器指纹规避**：对目标进行 headless Chrome 自动化时，需注入 evasion 避免被识别。完整规避套件（navigator.webdriver、plugins、languages、chrome.runtime、WebGL、Canvas）、Puppeteer 用法、AES 解密、以及新葡京站 capchaType 验证码对照表见 `references/puppeteer-evasion-captcha-analysis.md`。

```javascript
// 通过 CDP Runtime.evaluate 执行:
var pinia = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia;
// Lottery store: pinia.state.value.lottery
//   → lottery.lotteryCode, lottery.lotteryName, lottery.NowIssue, lottery.Odds
// User store: pinia.state.value.user
//   → user.loginName, user.accountId, user.money, user.type, user.parentId
// Site store: pinia.state.value.site
//   → site.lotteryList (所有彩票配置，从localStorage也同理)
```

从 localStorage 获取 JWT token：`localStorage.getItem('token')` 返回 JWT 格式字符串。其他关键键包括 `user.loginName`、`user.Balance`、`user.accountId`、`site.lotteryList`、`__uuid`。

---

### 5.5 API 参数探针核心代码

```python
import requests
api_url = "https://target.com/api/endpoint.php"

# 逐步添加参数
params = {"service": "User.Login", "username": "admin"}
while True:
    r = requests.get(api_url, params=params, timeout=8)
    if "缺少必要参数" in r.text:
        # 提取缺失参数名
        import re
        missing = re.search(r"缺少必要参数(\w+)", r.text)
        if missing:
            params[missing.group(1)] = "test"
            continue
    # 如果不是"缺少"错误，说明参数够了或换了错误类型
    print(r.text)
    break

# ThinkPHP 5 错误信息提取
r = requests.get(url, timeout=10)
if "ThinkPHP" in r.text and "variable type error" in r.text:
    version = re.search(r'V(\d+\.\d+\.\d+)', r.text)
    print(f"ThinkPHP {version.group(1)} - Debug模式开启!")
```

---

### 4.12 BetWin 验证码 Session 绑定与账号注册流程

**验证码是纯色 GIF** — BetWin CMS 的验证码图像（41×20 GIF）可能**不包含视觉上可识别的数字/字母**（全是纯色块）。但服务端 session 中绑定了有效值。用户凭经验可识别出验证码。

**Session 绑定流程**（必遵）：
```bash
# 1. 先获取一个 session
curl -sk -c sess.txt "https://target.com/" -o /dev/null

# 2. 用同一 session 获取验证码
curl -sk -b sess.txt -c sess.txt \
  -H "Referer: https://target.com/m/regagent" \
  -H "Origin: https://target.com" \
  "https://target.com/api/Public/main/authCode.php?entry=1&client_id=xxx" \
  -o captcha.gif

# 3. ***** 不要尝试 OCR — 直接把图片发给用户看 *****

# 4. 用同一 session 提交注册（验证码有效期很短）
SESS=$(grep -v "^#" sess.txt | grep -v "^$" | awk '{print $NF}')
curl -sk -b "Example_Session=$SESS" \
  -H "Referer: ..." -H "Origin: ..." \
  -d "code=用户给的值&..." \
  "https://target.com/api/Public/main/index.php?service=User.RegAgent"
```

**经验**：用户明确表示"验证码直接发给我"是最优解。不要花时间写 OCR 或爆破。

**`safe_pwd` 字段 — CDN JS 版本落后于服务端**：`User.RegAgent` 的 CDN 端 JS（regagent.js）不包含 `safe_pwd` 参数，但服务端校验该字段。遇到 `code:407` / "取款密码格式错误" 时，尝试传 `safe_pwd` 参数。

### 4.13 BetWin API 的 Referer/Origin 头验证

**这是最容易被忽略的阻塞点**：BetWin CMS 的 API 端点（`/api/Public/main/index.php?service=X.Y`）会校验 `Referer` 和 `Origin` HTTP 头。

**无 Referer 时**：即使传了正确的 `website` 参数，也返回 416。

```bash
# ❌ 失败
curl -sk -X POST -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
# → {"ret":416, "msg":"请求的website不存在！"}

# ✅ 成功
curl -sk -X POST \
  -H "Referer: https://9581kk.com/m/regagent" \
  -H "Origin: https://9581kk.com" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
```

**Referer 值**：通常是移动端 SPA 页面路径，如 `https://domain/m/regagent` 或 `https://domain/m/signup`。Origin 值是根域名。

**详细实例**：参见 `references/ag-61995q-9581kk-agent-registration.md`
**Vue 3 SPA 赌博平台详细实例**：参见 `references/x3891-vip-xinpujing-vue3-spa.md`

### Vue 3 SPA AES 加密白名单

services-*.js 中定义了 `ji` 数组，包含**仅有的5个不经过 AES 加密的操作**：

```javascript
ji=["addNewEbankPayOrder","getServerTimeMillisecond","internalWallet/buy",
    "gameChart/*","gameSgChart/*"]
```

其他所有 Action 必须经过 AES 加密（ECB 模式, key 从 `window.alias` base64 解码后 MD5 得到）。绕过方式：

- `e.noAes === true` 在前端可强制跳过加密
- `v0().__no_aes` 全局标志位也可跳过（demo/测试模式）
- `getSiteInitData` 能无加密访问是因为后端在白名单之外另有豁免逻辑（可能是 `__no_aes` 标志）

### Vue 3 SPA 注册/登录 API 探针模式

从 JS 中提取的注册验证规则：

```javascript
// 从 ut 验证对象提取
UserName:  /^[a-zA-Z1-9][a-zA-Z0-9]{3,15}$/    // 账号: 4-16位字母数字,首字符不能为0
Password:  /^[a-zA-Z0-9]{6,14}$/                 // 密码: 6-14位字母数字
Promotion: /^[a-zA-Z0-9]{6,10}?$/               // 邀请码: 可选,6-10位字母数字
Mobile:    /^1[0-9]{10}$/                        // 手机号: 中国1开头的11位数字
```

关键 API 探针路径：

```bash
# 1. 发现真实 API 网关
GET  /api/register            → 200 (SPA/CAPTCHA页) — 前端路由响应
POST /api/register            → 405 (OpenResty)
POST /tools/_ajax/getSiteInitData → 200 JSON (成功!)

# 2. 测试各 Action
POST /tools/_ajax/guestRegister  → "错误站点" (缺 sitePath/siteId 参数)
POST /tools/_ajax/register       → 404 (Action名可能不一致)
POST /tools/_ajax/login          → 403 Forbidden (IP/区域限制)
POST /tools/_ajax/walletTransfer/register → "nologin" (需认证)
POST /tools/_ajax/cache/MobileCache → SUCCESS (App下载信息泄露)
```

`guestRegister` 返回 `"错误站点"` 说明站点验证未通过。需要传 sitePath 或 siteId 参数：

```bash
# 尝试传 site 参数
curl -sk -X POST -H "Content-Type: application/json" \
  -d '{"Action":"guestRegister","Requirement":{"sitePath":"F376"}}' \
  "https://target:9016/tools/_ajax/guestRegister"
```

### 403 vs 405 诊断信号

| 响应码 | 来源 | 含义 |
|:-------|:-----|:------|
| `405` (OpenResty HTML) | OpenResty 配置 | 请求方法不被该路径允许 — 换路径或换方法 |
| `403` (JSON/空) | 后端应用层 | 请求到达了应用代码 — IP 限制/AES 缺失/CAPTCHA 缺失 |

当 `POST /login` 返回 403 时，说明 OpenResty 放行了请求（不同于 `/api/register` 的 405），但后端 PHP 拒绝了它。

### `.git` 披露 vs ModSecurity — 实用指南

检测 `.git` 存在的方法不是看 404/200，而是看**响应码模式**：

```bash
# 方法1：批量检测 .git 路径
for path in ".git/HEAD" ".git/config" ".git/refs/heads/master" ".git/logs/HEAD" ".git/index"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com/$path")
  echo "$code $path"
done
# 模式解读:
# 全部 404 → 不存在
# 全部 406 → ✅ 存在！WAF规则拦截（Confirmed）
# 混合 200/404 → ⚠️ 可能存在但配置不完整

# 方法2：检查备份压缩包
for ext in "zip" "tar" "tar.gz" "rar" "7z" "bak" "old" "~"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com/.git.$ext")
  echo "$code .git.$ext"
done
# 301 重定向到 CDN → 文件存在但已迁移
# 502/000 → 文件存在但被阻止
```

**已知绕过技术（全部失败已验证）**：

| 绕过技术 | 预期 | 实际结果 |
|:---------|:-----|:---------|
| HTTP Request Smuggling (CL.TE) | 前端→后端 | ❌ Cloudflare 封堵 |
| X-Original-URL / X-Rewrite-URL Header | Apache 重写 | ❌ ModSecurity 仍拦截 |
| HTTP/1.0 / HTTP/2 协议降级 | 绕过规则检查 | ❌ ModSecurity 检测所有协议 |
| `%2e%2e%2f` 双重编码 | 路径遍历绕过 | ❌ WAF 在解码后检查 |
| `..;/` 路径规范化 | Tomcat 风格绕过 | ❌ Apache 不支持 |
| 直接访问后端 IP (Host header) | 绕过 Cloudflare | ❌ 后端 IP 只响应 Cloudflare 流量 |
| OpenSSL s_client 原始请求 | 底层绕过 | ❌ ModSecurity 在 Apache 层 |
| Range header / Accept-Encoding 操控 | 响应分块 | ❌ 请求层即拦截 |
| Content-Type 切换 (json/multipart) | 绕过规则触发 | ❌ URL 路径匹配优先 |

**结论**：当 Cloudflare + ModSecurity 联合防护且 `.git` 返回统一 406 时，**WAF 绕过成本极高**。建议放弃此路线，转向其他攻击面（API 参数探针、关联域名、凭证复用等）。`.git` 406 只是确认了存在性，不能作为实际突破口。

---

### CDN 速率限制 —— 爆破节奏控制

**关键经验**：某些 CDN（MJCDN/Cloudflare）在检测到短时间内大量定向探测时，会**静默屏蔽源 IP**（返回 000 连接超时或空响应）。一旦被屏蔽，所有域名（包括靶站的不同子域）都会失效。

**速率限制触发特征**：
```bash
# 前20次请求：正常 → 200
# 第21次开始：突发 → 000 (Connection Timeout) 对所有域名都失效
# 浏览器也连不上 → net::ERR_CONNECTION_CLOSED
```

**控制方法**：
```bash
# 在循环请求中加 sleep
for path in /admin /login /api; do
  curl -s "https://target.com$path"
  sleep 2  # 至少间隔2秒
done

# 分段扫描：一批扫10个，歇30秒再下一批
for batch in 1 2 3; do
  start=$((batch * 10))
  for path in "${paths[@]:start:10}"; do
    curl -s "https://target.com$path" &
  done
  wait
  echo "Batch $batch done, sleeping 30s..."
  sleep 30
done
```

**IP 被封后的恢复**：
- 换 IP（VPN/代理）
- 更换 User-Agent
- 等待 CDN 自动解封（通常 5-30 分钟）
- 使用住宅代理而非机房 IP

### CDN 源站 IP 发现（Cloudflare DNS 链追踪穿透多层 CDN）

当域名通过多层 CDN（如 MJCDN → 中间层 → 源站）保护时，用 Cloudflare DNS 递归查询可穿透 CDN 层发现真实源站 IP：

```bash
# 1. 用 Cloudflare DNS 做递归查询（标准 nslookup 只显示第一层 CNAME）
curl -s "https://cloudflare-dns.com/dns-query?name=target.com&type=A" \
  -H "Accept: application/dns-json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for a in d.get('Answer',[]):
    print(f\"  {a['name']} → {a['data']} (type={a['type']} TTL={a['TTL']})\")
"

# 2. 典型多层 CDN 链（实战案例：qu18116.cn）
# qu18116.cn → CNAME teytest2.mjcdn.com → CNAME dljpjq1.322220.xyz → A records
#   域名           MJCDN 边缘节点           解析中间层               源站 IPs
#  CNAME 链：nslookup 逐级追踪
#  A 记录：194.147.100.43, 194.147.100.62, 194.147.100.64, ...

# 3. 找到源站 IP 后尝试直接访问（绕过 CDN 过滤层）
# 注意：源站 IP 的 HTTPS 可能报 SSL 协议错误（TLS 在 CDN 终止）
# 用 HTTP 直连源站 IP + Host header
curl -s --connect-timeout 5 \
  -H "Host: target.com" \
  -H "User-Agent: Mozilla/5.0" \
  "http://<origin-ip>/path"

# 4. 浏览器访问源站 IP 验证
# Chrome 访问 http://194.147.100.43/ 如果跳转到百度
# 说明该 IP 不是源站（被 CDN 重定向）
# 如果显示目标站内容 → 直连成功
```

**快速判断源站 vs CDN 边缘**：

| 现象 | 结论 |
|:-----|:------|
| HTTPS 正常，有 CDN 签名头 | CDN 边缘节点 |
| HTTPS 报 SSL 协议错误（ERR_SSL_PROTOCOL_ERROR） | **可能是源站**（TLS 在 CDN 终止，源站无有效证书） |
| HTTP 能连上且返回内容 | 源站 HTTP 端口开放（管理面板可能在此） |
| HTTP 跳转到百度/其他网站 | IP 被 CDN 用于其他业务，不是源站 |

**子域名批量发现 + DNS 查询**：
```bash
for sub in www m api admin agent boss pay manage; do
  curl -s "https://cloudflare-dns.com/dns-query?name=$sub.target.com&type=A" \
    -H "Accept: application/dns-json" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for a in d.get('Answer',[]):
    if a['type'] == 1: print(a['data'], end='')
" 2>/dev/null && echo " → $sub.target.com"
done
```

**原则**：IP 被封了不是结束——查 DNS 链追源站 IP、换子域名、换端口，总能找到入口。

**原则**：宁可漏扫不可封 IP。扫描节奏 > 扫描深度。

---
