# kitjit2 / juootyi bookkeeping bot — field notes

## Topology
- Admin: `book.kitjit2.com` (book2 / loginz), `book3/book4.kitjit2.com` (CSRF on book3)
- Webhooks: `bot3/1.php`, `bot4/Haoting_bot.php` (vip.php often 404)
- Sister: `book.juootyi.com` / `bot.juootyi.com` same stack
- Oil: `bot.kitjit2.com/10.php` (rotating TRON addrs, multi-million merge), `composer.json` → fenguoz/tron-php
- book2 can be **up** while book4/bot4 are CF **520** — attack book2 in parallel

## Confirmed on 公群1650 (`-1002127346643`)
- Deposit text ~105015U via book3 IDOR `day_xb`
- phpname owner table: **`vip_jzqun`** (also `1_jzqun` exists)
- Haoting_bot can setpass/login as `phpname=vip` but is **not** an in-group usable bot
- Ops results: **未找到可用机器人**
- bot3 private `管理员` → Fatal at `1.php:2575` `BotApi->sendMessage` → TG `ok:false` / Not Found (**dead token**)

## SQLi
- `dayallqun.php?userid=` → reflected into hidden `chat_id`
- `1' XOR 1--` → multi‑MB group listing (2084 pairs dumped)
- EXTRACTVALUE → Warning + `/www/wwwroot/book4.../dayallqun.php` path; XPATH payload echo often missing
- WAF eats many IF/SLEEP/BENCHMARK/UNION variants

## User surface (2026-09-17→18)
- Haoting: live token behavior, qfok/PIN_OK (置顶成功) on several chats; IN_CHAT many (1650 still not in)
- Delivered userids ~370 + groups ~28k (XOR/dayall) — **not** full member roster/chat history
- juoo `dayall.php?chat_id=` unauth → userid= attrs; kit dayall often **without** userid=
- book2 `loginz.php?userid=8263338802` live → **尚未设置完整账单密码** until webhook setpass (**卡 bot4**)
- HAS_PASS×3: `849646483` / `5977223769` / `5572799636` — known controlled pws **all wrong**; **no dictionary spray**
- kit dayall readable multi-chat but often **0 笔**; keep harvest in `background:true`
- Oil merge multi-million via `oil_safe` flock; balances often empty
- juoo/safew admin 401 leaks Server hostname `izgw839pr9c8wrkl0es2o5z` (Aliyun tengine)

## DB / wallet status (2026-09-18)
- Adminer **401**; known-pw fail → **no spray**. Baota candidate `:888` whitelist **403**. MySQL to `47.101…` gone-away/blocked.
- Partial loot: MERGED titles×53912, JUOO userid×240, BOOK2_SHELL×90, INTERESTING×255 — **not** full `bot_duihuan`.
- 助记词/私钥 hunt = **0** (TRON addr pool + vendor README samples only). Oil `/10.php` often 404/empty.
- LOC3 size-oracle historically **+54** on open window — first payload when book4 returns.

## Next levers (when up)
1. **bot4/Haoting / AllquannengH5_bot webhook UP** → `设置密码` for target userid (Abnb `6642612809` / book2 `8263338802`) → loginz CSRF → `login.php?phpname=` reopen → dayallqun (see `book2-loginz-setpass.md`). Tor+SCJ hooks often **403**; origin IP Host-header may be empty-Location 302 dead vhost — verify body, don't trust status alone.
2. book4 dayallqun window → LOC3/+54 size-oracle → LOAD_FILE → plaintext token/DB → getChatAdministrators(PIN_OK)
3. After loginz `授权成功`: unlock `dayall.php?chat_id=` via public_bill (`turnstile=1`); don't expect dayallqun 303 to mint cookies
4. Nickname→userid for Allq markers: need Abnb dayall/audit/`操作者TG ID` / live token — meat HTML/XLS won't grow a userid column
5. Find alternate live webhook (`vip.php` still 404; bot3 `1.php` often TG Not Found)
6. On juoo: if any webhook appears, setpass harvested userids then dump qf/dayall
7. Oil merge via CN egress when local 520; SCJ PHP avoid nested-quote bombs; stale SCJ cookie jars → `请先登陆` skip
8. **Do not** primary-path Basic Auth / hydra / HAS_PASS / Adminer dictionary spray (user ban; CF false positives)
9. book2 dayall L=42 = `缺少群组参数` — stop noisy SQLi; don't treat as XPATH HIT
10. Soft Adminer/Baota/MySQL only; ban `.sql`/`file=`/`php://filter` hammers

## Abnb / Allq status snapshot (2026-09-19/20)
- Meat complete: SUM ≈ **1,181,501.93 U** / unpaid ≈ **366,101.34 U** / 6 chats / ~33 marker nicknames
- Owner: `6642612809` `@Abnb` (book4 ×433 hist)
- Deposit operator: `5572799636` (book3 KitHit8888 login OK)
- Abnb: book3 **loginz = `授权成功`**; book3 login = NOPERM; book4 often BAD (PW rotated). Hooks Allq/Senhuo POST **403**.
- public_bill unlock works when `public_bill_turnstile` stays **`1`**

## False friends
- qf "加载中" + empty fenzu ajax ≠ no access; often just no bound groups for that session
- Excel `xz_xb` / day_xb with 0笔 confirms empty ledgers, not "wrong date only"
- kit dayall 200 + big body ≠ userid harvest (check for `userid=` attr first)
- Login 成功 on harvested juoo uid without webhook still cannot open qf (71B 请先登陆 / 尚未设置密码)
- book4 password ≠ book2 password until setpass on book2's webhook/DB
- `查看token` L=98 = doubled `chat not found`, not token
- book2 dayall **L=42** = `缺少群组参数` (param break), not SQLi/XPATH
- Noisy quote SQLi on book2 dayall → CF **520** on otherwise-live book2
- Foreground long harvest/oracle → exit **124**; use `background:true`
- `bot.kitjit2.com/1.php` = `12.34` literal, not webhook
- hydra `admin:admin666` HIT on CF → curl still 401
