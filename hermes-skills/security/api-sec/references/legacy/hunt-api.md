<!-- archived from /root/.hermes/skills/security/hunt-api/SKILL.md on 2026-10-21 -->

---
name: hunt-api
description: API attack hunting (REST / GraphQL / gRPC) - BOLA/IDOR, BFLA, mass assignment, excessive data exposure, auth/JWT, introspection +…
---

> 归档卡：原目录 `/root/.hermes/skills/security/hunt-api`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hunt-api/…')`，不要相对 `references/legacy/` 解析。

# Hunt: API Security

**Assumes `hunt-core`** for the scope gate, two-account rule, confirmation gate, enumeration limits, stop conditions, wiki protocol, FIND output, and Deadends. Do not re-derive any of that here.

## Wiki

```
qmd_query "API REST GraphQL gRPC BOLA BFLA mass assignment excessive data exposure OWASP API Top 10" via wiki-search MCP
```

Hub: [[web-moc]] (live web index). Primary page: [[api-security]]. Payload arsenal: `wiki/payloads/api.md`.
Anchors: [[api-testing]], [[graphql-attacks]].
Variants: [[grpc-web-attacks]] (gRPC-Web / protobuf transcoder abuse), [[rsql-injection]] with the [[rsql]] payload (RSQL/FIQL filter-query injection, e.g. Spring Data REST), [[rate-limit-bypass]] (header/race/distributed-source throttle bypass), [[redos]] payload (catastrophic-backtracking regex DoS in an input validator), [[jwt-attacks]] (token flaws).

For object-level authorization (BOLA/IDOR) see `hunt-idor`.

## Attack surface signals

`/api/`, `/v1/`, `/graphql`, `/rest/`, gRPC (`application/grpc`, HTTP/2), Swagger UI (`/swagger`, `/api-docs`, `/openapi.json`), mobile/SPA backends.

### Laravel API nuances

- **CSRF 419 loop:** Laravel session-based API auth binds the `_token` form field to the `_session` cookie from the SAME page load. To authenticate: GET the login page, extract BOTH the `Set-Cookie: _session=...` from response headers AND the `_token` hidden input value from the HTML body, then POST with the exact same session cookie + `_token` + login/password fields. Adding `X-XSRF-TOKEN` header (URL-decoded value of the `XSRF-TOKEN` cookie) helps.
- **API auth check:** `/api/user` returning `{"message":"Unauthenticated."}` (401) = Laravel default middleware. Cloud Mall / Laravel apps typically do NOT expose Passport/Sanctum token endpoints — session-only auth.
- **Login field name:** Cloud Mall uses `login` (not `username`/`email`) as the identifier field.
- **Registration blocked vs broken:** A register endpoint that always returns "密码请大于8位" regardless of password length usually means registration is disabled server-side. Try different field names (`password`, `repasswd`) but expect it to stay blocked.

**Rank before testing.** Not all surface is equally likely to be broken:

- **Undocumented endpoints** present in the spec (Swagger/introspection) but never called by the UI - the classic BFLA surface; nobody tested the route the client does not exercise.
- **GraphQL introspection** and the mutations/fields it reveals that the client never invokes.
- **Batching and alias endpoints** - one request, many operations; per-item authorization and rate limiting are frequently applied to the request, not each operation.
- **Bulk and export endpoints** - one call, many objects; much higher severity per finding.
- **Non-GET verbs on read-looking routes** - `GET /orders/123` authorized, `PATCH`/`DELETE` not.
- **Newest features** - authorization middleware lags new code; a route written outside the conventions misses it.

## Methodology

**Setup:** two accounts per `hunt-core` (A owns, B attacks, separate profiles). Get the spec if any - Swagger/OpenAPI, GraphQL introspection, `.proto`.

**Drive it through Burp** for operator visibility. Push the load-bearing requests (the BOLA cross-account swap, the mass-assignment body, the BFLA verb/route call) into **Repeater** via `Skill(hunt-burp)` / the native Burp MCP (`mcp__burp__*`) so the operator can replay and inspect them; brute/fuzz belongs in **Intruder** (`send_to_intruder`), not a hand-rolled loop. A quick throwaway `curl` per account for the writeup PoC is fine.

1. **Enumerate.** Parse Swagger/OpenAPI for every endpoint + param; GraphQL introspection (`__schema`); gRPC server reflection (`grpcurl -plaintext <h> list`, then `list <svc>` / `describe`). **No spec?** Discover endpoints with `ffuf -w <api-wordlist> -u https://HOST/FUZZ` and fingerprint hosts with `httpx`, not a hand `curl` loop. This is service / endpoint DISCOVERY, not object enumeration - it is bounded by the engagement RoE (`no_dos`, scan-rate caps), NOT by the 5-to-20 object cap. Do not clamp the wordlist to 20.

   **Laravel-specific routing:** Cloud Mall and similar apps serve SPA via nginx + redirect all unhandled routes to the HTML entry point. The REAL API paths are in JS bundles (`srcL entry point. The REAL API paths are in JS bundles (`src="..."` or `import(...)`). Use the front page HTML as a starting point to find JS bundle URLs; download and grep for `/api/`, `/auth/`, `/account/` patterns. Form fields also reveal backend field names (`login` vs `username`)."}, {"name": "tg-gray-ecosystem-pentest", "action": "create", "content": "---\nname: tg-gray-ecosystem-pentest\ndescription: Use when 目标为TG灰产生态基础设施集群（含Cloud Mall商城/发卡/Baby-Cloud/TG面板/Komari KVM/宝塔面板/自定义SSH代理端口）。覆盖多端口发现规律、共享基础设施模式（MariaDB同IP、代理端口群、自定义SSH端口）、各组件攻击方法论。\n---\n\n# TG灰产生态基础设施渗透\n\nTG灰产生态（TG Panel + Cloud Mall + Baby-Cloud + Komari KVM + 宝塔面板）通常部署在同一或相邻VPS，共享运维凭据和架构模式。\n\n## 基础设施指纹\n\n### 端口分布规律\n\n| 端口 | 服务 | 备注 |\n|------|------|------|\n| 5000 | TG Panel | Flask/Werkzeug，SQLi和喷洒统一401 |\n| 25778 | Komari KVM | Go JSON-RPC 2.0，可无鉴权查`/api/nodes` |\n| 25800 | Komari WS | 超时/空响应 = WebSocket口，需要认证 |\n| 4443/8443 | CloudFront | nginx/CloudFront 403，非本地服务 |\n| 3306 | MariaDB | 远程可达但host限制+密码未知 |\n| 17193 | OpenSSH | 非标准SSH端口（Debian 11），同一密码体系 |\n| 888 | 宝塔面板 | nginx IP白名单403，header注入绕过无效 |\n| 20326/32xxx/36xxx/44xxx/51xxx | HTTP代理 | HTTP Basic Auth，realm=\"proxy\" |\n| 7199/65530 | Go服务 | 404 page not found |\n\n**Port discovery depth:** TG灰产目标常用非标准端口（5000/25778/17193/888）。必须全端口扫描（1-65535），不能只扫top 1000——关键服务都藏在常规范围外。\n\n### 共享架构模式\n\n- **多机同密码体系**：主控(193)和资源机(152)共享相同的自定义SSH端口(17193)和代理端口模式\n- **MariaDB在主控IP**：193.122.113.240:3306 可远程连接，密码与运营者名称强相关\n- **宝塔面板**在888端口，nginx层IP白名单不可绕过\n- **Cloudflare前端 + 源站直连**：通过SSL证书CT日志找新子域，bypass CF\n\n## Cloud Mall（云商城）组件\n\n### 识别\n- Laravel 应用\n- 登录页：`/account/login` 而非 `/login`\n- 登录字段名：`login`（非 `username`/`email`）\n- API前缀：通常无 `/api/v1/` 路径，直接 Laravel route\n- JS bundle包含 Hyper 主题资产\n\n### 攻击方法\n\n1. **账号注册**\n   - 端点 `/auth/register` 接收JSON表单，字段名 `password` + `repasswd`\n   - \"密码请大于8位\"即使发送长密码=注册被运营者禁用，换路径\n   \n2. **登录**\n   - 需要CSRF token：GET登录页→提取 `_token` hidden input + `_session` cookie→同会话POST\n   - CSRF 419 = 会话不匹配，需用cookie jar保存完整会话\n   - 密码错误 vs 用户不存在返回不同错误消息（枚举oracle）\n   \n3. **密码重置**\n   - 密码重置端点存在用户名oracle\n   - \"邮件发送失败\"但用户存在=邮箱真实存在但SMTP未配置\n   \n4. **API访问**\n   - API返回 `{\"message\":\"Unauthenticated.\"}` 401 = Laravel默认中间件\n   - Cloud Mall通常不暴露Passport/Sanctum token端点，仅session认证\n   - 登录成功后通过session cookie访问 `/api/user`、`/api/admin/*` 等\n\n### 已知死路\n- Laravel `.env` / `.git` / `storage/logs` 等泄露路径全部返回302到/404\n- Debugbar/Telescope/Ignition全部302到/404\n- 注册关闭时所有字段组合返回相同错误\n\n## Komari KVM面板\n\n### 识别\n- Go + Vue SPA\n- 端口25778（JSON-RPC 2.0），25800（WebSocket）\n- Slogan: \"每个梦想的路上，一起前行....！\"\n\n### 无鉴权端点\n| 端点 | 返回 |\n|------|------|\n| `GET /api/nodes` | **32台节点全量泄露**（含UUID/CPU/内存/磁盘/OS/区域） |\n| `GET /api/version` | 版本信息、auth类型、ws配置 |\n\n### 认证机制（从源码逆向）\n- 算法：`SHA256(password + SALT) → base64`\n- SALT：`06Wm4Jv1Hkxx`（源码 `/internal/config/config.go`）\n- 接口：`POST /api/login` JSON `{\"username\":\"...\",\"password\":\"...\"}`\n- 统一401 \"Invalid credentials\"\n- admin:xxx RPC方法全部 `-32041 Permission denied`\n\n### 试探路径\n- `/api/rpc2` JSON-RPC endpoint\n- `/api/public/*` 全部返回SPA HTML\n- `/api/guide/*` / `/api/setup/*` 存在但全部返回SPA HTML\n- 密码重置需服务器CLI：`komari chpasswd` / `komari disable2fa`\n- 无默认凭据（install脚本无默认账户）\n\n## TG Panel（Flask/Werkzeug）\n\n### 识别\n- Flask 3.1.x, Werkzeug 3.1.x, Python/3.9.x\n- `/` 返回统一HTML页面\n\n### 攻击方法\n- SQLi注入（MySQL SLEEP/UNION/NoSQL）：全部统一401，无时间差\n- 密码喷洒（admin/byhaoya + 40+密码）：全部统一401\n- 默认凭据/默认路由/路径猜测：全部401\n- 无公开漏洞（截止2026-10）\n\n### 已知死路\n- 所有端点统一401（包括不存在的路径）\n- 没有登录接口暴露（可能是WebSocket或JSON-RPC）\n\n## MariaDB数据库\n\n- 端口3306，远程可达\n- 主机白名单：部分IP被拒绝（ERROR 1130），部分可连但密码错（ERROR 1045）\n- 常用用户：root, byhaoya, babycloud, komari, app, admin\n- 密码建议测试：运营者名家族（byhaoya/youyouku/ayouok/nxprobe/Komari），Laravel默认，空密码\n- 常见伪装：\"MariaDB 10.11.6\" Debian 11\n\n## 宝塔面板\n\n- 端口888，nginx IP白名单403\n- X-Forwarded-For / X-Real-IP / Client-IP等header注入全部无效\n- 需从本地host或SSH隧道访问\n\n## 客服站/Socket.IO\n\n- Socket.IO 4.5.4，`/socket.io/`默认路径\n- 无鉴权握手，可自生成chat_uid\n- 发送消息是纯文本，接收者（客服）点击URL后可获取会话cookie\n- 文件上传同域：检查 `/upload` 端点的文件上传能力（PHP/SHTML探针是否执行）\n\n## 参考\n\n- Cloud Mall Laravel CSRF处理 → `hunt-api` skill\n- 数据库渗透 → `database-tactics` skill\n- 代理爆破 → `scanning-tools` 相关"}]
2. **BOLA / IDOR (API #1).** Swap object IDs across accounts (numeric, UUID, in body/path/header) - the dominant API bug. Swapping IDs to pull other accounts' records IS object enumeration: bounded to 5 identifiers by default, 20 ceiling with operator approval, 0 under `no_bruteforce`, per `hunt-core`. Two or three adjacent IDs prove the sequential pattern; cite a `total`/pagination count for scale, never a sweep. Full bounded-sample loop and the trusted-identifier test live in `hunt-idor`. -> overlaps `hunt-idor`.
3. **Broken function-level auth (BFLA).** Call admin/privileged methods as a low-priv user; swap the HTTP verb (GET -> PUT/DELETE); hit the undocumented endpoints from the spec.
4. **Mass assignment.** Add fields the client never sends (`role`, `isAdmin`, `verified`, `balance`) to JSON bodies; look for the privilege/state change to actually take effect (confirm from a fresh read, step below).
5. **Excessive data exposure.** The API returns more than the UI shows (full objects, other users' fields, internal flags) - inspect the raw response, not the rendered page.
6. **Auth.** JWT flaws ([[jwt-attacks]]: `alg:none`, weak secret, `kid` injection), API-key reuse, missing auth on some routes, OAuth scope creep.
7. **GraphQL specifics.** Introspection, batching/aliases (rate-limit/brute bypass), nested-query DoS, field suggestion leaks. Payloads: [[graphql-attacks]].
8. **gRPC specifics.** Reflection to enumerate; `grpcurl` to call methods; tamper protobuf fields; run the same authz tests as REST.
9. **Rate limit / resource.** Unbounded pagination, no throttle on sensitive actions (OTP/login). Prove the throttle is absent with a bounded burst; honor `no_bruteforce`/`no_dos` - do not actually brute credentials or OTPs and never run this at volume against a live auth endpoint. See [[rate-limit-bypass]].

**When a direct call 403s or the extra field is stripped, it is not closed.** Parameter pollution (`?id=A&id=B` - check and fetch may read different occurrences), array/nested wrapping of the field (`{"user":{"role":"admin"}}`), casing and separator variants of a mass-assign key (`isAdmin`/`is_admin`/`admin`), alternate content-type (form vs JSON vs XML), verb-override headers (`X-HTTP-Method-Override`), **version downgrade** (`/v1/` predates the middleware `/v2/` has - the most reliable), and batching to skip per-item authorization.

**Chain: mass assignment -> privilege escalation.** A `role:admin`/`isAdmin:true` that actually takes effect turns the whole BFLA admin surface reachable - re-run step 3 as the escalated principal. For the broader workflow/state-tampering angle hand off to `hunt-bizlogic`.

**Distill** a confirmed, GENERIC pattern (product + endpoint + impact, no client host): `python3 scripts/wiki-stage.py --kind technique --slug <slug> --target-page techniques/web/api-security.md`

## Confirmation gate

**NOT confirmation:** a `200` echoing your own request back; an empty or shell response; B seeing an object that is shared, public, or org-visible; a body you have not compared against A's baseline; a BFLA endpoint returning `200` without the privileged action actually performed; a mass-assignment write returning `200` with the extra field accepted but the privileged field never verified in effect; any result not re-verified in a clean session.

**IS confirmation:**

- **BOLA** - B's low-priv session returns A's actual *data*, matching A's own baseline response, with A's legitimate/shared access ruled out, reproduced in a clean session.
- **BFLA** - a low-priv token reaching AND executing an admin/privileged function (perform the action, do not just get a `200`).
- **Mass assignment** - the privileged field (`role`/`isAdmin`/`balance`) verified in effect from a fresh authenticated read, not merely accepted in the request body.

## Severity

- **CRITICAL** - unauthenticated admin action, or cross-tenant data access.
- **HIGH** - BOLA/BFLA reaching other users' data or functions; mass-assignment privilege escalation.
- **MEDIUM** - excessive data exposure; missing or weak rate limiting.

## Deadends

```
Append: - [ ] API on <host> <endpoint> -- BOLA/BFLA/mass-assign all enforced;
              extra fields ignored; JWT validated; introspection off
```

Record what you tried (pollution/array/verb/version-downgrade/batch), not just that it failed.
