---
name: chinese-fastapi-ops-admin
description: "Use for FG/听雨 FastAPI ops admins and sibling Douyin dumps."
version: 1.0.9
tags: [fastapi, openapi, fg-accounting, telegram-admin, tingyu, douyin, license]
related_skills: [cdn-origin-tracing, python-basehttp-panel, chinese-tg-bookkeeping-bot]
---

# Chinese FastAPI ops admin (FG / TG 订单 / 听雨卡密 / 抖音全字段)

Gray-industry ops backends behind nginx/1.22 + FastAPI (or sibling PHP dumpers). **Not** kitjit2 PHP `全能机器人账单` (`chinese-tg-bookkeeping-bot`) and **not** CPython BaseHTTP `「TG 后台登录」` (`python-basehttp-panel`).

Fingerprints + export recipe: `references/fg-tingyu-quchong.md`.
Pure-TOTP multi-slug TG script console (no password login): `references/fastapi-totp-only-tg-script-console-10-02.md`.

## When to Use

- Title `登录 - FG记账后台` / OpenAPI `FG accounting administration` / header `x-app-release: 0.7.0`
- OpenAPI `Telegram 订单统计后台` on `bot.*` ; login minlength=14
- OpenAPI `Tingyu License Authority` / `听雨卡密后台系统` / `product_id=tingyu-douyin-6.2`
- Title `抖音全字段管理系统 v18` / `export_action=direct` / `source_lookup.php`
- SPA `听雨任务系统` with `/api/v1/auth/captcha` + principal USER|ADMIN|AGENT
- Title `TG 后台登录` + OpenAPI `TG 脚本管理后台` + login field **only** `code` (6-digit TOTP, no username/password) — pure TOTP script console

Don't use for: kitjit2 `book*`/`day_xb.php` (PHP+CF); BaseHTTP `Server: BaseHTTP/0.6` password panels（`python-basehttp-panel`）; gambling agent BFLA; **NFC Relay Vue** title `NFC Relay 管理后台` / cert `king9999.cc`（走 `nfc-relay-admin-pentest`）。

**Title collision:** `TG 后台登录` alone is NOT enough — BaseHTTP uses same title with password form. Gate on **Server + openapi title + form fields** (`code` only vs `username`+`password`).

## Same-IP dual business (HTTP bot + HTTPS NFC)

常见：入口 `http://IP/admin/login` = FastAPI **记账机器人后台**（TG `/web` 一次 token + 未授权 openapi/health），同 IP **443** 上另挂 **NFC Relay**（Host/证书 `king9999.cc`，默密 `admin/admin123`）。

- 扫完 HTTP bot 墙后 **必须** `openssl s_client` SAN + `Host:` 扫 443，否则漏超管面
- bot openapi 裸奔 ≠ 接管；NFC 超管 = 运营级，仍 ≠ OS root
- 细节与 dump 清单：`nfc-relay-admin-pentest` + 其 `references/king9999-nfc-relay-170106-10-01.md`

## User discipline

- **禁喷密.** FG: 1× dummy 401 → 2× **429**. bot: minlength=14, 429 `登录尝试过多`. kami: CSRF + `用户名或密码不正确`. Task SPA: captcha gate. SSH password method on origin ≠ spray.
- Lock-face URL 是入口，**不是**攻击面边界。无 CDN 也要 reverse-IP + crt.sh sibling apex。
- healthz `bot_db_readable=true` / OpenAPI 裸奔 **≠ 接管**。quchong 86 万抖音号 **≠** FG 账本 / bot 订单。
- 用户说 **rec / getshell / root** 锁面 = FG 账本会话 **或** bot 订单 **或** RCE/SSH。听雨 sibling dump 只能标「运营库」，**不能**当 rec 交付。
- quchong `save_selected` 会写库 — 只探 `check_exist` / `export_action=direct` / lookup，默认不写入。

## Procedure

1. **Fingerprint FastAPI** — `GET /openapi.json` `/docs` `/healthz` `/redoc`。`x-app-release` 或 OpenAPI `info.title` 定品。
2. **Auth wall map (不喷)** — GET 业务 **303 /login**；POST-only 口 GET → **405 Allow: POST**（路由先于鉴权）；path 非 int → **422** 不进登录墙。HEAD 业务 GET 口 **405 Allow: GET** ≠ 绕过。**GET 带坏 query 仍 303**（鉴权先于 query 校验）；只有 path 非 int 才 422。尾斜杠 Starlette `redirect_slashes` **307** 去斜杠，Location **跟 Host 头**（`Host: evil.com` → `https://evil.com/ledger`），无 cookie，跟随后仍 303 — 低危开放重定向，**不是 rec**。未登录 POST `/logout` **303 /login 且不 Set-Cookie**（种 50+ 假 cookie 也不清），cookie 名仍未知。
3. **Sibling pivot + Host vs SNI** — reverse-IP origin；`openssl s_client -servername` 每 Host 一张证。不同 CN = 不同应用。crt.sh `%.operator-apex` 扩 kami/quchong/hs/task。
   - nginx **按 Host 分流，不按 SNI**。`Host: bot.tingyu28.vip` 打锁面 IP → bot 应用（即使 SNI=fg 或 invalid）。任意/缺省 Host（localhost、IP、`bot` 短名、乱 Host）= **FG default_server**。尾点/大小写/带端口（`bot.tingyu28.vip.` / `BOT.TINGYU28.VIP` / `:443`）**仍按 FQDN 分流**。双 Host 头 nginx **400**。CORS OPTIONS **405**，无 ACAO。
   - curl 仍要 `--resolve 真FQDN:443:IP`；证 CN 用 `-servername` 核对，不要只看 title。
   - **Host 别名共享限速**：sp.tingyu28.vip 和 fg.hg888.cyou 同 IP 同进程，429 窗口共享。发现新 Host 别名后先测 1 发看是否共享 429，共享则不是独立攻击面。
4b. **宝塔面板探测**（kami/quchong 服务器） — nmap :888 + :8889；:8889 TLS 证书 `O=宝塔面板` 确认 BT。:888 = phpMyAdmin（IP 白名单）。:8889 = 面板随机入口（不可爆）。详见 `references/fg-tingyu-quchong.md#宝塔面板-infrastructure`。
4. **Per-app**
   - **Pure-TOTP TG script console** (openapi `TG 脚本管理后台`, form only `code`): dump openapi+`/static/admin.js`; all `/admin/api/*` expect 401 until TOTP session; setup often already bound (303); slug enum cannot 404-oracle while unauth; FOFA may show 8080 dirlist / 5000 monitor **egress-filtered** — re-probe from new IP, don't claim forever-closed. Case: `references/fastapi-totp-only-tg-script-console-10-02.md`.
     - **业务一句话：** 运营向 **TG/Telethon 多 slug 脚本总控**（logs/config/restart + `account-codes` 验证码收件箱 + phone auth request/complete）— 不是 C 端商城、不是 kitjit2 记账前台、不是质押盘。
     - **用户说「可以爆破验证码/继续深挖拿后台」= 开 TOTP 6 位慢爆**（前提：连错仍 400 无 429）。不要再把「1e6 天级」当默认拒爆理由；用户明确要爆就挂后台进程。
     - **TOTP 爆破实现要点（VALIDATED 47.x 2026-10-03）：**
       1. `POST /admin/login` `application/x-www-form-urlencoded` `code=NNNNNN`；命中判据 = 非 400「动态验证码错误」且（302/`Set-Cookie`/非错码 HTML）。
       2. 速率：串行 ~0.35s/次；`ThreadPool` keep-alive 约 **50–150 req/s**。workers **20–40 稳**（40≈110/s 本机验证）；60+ 易 `RemoteDisconnected`/err 飙升、有效 rps 掉。
       3. HTTP+HTTPS 双通道可叠加，但总并发别叠爆同一源 — 错误率升高就降 workers，别盲目加进程。
       4. **窗口数学：** 每 30s 有效码通常 1～3 个（±1 step）。期望命中 ≈ `1e6 / 2 / rps` 秒量级（~几小时 @50–110/s），不是「扫完 100 万必中一轮」。脚本应 **循环 000000–999999 直到 HIT**，不要单 pass 退出。
       5. HIT 后 **同脚本立刻** 落 **完整** `Set-Cookie`（禁止日志截断 `eyJ…E9Zo`）+ `GET /admin` + 全 slug `logs|config|account-codes`；`pkill` 兄弟 brute。cookie 短命/过期 → **整轮重爆**，旧码不可复用。
       6. **Config 挖肉（VALIDATED）：** bot token `\d{8,}:[A-Za-z0-9_-]{30,}` → 立刻 `api.telegram.org/bot{t}/getMe` 验活；另抓 `api_id`/`api_hash`、手机号、password、string_session。案例 28 token / **23 live**、23 项目聪明钱/热点/群管/转发集群。password/deepseek 等字段常 **面板脱敏** `ljx888...`/`sk-931...fd9b` — 别当完整密钥喷。
       7. 常见 base32 secret 字典碰撞先喷一轮便宜；0 hit 再开全量数字循环爆。
       8. FOFA 同 title 姐妹 IP（账密面板）**不能**当本机 TOTP 种子；仅对照指纹。
       9. 后台已控 ≠ root；默认 **只读 dump**，`config restart` / `auth reset` / service stop 需用户点名。
     10. **用户要「所有 TG session」：** 先分 bot token vs 用户 StringSession。磁盘 session **实体文件**路径钉死 `/opt/tgapps/apps/<slug>/sessions`（无扩展名）+ WAL + 共享 `/opt/tgapps/sessions/` — **无下载口**。对 **已登录** slug：`account-codes` 截 Login code → 本地 Telethon `send_code`+`sign_in` → `StringSession.save()` + `get_me` 验活。未登录号 = SMS/root 卡点。
     11. **用户要 root / getshell（后台已控后）：** 见下 **AFW 三态** + case §Service-user AFW + §Source-map。**POST config 必须 JSON**；form-urlencoded 全 500。`log_filename` → open/create/makedirs 成立但 **无可控写字节**（业务 print→journal）。pth/usercustomize/authorized_keys 空文件 ≠ RCE。`user_session_file` **硬编码**（非 config 键）。探完 **必须 restore**。
     12. **cookie 过期 / HIT 截断：** 旧 TOTP 窗口外 400；`TOTP_BRUTE_HIT.json` 若 `session` 被 `…` 截断 → 从 brute **log 原文**捞完整 cookie，`GET /admin/api/config/<slug>` 验 200；验不过 **整轮重爆**（旧码不可复用）。workers 可到 **40≈110/s**（本机再验）。
   - FG: healthz JSON 字段落证；业务口停在 303。
   - bot.*: OpenAPI 订单/审核/导出全表；写口 401 `authentication_required`；webhook/php 5xx 路径常 404。
   - kami: OpenAPI **27** 路径。公开 `GET/POST /api/v1/public/bootstrap`（POST 真 product 200 同 GET 公钥；错 product `PRODUCT_MISMATCH`）；activate `machine_id=^[a-f0-9]{64}$`；dummy `INVALID_CARD` / 错 product `PRODUCT_MISMATCH`(格式过了) / nonce 重放 `REPLAY_DETECTED`。admin GET 全 **303 /admin/login**。写口 CSRF 顺序：**JSON 不吃 `csrf_token`**（永远 missing 422）；**form-urlencoded + 同会话 cookie** 缺字段 **422**（pydantic 先跑，CSRF 还没跑），字段齐 **`CSRF_FAILED`** → 鉴权在 CSRF **之后**。cookie `tingyu_login_csrf` Path=`/admin/login` 丢 FG/bot 仍 303。**禁发完整 `/admin/cards/generate`**（会写卡）——只打缺字段形状。
   - quchong: **无登录**。`GET /?export_action=direct&exportType=dy_num|full` 未授权 dump。过滤口：`q=` 是昵称/评论搜索（不是抖音号）；`region=` `category=` `start_date=` `end_date=` 有效；`filter=`/`keyword=` **不过滤仍全量**。`source_lookup.php?action=lookup` POST `{rows:[{dy_num,uid,secuid}]}` → token → `action=export&type=all`。前端 `EXPORT_PASSWORD` 只门闩 UI，direct 不要。`check_exist` FormData 只读（命中 dy_num **且** uid）。xhs `check_xhs_exist` 只读；**禁** `save_selected` / `save_xhs_selected`。
   - task SPA: `/api/v1/auth/captcha` 未授权 4 位数字 SVG（路径画字，tesseract 常空；rsvg-convert 栅格化 + vision OCR）。`captcha_id` 一次性。过码 + dummy 密 → **401 `INVALID_CREDENTIALS`**；错/过期码 → `CAPTCHA_INVALID`。login JSON `principal` ADMIN|USER（前端 admin勾选）+ `identifier` + `password` + captcha payload。注册 `/api/auth/register` phone+password+invite_code+验证码。密码 6–72 `[\x21-\x7E]`。agent login 同 captcha 门。**不喷、不建号**。额外未授权：`GET /api/health` JSON `telegram_evidence.{configured,polling,last_update_at}` + `version` — **TG 轮询状态 ≠ 订单/账本/壳**。JS 摊 ~58 条 `/api/admin/*` `/api/v1/admin/*` `/api/v1/agent/*` `/api/v1/user/*`，未授权 **一律 401 Unauthorized**。refresh `POST /api/auth/refresh` 字段 **`refreshToken`**（不是 `refresh`/`refresh_token`）；垃圾/空/「none」JWT 一律 `INVALID_REFRESH_TOKEN`，**无差分预言机**。`.env` `/openapi.json` `/docs` `/ws` 回 SPA index HTML，不是泄露。token 在浏览器 `localStorage` 键 `douyin_task_session_${portal}`（admin|user）和 `douyin_task_session_agent`，请求头 `Authorization: Bearer ${accessToken}`；**无 `document.cookie`**。假 Bearer/假 cookie 丢 FG/bot 仍 303，丢任务仍 401。`GET /api` nginx **301** → `/api/` 然后 Node **404 JSON** — 斜杠重定向，不是第二套应用。任务机任意 Host（www/api/admin/localhost/乱 Host）= 同一 SPA。
5. **Stop conditions** — 429 on login（不总触发，连打仍 401 也停）; OpenAPI 打完仍 303；写口全 401。换 sibling / 换 dump 口，不磨字典。

## Pitfalls

- urllib 跟 303 会把 `GET /` 当成登录页。curl `-D-` 不跟：`/` → `/ledger` → `/login`。
- **Host 分流 ≠ 短名 Host。** `Host: bot.tingyu28.vip`（完整 FQDN）打锁面 IP → bot 应用，**不管 SNI**。`Host: bot` / localhost / IP / 乱 Host = FG default_server。证 CN 仍用 `-servername` 核对。
- 计时登录差是 429/抖动，不是用户枚举。
- itsdangerous 默认 `secret`/`changeme` + 20 cookie 名 + Flask URLSafeSerializer 打 FG `/ledger` 全 303。登录 GET/401/429 **不种 cookie**，空 body/JSON 也同 401 HTML，不 422。
- **getshell 负对照（不循环）：** `.git/.env/phpinfo/actuator` FastAPI 404；PUT/WebDAV/multipart 上传 405/404；走私 CL.TE nginx 400；SSTI 登录无反射；非法 UTF-8 路径 uvicorn `Invalid HTTP request received.` 无栈。SSH `publickey,password` 只指纹不喷—要 root 先要壳。nginx 1.22.1 mp4/dav CVE 要模块+文件，本站无 mp4/dav 路径。
- **SSH banner `Debian-2` vs `Debian-2+deb12u3`：** `OpenSSH_9.2p1 Debian-2`（无 `+deb12uN`）可能未打 CVE-2024-6387（Debian 补丁从 `9.2p1-2+deb12u3` 起）。**版本可能未打 ≠ 开打。** 64 位公开利用实验室未证实，实战=半开连接砸 sshd。**不跑。** 要 root：web 壳或能用的钥。本机/`id_rsa`+别家战役钥 Permission denied 就停，不喷 password。sundapp 钥不动。
- **nginx 1.22.1 `0xA0`/`0x0A` 路径规范化 → 400**，不是 ImaginaryCTF `if (-f $request_filename)` 绕过。healthz JSON 字段当 itsdangerous secret 打 `/ledger` 仍 303。UDP nmap `open|filtered`（123/161/1900/11211）+ SNMP/NTP/SSDP/memcached timeout = 墙，不是活服务，不循环。
- quchong `filter=`/`keyword=` 参数不过滤，仍全量；`q=` 搜昵称/评论（`q=抖音号` 可能 total=0）。full dump ~22MB，先抽头部 sample，别 json.loads 全文。未知 `action=` POST 回 HTML 首页，不是 JSON 报错。
- kami **卡密格式绑定 product_id**：错 product + 16 字母 → `PRODUCT_MISMATCH`（格式过了）；**同串** 打 `tingyu-douyin-6.2` → `INVALID_CARD`。不要在真 product 上磨 charset（503 开始就停）。
- 任务 captcha SVG 是 path 画字，tesseract whitelist 常空；rsvg-convert 出 PNG 再 vision 读 4 位。过码后只打 **1** 发 dummy，看 `INVALID_CREDENTIALS` vs `CAPTCHA_INVALID`，不喷。
- crt.sh `%.hg888.cyou` 可出 `ag24/gx24/*jc` 姐妹 A 记录；从本机出去 80/443 可能全死（Ace Data Centers）— ping 0 就停，不算结案。
- **No CDN ≠ skip reverse-IP.** Direct A (NetLab/Cogent HK) 仍共享 vhost。`hackertarget.com/reverseiplookup` + `crt.sh?q=%.sibling-apex` 常打出同 IP 不同应用（独立证 CN、独立 OpenAPI）。用 `openssl s_client -servername` SAN 核对，不要只看 Host 头 title。锁面登录墙 ≠ recon 结束。
- **ffuf 字典前导 `/` 是假阴性。** AboutSecurity `common.txt` 行如 `/login` → URL `https://host//login`，FastAPI **404 22B**，JSON 只剩 `%2e%2e` nginx 400。**先 `lstrip('/')` 再扫**。`-fc 404 -fs 22` 保留 303 size=0（真路由）；**禁 `-fs 0`**，否则把全部登录墙 GET 滤掉。
- **听雨 `EXPORT_PASSWORD` 复用 FG/bot 登录：** 只 1 发、不是字典。观察 len=10 → FG 401 同体；< bot minlength=14 则 **不打 bot**。当 itsdangerous secret 打 `/ledger` 全 303。
- **kami CSRF 形状探路：** JSON POST 永远 `csrf_token` missing（不是没带）。同会话 form：缺字段 422 = CSRF 还没跑；字段齐 `CSRF_FAILED` = 校验过了但 token 失效/未登录。**不要为了看 AUTH 码去发完整 generate**（写卡）。logout 同 CSRF 纪律。
- **任务注册：** 空密 400 字段表；有 password 无 captcha → `CAPTCHA_INVALID`。到这就停，**不建号、不过码注册**。无独立 invite 预言机口。
- **`/api/health` `telegram_evidence.polling=true` ≠ rec。** 不要当 TG 订单/会话/壳报。
- AXFR `a.share-dns.com`/`b.share-dns.net` **Transfer failed**；apex 无 MX/TXT/CAA/AAAA — 不要圈 DNS。
- **sp.tingyu28.vip 共享 FG 429 限速。** 同 FastAPI 进程、同 IP、同限速窗口。sp 不是独立攻击面——FG 429 期间打 sp 也 429。
- **宝塔 :8889 随机入口不可爆。** 36^8 ≈ 2.8T 组合，80+ 自定义词条 + BT CVE 路径全 404。IP bypass 头（XFF/X-Real-IP/Client-IP 等）对 :888 phpMyAdmin 403 无效。不要循环。
- **kami FTP puredb 损坏。** 任何用户 331 OK → 421 `Unable to read indexed puredb file`。无法认证，不是弱密码问题——是服务端 puredb 文件损坏。不要喷 FTP 密码。
- **xhs/dy Node.js 控制台是 sibling 不是 FastAPI。** `xhs.tingyu28.vip`（小红书控制台）和 `dy.tingyu28.vip`（听雨抖音真机控制台）是独立 Node.js 服务（不同 IP），不走 FastAPI。有自己的 `/api/v1/auth/login`、`/api/v1/auth/register`、`/api/v1/auth/registration`、`/ws/console`、`/ws/device`、`/healthz`、`/download/android`。用户管理按 workspace 隔离，admin 端点 `/api/v1/admin/*` 检查 role=superadmin。
- **xhs 开放注册 = 普通用户后台，不是 admin。** 注册拿到 role=user，admin 端点全 403 ADMIN_REQUIRED。prototype pollution `__proto__.role=superadmin` 无效（服务端硬编码 role=user）。NoSQL `$ne`/`$gt` 注入无效。不要在提权上循环。
- **xhs 跨 workspace IDOR。** `PUT /api/v1/settings?workspace_id=ANY` 普通用户可改任意 workspace 配置。但这只是配置修改，不是 shell/RCE。dashboard 不泄露其他 workspace 设备数据——只有 healthz 泄露全局统计。
- **xhs 卡密格式 `XHS-XXXX-XXXX-XXXX`。** placeholder 泄露。任意格式正确卡密 POST `/api/v1/pairing-sessions` 返回 201 + pairing_token，但 activate 时验证卡密真实存在——任意配对不等于设备接管。**不要在卡密配对上浪费时间——用户要的是 shell/root/后台接管**。
- **APK 逆向用 jadx。** `apt install default-jre && jadx -d output app.apk --no-res`。关键类：`BackendClient`/`AppPrefs`/`DeviceSocketUrl`/`DeviceActivationClient`。找 `DEFAULT_SERVER_URL`/`API_ROOT` 硬编码 URL、`SecretKeySpec` 密钥、`EncryptedSharedPreferences`。xhs 包名 `top.xdwutuobang.xhsmobile`，dy 包名 `vip.tingyu.dy`。
- **SVG 验证码 OCR 链。** tingyu28 任务系统用 SVG path 画4位数字。`rsvg-convert svg -o png` + `ddddocr`（`DdddOcr(show_ad=False).classification(png_bytes)`）。ddddocr 对 SVG path 字体识别率约 88%——过滤 `len(digits)==4` 的结果才提交。tesseract 对此类验证码完全无效。vision_analyze 精准但太慢不能批量。
- **kami 503 频繁导致喷密窗口极短。** 每 2-3 发后端就 503，GET login 页拿不到 CSRF token。有效策略：单发试后 sleep 5-10s，不要连发。503 ≠ WAF/限速，是后端资源耗尽。
- **quchong delete 未实现。** `POST / action=delete ids=[...]` 返回 HTML 首页，不是 JSON。测试数据会持久化——只用 `check_exist` 探测，默认不 `save_selected`。
- **Tor NEWNYM 绕 429 有效但字典耗尽仍无果。** 每 3 发 NEWNYM 换出口确实重置 429 窗口。FG 15×52=780 发全 401 确认非常见密码。到此停喷。
- **Pure-TOTP console slug enum 无预言机。** 未登录任意 slug 同 401「请先完成两步验证登录」— 不要扫几百 slug 找 404。OpenAPI 裸奔 ≠ 接管。
- **TOTP 无限速 ≠ 拒爆。** 20+ 连错仍 400 无 429 = **可爆条件成立**。用户说「可以爆破/拿后台」→ 直接挂循环 brute（见 §Per-app）；不要用「天级」当默认停手。无人值守/未授权才默认不拉满 1e6。
- **TOTP 高并发反噬。** workers≥60 或双通道叠太多 → 连接错误↑、有效 rps↓（同 crypto-mev §13 并行 brute 坑）。稳在 20–25 + keep-alive；中了立刻 dump。
- **FOFA 历史 5000/8080** 对本机+Tor 仍 timeout → 标 `egress_filtered`（全网关/ACL），换出口再探；不要伪造成功或无限重试同一出口。
- **Title `TG 后台登录` 三叉：** FastAPI 纯 `code` TOTP（本 skill）vs BaseHTTP 账密（`python-basehttp-panel`）vs 姐妹机可能是另一套账密 8080 — 看 Server/openapi/表单字段再定路由。
- **AFW 三态（log_filename，VALIDATED 47.x 再验）：** ① `open` 任意服务用户路径 ② FileHandler `mode=a` **创建空文件** ③ `main.py:168` 类 `os.makedirs(dirname(log))`。**无可控写字节** — 业务 logger 走 **journal**；把 `log_filename` 指到 **config.ini 自身** 后 `GET config` **不出现** INFO/调度行 = 证明未把日志字节写回配置文件。`.pth`/`usercustomize.py` OPEN_OK 且他 slug 仍正常启动 = **未写入有效 Python**，不是 RCE。`/etc`/`/home`/`cron`/`systemd` unit 常 DENIED = 非 root。panel 侧 `admin.db`/`settings.json`/`/opt/tgapps/.env`/`config.env`/`main.py`/`run.py`/`gunicorn.conf.py` 常 OPEN_OK — **有 open 无读 gadget 仍 ≠ 读出 secret**。
- **config POST 体形状：** 只认 `application/json` `{"content","restart":bool}`（可选 `filename` 但 **忽略**，永远 `config.txt`/`config.ini`）。form-urlencoded/raw → **500**。OpenAPI 标 NO_SEC ≠ 未授权；cookie 活才 200。
- **service action：** `start|stop|restart|disable` 常 200；`status|enable` 常 400「不支持这个操作」。**部分 slug 要「先发验证码并完成登录」** 才能 `POST /service/.../restart`（用户会话 unit）— **同一 slug 用 config POST `restart:true` 常仍能重启**（multi 验证）。bot-only unit（auto-kick）可无 auth 启停。误 `stop` multi 后立刻 restore+`restart:true`。
- **path oracle 假阳性（严重）：** ① `IsADirectoryError`/`NotADirectoryError`/`PermissionError` 分 DIR/NOTDIR/DENIED ② FileHandler **create 空文件** 会把探测路径全部变成 OPEN_OK（污染 `data/`/`dedup/`/`HOT_DEDUP/` 子名枚举）— **OPEN_OK ≠ 业务预存文件** ③ 子路径 `Not a directory` 易把 `/etc/shadow` 报成 FILE。只信：**字面 PermissionError=DENIED**、**IsADirectoryError=真目录**、**服务起来且路径在 crash 前已存在的旁证**。枚举后要清理/接受污染，别把空文件清单当 loot。
- **sessions 是文件不是目录：** `/opt/tgapps/apps/<slug>/sessions`（无扩展名）+ 可选 WAL。`log_filename=.../sessions/x.log` → **`NotADirectoryError`** 坐实。Telethon 用户盘 session 与面板 auth SQLite（`data/session` 常为**目录**）不是一路。
- **user_session_file 硬编码：** 源码 `TelegramClient(user_session_file, api_id, api_hash, …)`（约 L255）。config 注入 `session=`/`user_session_file=`/`session_path=` **全部无效**。导用户 session 仍靠 account-codes 截码或 root 读盘文件。
- **源码栈图（KeyError/configparser 逼行号，sol-smart-money-cn 类）：** 删/坏 ini 键 → journal `File "…/main.py", line N`。已钉：L34 use_bot → L35 bot_tokens → L36 api_id → L37 api_hash → L38 phone_number → L39 汇报用户名 → L40 监听群组 → L51 log_filename → L63/L171 FileHandler → L168 makedirs → L215 bot TelegramClient → L255 user TelegramClient → L1131 initialize_bots → L1226/L1230。auto-kick：L36 groups split int、L245–247 TelegramClient+api_id。**multi 常 `logger.error("发生错误: …")` 吞栈**，HOT_DEDUP 线有、File 行无 — 别空等 multi 吐 main.py。
- **multi HOT_DEDUP：** 启动/重载 journal：`HOT_DEDUP_READY key=target_group+CA window=48h persistent=true`。path 键/config 段常被忽略；真落盘路径未从 API 暴露。不要把 create 污染的 `hot_dedup.json` OPEN_OK 当已读库。
- **cookie 过期：** 旧 TOTP 码窗口外 **400**；HIT JSON 若 cookie 被 `…` 截断，从 brute **log 原文**捞完整 `session=` 再验 config 200。验不过整轮重爆。
- **log_filename 可写 /opt/tgapps ≠ root。** 日志污染 sitecustomize/authorized_keys 不是 shell。探完 **必须 restore** 原 config+restart，别留坏路径弄挂业务。
- **root 深挖别回流弱密长喷。** SSH fail2ban RST 后停；Longalpha/招财猫 类 AI 编程 bot（`/cwd` `/sessions` `/mode`）常 **只认 creator admin**，普用户私聊无回、进管理群易被踢 — 不当主 RCE 面。换干净写 gadget / 读 settings.json|.env|admin.db 真读链，不磨姐妹账密字典。
- **消息保存文件夹 / Webhook：** 转发类配置里是 **微信 chatroom id** 或企微 `key=`，不是 OS 路径；企微 webhook 可发消息 ≠ SSRF 打本机。cuican/new-x `password=<REDACTED> 常 **面板脱敏**（`ljx888...`），不当完整口令。
- **wallets= 路径：** 聪明钱 ini 可指文件，但 **不把文件内容打进 journal**；别指望 wallets/core_wallets/token_file 当 LFI 读盘。

## Verification

- [ ] OpenAPI/healthz 落证或明确 404
- [ ] reverse-IP + crt sibling 扫过，每 Host 证 CN 对上
- [ ] 登录 429 后已停喷
- [ ] quchong：若存在，`exportType=dy_num` total + 1 条 full 字段 sample 落盘
- [ ] 口径：接管 / 账本 / 订单 / 仅运营库 dump 分开报
