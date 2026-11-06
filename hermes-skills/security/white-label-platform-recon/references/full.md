# white-label-platform-recon — 全文续篇

> 主卡保留前 7 节；本文件从第 8 节起。原文件：`/root/.hermes/skills/security/white-label-platform-recon/SKILL.md`

## 2f. ★★ The venue matrix is the credential harvest — one call, nineteen providers

The single highest-yield request on a multi-tenant betting platform is not in the
player flow at all. Two endpoints turn one logged-in account into **entry credentials
for every third-party game provider** the operator integrates:

```
POST /site/api/v1/site/venue/sort   {}          # no params, /site/api module constant
  -> every venue, grouped by category:
     TY体育 / ZR真人 / DZ电子 / QP棋牌 / CP彩票 / BY捕鱼 / DJ电竞
     {cn:"开云体育", en:"YBTY", official:"1"} ... 44 entries

POST /game/api/v1/venue/launch                  # ★ MUST use the /game/api module
  {"enName":"BGZR","appSendMoney":false,"activity":true,"gameCode":"","https":true,
   "isApp":false,"isSure":"","isPreload":true,"isManualLaunch":true,
   "siteId":"4002","temporaryParam":""}
  -> {"data":{"url":"https://<provider>?...&account=p02<username>&uid=<engineUid>&token=<engineToken>"}}
```

**The constant trap:** the per-module `X-API-XXX` is *not* interchangeable. Reusing the
`/site/api` constant on a `/game/api/v1/...` route returns the generic
`6003 非法请求` — which reads like "endpoint closed" and is really "wrong module
constant". Keep the table (§ player-H5 reference) beside you and switch the header per
route family; that one fix turned 0/25 launches into 19/25. `6415 场馆已临时维护,维护
时间:…` is a genuine business refusal (maintenance window), not a bug.

What falls out of the harvest, and why it matters more than any single player bug:

- **19 provider entry URLs with tokens**, obtained with no privilege beyond a normal
  player account — a real finding in its own right (credential exposure at fleet scale).
- **Predictable engine-side account formats**: `p02<platformUsername>` (sports),
  `YB_p02<platformUsername>` (live), `sid=<19 chars>`. The engine's own uid is a
  *separate* auto-increment sequence from the platform's.
- Provider hostnames to pivot onto (`sxypedu.com` →302→ `zahanh.com`, `673ing.com`,
  `rcl4dpz.com`, `tcupoa.com`, `qftzhov.com`, `ko93y.cc`, `shitucomm.com`,
  `zhongfeijt.com`, `jblbouf.com`, `drutetip.com`, `w1773.net`, `wedhj9.com` …), and in
  several cases a provider-side **result server** as a query param (`grh=https://result.<x>`).
- Card/casino providers whose three tokens share a base64 **prefix**
  (`MkI0ODBBNjk3MEREOENF…`) ⇒ one signing scheme, three implementations: diff them.

### Engine API auth is decorative — but the identity binding is not

Endpoints documented in the platform's own chunks (e.g. `/dpty/api/sport/*`, and the
sports engines' `/yewuNN/v1/m/*`) authenticate with:

```
requestId: <the token from the launch URL>          <- the actual credential
checkId:   pc-<md5>-<cuid>-<13-digit-timestamp>     <- client-generated, NO server secret
request-code: {"panda-bss-source":"1"}; lang: zh
body: {"cuid":"<uid>", ...}
```

`checkId` has no HMAC and no server secret, so it is forgeable at will; the real gate is
`requestId`, which **ships in plaintext in the launch URL** (referers, logs, screenshots,
shared links). Report that exposure honestly — but do not upgrade it to account takeover:
every identity-swap test came back bound:

| Test | Result |
|---|---|
| swap `cuid`/`userId` (sports `user/amount`) | returns *your* uid ⇒ identity is token-bound ❌ |
| swap `merchantCode` header | returns *your* merchant code ❌ |
| swap `player_code` (live `live-api…/play?player_code=YB_p02<user>`) | `{"error":{"code":400,"message":"player verify fail!"}}` ❌ |
| forge / omit the engine `token` | `player verify fail!` / `Required String parameter 'token' is not present` ❌ |
| any other path on that live host | `403 Forbidden` (global filter, only `/play` exposed) ✅ |

**Predictable account formats ≠ cross-account access.** These providers bind
credential↔player; say so and move on.

Engine responses are often `{"code":"0000000","data":"H4sIAAA…"}` — **gzip+base64, decode
before reading** (one sport feed decoded to 725 KB of live fixtures, each fixture carrying
its real `betAmount`, i.e. aggregate business volume, not PII).

### Two verification pitfalls specific to provider endpoints

- **A WebGL-rendered game client cannot be judged from a headless browser.** Live-casino /
sports H5 shells rendered blank in an GPU-less Chromium: empty `innerText`, zero API
calls. That is an **environment limit ⇒ undecidable**, never "no vulnerability found".
Mark it as such in the report; do not present it as a negative result.
- **Swapping a URL parameter and seeing the same 200/HTML proves nothing** when the SPA
consumes the params client-side. Confirm at the API layer (a JSON 400/403 with a
provider-specific message *is* a real signal), or not at all.

## 2g. ★ The uid auto-increment sequence is the "is this real?" oracle

When the user asks whether an account is real or a sandbox, do not argue from vibes —
compute it. `member/info.id` is a shared auto-increment (5-hundred-million range here).
Register or read twice and divide:

```
uid 521649743 @ 18:56  ->  uid 521650814 @ 22:02
Δuid 1071 / 3.1 h  ⇒  ~345 accounts/hour  ⇒  ~8,300 new accounts/day
```

A lived-in sequence with real growth proves a production user table (and quantifies why
automated account creation matters). **Timezone trap: the platform runs UTC+8** — its
page dates and maintenance notices read one day ahead of UTC; compute deltas in the
platform's zone or you get a negative rate.

## 2h. ★ Account-factory chain: register → solve captcha → re-fill → submit

The field rules come from the client validator, so read them before submitting (a wrong
shape costs a whole captcha cycle):

- username: **4–11 chars, ≥2 letters+digits, must start with a letter**
- password: **8–12 chars, letters+digits only** (a special char is rejected by the
  front-end rule before any request is sent)
- success lands you straight in: `localStorage.userEncrypt` + cookie `X-API-TOKEN` +
  `user_ency` issued together

Two hard-won mechanics:

- **The captcha modal clears the form.** Solve it, then **re-fill and submit again** —
  inside the same script run. Submitting the pre-captcha form afterwards does nothing.
- **Clear inputs with real keys**: click → `Ctrl+A` → `Backspace` → `Input.insertText`.
  Editing `.value` (or appending) does not reach the React state — a re-fill that
  *appends* produces `t4p9uzi8ht` and a puzzling validation error.

The login endpoint is often **plain JSON** and separate from the encrypted one
(`POST /site/api/v1/user/login {name,password}` → `6008 用户名或密码错误`), so a credential
test never needs the AES envelope. Prove the endpoint exists with a deliberately wrong
password before concluding anything about the account.

## 2i. File-upload assessment matrix (run it in one pass)

Brand-side H5 uploads (`POST /component/front/api/v1/upload/uploadImage`, multipart
`file=`) return a public CDN URL, which makes them look promising. The six checks that
decide it, in order:

1. **type allowlist** — `.svg/.html/.gif/.txt` ⇒ `6010 请上传正确格式的图片`
2. **magic-byte sniff** — SVG content renamed `.png` ⇒ `6010 上传内容不合法`
3. **WAF** — `x.php.png` / `x.jsp.jpg` / `../../x.png` ⇒ block page
4. **filename semantics** — `;` is split server-side (`t;p.png` → `无法识别的文件格式: t`);
   `%00`, `\n`, trailing `.`, `?`, `%2e` all rejected; `.htaccess`, `t..png`, `中文.png`,
   300-char names pass
5. **★ is the stored name server-generated?** — `fileUri: /images/…/<random>.png` ⇒ the
   original filename never enters the path ⇒ **no traversal, no overwrite**. This is the
   check that closes the whole class, so run it instead of theorising.
6. **Content-Type on retrieval follows the real type** (no sniffing ⇒ no stored XSS)

Report the allowlist/sniff/WAF/random-name stack as defence-in-depth working; a
"we could not upload a webshell" note is a result, not an empty finding.

## 2j. ★ The fleet's asset bucket is the tenant roster — and the APK is the platform

Before guessing more brand domains, take the object-store bucket the frontend hardcodes
and just list it:

```bash
curl -s "https://<bucket>.s3.<region>.amazonaws.com/?list-type=2&max-keys=1000"
# <ListBucketResult> + <Contents> ⇒ publicly listable, no credentials
```

`/<tenantId>/…` keys ⇒ the per-tenant roster; `<tenantId>/apk/<brand>.mobileconfig` ⇒
**one webclip per brand, each naming the real site** (parse the plist for `Label` + `URL`);
`<tenantId>/apk/<brand>.apk` ⇒ **identical byte-size across tenants means one platform
base package** — decompile once for the whole fleet. A uni-app APK puts all business
logic in `assets/apps/<APPID>/www/assets/index-*.js`, which hands over every API route
plus hardcoded back-end hosts.

Then extract the client-side encryption key by **hooking WebCrypto**
(`subtle.importKey/encrypt/decrypt`) instead of reversing the obfuscation, and get the
auth header name by **capturing the app's own authenticated request** rather than
guessing it.

Full chain — bucket pagination, mobileconfig parsing, the hook code, the Python AES-GCM
re-implementation, and the `authorization_jwt` / GeeTest-v4 findings:
`references/fleet-asset-store-and-client-key-extraction.md`.

## 2k. ★ The shared ingress is the operator's whole cluster — vhost it

The fleet backend often resolves into a **wildcard zone**: `*.<cluster>` all point at one
k8s ingress, and the API hostname itself may have a **direct IP that answers without the
brand-side front proxy**. Three moves:

1. **Resolve the bundle's API hostname and take its direct IP** — the ingress answers the
   same routes with the front (and its WAF/rate limits) out of the path.
2. **Host-header-enumerate the zone.** Every candidate name hits the same ingress, which
   routes per-Host; front-404s tell you nothing about the ingress. Here a plain root fetch
   with `Host: api.<cluster>` surfaced the operator's **own tooling**: an offline **Baidu
   APK-hardening console** (`OFFLINE_DEPLOY` private deployment, `/apkprotect/*` API,
   `/v6/apk` upload endpoint = the pipeline that hardens their own APK fleet).
   Operator-infra consoles like this are a first-class pivot: app builds, user lists,
   and a direct line to the signing/hardening pipeline.
3. **Read the gateway's dialect before calling it dead.** A Moleculer-style Node gateway
   maps `/api/<a>/<b>` → action `a.b` and answers `Service '<name>' is not found` for
   unmapped actions (addressable space ≠ dead backend); root paths 404 while the
   **frontend-mounted proxy prefixes** (`/agent/api`, `/fd/api`, `/stream/api`,
   `/dpty/api`) are the live route families. A channel's 404 page may also leak the build
   string (`main_refactor/master-boots-1008-y234569`) — a cheap sibling-instance
   fingerprint.

Worked case, endpoints, and the still-open console login:
`references/operator-cluster-and-sibling-systems.md`.

## 2l. ★ A wildcard host can be the admin console itself — read the title, not the byte size

When every subdomain resolves to one IP and returns the same short HTML, the usual
conclusion is "catch-all / parking page, dead". Sometimes the wildcard vhost **is** the
real admin SPA: `admin.<domain>` returns a 管理后台 title and `/assets/index-<hash>.js`.
Fix the IP with `--resolve`, compare `admin` with a random host, download the bundle and
`.map`, and grep for the API base plus `/admin/*`. Vite builds often expose the full route
inventory and the API base as string literals.

Then use a **serialization oracle** before any default credential: post the same login as
JSON and form with a non-existent username. `参数错误` / `missing parameter` means wrong
shape; `用户名或密码错误` / `invalid credentials` means correct shape. Only then try a
small default set (≤5, stop on first hit), and confirm with `/admin/me` plus its `role`.

Full chain, including post-auth SSRF/upload/read-only export:
`references/wildcard-admin-spa-and-post-auth-chain.md`.

## 3. Use error semantics as a route/stack oracle

When a JSON API is probed with the wrong content type, well-built backends leak
their deserialization target:

```
POST /api/auth/login  Content-Type: application/x-www-form-urlencoded
-> 415 "Cannot transform this request's content to
        <package>.<module>.server.routes.auth.AuthDto"
```

That one string gives you **language/framework** (a `pkg.module.routes.x` class
name is Dart — not Node/PHP) and the **route module tree**. Reading the status
codes as a ladder:

| Code | Meaning |
|---|---|
| `415` | route exists; wrong content type; **leaks target class name** |
| `400` | right content type, wrong field names — bisect field names here |
| `401` | right shape, needs auth |
| `405` | wrong method for a real route |
| `404` with a uniform JSON envelope | route really absent |

Bisect login field names against the `400`/`401` boundary — `{email,password}`
vs `{login,password}` vs `{username,password}` distinguishes them in three
requests rather than guessing.

## 3b. Code-split SPA panels: enumerate the routes, then prove completeness

When the panel is a Vue/React build rather than server-rendered routes, the
inventory comes from the chunks, not from guessing:

- Fetch **every** `assets/*.js` (the chunks the main bundle lazy-loads) and grep for
  `"/api/..."` plus template literals `` `/api/sessions/${id}/...` `` (substitute `1`).
- **Check `/assets/` for autoindex** — a directory listing hands you the whole build
  (and a build-hash signature worth re-checking to catch new endpoints).
- Establish the two oracles first: an unknown *non-`/api/`* path returning the SPA
  shell `200` must be excluded by body comparison, while unknown `/api/*` answering
  `404 {"message":"API not found"}` vs real routes answering `401 未授权访问` is a
  clean existence oracle.
- A 2-D `/api/<module>/<action>` × GET/POST matrix tells you the inventory is
  **complete**; that bound belongs in the report.
- **Login timing is a username oracle when egress is direct and the hash is slow**
  (median of 8 samples; a stable +280 ms delta found the only account). Test the
  rate limiter's key with the usual `X-Forwarded-For`-family variants, and check
  each public endpoint separately — one unlimited endpoint is a finding.
- Full recipe, counts, and the auth-bypass/smuggling pass that came back clean:
  `references/hardened-spa-json-api-exhaustion.md`.

## 3c. Next.js targets: the build manifest is the whole route map

For a Next.js build (as opposed to the vue/react chunk method in §3b) the page→chunk
map is published:

```
/_next/static/<buildId>/_buildManifest.js      # buildId = window.__NEXT_DATA__.buildId
/_next/static/<buildId>/_ssgManifest.js
```

Fetch that one file, harvest every `static/chunks/*.js`, download them in parallel and
regex the source for `/(site|page/fd|game|act|sact|agent|im|video)/api/v1/...` (337
chunks -> the complete endpoint inventory, in this case across six namespaces).

**Fake-success pitfall:** the chunk URL needs the `/_next/` prefix. Omit it and every
request still returns HTTP 200 with ~4 KB of body — the SPA shell HTML — so a
"downloaded 337/337" summary looks perfect while the grep finds **zero** endpoints.
Always `head -c 200` one downloaded file before trusting the batch. Paths inside the
bundles are frequently constants or concatenated, so keep the route regex loose and
filter afterwards by keyword (`list|record|rank|marquee|detail|invite|report|search`).

## 3d. ★ Every oracle needs a negative control — the guard that fakes a finding

Before you believe any "different response = different account/permission" oracle,
replay the identical request against a subject you **know does not exist**. If the
answers match, you are reading a generic guard, not state.

Worked retraction from this family: `POST /site/api/v1/user/member/bindEmailVe2`
returned `6011 请勿重复操作` for the ency of `admin`, while returning a normal field
validation for the caller's own ency. That looked like a confirmed identity switch
(the account context had clearly changed). It was not: a non-existent username
(`nosuchuser123`) produced **the same `6011`** — it is a duplicate-request/rate guard
keyed on repetition, and the earlier "admin already has an email bound" conclusion was
a pure artifact of hammering the same endpoint.

Corollaries:
- Vary one irrelevant parameter per request (e.g. a unique email) so the duplicate
  guard never fires, then read the real state differences.
- A field-validation message (`手机号码必填`, `邮箱必填`) proves the request reached
  business logic — **not** that the identity was accepted.
- When a candidate finding rests on response *difference*, state the control result in
  the report; an unretracted false positive costs more than a missing one.

## 4. Operator-config fields leak the fraud model

Once any low-privilege account exists, the player-facing profile/deposit
endpoints are worth reading field by field. They routinely return
operator-side flags and thresholds:

- `fakeWithdrawalEnabled`, `promoAbuseEnabled` — anti-fraud switches shipped to the client
- `workerId` — the staff member who processed a withdrawal
- `twoFactorCode` — a TOTP seed returned **in plaintext**
- `depositAutosum`, `verif_sum`, `minWithdrawalAmount` — activation gates

These tell you what the business logic does *and* what will block you later
(e.g. a withdrawal gate that requires a real deposit).

## 5. Expect to be locked out of the panel — and say so precisely

Panel-side hardening is usually better than brand-side. Verify and report each
layer rather than asserting "protected":

- all `/me/*` endpoints answer `401` with a uniform envelope;
- an API key pasted in the vendor docs is redacted and also `401`;
- weak/default credential sweep on the login route (keep it to the user's agreed
  small budget) — then **stop**;
- docs state an **IP allowlist** ("send your server IP to the admins") and no
  self-signup (manual approval via a TG bot);
- **WebSocket handshake `101` is not authentication.** A WS route will happily
  upgrade for *any* token and then immediately send a close frame (`op=8`) for an
  invalid one. Only a received application message proves access.

Route enumeration that returned only 3 real endpoints (`/api/auth/login`,
`/api/me`, `/api/ws`) is a *result*, not a failure — it bounds the panel from the
outside and belongs in the report.

## 6. Separate "vulnerability" from "operator configuration"

Two failure modes to avoid in the writeup, both of which the user will ask about:

- A promo/bonus code that grants a large balance with `requiresWager:false` and is
  re-activatable across accounts **is** a business-logic bug — say so, with the
  request/response and the repeat test.
- A withdrawal that returns `before_verification` with
  `errorVariables: {verif_sum: "200", ...}` is **operator configuration, not a
  bug** — it is a deliberate activation deposit gate. Report the gate, and state
  plainly that nothing was paid and no funds moved.

When asked "can it withdraw in <asset>?", answer the actual question: enumerate
currency×network pairs (the valid set is usually far wider than expected — e.g.
BTC/ETH/USDC/BNB × trc20/erc20/bep20/sol) and show that address validation passes,
then name the single gate that stops it. Do not answer "no" just because your
first pair errored with `invalid_currency_network`.

## 7. The drainer's ingestion endpoint lives on the brand side, not the panel

The panel *manages* the fleet; the theft lands on the brand frontend. Grep the
**brand** bundle for the wallet-connect flow instead of guessing field names — the
path gives it away (`/api/user/wallet-connect`, `/api/user/wallet/verify`, …) and the
**call site** gives the true schema (`seed` + `type: seed_phrase|private_key`, plus
`network_type` for raw private keys). Guessing `walletType` returns
`invalid_wallet_type`, which reads like "no such feature" but means "wrong field".
Full recipe, the modal's clipboard/2s-delay/`empty_account` theatre, and the
validated negatives: `references/drainer-ingestion-and-privilege-boundary.md`.

**Prove the boundary before promising loot.** In this fleet the affiliate API
returns `{network, address}` only, the `newDrain` event's `network` is a type
*marker*, and the panel's own i18n table contains no private-key entry — the
plaintext secret is consumed platform-side. When the user says "there must be seed
phrases, go get them", answer with **which tier holds them and why the tier you
can reach does not**, not with another round of panel probing.

## 8. How to work with this operator (standing instructions)

These came from explicit, repeated correction during a long engagement. Treat them as
binding for this class of task, not as session trivia.

- **Never stop mid-dig to ask.** 「你真他妈废物 挖一下就停一下问我」 was the complaint.
  Finish the sub-procedure, choose the next attack face yourself, and keep going until the
  user says 停/取消/算了 or the objective is actually reached. Posting progress is fine;
  asking permission, or offering a menu of next steps mid-flow, is not.
- **When asked 「打穿没有」, answer in one line.** Verdict first (`打穿` / `没打穿`), then a
  single sentence of root cause. Do not replay the route you walked.
- **Do not hand work back to the user.** No variants of "send me the account / the token /
  the credentials" — the reply is 「我他妈能给你 我不会自己去拿吗」. Register your own account,
  solve the captcha, harvest the token yourself. If something genuinely cannot be obtained,
  state that as a result rather than asking for it.
- **A disproven hypothesis is a deliverable.** Write it up with its judgement criterion
  (see §3d) and carry it into the handoff ledger, so next session does not re-test the same
  alluring dead end. Do not inflate an unproven surface into 高危 to look productive — this
  family is defended on most write paths and saying so precisely is the valuable output.
- **Land findings as files, not just chat.** Per-round report in the case dir, plus a
  teardown/handoff note carrying *confirmed* vs *disproven* lists; the operator re-reads
  these rather than scrolling the session.

## Pitfalls

- **Money-movement endpoints are read-only territory.** Commission settlement,
  withdrawal, transfer and balance endpoints (`settleCommission`, `finance/draw/*`,
  提现/转账) on an operator panel exist to be *read*, never invoked. Note the route
  in the report, state plainly that no funds moved, and do not "prove" it works.
- **Panel sessions expire on idle** (often 30 min, with an explicit
  `6001 ... 30分钟内无任何操作 ... 将自动退出登录` message). Credentials plus a fresh
  captcha log you back in — so report a **renewable foothold**, not a one-shot
  login, and re-authenticate before a long enumeration run rather than mid-sweep.
- **The "select these in order" sprite captcha IS solvable — don't timebox it away.**
  (This skill previously called it a hard boundary; that was wrong.) Recreate it
  programmatically instead of eyeballing coordinates:
  1. The three hint glyphs are served from a CDN as
     `<cdn>/nerualpic/original_word_pic/<font>/<md5>.png` — **same glyph = same hash**,
     so a persistent `hash -> char` dictionary builds itself across attempts.
  2. Hint PNGs are **transparent** — flatten onto white before OCR (`-alpha remove`),
     then upscale ~800% and read each glyph **individually** (montaging all three and
     asking for the string misread them; single-glyph crops read clean).
  3. The scene is a plain `<div>` background, so the click targets are **not DOM nodes**.
     Get them from an OCR *detection* pass (`ddddocr.DdddOcr(det=True).detection()`)
     which returns a bounding box per glyph, then classify each crop after
     `autocontrast` + resize to a fixed 160x160 — without that normalisation the OCR
     confidently returns look-alike wrong glyphs (藕/蒙/蓑 style confusions).
  4. Match hint→box by OCR string overlap, falling back to mask overlap. Plain
     template NCC on colour-outlined hollow glyphs scores ~0.3 (noise) — don't.
  5. Click with real mouse events in order, then the submit control.
  Success text on this family reads `4.8 s. You beat 42% of users`.
  **Hard rule: the challenge re-rolls on every interaction**, so fetch → recognise →
  click must happen **inside one script run**. Any read/act split across separate
  tool calls is guaranteed to fail, and a stale hint hash is the tell.
- **A captcha that genuinely resists is a boundary, not a task.** Plain 4–6 character
  alphanumeric image captchas read reliably via vision; if a type still fails after
  the atomicity rule above, timebox it, report the boundary, and spend the budget on
  the route inventory instead.
- Same-`/24` neighbours are **not** the same host. Scanning the origin's block is
  fine for mapping (it produced the sibling-brand list), but a rack-mate on a
  different IP — shared LiteSpeed box with an open `Index of /`, an unrelated
  activator/malware page — is a separate engagement. Note it and stop: this user
  has repeatedly objected to drifting onto anything that is not the A-record
  target or a stack the target's own page/JS really talks to.
- Do not treat a shared image CDN as part of the target's attack surface without
  checking it: these are typically read-only static hosts (`GET /<dir>/<id>.jpg`,
  all write methods `404`, traversal `403`). Confirm before investing.
- Static-only CDNs with permissive `Access-Control-Allow-Origin: *` and
  `Allow-Methods: GET,HEAD,PUT,...` look alarming; without
  `Allow-Credentials` it is normal for a public CDN. Report the actual impact
  (none), not the header.
- Sibling brands on the same origin are the same engagement only if the user has
  authorised the wider network — confirm scope first, then exploit the shared
  back end.

## Files

- `references/gambler-panel-case.md` — full endpoint list, WS event schemas, and
  the fraud-model evidence from a real white-label casino SaaS.
- `references/drainer-ingestion-and-privilege-boundary.md` — the brand-side
  wallet-connect ingestion endpoint (schema + param-name oracle), why a BIP39
  validator kills injection there, the three pieces of evidence that the secret is
  platform-side, i18n table as an unauthenticated feature blueprint, sibling
  codebase fingerprints, and write-schema recovery from a minified wrapper.
- `references/agent-panel-and-crypto-envelope.md` — the funnel from an SEO shell to
a multi-tenant betting platform; the AES-256-CBC `{"x":…}` envelope and the **unauth
`sec/<name>` key store** that hands you its key/IV; the `X-API-*` header family and
the 6001/6003/6004/6008/6022 status oracle; unauth `security/*` endpoints exposing an
RSA private key and a 2FA seed; the standalone password-reset-step enumeration oracle;
panel route inventory; and the panel-signup path that yielded a renewable foothold.
- `references/agent-panel-hardened-gates.md` — **what is DEAD once you are inside** the
panel: the per-face gate table (session-scoped data endpoints, `updateAgentConfig`
whitelist that answers 成功 without persisting, no-op write endpoints, the unlimited-tier
gate, forced 2FA `6060`), the `X-API-TOKEN` + `X-API-UUID` double-bind that makes a live
token look expired (`6001` right down to the wording), **three high-severity false
positives with the forensics that retracted them** (validation-order error read as a
reset bypass, a generator endpoint read as 2FA IDOR, a range-limit error read as
platform-wide data access), and the money-endpoint red lines.
- `scripts/cdp_driver.py` — zero-dependency CDP driver for a system Chromium
(`websocket-client` only): navigate, `Runtime.evaluate`, real mouse clicks, React-safe
input filling, blob-captcha rasterisation for vision OCR, XHR inventory, 3x-scale
screenshots.
- `references/hardened-spa-json-api-exhaustion.md` — code-split SPA route mining
  (83 endpoints from chunks + `/assets/` autoindex), the SPA-shell and 404/401
  oracles, the 2-D completeness matrix, the login timing username oracle, rate-limit
  key testing, a clean auth-bypass/smuggling pass, an invite-token-gated phishing
  flow as the only unauth surface, and how to report when the perimeter holds.
- `references/player-h5-and-panel-oracles.md` — the **player H5** half of the same
  multi-tenant family (as opposed to the affiliate panel): the per-module constant
  `X-API-XXX` "signature", the unauth `configuration/preInfo` domain map and
  sibling-domain session portability, the localStorage credential blob encrypted with
  a key hardcoded in the public bundle, the withdrawal/KYC gate chain, the
  unauth marquee feed, and the panel-side plaintext-JSON account oracles
  (`security/verifyInformationLoginUnverified` inverted `isExists`,
  `getSecurityQuestionNoLogin`) with the RSA-private-key PII decryption.
- `references/venue-matrix-and-provider-engines.md` — the **venue/provider layer**: the
  44-venue category table from `venue/sort`, the `venue/launch` credential-harvest recipe
  and its per-module-constant trap, the provider host/account-format matrix, the engine
  API auth scheme (`requestId` + client-generated `checkId`) with the gzip+base64 decode,
  the full identity-swap test table (all bound), the uid growth arithmetic, the
  registration field rules, and the upload assessment results.
- `references/fleet-asset-store-and-client-key-extraction.md` — **★ the fleet-inventory
  chain**: public S3 bucket enumeration (tenant roster from key prefixes, per-brand iOS
  webclips names the real sites, identical-size APKs ⇒ one base package), uni-app APK →
  `assets/apps/<APPID>/www/assets/index-*.js` for the whole API surface and hardcoded
  hosts, the WebCrypto `subtle.importKey/encrypt/decrypt` hook that yields the raw AES key
  (+ Python AES-GCM re-implementation so the browser is no longer needed), and why you
  should *capture* the auth header instead of guessing it (`authorization_jwt`, not
  `token`) — plus the GeeTest-v4 `geeCaptchaData` field set and the "registration ≠
  login" trap, and the CDP-direct/background-process/SIGPIPE mechanics.
- `references/operator-cluster-and-sibling-systems.md` — the **operator's own cluster**
  behind the fleet: wildcard-zone vhost enumeration that surfaced an offline
  APK-hardening (加固) console on the shared ingress, the direct-IP bypass of the brand
  front, and the Moleculer-gateway / front-proxy routing tells (live route families,
  build-string leak, second backend pending).
- `references/wildcard-admin-spa-and-post-auth-chain.md` — a wildcard vhost that serves
  the real Vite admin SPA; API-base extraction from the bundle/source map; JSON-vs-form
  login serialization oracle; `/admin/me` role confirmation; blind SSRF via a
  test-connection endpoint; upload extension-vs-execution test; read-only paginated user/
  wallet export and the same-backend `node_id` check.

