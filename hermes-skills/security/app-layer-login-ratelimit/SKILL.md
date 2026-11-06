---
name: app-layer-login-ratelimit
description: "Use when login lockout or global 401 write middleware."
version: 0.1.0
tags: [ratelimit, xff, login, auth-middleware, secret-gate, python-panel]
---

# App-layer 登录限速键 · 全局写中间件路由预言机

单密码/管理门登录出现「尝试过多 / 15 分钟后再试」、或任意路径 `POST` 都回 `{"error":"unauthorized"}` 时用。**先差分限速键与真路由，再决定是否短主题词。** 不替代 `pentest-execution` NO-SPRAY。

细节与案例：`references/xff-key-and-route-oracle.md`。Tor 出口轮换助手：`scripts/tor_rotate.py`（check / rotate / exits，含 NEWNYM raw-socket 与出口验证）。**批量爆破引擎**：`scripts/tor_batch_brute.py`（v23 长连接 10发/出口批量轮换，泛化自 bidi/fragment 实战，见 §D'）。**多实例锁等价判定**：`scripts/cross_lock_matrix.py`（探测名锁一实例→逐域名读锁态，一轮跑出全部等价类——先判定独立实例数再决定并行投入，防止对共享后端重复烧预算）。**高吞吐数据面收割的车队形态**（多实例×隔离端口池×IsolateSOCKSAuth、免 NEWNYM、按核数扩容、响应分型 4001/602 处理）见 `chinese-fund-scam-platform-pentest`「Tor 车队」节 · `references/tor-fleet-mass-extraction.md`。

## When to Use

- 登录失败文案：`密码错误` vs `登录尝试过多，请15分钟后再试` / 429 JSON
- 单字段管理门：`name=secret` /「输入管理密码」/ cookie `auth=`
- 写方法（POST/PUT/DELETE）打**任意**路径都 401 JSON；GET 未知路径却是 HTML 404
- CF 后 Python 味 `/health`（isoformat 微秒）+ SSR 账单 UI CSS 内嵌登录页

Don't use for: slowapi 已确认只键 peer 且 XFF 差分无效时的长喷；BaseHTTP 双路径面板（走 `python-basehttp-panel`）。

## Procedure

### A. 限速键差分（≤1 分钟，先做）

1. 同一出口用**唯一** wrong secret 打到锁（记下锁文案）。
2. 换头各 1 次（仍用唯一 secret）：
   - `X-Forwarded-For: 203.0.113.N`
   - `X-Real-IP` / `True-Client-IP` / `Forwarded: for=`
3. 判据：
   - 锁文案 → 又变「密码错误」= **源站信任该头**（中危；可轮换头做**短**主题词）
   - 仍锁 = 键在 TCP peer / 账号级 → pacing 或 Tor NEWNYM 或源站直连
   - `CF-Connecting-IP: 8.8.8.8` → CF **403** = 边缘校验，弃用该头
4. **XFF 可绕 ≠ 开喷许可证。** 主题词几十条不中就停（NO-SPRAY）。

### B. 真路由 vs 全局写中间件

1. `POST /totally_unknown_xyz` → 401 JSON 且 `POST /api/anything` 同形 → **写方法全局鉴权中间件**，禁止当「API 面很大」。
2. 真路由只认 **GET 形状差**：
   - 存在：`GET /api/bills/1` → 401 JSON（或 302 `/login`）
   - 不存在：`GET /api/nope` → 应用 HTML 404（固定 size）
   - id 类型：`/api/bills/abc` 404 而 `/api/bills/1` 401 → 数字 id 路由
3. `OPTIONS`：`Allow: HEAD, OPTIONS, GET` 辅助；`PATCH` 统一 500 美化页 = 未实现 method，不是 RCE。
4. 记「存在」的路径进 Approach；门后优先 IDOR（`/group/{id}`、`/api/bills/{id}`），别空转字典。

### C. 单字段 secret 门（附加指纹）

- 成功信号：302 `/` 或 `/admin` + `Set-Cookie: auth=...`（非空）
- 伪造 `auth=1/true/admin/base64` 仍 302 `/login` = 服务端 token 表/签名
- 登录页内嵌 `group-card`/`income-row`/`summary-grid` + CSP `chart.js` → SSR 账单后台
- 源站仅 CF、旁 suffix 其它 A 记录 = 邻机 recon only（用户点名才扩）

### D'. 绕限速升级阶梯（2026-10 实弹数字，先判前脸再选层）

0. **先判前脸**：`server: cloudflare` / 有 `cf-ray` → CDN 前脸，客户端传递的 XFF/X-Real-IP/cf-connecting-ip 会被边缘覆盖，**头技巧无效**；裸源站（直连 IP:port、无 cf-ray）→ 头技巧大概率有效。
1. **裸源站层：XFF/X-Real-IP 头轮换**。每请求换 `X-Forwarded-For`+`X-Real-IP`（随机 IP），键在客户头 → 无限流。实测：3次/窗口限速的 BladeX 后端，轮换后 12/12 连过、随后 **267k 字典 30 rps 跑数小时不封**。多线程引擎合并每批计数，别用同一 XFF 连发。
2. **CDN 前脸层：Tor SOCKS5 + NEWNYM 换出口**（头技巧已死时的主力）。可用性三步验证：① `curl --socks5-hostname 127.0.0.1:9050 https://api.ipify.org` 出口≠本机；② 目标站经 Tor 直取返回应用响应（CF 不一定拦 Tor，本战役 bidi/fragment/crm/nav 全部放行）；③ 控制口在（torrc `ControlPort 9051`，无密码时 `AUTHENTICATE` 直接通过）。
   换电路（raw socket）：`AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT\r\n` → 等 ~2.8s 生效。**NEWNYM ≠ 换出口（2026-10 实测翻车）**：同一出口会被反复复用（控制口未先 `AUTHENTICATE` 时 SETCONF 静默失败，多国轮询全落在同一 IP，看起来在轮换实际原地复读）——轮换后**必须验证出口真变**（经 socks 查 `api.ipify.org`），未变则 `SETCONF ExitNodes {<国>} StrictNodes 1` + NEWNYM 重试（≤6 次，国家池 us/de/gb/nl/fr/sg/jp/ca 逐个试）。**连接模式按轮换频率选**：≤4 发/出口的高频轮换 → 每请求独立连接（`Connection: close`），keep-alive 旧套接字在 NEWNYM 后变死、requests 挂死到超时（实测猎手静默停摆数分钟）；10 发/出口的低频轮换才用 v23 长连接批量。**关键工程点（v23 批量设计，2026-10 定型）**：keep-alive 长连接**批量**轮换——每进程 1 个长活 Session 复用连接，用满 ~10 发/出口（对齐常见 10/60s 预算）后：NEWNYM → 等 ~2.2s → **关 Session 再新建**（旧连接淘汰，新连接必走新电路）。**NEWNYM 不杀已建电路**——长连接在别进程轮换时照常工作，这是多进程共享同一个 Tor 可行的根本；反之「每请求新建连接（Connection: close）× 多进程 × 高频 NEWNYM」= **电路饥饿**：SOCKS 握手挂死（线程栈停在 socks.py `_SOCKS5_request`）、ConnectTimeout 风暴、零吞吐（本战役 5 进程叠加实测翻车；改 v23 后 0.46-0.48 发/秒/进程稳定）。工程兜底：`socket.setdefaulttimeout(15)` 兜住卡死的握手（requests 的 timeout 不保证覆盖 SOCKS 协商层）；worker `except` 里**把 pwd 放回队列**（否则异常静默吞条目）+ 前 N 条异常打日志（静默 except = 伪装成卡死）。可复用引擎：`scripts/tor_batch_brute.py`。
   节奏：按目标窗口预算，每出口用 ≤(限额-1) 个请求就轮换（如 5 req/225s/出口 → 每 2 次登录尝试（4 请求）轮换一次）。实测吞吐：2min/发 → **~7s/发（17×）**；多站并发共享 Tor 可行——**前提是上一条的批量长连接设计**；偶发 429 → 轮换重试即可。
3. **每次动手前先实测限额**：同应用不同端点限额不同（captcha/get 与 login 分开测）；不少站点**某个端点完全无限速**（NestJS 登录 47 rps、Go basic-auth 29 rps、FastAPI /api/login 31 rps 连打无 429）。小突发 10-15 发快速判定，别默认「都要慢慢来」。

3b. **限速键拓扑 · 三种「换 IP 也没用」的形态（2026-10 实战定型）**：
   - **多副本稀释（k8s/负载均衡 + 进程内存计数）**：in-memory limiter 每副本独立计数 → 单击可连过 10+ 发（正常单击 10 次即锁的却全过，因为请求散在多个 pod 上）；预算 ≈ 副本数 × 窗口限额。判定：静默 ≥窗口后突发 10-15 连发全过 = 稀释确认。但别得意——常态 pacing 仍贴限速器地板（实测单流 ~0.07-0.15 发/秒，多流叠加即触各副本上限，进 429 轮盘后反复轮换空转）。
   - **账号/用户名级全局锁**：换出口（Tor NEWNYM）、换头全部无效，仍 429/「15 分钟后再试」→ 键 = 被锁定账号（全站共用一个计数器；实测 finance 类系统 5 次/15 分钟全站）。校验法：封禁期过后用**全新出口**打 1 发（过）→ 连打 5-10 发（又被锁）→ 再轮换出口仍锁 = 全局。出路：每窗口 ≤4 发慢速数学，或直接弃喷 pivot（Tor 在这类目标上纯浪费）。
   - **账号锁 + IP 锁双层同装（2026-10 实测定型）**：真实目标常两段文案并存——账号级「该账号已被临时锁定，请15分钟后再试」≈5 发/15min；IP 级「登录失败次数过多，请30分钟后再试」≈5-9 发/30min。**Tor 每发真换出口只解 IP 层**：实测 5 个不同出口连打 5 发，第 6 发照上账号锁（账号层不可绕）。出路 = **多候选用户名并行摊薄**（6-8 个账号 × 5 发/15min ≈ 160 发/时）+ 优先词表先跑 + 账号锁出现即从本窗口剔除（统计消息模式识别「锁而未耗」，别对锁定账号空烧）。
   - **账号锁语义三补（九州农脉定稿）**：① **无枚举神谕**——假用户名锁行为与真账号完全一致（5 发后第 6 发照锁），别做存在性推断；② **大小写同归一**（jznm/JZNM/Jznm 共享锁态），变体不增配额；③ **未触碰过的用户名 = 独立满额 5 发**（任意字符串）→ 战术 = **宽度优先网格**（30-40 候选用户名 × Top10-20 密码 × 多实例）：聚合吞吐 ~4.4 发/分（深度线）→ **~16 发/分**；节奏 = 每用户名 5 连发（吃锁即跳窗 16.5min）+ 每 4-5 发换出口。
   - **数字预算型 per-用户名计数（2026-10 .NET 支付台实证）**：错误文案直接回「剩余登录次数：N」（10 起倒数）＝键在**用户名**、预算数字可视化。探测法仅需 1-2 发：全新名打 1 发（满额 = 新预算）→ 同名再 1 发（-1 = 计数在名上；不变 = 在 IP/全局）。耗尽文案变「账户因频繁验证信息失败已被锁定」。此型下换用户名 = 换预算（换 IP 无用），吞吐靠用户名空间放大——**但盲猜上限卡在不知道真用户名**：先找枚举口（找回密码/注册回显/错误差分）再决定投入，找不到枚举口就记账别烧。
   - **多实例预算拓扑（2026-10 九州农脉定型）**：同一套后台常挂 N 个域名/实例（CT 日志 certspotter `api/v1/issuances?domain=X&include_subdomains=true` 分页一把挖全；通配 DNS 会让任意子名都回响应，别把 catch-all 当真实例）。**先做锁等价判定再并行**：取全新探测用户名在 A 实例 5 连发（第 6 发回「已锁定」为准）→ 同探测名去 B 实例打 1 发——回「已锁定」= 同后端共享计数（不增预算，别重复投入）；回「账号/密码错误」= 独立实例（各自 5 发/15min）。实测一站群 6 实例互为独立、另 3 个域名与旧实例同后端。天花板 = 实例数 × 用户名数 × 5 ÷ 15.5min。**判定工程细节（实测踩坑）**：锁 ~15min 过期——同一批等价判定要在窗口内跑完（跨窗口旧读数全变「未锁」→ 假独立）；一个探测名只能验证一个等价类，多候选子域时逐类轮换全新探测名（探测名不进正式词典，不污染预算）；部分实例阈值略漂（5-7 发才锁）——判定腿数打到「第 6-8 发回锁定」为准，别只打 5 发就下结论。**多引擎编队**：每进程 1 条独立 Tor（**绝不并行 NEWNYM 同一 Tor**——互踩致 SOCKS 挂死）；进程间用户名切片互斥（同实例同用户名给两进程 = 互偷预算）；冷却 15.25min + 0-1.2min 抖动防锁步谷；同步重启后必有一次全锁谷（预期，非故障）；实测 7 进程 ≈ 90-100 发/分。
   - **CDN zone 级 IP ban（CF Error 1015）**：与 per-endpoint 429 不同——整个 zone 对该 IP 临时拉黑；**浏览器同 IP 也吃 "banned temporarily"**；换 Tor 出口能过 ban 但吃 "Just a moment" JS 挑战（requests 永远过不了）。恢复通道：patchright `proxy={'server':'socks5://127.0.0.1:9050'}` + 过挑战后用 `page.evaluate` 页内同源 fetch 代打 API（带 Authorization 头照常）——一切照旧，只是链路换成浏览器。截图/字体在 Tor 下可能超时，跳过截图。

4. 大规模并行（多站多起跑）时每个 runner 独立日志 + 断点文件（tried.txt）+ 命中即存 LOGIN_OK.json + 停止标志；命中后接跨站复用 sweep。**杀 runner 用 PID**：`pkill -f <script>` 会匹配到「发起命令的自身 shell 命令行」把当前会话一起 SIGTERM（实测翻车）；先 `ps | grep` 取 PID 再 kill。worker 的 `except` 里必须打日志——静默 sleep 的异常会被伪装成「无进度卡死」（实测一次因非可重入 log 死锁 + 静默异常双重叠加，排查花了好久）。

### D. 失败计数窗口语义（pacing 数学 · 读源码定节奏）

- **gap-reset 型计数**（自写限流，RenewHelper 类，2026-10 实读源码）：每次失败都刷新 `last_fail`；只有「距上次失败 > WINDOW」才清零；WINDOW(=300s) 内累计 THRESHOLD(=5) 次 → 封 IP BAN_TIME(=900s)，计数删除，封禁期不计失败。→ **均匀慢喷也会死**（95s 间隔照样第 5 次被封）。正确节奏 = 每轮 ≤THRESHOLD-1 次失败，然后**主动静默 ≥WINDOW** 再进下一轮；或按源码实算。
- 同源码第二/三层：内存 1s 冷却 + 每日 ~100 次/动作/IP 桶；**注意全局配额副作用**（KV 1000 写/日——长喷会烧掉对方应用的配额造成业务影响）。上限内只做短定向，不对生产长喷。
- **目标跑开源/已知工具时先读源码**（续费助手 RenewHelper、cat2bug 等 GitHub 一把梭）：窗口/阈值/封禁时长/默认口令兜底（如 `env.AUTH_PASSWORD || "admin"`）全部实算后再定字典与节奏，比盲测省一个数量级。
- 限速/封禁信息常在 **body** 里（`{"Retry-After":"225"}` / `{"code":429,...}`），别只看 headers；封禁键 TTL 到期即解封。
- **burst 后突然变「schema 类」错误 = 软限速伪装**：例 明明字段非空却回「验证码不能为空」/「参数不正确」。歇几秒~几十秒自愈，不是链路坏了，别急着重写脚本。

## Pitfalls

- Tor NEWNYM 同 /24 出口仍粘锁时，优先再做 XFF 差分，别断定「全局锁死」。
- 开喷前先打一发**已知错口令**做链路验通：必须看到「账号/密码错误」级响应才算请求到达凭据校验层；一律 422/字段校验错 = 假阴性（content-type/加密/字段名问题），先修链路再谈字典。
- 把全局 POST 401 写成「未授权 API 可写」= 假阳性，用户会骂。
- 主题密全挂后继续加字典 = 违反 NO-SPRAY；报告写「限速可 XFF 绕 + 弱密未中 + 未接管」。
- 旧文档写「slowapi 永不信 XFF」是片面的——取决于 ProxyFix / 自写 header 键；**先差分**。
- Wayback 同 suffix 历史站（WebSSH/Render）≠ 当前记账应用；路径交叉无命中就停，别当 pivot 主线。
- 旁共享主机（hostypanel）探 phpMyAdmin/webmail 易触发 **cPGuard** 整站挡 IP——soft 探、少路径、换出口。
- **cPanel/cphulk（共享主机整机入口，2026-10 实测）**：`https://<ip>:2083/login/?login_only=1` POST `user/pass/goto_uri=%2F` → 失败 `401 {"status":0,"message":"invalid_login"}`（无锁定文案=可慢磨）。cphulk 按 IP 计数（换 Tor 出口=新配额）、对真用户名有账号级锁 → 与 django-axes 同用「cron 慢磨 1 发/25min + 状态文件」形态；用户名候选从托管商别名反推（如 `*.wfi.cba.mybluehost.me` → 试 wficba/cba/wfi）。
- 全角 secret 500 ≠ RCE/栈；只记「输入校验炸」死端。
- 对 CF 站用 requests 测速率/判死活 = 测的是自己不是目标：先分「JS 挑战（Just a moment，浏览器可过）」「zone ban（1015，换出口）」与「per-endpoint 429（pacing/轮换）」，再谈字典。
- **MFA 密码预言机**：正确密码但未带 MFA → 差异化提示（如 `mfa_required`）≠ 错误凭据提示。MFA 开着也能纯爆破**验出正确密码**（实测 Kite k8s 面板）；先打 1 发已知错凭据定响应面再开喷。
- **长跑枚举工程坑（2026-10 血泪六条）**：① 响应可能带 UTF-8 BOM（WAF/高负载下）→ `json.loads(r.content.decode('utf-8-sig','replace'))`，否则整实例 lane 静默全废（实测近 2000 发白打）；② **被锁响应不算「已测」**——锁时不推进字典指针，否则词被跳过且无结论；③ 用字符串替换生成脚本变体 → 必 `ast.parse` 校验（实测漏 `import random` 致三进程全崩）+ 替换会串日志名（v18→v19a 产出 hunt19aa）→ 巡检脚本写死精确文件名；④ 看门狗 cron 的脚本名清单必须随版本同步（否则复活旧版僵尸进程偷同一份锁预算）；⑤ 断点续传 = 解析自家日志取每 lane 词进度 + 注入 RESUME dict（re.sub 用 lambda + `json.dumps(ensure_ascii=False)`，中文键防 bad escape \u）；⑥ 分卷/改名等文件操作用 Python 小脚本，别用 shell 循环（printf 失败的 mv 把所有分卷覆盖成同名——实测丢件）；⑦ 长等待巡检别挂前台长 sleep——本机前台命令 ~420s 硬顶（超长直接超时白等），用 background 后台跑或拆 <380s 段；固定巡检写成 `check.sh` 落文件反复调用（复杂内联易被 hardline 拦，落盘脚本即稳）。
- **主机层 JS 门 cookie = 假阴性第三型（2026-10 实测）**：200 但 body <1KB 且含 `document.cookie=...` + reload = 主机反机器人门（Beget 系：`beget=begetok`）。**不是口令错误**——不带门 cookie 时整轮爆破全部假失败（每个响应同尺寸小页即是翻车信号）。先 GET 一次解门拿到 cookie 名/值，此后每请求都带。判「墙形态三分」顺序：JS 挑战 / zone ban / 门 cookie，再开喷。
- **IsolateSOCKSAuth 按请求换用户名 = 电路饥饿变体**：换 SOCKS 认证用户名即换电路，每请求都换 → 电路构建慢+失败率高的空转循环（实测 75 分钟零推进，且异常被静默吞掉无任何输出）。正确节奏 = **粘滞电路连续 20-45 发**再切下一个用户名；每发都打日志（有噪声才有进度感）。每电路发数按单发耗时调：快目标 20-45 发/电路；**慢目标（单发 10-30s，且每发含 GET 登录页 + POST 两条请求）4-6 发/电路**——把电路构建开销摊到数发上，别让每次尝试都付一次建路成本。
- **全路径统一 403（含 /favicon.ico、静态资源）= 主机级 WAF 规则**，非 URL 级。用另一出口（Tor）打一发判归属：换出口能过 = 本 IP 已被烧（换出口继续+降速）；全出口同 403 = host-wide，收手记录。
- **共享主机别名直连（CT 日志 → 绕 CDN 达源站）**：证书透明日志常暴露托管商别名（`<site>.<account>.mybluehost.me` 类）——经别名请求可绕过 Cloudflare 前脸直达源站、把 wp-login 等路径从 CF 反爆破手里夺回来；但源站自带独立反爆破分层（实测直连 406 拉黑、Tor 出口 409），别名 ≠ 免限速，仍需慢速 + 出口轮换 + 看守式重试。
- **源站直连 421 Misdirected Request（IP + Host 头）** = 主机拒绝非边缘请求，直连绕墙此路不通，别在链路层耗时间。
- **假凭据错误 = 机器人评分假响应（2026-10 定型）**：非浏览器客户端可能恒回格式完美的假错误（如注册端点对任意输入回 `invalid login/password`），真实校验/挑战只在浏览器上下文可见。对认证语义下任何结论前，先 Playwright `page.evaluate` 页内 fetch 对照重放（细法见 `spa-js-api-mapping` 的 `references/antibot-pow-reversal.md`）。
- **用户名锁（django-axes 型：65B「locked」/「请15分钟后再试」）→ 慢速看守而非实时喷**：锁按用户名全局（换 Tor 出口照锁）；形态 = 状态文件 + cron 20-30min 一发，锁时**不推进**指针、解冻自动续，静默仅报命中；首轮验证通过（未锁时指针推进）。
- **业务端点 429 窗口（注册/OTP 类，非登录）**：文案 `{"reason": "requests limit"}`，窗口比登录更紧——同 IP 短时间内约 2 个完整流程循环即触发。正确姿势 = 状态保持 + 退避递增（如 240s + 120s×轮次）后**重开完整循环**，守护式静默重试到出现非 429 结果；与挑战系统（PoW/X-Verify）交织时每轮都重新取挑战，别复用退避前的挑战头。

## Verification

- [ ] 链路已用已知错口令验通（响应达凭据校验层，非 422/校验错）
- [ ] pacing 依据计数窗口语义（源码或实测），不靠感觉
- [ ] XFF/peer 键结论有对照臂（锁 ↔ 密码错误）
- [ ] 至少一条「真路由」用 GET 401/302 对 GET 404 证伪过中间件
- [ ] 未把写方法全局 401 算高危未授权
- [ ] 短主题词有上限；不中已停并换格子
