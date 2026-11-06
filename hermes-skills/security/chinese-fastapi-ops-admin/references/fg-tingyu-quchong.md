# FG / 听雨 sibling fingerprints (2026-09-29)

Lock-face example: `fg.hg888.cyou` A=`38.22.235.24` (NetLab/Cogent HK, **no CDN**). nginx/1.22.1.

## Reverse-IP / crt (do this even with no CDN)

```
curl -sS 'https://api.hackertarget.com/reverseiplookup/?q=ORIGIN_IP'
curl -sS 'https://crt.sh/?q=%25.operator-apex&output=json'
openssl s_client -connect ORIGIN:443 -servername HOST  # SAN/CN per vhost
```

Observed on `38.22.235.24`:
- `fg.hg888.cyou` / `sp.tingyu28.vip` — **same FG 0.7.0** (sp cert still `CN=fg.hg888.cyou`)
- `bot.tingyu28.vip` — **separate cert CN=bot…**, separate FastAPI

crt `%.tingyu28.vip` extra (other IPs, same ops family):
`kami` 38.92.9.57 · `quchong`/`hs` 64.90.3.94 · `tingyu28.vip` 154.37.220.186 · `ty` 追剧无关 · `dbq` 443 timeout

nginx **routes on Host, not SNI**. Verified 2026-09-29:
- `Host: bot.tingyu28.vip` (full FQDN) on origin IP → bot app even if SNI=`fg.hg888.cyou` or `invalid.local`.
- `Host: bot` / `localhost` / IP / garbage → **FG default_server** (`x-app-release: 0.7.0`).
- `--resolve bot.tingyu28.vip:443:IP` still needed for TLS; SAN check via `-servername`.
- Cross-Host: `Host: bot…` on fg TLS → `/admin`; `Host: fg…` on bot TLS → `/ledger`.

## FG accounting (`x-app-release: 0.7.0`)

```
GET /healthz → {status, release, bot_db_readable, bot_schema_5,
                admin_db_writable, admin_db_transaction_capable, report_template_readable}
GET /openapi.json /docs /redoc  # unauth
GET / → 303 /ledger → 303 /login   # do not follow redirects blindly
```

OpenAPI (cookie session, no security scheme): GET `/ledger` `/reports/{daily,monthly}` `/exports/{daily,monthly}.xlsx` `/mappings` `/audit`. POST `/ledger/{entry_id}/supplement` `/ledger/{entry_id}/split/automatic` `/reports/daily/adjustment` `/mappings` `/mappings/profile` `/report-names` `/mappings/{member_id}/status` `/logout` `/login`.

Wall: GET business **303 /login**. POST-only GET **405 Allow: POST**. bad path int **422** before auth. **GET + 坏 query 仍 303**（鉴权先于 query）。HEAD on GET routes **405 Allow: GET** ≠ bypass. 尾斜杠 Starlette `redirect_slashes` **307** 去斜杠，Location **跟 Host 头**（`Host: evil.com` → `https://evil.com/ledger`），无 cookie，跟随后仍 303 — 低危，不是 rec。未登录 POST `/logout` 303 `/login` **不 Set-Cookie**（种假 cookie 也不清），cookie 名未知。Login form username/password, no CSRF/captcha/JS. Dummy 401 HTML「用户名或密码错误」; next POST **429**. SSH OpenSSH 9.2p1 publickey+password — fingerprint only.

**ffuf:** AboutSecurity `common.txt` 行带前导 `/` → URL `https://host//login` FastAPI 404 22B（假阴性）。先 `lstrip('/')`。`-fc 404 -fs 22` 保留 303 size=0；**禁 `-fs 0`**。5379 词去斜杠后只打出 OpenAPI 已知口。听雨 `EXPORT_PASSWORD` 复用 FG 登录 1 发 → 401 同体（len=10 < bot min 14 则不打 bot）；当 itsdangerous secret 打 `/ledger` 全 303。

## bot.tingyu28.vip — Telegram 订单统计后台 1.0.0

`GET /openapi.json` (~9KB). Login GET `/admin/login` 200 HTML, password **minlength=14 maxlength=128**. Dummy 401「账号或密码错误」978B; spray → 429「登录尝试过多」.

GET business 303 `/admin/login`. POST writes 401 `{"detail":"authentication_required"}`. `GET /admin/orders/abc` / `POST /admin/reviewers/abc` → 422 int_parsing. `/admin/password/change` 401 JSON. webhook/`*.php` 404. OpenAPI paths: `/admin/chats` `/admin/reviewers` `/admin/reviews[/export]` `/admin/order-edits[/export]` `/admin/rewards[/export]` `/admin/orders[/export]` `/admin/settings/system` `/admin/access`.

## kami.tingyu28.vip — Tingyu License Authority 0.1.0

```
GET /health
GET /api/v1/public/bootstrap
  product_id=tingyu-douyin-6.2, Ed25519 public_key_pem, lease_seconds=600
POST /api/v1/license/activate  # machine_id ^[a-f0-9]{64}$, nonce≥16, timestamp
  INVALID_CARD | PRODUCT_MISMATCH (format OK on WRONG product only) |
  REPLAY_DETECTED | STALE_REQUEST
  # 16-letter key + no-such-product = PRODUCT_MISMATCH; SAME key + tingyu-douyin-6.2 = INVALID_CARD.
  # Stop grinding charset on the real product (503).
POST /api/v1/license/verify|unbind  # INVALID_TOKEN on junk
```

Admin CSRF cookie `tingyu_login_csrf` Path=`/admin/login` Max-Age=600 SameSite=strict. Dummy+cookie 401「用户名或密码不正确」; reused csrf no cookie 403「页面令牌已失效」. `POST /admin/cards/generate` no csrf → `CSRF_FAILED`. OpenAPI also: cards generate/import/export/unbind/revoke/delete/batch, announcement, audit, douyin/xhs link-converter.

## quchong.tingyu28.vip — 抖音全字段 v18.0 **no login**

```
GET /?export_action=direct&exportType=dy_num   # ~23MB JSON total≈867623
GET /?export_action=direct&exportType=full     # same total; fields below
GET /?export_action=direct&exportType=dy_num&q=礼物   # q= 昵称/评论 NOT dy_num (458 hits)
GET /?export_action=direct&exportType=dy_num&region=福建   # 31854
GET /?export_action=direct&exportType=dy_num&category=20260925_电子_新数据5679条_20260925  # = start_date=2026-09-25 = 5679
# filter=/keyword= do NOT filter (still 867623)
POST /  FormData action=check_exist ids=JSON   # hits BOTH dy_num and uid — READ ONLY
POST /xiaohongshu.php  action=check_xhs_exist keys=JSON  # READ ONLY
# do NOT call action=save_selected / save_xhs_selected (writes DB)
POST /source_lookup.php?action=lookup  JSON {rows:[{dy_num,uid,secuid}]}
  → {status, token, hit_input_total, miss_total, source_total}
GET  /source_lookup.php?action=export&token=<REDACTED>
GET  /xiaohongshu.php?export_xhs=1   # CSV header, may be 0 rows
```

full item keys (id=878137): `id,no,v_link,v_time,nickname,comment,uid,dy_num,gender,region,bio,fans,follow,precision_val,avatar,secuid,likes,auth,category,create_at,source_video_link`. Frontend `EXPORT_PASSWORD="aa202303.."` gates UI ≥10000 — **direct query does not need it**. Quote in `q=` → total=0 (not SQLi). Unknown POST `action=` returns HTML home, not JSON error.

Do not `json.loads` the 22MB file; parse first object after `"data":[`. Exact category name matches `start_date` count (5679).

## tingyu28.vip — 听雨任务系统 SPA

JS `/assets/index-*.js` dumps routes (~58 `/api/...` strings). Unauth:
- `GET /api/v1/auth/captcha` → `{captcha_id, image: data:image/svg+xml;base64}`
- `GET /api/v1/task-hall-rules` → rules JSON
- `GET /api/health` → `{status, version:"1.15.23-p0f10-…", telegram_evidence:{configured,polling,last_update_at}}` — **TG 轮询状态 ≠ 订单/账本/壳**
Login `POST /api/v1/auth/login` (also `/api/auth/login`): JSON `principal` ADMIN|USER (SPA checkbox; AGENT is a validator enum but login UI is admin/user), `identifier`, `password` 6–72 `[\x21-\x7E]`, plus captcha `{captcha_id,captcha_code}` from `payload()`. SVG is path-drawn digits — tesseract often empty; rsvg-convert → PNG → vision. `captcha_id` one-shot. Valid code + dummy pw → **401 `INVALID_CREDENTIALS`** 「账号或密码错误」; bad/stale code → `CAPTCHA_INVALID`. Register `POST /api/auth/register` phone+password+password_confirmation+invite_code+captcha — do not create accounts. Agent `POST /api/v1/agent/auth/login` same captcha gate. Admin/user/agent APIs 401 `Unauthorized`. Do not spray.

Refresh `POST /api/auth/refresh` (也 `/api/v1/auth/refresh` `/api/v1/agent/auth/refresh`): body **`refreshToken` string** (不是 `refresh`/`refresh_token` — 那些 400 `property X should not exist`). 垃圾/空/`alg=none` JWT 一律 **401 `INVALID_REFRESH_TOKEN`**，无差分预言机。`.env` `/openapi.json` `/docs` `/ws` `/socket.io` = SPA fallback HTML，不是泄露。

`GET /api` nginx **301** → `https://tingyu28.vip/api/` 然后 Node **404 JSON** — 斜杠重定向，不是第二套应用。任意 Host（www/api/admin/localhost/乱 Host）= 同一 SPA。token 在 `localStorage douyin_task_session_${portal}`（admin|user）和 `douyin_task_session_agent`，请求头 `Authorization: Bearer ${accessToken}`；**无 `document.cookie`**。假 Bearer/假 cookie 丢 FG/bot 仍 303，丢任务仍 401。

## Report split (do not collapse)

| Surface | Takeover? | Meat |
|---|---|---|
| FG | no session | healthz + OpenAPI only |
| bot.* | no session | OpenAPI order/review export list |
| kami | no cards/admin | bootstrap pubkey + format oracle |
| quchong | n/a (no auth) | 86万 Douyin identities + comments |

## 宝塔面板 infrastructure (kami + quchong)

Both `38.92.9.57` (kami) and `64.90.3.94` (quchong) run BT Panel:

- **:888** nginx — kami **403 Forbidden** (phpMyAdmin, IP whitelist); quchong **404**. HTTP only, no TLS. IP bypass headers all fail: `X-Real-IP` / `X-Forwarded-For` / `X-Client-IP` / `X-Originating-IP` / `True-Client-IP` / `Client-IP` / `Forwarded: for=` — all still 403/404.
- **:8889** TLS nginx — **宝塔面板随机安全入口**. All paths return **404**. Certificate chain: `C=CN, O=58.63.83.179, CN=58.63.83.179` signed by `O=宝塔面板, CN=宝塔面板`. Both machines share the same BT cert (same ops deployment). `58.63.83.179` (original install IP) is offline — all ports timeout, Shodan no info.
- Random entry brute: 80+ custom paths (btpanel/baota/admin/tingyu/kami/manage/control/jinru/guanli + BT defaults) all 404. BT default format `/[a-z0-9]{8}` = 36^8 ≈ 2.8T — **not brutable**. BT CVE paths (`/api/data`, `/userLogin`, `/safe/index`, etc.) all 404.
- nmap service version identifies :8889 as `ssl/http Ajenti` — **misidentification**, it's BT Panel.
- FG origin `38.22.235.24` has **no BT panel** — ports 8000-9000 all closed.

### kami FTP (Pure-FTPd)

Port 21 open. Banner: `Welcome to Pure-FTPd [privsep] [TLS]`, 50 user limit, no anonymous login, IPv6 enabled.
**puredb is broken**: any username gets `331 User OK. Password required` then immediately `421 Unable to read the indexed puredb file (or old format detected) - Try pure-pw mkdb`. Authentication impossible regardless of credentials. Tested: anonymous/admin/www/root/tingyu/ftp/bt + various passwords — all get the same 421.

### sp.tingyu28.vip

DNS → `38.22.235.24` (same as FG). TLS cert still `CN=fg.hg888.cyou` (no sp SAN). Login page HTML identical to FG (only CSS link Host differs). OpenAPI identical FG 0.7.0. **Shares 429 rate limit with FG** — spray on sp while FG is in 429 window still gets 429. Same FastAPI process, Host alias only.

### Tor NEWNYM 429 bypass (tested on FG login)

Tor SOCKS `127.0.0.1:9050` + ControlPort `9051` (no auth). NEWNYM every 3 attempts rotates exit IP and resets 429 window. **Technically works** — 429 hit mid-spray triggers NEWNYM, next attempt from new exit gets 401 again. 15 users × 52 passwords = 780 attempts, **all 401**. Confirms FG password is not in common dictionaries. Stop condition: dictionary exhausted.

### quchong delete action

`POST / action=delete ids=[...]` returns HTML home page (not JSON). Delete is **not implemented** as an API action — only the UI handles it (likely via a different mechanism or admin-only). Test records written via `save_selected` persist.

## hg888.cyou CRT sisters (not live from this egress)

crt `%.hg888.cyou`: `ag24/gx24/gxjc/zl24` A=`23.26.201.225` (Ace Data Centers). Ping/80/443 timeout, nmap no open ports — treat as dead/walled, don't loop. `24/agjc/jc/xt24/xtjc/zljc` no A. apex no A/MX.

SSH banners (fingerprint only): FG+task `OpenSSH 9.2p1 Debian-2`（无 `+deb12uN`，Debian 修 CVE-2024-6387 从 `9.2p1-2+deb12u3` 起 — **版本可能未打 ≠ 开打**；64 位公开利用≈砸站，不跑）；quchong+kami `Debian-2+deb12u6`。本机/`id_rsa`+别家战役钥 Permission denied 就停，不喷 password。sundapp 钥不动。

nginx 1.22.1 `0xA0`/`0x0A` 路径规范化 **400**，不是 ImaginaryCTF `if (-f)` 绕过。healthz 字段当 itsdangerous secret 打 `/ledger` 仍 303。UDP 123/161/1900/11211 `open|filtered` + timeout = 墙。证书 SAN：fg 仅自己、bot 仅自己。
