<!-- archived from /root/.hermes/skills/security/web-security-hardening/SKILL.md on 2026-10-21 -->

---
name: web-security-hardening
description: Use when 给 web 后端(尤其 Go/Gin)做安全加固——安全响应头/CSP/登录爆破防护/CSRF。
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-security-hardening`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-security-hardening/…')`，不要相对 `references/legacy/` 解析。

# Web 安全加固（Go/Gin 后端）

给 web 后端补安全短板。重点是渗透平台/管理面板自身的安全——攻击者最爱的目标，自己先不能裸奔。

## 流程

### 1. 侦察现状（先摸清短板，别上来就改）
```bash
# 安全响应头是否缺失
cd <repo> && grep -rn -iE "Content-Security-Policy|X-Frame-Options|X-Content-Type-Options|Strict-Transport|Referrer-Policy" internal/ --include="*.go" | grep -v _test.go
# 登录接口有没有限流/失败锁定
# CORS 是否宽松(找 `Access-Control-Allow-Origin` + `*`)
# 认证方式：Bearer 头 vs cookie(决定 CSRF 是否相关)
```
- 全缺失 → 加安全响应头 middleware；登录无限流 → 加失败锁定；CORS `*` → 收紧白名单。
- Bearer 头认证不受 CSRF 影响（跨域无法带自定义头），token 存 localStorage 则 XSS 是主要风险（CSP + DOMPurify 双缓解）。

### 2. 安全响应头 middleware（最基础、最高价值）
统一 middleware，全响应生效：
```go
h.Set("X-Content-Type-Options", "nosniff")
h.Set("X-Frame-Options", "DENY")
h.Set("Referrer-Policy", "strict-origin-when-cross-origin")
h.Set("X-XSS-Protection", "1; mode=block")
h.Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
h.Set("Content-Security-Policy", csp)
// HSTS 仅 HTTPS(含 X-Forwarded-Proto: https)下发，别误锁本地 HTTP
```
注册在 CORS middleware 之后、认证 middleware 之前。

### 3. CSP 策略设计（先侦察前端，再精确写）
写 CSP 前必须侦察前端现状，否则策略过严直接打断功能：
```bash
grep -cE "<script[^>]*>" templates/*.html          # <script> 总数
grep -cE "on[a-z]+=" templates/*.html              # 内联事件处理器数
grep -cE "style=" templates/*.html                 # 内联 style 数
grep -oE "new WebSocket|wss?://|EventSource|data:image" static/js/*.js
```
按结果定策略：`default-src 'self'`（无外部 CDN 时）+ `connect-src 'self' ws: wss:`（有 WebSocket/SSE）+ `img-src 'self' data: blob:`（有 data:image）+ `frame-ancestors 'none'` + `object-src 'none'` + `base-uri 'self'` + `form-action 'self'`。

### 4. 登录暴力破解防护（失败锁定，非全请求限流）
- 用「失败锁定」而非「全请求计数」：只在登录失败时计数、成功即重置，不误伤正常用户。
- 按 `IP + 用户名` 组合隔离，防分布式爆破（多 IP 打同一 admin）。
- 结构：`Allowed(ip,user)` 开头拦截(429) → 失败 `RecordFailure` → 成功 `RecordSuccess`；map 存 `count/firstFail/lockedUntil`，加清理 goroutine 回收过期条目。
- 现有全请求 `RateLimiter` 不适合登录场景（会把成功登录也算进去）。

## 坑（实测踩过）
- **内联事件处理器也算内联 script**：`onclick="..."`/`onkeydown` 会被 CSP `script-src` 限制。前端有几百个 onclick 时只能 `script-src 'unsafe-inline'`（重构成本过高）；但 CSP 核心防护(`default-src 'self'` 禁外部资源、`frame-ancestors 'none'` 防点击劫持、`object-src 'none'` 禁插件)不受 `'unsafe-inline'` 影响，仍有效。同理内联 `style=""` 属性强制 `style-src 'unsafe-inline'`。
- **vet 单文件报 undefined(同包符号)是误报**：`go test ./internal/xx/` 才是真验证，别被单文件 vet 带偏。
- **HSTS 只在 HTTPS 下发**：本地 HTTP 部署下发 HSTS 会把浏览器锁死在 http 上，要判断 `c.Request.TLS != nil || X-Forwarded-Proto==https`。
- **安全头 middleware 放 CORS 之后**：CORS 请求要先过 Origin 校验(跨域直接 403)，再补安全头，顺序别反。
