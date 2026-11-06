---
name: python-basehttp-panel
description: "Use for Python BaseHTTP/http.server custom login panels."
version: 0.1.0
---

# Python BaseHTTPRequestHandler 自写登录面

CPython `http.server` / `BaseHTTPRequestHandler` 自写面板（常挂 8080，标题「TG 后台登录」）。**没有** FastAPI `/openapi.json`、没有 JWT。先黑盒重构 GET/POST 匹配器，再打会话；禁喷密。

完整指纹/假阳性表：`references/basehttp-custom-login.md`。

## When to Use

- `Server: BaseHTTP/0.6 Python/3.10.x`（或其它 3.x）
- 标题 `TG 后台登录` / h1 `TG 多账号后台` / cookie 名 `tg_admin_session`
- 失败固定 **HTTP 403 + 「账号或密码不正确」**，成功应是非 403 + 非空 session cookie
- nmap 把该端口标成 `http-proxy`

Don't use for: FastAPI/uvicorn TG 云控（走 `chinese-fastapi-ops-admin`）；**FastAPI 纯 TOTP「TG 后台登录」**（openapi `TG 脚本管理后台`、登录只有 `code` 六位、Server 常 nginx — 走 `chinese-fastapi-ops-admin` + `references/fastapi-totp-only-tg-script-console-10-02.md`）；nginx+Next.js 同名标题站。

## Procedure

1. **锁面 = 用户 URL 的 A 记录 IP。** 同 /24 另一 IP 不是同机。`-p-` 常只有 22+8080。
2. **禁喷密。** 常见弱口 10–20 个不中就停。空字段/换字段名/JSON 仍 403 不是用户枚举。
3. **差分 GET vs POST 路径**（两套规则，已验证）：
   - GET：`urllib.parse` — `/login;` `/login?` `/login#` 当登录页（200）
   - POST：`lstrip('/')` 或 `strip()` 后精确 `'login'` — `//login`、`/login`+尾空白 **进鉴权**；`/login;` `/login?` **不进**（302）
   - 不要用 GET 200 推 POST 也进 `do_POST`
4. **会话**：未登录唯一 Set-Cookie 是 **GET `/logout`**（清空 `tg_admin_session=; Max-Age=0`）。POST `/logout` 不清。随机 cookie 值不跳鉴权 → 服务端 token 表。
5. **崩溃 ≠ HIT。** 非 ASCII / `\xff` / 非法 UTF-8 打崩当前线程（curl 000/52），服务还在。是未捕获 `decode('utf-8')`/`encode('ascii')`，不是正确口令或 RCE。Cookie 非 ASCII 不崩 GET。
6. **证伪 nmap http-proxy**：CONNECT → 501；`GET http://127.0.0.1:8080/login` 只是 `urlparse` 抽 path=`/login`。不是正向代理/SSRF。
7. **OSINT 假同源**：urlscan 标题「TG 后台登录」常是 nginx+Next.js。必须 `Server` + HTML sha256 + 「请输入后台账号和密码」三者齐。cookie 名 alone 不够（techgeneses 等同名）。

## Pitfalls

- HTTP/0.9 `GET /login\n` 回裸正文 = 请求行切开，不是绕过，也不吐文件。
- HTTP/2.0 → 505 标准页（~491B），不是泄露。
- 计时 ~0.49s 常数：错用户/空密/长密无差。
- 邻 IP Jenkins/JobWork/IIS 是隔壁租户，锁面时不切主线。

## Verification

- 路径表：GET `/login;` = 200 且 POST `/login;` = 302；POST `//login` = 403。
- GET `/logout` 188B + Set-Cookie Max-Age=0；其它 path 114B 无 cookie。
- UTF-8 POST 空回复后，立刻 ASCII POST 仍 403（进程没死）。
