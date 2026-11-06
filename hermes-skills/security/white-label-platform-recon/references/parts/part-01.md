# white-label-platform-recon 全文 第 1/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

