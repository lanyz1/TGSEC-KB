# Python BaseHTTPRequestHandler 自写登录面 — 指纹与假阳性

> 授权评估 2026-09 黑盒重构。用于 `Server: BaseHTTP/0.6 Python/3.10.x` 自写面板。**不是打穿链**；是匹配器、假阳性与下一格。

## 指纹

- 响应头：`Server: BaseHTTP/0.6 Python/3.10.12`（CPython `http.server` 默认）
- GET `/login` 约 1414B HTML；表单 `method=post action="/login"`，字段 `username` + `password`
- CSS：`background:#eef3f8`；`.login{width:min(380px,calc(100vw - 36px));box-shadow:0 18px 48px rgba(28,45,70,.12)}`
- 失败固定签名：**HTTP 403 + 正文 1461B + 「账号或密码不正确」**（跟 GET 登录页同模板，多 `.msg` 块）
- 成功判定：**非 403**（预期 302 + `Set-Cookie: tg_admin_session=<非空且非 Max-Age=0>`）
- 唯一未登录 Set-Cookie：**GET `/logout`** → 302 `/login` + 188B + `tg_admin_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`
- POST `/logout` **不** Set-Cookie（114B 普通 302）——logout 是 GET-only
- 除 `/login`（及 GET 的 `;?#` 变体）外，GET/POST 多 302 `/login`；OPTIONS/PUT/PATCH/DELETE/CONNECT → 501
- 无 Set-Cookie 登录成功前；随机/空/`admin` cookie **不** 跳过鉴权 → 服务端 token 表
- 空字段 / 缺字段 / JSON / XML / 换字段名 全部仍 403|1461 — 无用户枚举
- 计时约 0.49s 常数，错用户/空密/长密无差 — 无 compare-digest 侧信道
- 手写 `Set-Cookie` 串（不是 Python `http.cookies.SimpleCookie`）

## GET vs POST 路径匹配不一致（必测）

自写 `do_GET` / `do_POST` 常用**两套规则**，不要用 GET 的 200 推 POST 也进鉴权。

| 请求行 | GET | POST `username=&password=` |
|--------|-----|------------------------------|
| `/login` | 200 登录页 | 403 鉴权 |
| `/login;` `/login?` `/login#` | 200 登录页 | 302 跳 `/login` |
| `//login` `///login` | 302 | **403 进鉴权** |
| `/login` + 尾空格/制表符 | — | **403 进鉴权**（`path.strip()`/`lstrip('/')=='login'`） |
| `/login/` `/Login` `/./login` `/foo/../login` | 302 | 302 |
| `/logout` `/logout;` `/logout?` | 302 + **清 cookie** | 302 无 cookie |

CPython `BaseHTTPRequestHandler.parse_request` 在 handler 之前把路径头 `//` 收成单 `/`（gh-87389），所以 GET/POST `//login` 进 handler 时已是 `/login`。
GET 再走 `urllib.parse`（`;?#` 截断后 path==`/login` 就回登录页）；POST **不** urlparse，要求 `path.rstrip()=='/login'`（尾空白也进鉴权；`/login;` `/login?` 走 302）。
HEAD/PUT/PATCH/DELETE/OPTIONS/TRACE/CONNECT 全 501 → **不是** `SimpleHTTPRequestHandler`，没有 `translate_path` 文件服务。
不完整 POST 读 body 不挡其它连接 → `ThreadingHTTPServer`。HTTP/0.9 只允许 GET；`POST /login\r\n` → 400 `Bad HTTP/0.9 request type`。

绝对 URI（`GET http://127.0.0.1:8080/login`）对 GET 进登录页、对 POST **不**进鉴权（path 不是精确 `login`）。

## 崩溃 ≠ 口令 / ≠ 绕过

非 ASCII、非法 UTF-8、`\xff`、overlong、用户/密码字段里的 raw UTF-8 会让 **当前线程** 未捕获异常退出（curl 000 / exit 52 / 空回复，耗时仍约 0.49s）。服务进程还在，下一个 ASCII 请求正常。

原因：`do_POST` 里 `body.decode('utf-8')` 或 `value.encode('ascii')` 未 try。**不要当成正确密码、RCE、或鉴权绕过。** 多余 ASCII 字段 `note=测` 不崩（`parse_qs` 不触发 encode）。Cookie 里非 ASCII **不**崩 GET。

Content-Length 过大/负数/非数字也会空回复（读 body 挂或异常），同样不是 HIT。

## 假阳性（别再跑）

1. **nmap `http-proxy` on 8080** — CPython `parse_request` 对绝对 URI 走 `urlparse`，`GET http://127.0.0.1:8080/login` 只是 path=`/login`。CONNECT → 501。不是正向代理 / SSRF。
2. **HTTP/0.9 `GET /login\n`** — 请求行切开，回裸正文；不是绕鉴权，也不吐 `SimpleHTTPRequestHandler` 文件。
3. **HTTP/2.0 → 505** 标准页（约 491B），不是泄露。
4. **urlscan `page.title:"TG 后台登录"`** — 常命中 nginx + Next.js（例 `kaifatg.wa-link.net` 标题 `TG-后台登录`）。**比对 `Server` + HTML sha256 + 「请输入后台账号和密码」**，标题单字不算同源。
5. **cookie 名 `tg_admin_session`** — techgeneses.com 等 Next.js 站也用这个名；只当 `Set-Cookie` 串 + BaseHTTP 头 + 登录 HTML 三者齐才算同源。随机值伪造不跳鉴权。
6. **同 /24 另一 IP** — 不是同机。锁面时只打用户 URL 解出的 A 记录。邻 IP 上的 Jenkins / JobWork / IIS+Express WS 是隔壁租户。
7. **`send_error` 的 `%` 反射** — 400 页会把请求行塞进格式化；关连接。逼不出 traceback 当 RCE。

## 下一格（禁喷密）

常见弱口试 10–20 个不中后**停喷**。剩余格子：

- 同 IP `-p-`（常只 22+8080）+ SSH 指纹 / InternetDB；loot 钥 IdentitiesOnly 复用一次（chmod 600）
- GET `/logout` 外还有没有会 Set-Cookie 的精确 path（并发短表，跟 114B 普通 302 差分）
- 登录 HTML sha256 / 独特 CSS 公开源码；命中后对 `Server`+body 实测。`#1769e0` + `width:min(380px,calc(100vw - 36px))` + sha256 `131ec455…` 2026-09-27 公开仓 0 命中。
- 崩溃窗口不会掉鉴权（ThreadingHTTPServer；异常只关当前连接）
- 本场已控口令/钥对 SSH 复用一次，不是字典喷
- 用户枚举：任意用户名 403 正文 sha256 恒 `2a522b4d…`（1461B）
- HTTP/0.9 非 `/login` 空体 = 302 头被丢掉，不是后台
- `POST /login?...` 不进鉴权（query 不是 body）。`parse_qs` 重复键、charset、utf-7/ibm037 仍 403 或崩线程。
- debug/2fa/otp extra 字段忽略。cookie 当文件名/穿越 302。
- TG 云控标准路径（openapi/docs/export-session/worker）全 302。同 IP 旁端口仍仅 22+8080。
