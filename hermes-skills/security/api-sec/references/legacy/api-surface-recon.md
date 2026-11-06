<!-- archived from /root/.hermes/skills/security/api-surface-recon/SKILL.md on 2026-10-21 -->

---
name: api-surface-recon
description: "Use when mapping a hardened API before attacking it."
version: 1.1.0
tags: [recon, api, spa, traversal, ssrf, gin, fastapi, bfla, user-enumeration]
---

> 归档卡：原目录 `/root/.hermes/skills/security/api-surface-recon`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/api-surface-recon/…')`，不要相对 `references/legacy/` 解析。

# API Surface Recon (hardened / undocumented)

Use when you have a live backend, no docs, and the front door is a SPA. Goal: turn the frontend bundle into a
complete API + auth map, and know which of your conclusions are actually trustworthy.

## Procedure

### 1. Fingerprint the backend from its error body, then speak its contract
- Go/Gin: `{"error":"Key: 'Username' Error:Field validation for 'Username' failed on the 'required' tag"}` — the JSON
  field in that message is the **Go struct field name**. Go's `encoding/json` matches field names
  **case-insensitively**, so `username` and `Username` both bind.
- FastAPI: `{"detail":[{"type":"missing","loc":["body","x"],"msg":"Field required"}]}` → Pydantic; 422 bodies leak
  exact field names, types and nesting. `/docs`, `/redoc`, `/openapi.json` are often left enabled.
- `404 page not found` (lowercase) = gin/chi default handler. `{"error":…}` JSON = custom handler.
- **Decision rule that saves whole sessions:** a `400 … 'required' tag` means your credential was **never tested** —
  fix the field name and retry. Only a `401 invalid username or password` means the credential was tested. Never
  report "credentials rejected" on the strength of a pile of 400s.
- **Uniform-denial gate.** A hardened host answers *every* unknown path with the same `200` + fixed body (identical
  bytes / Content-Length, e.g. a 76-byte `{"timestamp":…,"code":0,"message":"失败","sign":null,"data":null}`).
  That is a catch-all deny shim, not a route map — fingerprint it by **body hash + length**, never by status code,
  and void every "200 = endpoint exists" conclusion drawn against it. Corollary: a *different* error on one path
  (a Tomcat `400` on a quoted param, a framework 404) proves that parameter reached a real route — put one
  deliberately malformed char in each probe and diff the body; that divergence is your route oracle, so do not
  enumerate blind. **Apply the same byte-identity test to your own probe matrix: if every variant of a filename / param /
  header payload returns identical response bytes, the matrix has no discriminating power — hunt the one variant that
  yields a distinct body (a known-bad extension, a malformed field, a permission error) and confirm your probe actually
  reached the parser before reading anything into the results.** The same trap fires when the *probe principal* owns no data: on a
  self-scoped endpoint (`my-team` / `my-orders` / `my-logs`) a fresh test account answers `count=0` for every parameter you
  throw at it, so the matrix has zero discriminating power and "this filter is unsupported" is unfounded. Re-run the matrix
  from an account that demonstrably holds rows (a harvested low-priv account), or test the same parameter on a sibling
  endpoint that searches the whole table, before writing off a whole parameter family.
- **Header-key gate: identical 401 for missing vs guessed value = false hit.** When a gate wants `X-Admin-Key` /
  `X-API-Key` / `Authorization`, capture the body with (a) no header and (b) your guessed value and compare bytes.
  Same bytes → your value was never compared, the key space is unprobed. Only a *different* body/message counts as
  a lead; a bare `401` on a guess is not.

### 2. Extract the SPA route table and replay it under the API prefix
- **Mobile app first, when one exists.** The official store build hard-codes the real API base and the whole endpoint list, and it is public. Pull the APK and branch on framework before anything else: native → `strings classes.dex`; React Native → `assets/index.android.bundle` is **Hermes bytecode**, so `pip install hermes-dec` then `hbc-disassembler bundle.bin out.hasm` and ripgrep the string table (hosts + quoted path literals + `baseURL|apiKey|x-key`); Flutter → `libapp.so`. Running dex `strings` on an RN build yields the false conclusion "the app has no backend address" — the URLs are not in the dex. Full chain: `references/mobile-app-bundle-reverse.md`; bulk string harvest (paths / hosts / key-like literals) from a
  multi-MB disassembly: `scripts/harvest_bundle_strings.py`.
- Pull every route/endpoint string out of the bundles **and every lazy chunk**, then replay each one under the real
  API prefix with GET/POST/PUT/PATCH and record the status:
  - `401 {"error":"missing bearer token"}` = a live protected API route — this is the auth surface
  - `404` on every method = frontend-only route (the `/tenant/login` page exists as a SPA path, not an API path)
  - `200` + identical index.html bytes = SPA historyApiFallback, **not** an endpoint
  - `405` on your GET = **the path is real and wants another method** — the cheapest route oracle there is. Re-probe
    with POST/PUT before clearing anything; the 405/422 pair then hands you the DTO field names.
  - **Name the stack from the 404 *body*, and expect one hostname to front two apps.** A Werkzeug/Flask HTML 404
    (`<h1>404 Not Found</h1>The resource could not be found.`) at `/x` plus a FastAPI JSON 404 (`{"detail":"Not Found"}`)
    at `/api/x` on the *same* hostname means nginx routes by prefix to two different backends — the JSON side owns the
    paths you mapped, the HTML side is an app you have not touched. Fingerprint the 404 before treating "not found" as
    one thing, and probe every path under both prefixes.
- **Minified SPA bundles name their calls, not their routes.** Grep every chunk for the http-wrapper call, not for path-shaped strings: `\.(get|post|put|delete)\("([A-Za-z][A-Za-z0-9_/]{2,60})"` — the first argument **is** the API path (these builds call `baseUrl + "/" + path`, no `/api` prefix), and the neighbouring `xxxApi=function(e){return get("nation/save",e)}` definitions hand you the parameter name and method with it. Guessing paths from page names produced a wall of 404s; the regex produced the real 132-endpoint surface in one pass.
- **Triage the whole response body before judging an endpoint — never a truncated prefix.** Dump the raw bytes to disk, print `len(raw)`, the top-level keys, then for *every* key under `data` its type + `len()` + one sample row. A response that looks like a config/stat dict (`{"rank":[…],"chart":[…],"edit":…}`) routinely carries a sibling `"list"` holding the actual records; a `json.dumps(resp)[:200]` probe loop shows you the first dict and hides a full PII table sitting in the same body. Likewise, when you grep a body for a marker (`"id_card" in raw`), print `raw[i-250:i+150]` around the hit — a hit you cannot see is a hit you will lose.
- **Probe an unknown list endpoint in this order, and URL-encode every value:** body skeleton → `limit` cap (try 20/50/200/1000; the cap is a per-endpoint constant, not a default) → cursor names (`page`, `id`, `offset`, `last_id`, `start`) → filters (`status`, `province`, `type`…). Pass every value through `urllib.parse.urlencode`: a raw CJK value dies **client-side** with `'ascii' codec can't encode` and reads exactly like "the filter changed nothing". A parameter that changes nothing across the whole matrix means the endpoint hard-codes its window — stop paging and switch to feed-polling (see the "Latest N" rule).
- **Extract with leading context, not bare paths.** Run `re.finditer(r'/api/[A-Za-z]+', blob)` over the whole
  concatenated bundle, print ~170 chars *before* each hit, and dedupe with a `set()`. The context carries the HTTP
  method (`this.http.put(...)`), the query params (`?userId=`) and the field order; a bare path list leaves you
  re-probing method-blind.
- **Grep every frontend tier for its API-base variable — each one names its own.** `var server = "https://…"`, `baseURL`, `API_BASE`, `VITE_API`. The client app, the admin panel, and the reseller/proxy panel of one platform are separate deployments, and the admin shell frequently points at an API host the client app never references and DNS never hinted at. Harvest that string from the admin HTML/JS: brute path lists against the known host can never find it, and it opens a whole second realm (its own `/admin/*` space with its own auth).
- **A bundle saved as text is corrupt when the server sent gzip without `Content-Encoding`.** `bytes.decode('utf-8','replace')` rewrites unmappable bytes to U+FFFD, so the file head reads `1f ef bf bd` instead of `1f 8b` and the stream is unrecoverable — greps come back empty and the bundle looks path-free. Check `head -c2 | od -An -tx1`, read bytes, `gzip.decompress`, then decode; never re-fetch by writing the decoded string, which bakes the corruption in.
- **Controller-level vs framework-level auth decides where the session is spent.** An app-authored body on an
  unauthenticated call (`{"success":false,"reason":"NOT_LOGGED_IN"}` / `INVALID_CREDENTIALS` / `INVALID_ID`) means
  that endpoint's own code does the check — the gate is per-endpoint, and the authorize step is often simply missing.
  A framework-default denial (`401` + `{"timestamp","status","error","path"}`) means the whole base sits behind one
  uniform gate. Tag every endpoint with which of the two it returned; the app-authored ones are the attack surface.
- Probe the privilege-transition and token-lifecycle routes first: `auth/switch-role`,
  `auth/change-super-admin-password`, `auth/me`, `auth/refresh`, `license/*`, `bot/*`, `onboarding/*`.
- A `refresh` endpoint whose validation names its field (`RefreshToken`) hands you the token-pair shape for free.
- **The bundle is also the protocol spec.** WS/REST handlers validate a fixed set of literal strings and the bundle
  carries them verbatim (`{type:'fetch', status:'accepted'|'solved'}`, `wsHost/wsPort/wsKey`, `/broadcasting/auth`).
  Grep the bundle for the field name and copy the accepted values before fuzzing: near-synonyms (`ok`/`done`/`all`)
  get a bare `Invalid status` and burn a whole round, and a Ratchet-style 404 on `/` usually means the real path is
  `/app/<key>` plus a signed auth — the key is required, not a bypass.
- **The bundle dictates the body *shape*, not just the field names.** `svc.method(this.form.value.email)` means that
  endpoint takes a **bare string body**, not an object; posting an object then 400s on every field-name guess and reads
  like "the endpoint is broken". Copy the caller expression (and whether it is JSON/string/form) before iterating
  payloads — the same endpoint returning 400 for an object and 200 for a raw string is a real, common shape.
- **Echo endpoints that return the service's own outbound request are a routing + version oracle.** A body like
  `{"response":null,"request":{"url":"https://nodeapi.<x>:8546/","headers":{"User-Agent":"Web3.py/5.31.3"}}}`
  proves which upstream node and client library a route actually talks to — use it to settle "this API's
  chain/environment is X" against what the docs claim, and read the echoed headers for credentials before assuming
  there are none (dump the whole object, not a truncated slice).
- `register` / `signup` / `onboarding/status` 404ing on every method = **no self-service account creation**. Without a
  real account the entire logic/IDOR/role face is unreachable — say that plainly once and pivot instead of grinding it.
- **When self-registration IS open, run the closed loop: register → activate → session.** Then go straight for the
  operate-by-userId admin face (`listUsersFiltered`, `changeUserPassword?userId=`, `changeUserStatus?userId=&active=`,
  `updateUser?userId=`, `getUserById?userId=`). These routinely authenticate without authorizing, so *any* low-priv
  session is a mass-takeover primitive — worth more than the account itself.
- **`INVALID_PASSWORD` at registration is the policy, not your credentials.** Registration feedback is a schema oracle:
  rotate candidate passwords (symbol-bearing ones) until the service returns success. Never record a policy rejection
  as "registration refused" — the wrong conclusion propagates into every later report.
- **Activation is where open registration usually dies.** `register → 201` then `login → NOT_ACTIVE` with no mail ever
  arriving (a dev/staging SMTP that does not deliver) leaves a real account and no session; the logic/IDOR face stays
  unreachable. Do not fall back to credential grinding — pivot to the platform's own **mail-plane admin panel**
  (Postfix Admin `login.php`, fingerprint `x-served-by: <product>-mail`): reading mail = reading the activation and
  password-reset links, unlocking the loop from the other side. Register with a mailbox you can actually read: the
  Guerrilla Mail JSON API answers server-side requests (`f=get_email_address` → `sid_token`; `f=check_email&seq=0`;
  `f=fetch_email&email_id=`) and one login covers all its domains — use **`sharklasers.com`**, since
  `guerrillamailblock.com` is a blocking domain where mail never lands. yopmail and 1secmail reject datacenter IPs
  (400/403) — do not grind them. And check whether the platform can send mail at all first: dead SMTP auth means the
  activation loop is dead, so record that and pivot to offline paths instead of waiting on the inbox.
- **A 500 on every structurally-valid bearer token means there is no JWT oracle.** When a well-formed token with a
  garbage signature 500s rather than 401/403, the code throws *before* signature validation — weak-secret and
  `alg:none` enumeration produce indistinguishable 500s and can never confirm a guess. Record the dead end and stop;
  guessing secrets there is pure loss.
- Diff the API reachable from the bundle against any published OpenAPI; the difference is the undocumented admin surface.
- **管理端/租户面板的表格渲染层常自带存储型 XSS sink——grep 它，不靠猜。** 国产 Metronic(Keenthemes) 系后台几乎共用同一份 `tablehelper.js`：`tableLineHtml = "<td><p id='invalidId'>#tableLineData</p></td>"`，`fmtTableLine(d)` 用 `.replace("#tableLineData", d)` **直接字符串拼 HTML**，而 `hasIllegalChar(s)` 只用正则拦字面 `script` 字样 ⇒ `<img src=x onerror=…>` / `<svg onload=…>` 全过。判据就一句：`.replace("#tableLineData", <某字段>)` + 只拦 script 的正则。
  **但 sink ≠ 可利用：** 还必须再找到一个「低权账号能写、管理端表格会渲染」的字段。先把低权侧**全部可写字段**枚举干净（客户端/代理端能调的每个写接口逐一看有没有自由文本）；只剩消息/短信正文时，发信接口又受红线约束 ⇒ 链断在此。**没拿到可写字段之前，不要把 XSS sink 当已成立的漏洞报。**
- **Read the spec's per-path security scheme, not just its path list.** A captured `openapi.json` names the scheme each
  path requires (`none` / `bearer` / `ApiKeyHeader`); bucket every path by it and the unauthenticated face falls out in
  one pass. Then **retest any token you already hold under each scheme** — acceptance in one scheme proves nothing about
  another (a token minted for an `ApiKeyHeader` route is still rejected as a `Bearer`, and that is a property of the
  schemes, not proof you hold no token). And when a device/OAuth-style flow's *create* leg is open while its
  *approve/authorize* leg is bound to the victim's own bearer (`auth-request`-style), the flow is not exploitable on its
  own — check which leg carries the binding before building a plan around it.
- **No admin/panel/manage route in the bundle ⇒ the admin face is server-side only.** The frontend cannot call what it
  never names. Settle this once with the bundle inventory as evidence, then stop fuzzing panel paths and endpoint
  dictionaries on this host — pivot to other infra (operator estate, sibling hosts, origin ports) instead of grinding
  waves that cannot pay off.
- **Catch-all stub base.** Send a nonsense path and a wrong method to an API base you are enumerating. If both also
  return success (`{"msg":"OK"}`, a generic 200), the entire base is a mock/catch-all: every "hit" there is noise.
  Stop enumerating that base, record it, move on. **Also sample it for randomized values: the same request returning
different counters each time (`views` 9463 → 7435 → 6066 across identical calls) is a mock/sampled payload — nothing you
do there credits, counts or persists, so drop the economics angle (view / like / reward inflation) for that endpoint.**
- **"Latest N" paging is not history.** When an `?id=`/`?page=` endpoint returns records, sweep many windows and count
  **unique record IDs** — not response sizes, which stay large either way. A unique count that plateaus (~100–233 over
  40+ windows) means the endpoint caps at the newest N; there is no buried history to mine, so stop sweeping it. **Then
  decide which fixed window it is:** if the newest id *climbs* between two calls and the window slides, it is a **live
  feed**, not a dead end — the harvest is a long-running poller that appends each new row id to a JSONL and stays up for
  the session (the climbing max id doubles as the table's true size), whereas a window that never moves is the dead one.

### 3. Check Host-based vhost routing once
- Replay one request against the origin with a set of Host values (`admin`, `tenant`, `api`, `www`, `app`, `bot`, `pay`,
  `localhost`, the bare apex). Identical status+body across all = a single server block, no vhost routing: one cheap
  test, then stop thinking about it. Divergent responses = a real routing map worth exploiting.
- On the origin, `:80` with an unconfigured Host falls through to the default nginx server; a `:443` default block that
  500s on every path is misconfiguration, not a vulnerability.

### 4. Prove the origin, then test it directly
- If a CDN fronts the host, resolve the origin IP and connect to **the origin IP directly with a `Host:` header** —
  this removes CDN normalization and WAF rules from your results. Test both `:443` and `:80`.
- `<center>cloudflare</center>` in a 400 body confirms the CDN was already mangling the request upstream of you.
- **Confirm you are talking to the edge before drawing conclusions from it.** A high-defense CDN answers the resolved pool with a vendor banner (`Server: Xcdn`) plus a fixed body such as `Please access via the domain name.` — that means **those A records are the edge fleet, not the origin**, and a port scan of them (including `3306`/`6379`/`27017`) **proves nothing about the origin's exposure**. Never write up "the host has no database port exposed" from an edge scan; fingerprint the edge first, then keep hunting the origin or record the blocker. One pool normally exposes the same one or two app ports on every IP, so fingerprint a single IP and stop sweeping the pool.
- **Separate the two layers' verdicts, and re-derive the gate before replaying.** A payload the CDN 403s may be perfectly
  acceptable to the app itself (and the reverse): retest the identical request on the bare origin and report "the WAF
  blocked it" and "the app accepts / rejects it" as two findings. A `200` whose body is the app's own rejection text
  (`Allow certain file formats`, `File is empty`) is the app's verdict — never log it as a write that worked. And when a
  recorded origin stops answering for its vhost (a foreign `404`, or a framework `401 {"path":…}` where the old build
  was open), the app has moved or been hardened: locate the current origin and re-read the auth gate **before** replaying
  the archived exploit — a technique recovered from the case file is not a live entry point.
- A full-port scan coming back "all filtered" while a plain TLS request to the same IP succeeds means the scan was
  rate-limited or probe-shaped, not that the host is closed. Retry slower on a targeted port list.
- **A CDN 520/522 is origin flapping — not a block, and not "the host is down".** Never write the domain off or report
  it as offline. Loop the endpoint with short timeouts, print `status | len` each round, and persist the body the
  moment a live window answers 200 (or a `426 Upgrade Required` for a WS service), then fingerprint from the captured
  bytes. One domain flapping says nothing about the other hosts on the same IP — and the reverse: a domain that never
  comes back within minutes is worth recording as down rather than re-probed all session.

### 5. Traversal: only trust the raw clients
- **Never** draw a traversal conclusion from python `requests`/`urllib` — they normalize `../` client-side and silently
  eat the payload. Use `curl --path-as-is` or raw sockets. Every "traversal blocked" conclusion from requests is void.
- nginx rejects an escaping `..` with **400**; `%2e%2e`, `%252e%252e`, `..%2f`, `..;/`, `..%5c`, overlong `%c0%ae`
  do **not** bypass it on current nginx.
- Status archaeology on a static handler: `404` = missing, **`415` = exists but outside the allowed root** (an
  existence oracle), `400` = nginx/WAF.
- `requests.Session` normalization kills SSRF traversal payloads too — encode at the last layer.

### 6. Know when SSRF cannot exfiltrate
- Pattern: the server fetches attacker-controlled `url` then hands the bytes to a third-party sink (a CMS upload) that
  rejects anything non-image → the body lives only in the fetcher's memory. The SSRF is real and useless for exfil.
- Read the log semantics as the oracle: `Failed to fetch` = the download failed; **`Failed to upload` = the download
  SUCCEEDED** and was rejected later. A WordPress `rest_upload_unknown_error` / "not allowed to upload this file type"
  is a size/type oracle (empty file → `File is empty`).
- Exfiltration needs one of: a local-file-read primitive, a permissive sink, a service that converts or echoes content,
  or a writable path that is served. `file://` won't work through a requests-based fetcher, and a `302` to an internal
  target makes the *target* fetch it — your callback sees nothing.

### 7. A "list" endpoint is often a local filesystem walk
- `/api/<cloud>/list?prefix=` returning `../../api/.env` with `url:"/media/../../api/.env"` is a **local directory
  walk with traversal in the prefix**: paths + sizes + mtimes with no read primitive. Sizes alone identify the prizes
  (`.env`, `*.pyc`, secrets modules, `cloud-init`, `instance-data`).
- The returned `url` field hints at the serving route — test it, but expect the static handler to block escaping.

### 8. Leaked-credential reuse is not spraying
- Replaying looted credentials (real usernames/emails × the passwords those same people reuse) against a sibling
  system is logic/OSINT work, not a dictionary attack — allowed under a no-spray policy, but bound it hard (tens of
  attempts, stop at the first wall) and never let a wordlist into it.
- The outcome is a decision, not a dead end: a clean all-`401` with no lockout means the credential face is **closed**.
  Record it, note the missing throttle as its own report finding, and pivot.
- **Looted hashes are the offline half of the same rule.** Crack them locally with a wordlist built from engagement
  intelligence (product/person/email-prefix + the target's local language + `1`/`!`/year mutations) before any online
  attempt: `john --wordlist=` handles bcrypt on CPU, whereas `hashcat` needs an OpenCL device and will not start
  without one. Zero hits is a recorded dead end ("password policy holds"), never a licence to go back online.

### 9. 上游代理端点：平台代持的第三方 key 是免鉴权资金面
- 平台代持 vendor key（Pi Server API Key / 支付网关 key / webhook 签名）并暴露「代调用」接口时，**第一件事是确认它要不要认证**。
  `/api/<vendor>/payments/approve|complete|incomplete` 这类实测常常**完全无鉴权**（BFLA）——任何人有任意一个有效对象 ID 就能借平台的 key 代为操作。
- **拼接点常在 body 字段，不在 path。** `{"payment_id":"1"}` 正常；换成 `{"payment_id":"../../me"}` 若上游回**通用 404**
  （而非 `payment_not_found`）就证明该值被原样拼进了 `https://vendor/v2/payments/{payment_id}/approve`，路由已被穿改。
- **用控制字符逼出内部 URL 模板。** 拼接字段里放 `\x00\x01`，客户端库会抛
  `URL can't contain control characters. '/v2/payments/\x00\x01/approve'` —— **内部路径模板直接印在 502 体里**，比猜快一个量级。
  同类触发器：超长值、非法 UTF-8、孤立代理对（`\ud800` → 未捕获异常 500）。
- 上游错误原样回显（`{"error":"payment_not_found"}`）同时是**存在性预言机**与「key 有效」的旁证（401 / `invalid_key` 才是 key 错）。
- 同平台的兄弟端点会自相矛盾，别放过：`approve` 能用同一个 key 成功调用，而 `incomplete` 回 503「key 无效或未配置」
  = 两条代码路径读了不同的配置项，是可报告的代码缺陷。
- **边界要写清楚**：字符串拼接改不了 host（除非代码用 `urljoin`），所以拿不到任意外部 SSRF；能拿到的只有
  「在供应商域名内改路径」。报成 BFLA + 资金面，**不要包装成 SSRF**。
- **可达面用「响应格式差分」画图，不要逐值猜路径。** 穿越值若仍落在供应商业务路由内，上游回**业务错误格式**
  （如 `{"error":"payment_not_found"}`）；飘出业务路由则回**框架通用 404**（`{"status":404,"error":"Not Found"}`）。
  逐个候选值发一轮，按格式分桶，一次就画出「哪些路径段可达」的地图（例：只有 `../payments*` 落回业务格式 =
  可达面就是 `/v2/payments/*` 全域）。
- **先打无鉴权的 `/api/<vendor>/config`。** 这类端点常泄露 `sandbox` / `server_key_configured` 等布尔位——
  生产站跑沙盒 key 本身就是配置管理发现，且决定支付链是否有真实资金后果。
- **先确认对象 ID 在哪一侧创建。** 若创建走浏览器 SDK（`Pi.createPayment` 等）而服务端只有 approve/complete，
  BFLA 链会卡在「没有有效对象 ID」：服务端 ID 扫描常全空（ID 属于供应商侧命名空间）。别在服务端找不存在的
  create 端点；拿 ID 只有两条路——枚举真实用户流量产生的 ID，或自建 SDK 沙盒环境自己发起一笔。

### 10. 用户枚举双预言机：注册错误 + 交错时序
- **注册接口是最干净的枚举预言机。** 已存在邮箱回业务错误（`400 "该邮箱已注册"`）vs 新邮箱 `200` 注册成功——
  无时序噪声、无需采样。优先测它，再考虑时序。
- **登录无显式差异时用交错时序采样。** 存在的账号走 bcrypt 比对（约 2× 慢）。必须**交错**发（每轮轮询全部
  候选各一次，≥5 轮取中位数）——单候选连发会被网络抖动和缓存淹没。判据：中位数差 ≥15ms **且**分布零重叠
  才算成立；有重叠就加轮数，不要硬下结论。
- **邮箱规范化一并测。** 大小写/前后空格变体也回「已注册」= 服务端做了 lowercase+strip（枚举仍成立，注册位
  不可派生）；`+tag` 或加点变体注册成功 = 无别名归一，一个邮箱可派生无限注册位（本身是个发现）。
- 用户名面同理：`/api/admin/login` 的 username 时序（有效用户名 ~2× 慢）可单独锁定管理员用户名，与邮箱面互补。
- **登录期的第二种枚举：状态检查前置于密码校验。** 存在+错密码回 `INVALID_CREDENTIALS`，存在+**任意**密码回
  `NOT_ACTIVE` ⇒ 激活/锁定状态在校验密码之前就返回了 —— 既泄露用户存在性，也是可报告的逻辑缺陷。
- **注册/更新 DTO 做一次批量赋值尝试。** 塞 `active:true` / `roles:["ROLE_ADMIN"]` / `enabled` / `verified`。后端忽略 =
  防护正确（记录，别当洞）；生效 = 直接提权。
- **签名式登录（web3/钱包）要分清它验的是签名人还是只验签名有效。** 用**自己的**私钥对**别人地址**的 challenge 签名
  提交：换来会话 = 任意账户接管。返回业务级 `NOT_FOUND`（而非框架 400）= 地址参数名正确、目标集合是另一套数据。
- **挑战-签名类端点的验签要用四连测证明，不能停在「它要签名」。** (a) 垃圾签名；(b) **自己的**钥签**别人地址**的
  challenge；(c) 自己的钥签自己的 challenge。期望 `403 / 403 / 业务层 200`。若 (a)(b) 也过 ⇒ 任意账户接管；若 (c) 只回
  业务错（`no_location` 之类）⇒ 验签实现正确，记录后放弃该端点，别反复换令牌格式重试。**(d) 重放：复用已消费的 challengeId，期望 `401 challenge not
  found`；若仍能过，说明 challenge 不是一次性 nonce —— 签名虽真也可被重放攻击。**
- **签发令牌的 BOLA ≠ 资金面，先验证值端点的托管模型再定级。** `GET …/generateToken?address=<任意地址>` 这类零鉴权发
  token 的洞只给到「以该地址身份」的会话级读写。拿到 token 后**第一件事**是打余额/提现/转账端点：若它们 422 要
  `signed_serialized_tx` / `signed_*`，说明服务端不持钥（非托管设计）⇒ 该 BOLA 的影响上限就是读 + 会话操作，报告按此
  定级，并把剩余预算转到服务端代码执行/数据库，而不是继续在 API 层找资金移动路径。
- **一次登录尝试的分支状态码就是账号存在性预言机。** 同一密码打全部候选账号：**框架级异常**（`500 系统异常`）vs **业务级否定**（`1001 用户名或密码错误`）即区分存在与不存在 —— 存在的账号在密码校验前就走进了另一条取数路径（常见于该账号开了 2FA、或缺密钥记录导致 NPE）。前提是必填字段已补齐：把「缺参数」校验排在这条路径*之前*的接口不带该信号（所有账号一律回缺参），此时先枚举出完整的必填三元组（如 account+password+googleCode）再比。
- **方法检查先于鉴权检查 = 端点存在性泄露（不是绕过）。** `GET /admin/updatePass` 回「不支持的请求方式:GET」而 `POST` 回 `401 未授权`，说明该端点存在且鉴权排在方法检查之后；反向：无参 GET 直接 `401` 的端点连存在性都确认不了。用它把 `admin`/`proxy` 两个 realm 的功能表画出来，再逐个确认真实鉴权边界。
- **路径变形绕鉴权过滤器时，变体必须与基线同 method，否则方法守卫会伪造「已到达控制器」的假信号。** 以 `/admin/*` → `401` 为基线后试 `//x`、`/./x`、`/x/`、`/x;.js`、`/%61dmin/`、`/google%2fadmin%2fx`、大小写与尾随空格时，若基线是 `POST` 而变体写成 `GET`，你收到的 `{"不支持的请求方式:GET"}` 只能证明**请求到达了控制器**，与过滤器无关：方法检查与鉴权检查是两条独立路径，GET 被前者先挡掉，你既没拿到 401 也没拿到数据 ⇒ 那一轮对过滤器**零判读力**（很容易误当成「绕过了！」）。全变体同 method 复测后仍全 401 = 过滤器路径规范化严实、绕过不成立；负结论也要写明是用哪个 method 测的。

### 11. Hunt the non-production instance of the same product
- Once the primary host is hardened, enumerate subdomains and **prefer whatever is named `dev-` / `test-` / `staging`**:
  same backend code, looser configuration, self-registration still on, debug surfaces still enabled. This ordering is
  the durable product-level play, not a lucky one-off.
- Find internal names where certificate-transparency sources have gone dry: `dnsx -l <wordlist> -a -resp -silent -t 400
  -retry 1` over `seclists/Discovery/DNS/subdomains-top1million-20000.txt`, repeated per apex. Names like `dev-api`,
  `webapp`, `services`, `ws1`, `claim`, `mailadmin` rarely appear in CT logs at all.
  **When the CT API itself rate-limits (`crt.sh` → 429), swap the source, not the wordlist:**
  `https://api.hackertarget.com/hostsearch/?q=<apex>` (free, no key) returns host→IP pairs for the whole apex in one
  request; resolve them, filter every IP through your CDN range list (`cdn-origin-tracing`), and keep the bare origins.
  One pass is what surfaces `dev-`/`test-`/`nodeapi`-style hosts on their real IPs when the primary host is fully
  CDN-fronted.
- Read the panel/mail/API roles off cheap fingerprints before attacking: a `426 Upgrade Required` on the root is a
  WebSocket service; a `login.php` returning `x-served-by: <product>-mail` is the mail admin panel; a bundle titled
  after the product but served from a `dev-` host is the soft deployment of the same app.
- **品牌矩阵 = 同一产品的多次部署，加固程度逐个不同。** 一个品牌前端壳被加固不代表整个舰队被加固：`crt.sh` 跑一次 apex 就能把运营子域全抖出来（`admin.` / `proxy.` / `sender*` / `server.`），每个都要单独过一遍侦察（同一个 `crt.sh` 的结果里，`admin.*` 上挂着的是管理后台外壳、`sender*.*` 是群发网关，角色一眼可辨）。
- **管理后台未必挂在客户品牌域名下——它常是*另一个*品牌域名的子域。** 配置表（`*_proxy_relation` / `*_enc_domains`）给的是**客户前端**域名集，管理端要另外找：拿已知品牌域名集 × `admin manage houtai console backend boss gl ht oa` 跑一轮本地高速 DNS 爆破（crt.sh 被限流时尤其划算，也比 CT 快）。命中后管理端往往是**独立应用**——与客户 API 不同端口、由同一 nginx 按 `Host:` 分流，用 actuator `self.href` 把「域名 → 内部端口」对上号；页面带 `jsessionid` 说明是服务端渲染模板的 Spring 应用，页面路由本身也是攻击面。
- **管理端的接口表埋在*每个功能页的内联 script* 里，主 bundle 里几乎没有。** 管理端一页一功能（`menuPower.html`/`proxyUser.html`/`machineStatus.html`/`systemConfig.html`/`awaysOnlinePhone.html`…）：把所有页面拉下来逐页 grep `/admin/*`、`/adminproxy/*`、`/command/*`、`/simswitch/*`、`/machine/*`、`/systemconfig/*`、`/google/*`，一次就能拿到完整管理面（`unbindGoogleAuth` / `bindGoogleAuth` / `listAdmin` / `command/at` / `simswitch/switch` …）。**别漏 `changelog.html`**：厂商变更记录常直接写出真正的重置接口路径和厂商自己承认的业务漏洞。
- **用存在性预言机测账号表是否跨品牌共用。** 拿自己已有的有效账号去打兄弟品牌 API 的 `/user/beforeLogin?account=<自己账号>`：回「存在」= 一套用户表多品牌运营，一个凭据在所有品牌通用，且各品牌的数据面常由同一套代码暴露（同一套越权/IDOR 会在每个品牌上复现）。

## Pitfalls
- Don't clear a route from one method — a read-path role check frequently does not cover the write path.
- Don't accept a 200 as success on a Go backend: gin/echo/fiber silently discard JSON fields with the wrong type and
  return 200 with an **empty body**. Verify with Set-Cookie / a known-good error shape, not the status code.
- Don't paste credentials into the summary document — record existence + path, keep values in the loot pack.
- Note **your own** test accounts when you later loot the user table (`sec_research_*`) — they pollute analysis and
  prove you were there.
- **Never name a helper function after a stdlib module you call inside it.** `def http(...)` shadows `http.client`, and
  the failure surfaces late and misleadingly (`'function' object has no attribute 'client'`) long after the probe logic
  looks correct. Name request helpers `req()` / `post_json()`; check your own imports before blaming the target.
