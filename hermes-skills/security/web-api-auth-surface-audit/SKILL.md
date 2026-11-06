---
name: web-api-auth-surface-audit
description: "Use when auditing web/API auth surfaces, mass-extracting gated records, or resolving platform identifiers into identities."
version: 1.3.0
tags: [pentest, api, auth, unauthenticated, idor, bruteforce, captcha, enumeration, oracle, im]
---

# Web/API Auth-Surface Audit

Class of task: on any web/API target, settle **which operations are actually gated**, **whether object IDs
are guessable**, and **whether the credential path can be attacked with honest accounting**. Do this first on
every engagement — BFLA, BOLA and injection findings are all downstream of it, and a wrong read here poisons
the whole report.

## Procedure

1. **Get the COMPLETE operation list before testing any of it.** `/openapi.json` (+ `/docs`, `/redoc`); on a gateway whose routes are otherwise all token-gated, pull each module's docs path (`/<gateway>/<module>/v2/api-docs`), which routinely stays in the auth whitelist and whose listing also confirms the exact gateway prefix;
   JS bundles (`apiUrl(`, `request(`, axios instance), `action=`-style dispatch tables, dir fuzz;
   on RuoYi/Spring stacks the Druid monitor's `/druid/weburi.json` + `/druid/sql.json` inventory every URI and SQL the live traffic actually hit — but it is capped at ~1000 rows and **resets on JVM restart**, so it shows only the recent window: a route missing from it is not missing from the app, and its SQL view hands you the datasource DSN (host/port/db/user) and the driver/jar path for free.
   A partial list produces a partial conclusion, and the user will call it out.
   SPA bundles are **chunked**: the entry bundle often contains no API literals at all. Pull every
   `assets/<route>-<hash>.js` the entry bundle references and grep those for path-like strings — restricted
   routes (`/user/list`, `/user/setPwd`, `/email/list`, `/account/add`) surface exactly there, and their
   absence from the entry bundle is not absence of the endpoint. Read the route names too: they map 1:1 to
   the admin surface worth probing — then grep the chunk set for FEATURE keywords (`reset`, `bind`, `key`,
   `white/ip`, `export`, `log`, `record`): the destructive admin calls (`reset/password`, `reset/google`,
   `get/md5/key`) live in exactly those chunks, and that list is simultaneously your high-value probe list
   and your post-access action list.

   **Compiled mobile/web clients carry the request SCHEMA, not just the paths.** A Flutter web build ships one
   `main.dart.js`; grep it for the endpoint literal, then read the ~600 chars *before* each hit — the minified
   call builds its body inline, so that text IS the authoritative key list (`A.u(["accid",a],...)` → key
   `accid`; `A.u(["tid",p.w,"memberList",a],...)` → two keys; `A.u(["type",a,"value",b?"1":"2"],...)` →
   the value is the string `"1"`/`"2"`, not a bool). Read the response field the client reads back
   (`.h(o,"appid")`) to recover the reply schema too. Guessing key names is what burns a rate-limited egress
   and returns nothing but the same "required field" error; a deserialization error such as Jackson's
   `Cannot deserialize value of type 'java.lang.String' from Array value` is instead a free TYPE oracle proving
   the handler is reachable and the field is scalar. This bounds the **client's** surface only — an
   operator/admin panel fronting the same API can own routes the app never calls, so "not in the bundle"
   means "no app-facing route", never "no route".

   **"Backend started, UI not deployed" is a probe target, not a verdict.** An admin API root answering a
   startup banner ("<product> started, start <ui> to open the page") means the backend is live while the
   UI bundle sits elsewhere on the SAME host. Probe the static roots before believing it: `/index.html`,
   `/assets/`, `/ui/`, `/web/`. A `200` on `/index.html` is the real admin SPA; its entry bundle carries
   the runtime config (`SITE_CONFIG.apiURL`) and a lazy-chunk map whose module names (`cash`, `pledge`,
   `oss-upload`, `schedule`, `log-login`) map 1:1 to the business surface worth probing. Grep those chunks
   for quoted path literals to recover the API table (`/sys/user/page`, `/sys/user/export`, `/lz/config/cash`,
   `/googleAuth/gen`), then fire every path with GET **and** POST — `401` on both is the gate, and the list
   doubles as the post-access action list.

   **Obfuscated front-end config: decode char-code arrays with a loop; run jsjiami pages in a browser.**
   Chinese vendor pages hide config in `document.write(deC("60 33 68 79 …"))` — `''.join(chr(int(n)) for n
   in s.split())` restores the HTML. A second layer can be base64 inside the char codes (`MjA3LjU2…` →
   `IP:port,domain`) — decode both; together they hand you the live customer-service/API endpoint. For
   jsjiami v6 (base64 + RC4 string table) do NOT hand-port the RC4: a hand-written decoder produced garbage
   and a Node eval of the page hung in the anti-debug loop. Open the page in the real browser instead and
   read what it actually calls — `performance.getEntriesByType('resource')` names the real backend in one
   shot.

   **Vendor-side docs and SDKs are an operation list too.** The vendor's public GitHub org
   (`api.github.com/orgs/<org>/repos`) routinely publishes integration SDKs and the full merchant/admin
   manual; Mintlify-hosted docs answer `/llms.txt` and `/llms-full.txt` with the complete surface in one
   fetch, including endpoints the client never calls and the exact crypto recipes (AES key derivation,
   HMAC signing) for sensitive fields. Treat the manual as the authoritative operation list, then confirm
   each candidate live. Check `git log -p --all` in those repos for secrets redacted only in the latest
   commit — but expect the history to be clean; redactions are usually applied before first push.
2. **Run the classifier sweep** — `scripts/classify_api_auth_surface.py <base_url> <openapi.json>` —
   empty body first, then a schema-shaped body, then classify. Keep the counts.
3. **Record the ID format of anything you create** (task, order, ticket, export) and test its entropy.
4. **Probe the credential path's real POST target and semantics** (rate limit, lockout) with a throwaway account before
   budgeting a dictionary. Only the form's action accepts the POST — walk the redirect chain (`/` →
   `/admin/index.php` → `/admin/login.php`) instead of guessing; posting a guessed-but-wrong path fails
   silently. Confirm the failure signature from one known-bad response: a panel that re-renders its form
   with HTTP 200 will false-positive a status-code-only detector.
5. **Report as a matrix** (endpoint × method × auth-state counts) + deadends *with reasons* + the one
   remaining lever. Never a narrative conclusion.

## Rules (always on)

### R1. Auth is decided by the error SHAPE, not the status code

| Response | Meaning |
|---|---|
| `401` / `403` | gated |
| `400/422/500` + a business field error (`"X 不能为空"`, `"messages is required"`, `"token 格式错误"`) | **handler RAN with no auth check → unauthenticated access is proven** |
| `200` + data | already leaking, or already writable |
| `405` | endpoint EXISTS, wrong HTTP method — retry POST/PUT/DELETE (405 ≠ 404) |
| `404` | test ID missing; the operation itself is still ungated |

A business-validation error is *the* proof: the request reached the business logic.

**A field-empty error for a field you DID send means the key name is wrong, not the credential.** Every
service in a stack names its login fields differently, so the same correct credentials that answer `200` on
the business API come back `501 邮箱和密码不能为空` on the paired mail API when sent as `userName` instead of
`email`. Before concluding a credential is wrong, replay the identical values under the sibling key names
(`email` / `userName` / `account` / `number`) and read which one stops complaining. An app-level `501`
naming a field you definitely supplied is a schema-mismatch oracle, never a failed password. Never conflate "no
session" (401) with "no auth code" (business error) — they look nothing alike.

ASP.NET Web API status codes enumerate hidden endpoints — treat every non-404 as a live lead:
- `405` `"does not support http method 'GET'"` = controller/action exists, method wrong → try the other verbs.
- `401` `"Missing <X> header"` = the auth header NAME is echoed back (e.g. `Missing InternalSecret header`) —
  that name is the next lever, probe arbitrary-non-empty and known-default values against it.
- `500` `"Internal server error"` = action exists but a parameter is wrong-typed (an `Id` passed as string
  where `Int32` was expected) → read the front-end JS call for the correct params, don't write it off as 404.

**A business-JSON gateway (`everything answers HTTP 200 with {"code":...}`) makes status codes useless —
classify by response class against controls.** Anchor every suspect row on a control trio first (one route you
know answers unauthenticated, one nonsense path, the suspect), per method:
- `403` + a generic denial body (`{"code":403,"msg":"页面不存在"}`) is the stack's **misleading refusal**
  (commonly auth-middleware reuse), not "route absent" — it comes back for guarded routes and can also come
  back for nonsense paths. Identical bodies across the trio ⇒ the gate is global and the suspect stays
  *unknown*; never record it as "endpoint exists".
- `200` + a generic handler error (`{"code":2,"msg":"服务器出错,操作失败"}`) is an **existence** signal: the
  route exists and the handler ran (typically an NPE from the missing session). The same path can differ per
  METHOD (`POST` denied, `GET` errored) — sweep methods on every promising path before writing it off.
- **Stack the client's base path when bundle literals and the app disagree.** axios `baseURL:'/api/'` + a
  chunk literal `/api/get/x` ⇒ the live route is `/api/api/get/x`; the unstacked form answers nginx `404`
  while the stacked one reaches the app. Test both forms for anything found in a bundle.
- **A no-token error on a guessed path is not proof the route exists.** Auth middleware can run before the
  router: a guessed `/api/<module>/<action>` answered `token不能为空` with no token and looked like a live
  module, yet every sibling path answered the router's `请求资源不存在` once a valid token was attached. Control:
  send the identical token-less request to `/api/<random>zzzNothing` — the same answer means the body is the
  middleware's, and route existence stays **unknown**; never promote it to "endpoint exists".

### R2. Validation runs BEFORE authorization — never judge from an empty body
Sending `{}` to a protected endpoint returns `422`, not `401`; the real gate only appears once the body is
schema-valid. Probe with a minimal **schema-shaped** body (the script builds it from the spec, resolving
`$ref`s) before writing "open" or "protected" next to any row. Corollary: an endpoint whose spec type is a
bare `{"type":"object","title":"Payload"}` usually accepts **plain JSON** — only those typed with a real
encrypted-request schema (e.g. `SecureRequest`) are actually protected.

**A field-validation message is never proof of authorization.** A backend `managerApi`-style handler checks
the body schema *before* it reads the credential, so a schema-incomplete body answers `请选择修改的参数类型` /
`请输入 value` and a deliberately WRONG key looks like it "passed". The error message is then a lying oracle
and the ordering alone will make you report an escalation that does not exist. Discriminate explicitly before
believing any 200/field-error: replay the identical request with a known-bogus credential (`apiKey=demo`, an
empty key, a same-shape random string) and compare the two answers byte for byte. Identical answers = the gate
is intact, you learned only the parameter shape — record it as a **validation-order artifact, NOT a bypass**.
Tune the body until the permission error appears (`权限不足` / `access deny`); that is the real wall, and the
wall is what you report.

**Mirror case: a success message on an empty/invalid body is not "open" either.** Async-task backends ACK a
malformed submission into a queue BEFORE any auth/schema check — measured on one stack: `POST add/dkim {}`
answered `"Task completed"` while its sibling `add/domain {}` answered `access_denied`. The receipt means only
that one handler queues before validating; it is never proof the operation ran. Replay with a schema-real body
and the true gate (`access_denied`/401) appears. This applies to writes that SHOULD succeed too — an async ACK is
a queue receipt, not an outcome; only a read-back proves the write landed.

### R3. Object-ID entropy decides whether "IDOR" is real or theatre
Capture the ID format at creation time — it is free, and it is the whole finding:

| Format | Entropy | Consequence |
|---|---|---|
| `1789378994010` (raw epoch ms) | **0 bit** | enumerate the namespace; with ungated read/delete = steal + destroy other tenants' records |
| `monitor_20260914094407_b156c9` (timestamp + 6 hex) | ~24 bit | space collapses to a few million per second-window |
| random hex/base64 ≥ 64 bit | — | enumeration infeasible, stop and say so |

**PoC recipe** (needs nothing from the server): create 3 objects → parallel blind-enumerate the
`created_at ± 3s` window against the read endpoint → `200` = found → unauthenticated `DELETE` → re-read and
expect `404`. ~7.9k candidates finish in under a minute at 25 threads.

**Always clean up**: delete every probe object and re-read to confirm; sweeps and PoCs create residue.

### R4. A 5xx is not a tested credential
Any proxy/CDN-layer failure (Cloudflare `502`/`524`, reset, origin timeout) means the request **never reached
the credential check**. Re-queue the pair; never count it. A run that silently skips 5xx reports "dictionary
exhausted, no hit" while half the passwords were never tried. Log the status code beside every attempt so
coverage is auditable.

### R5. Probe lockout semantics with a throwaway username before trusting the banner
A "N failures then lock M minutes" banner is frequently cosmetic, and the word `锁定` usually also sits
inside that same static warning string — matching on it gives a false lockout. Fire N+2 wrong logins at a
**nonexistent** username first: a real lock returns a *different* message/page; an unimplemented one returns
"wrong password" forever. This also reveals whether the counter is per-account or per-IP, which decides
whether rotating usernames buys you anything. Once the captcha is bypassable, lockout is the ONLY thing
between a dictionary and the panel — establish it before spending the dictionary.

**A cooldown is a one-way clock: any request renews it.** Measured on an account-level limiter: 2 quick
failures opened a 90 s lock and every probe inside the window pushed the release forward — parallel workers
kept the account locked indefinitely (a global lock storm), and a fresh egress (new Tor circuit / new IP)
changed nothing, which is exactly how account-level is distinguished from IP-level. Protocol: fire ONE probe
on one account from a fresh egress; still locked ⇒ the dimension is the account — stop all traffic to it,
wait a full silent window, then measure once. Never use a retry loop or several threads as the measuring
instrument.

**No account lockout is not no rate control.** A high-rate spray can trip an edge IP ban: every vhost on
the origin starts answering RST while the CDN and unrelated ports stay up, and the ban can lift after a few
minutes. Tor exits are usually rejected outright. Pace the spray (tens per second), keep a logged resume
point, and confirm the ban scope by Host before blaming the credential or the WAF.

On ASP.NET MVC login forms, reuse the `__RequestVerificationToken` from ONE GET /Login across many POST
login attempts — the anti-forgery cookie+token pair is not single-use. Keep it in a `requests.Session`
(ASP.NET_SessionId + __RequestVerificationToken cookie persist), extract the token once, and POST in a
loop. This halves requests and avoids `anti_forgery_invalid`, which means the cookie/token pair was fetched
out of sync — not that the account locked. The same one-GET / many-POSTs reuse holds for PHP CSRF
forms (`PHPSESSID` + `csrf_token`) — refresh the session every few thousand attempts as insurance.

### R6. Captcha: check the control class before reaching for OCR
- `curl -s <captcha_url> | head -c 300`. `image/svg+xml` with the answer in `<text>` elements → extract with
  `grep -oP '<text[^>]*>\K[^<]+'`. Plaintext, no OCR, no model, no CAP_FAIL loop.
- Decode the session cookie. Flask/itsdangerous sessions are **signed, not encrypted** —
  `base64.urlsafe_b64decode(cookie.split('.')[0])` can print `{'captcha': '9SPJ', ...}`.
- Such captchas are single-use per session (reuse → `验证码错误`): fetch fresh per attempt, keep the cookie
  bound to the image, and only then fall back to `ddddocr` for real bitmap captchas.
- **reCAPTCHA v3 has no image to OCR** — it is score-gated server-side. Get a token in a browser with
  `grecaptcha.execute(sitekey, {action:'submit'})` (sitekey lives in the page's recaptcha script
  `?render=<sitekey>`). A valid token from a headless browser can still come back as a generic
  `{"result":"error"}` because the *score* is rejected, not the token — before blaming body fields, suspect
  score-gating (or a Content-Type mismatch, see R9).

### R7. Status/body mismatch and constant-error endpoints are findings, not noise
- A response with **HTTP 200 carrying a `403 Forbidden` body** (constant byte size, e.g. 138B) is a
deny-rule disguise. Before burning a bypass battery: if `POST` answers `405`, the backend is a static file
server — record the deadend with its reason and move on.
- An endpoint returning the **same error for every input** (e.g. one message for 20+ traversal encodings,
  including raw non-normalised request lines) has its validation wired to the wrong branch — no file read.
  Deadend, reason recorded.

### R8. Encrypted request channels: identify the envelope, then test keys OFFLINE
When an endpoint returns `{"payload":"<base64>"}` that differs every call:
`raw = base64.b64decode(payload)` → `nonce(12) + ciphertext + tag(16)`. All-unique nonces across 10 samples
kill nonce-reuse; a ciphertext length that never varies with input means a fixed response message.

**A GCM tag is a free offline key oracle** — a correct key makes `AESGCM(k).decrypt()` succeed, a wrong one
raises. Dictionary-test keys locally at high speed, deriving per candidate: raw bytes (len 16/24/32), md5,
sha256, truncations, hex-decode, base64-decode. ~6.5k checks/s; a few hundred thousand candidates is
minutes. Exhaust the plausible set, then state the key is strong and stop.

**Do not hunt for a decryption oracle on the protected side.** Endpoints taking an encrypted payload validate
auth *before* decrypting, so a forged payload only ever yields `401` — no feedback to learn from. Confirming
the envelope is shared (same `nonce+ct+tag` framing as the protected API) is itself reportable: it bounds the
blast radius of that key.

### R9. Reconstruct the exact ajax call before testing a body — Content-Type decides parsing
jQuery `$.ajax` defaults to `application/x-www-form-urlencoded`; `data: JSON.stringify(obj)` WITHOUT
`contentType: "application/json"` sends a RAW JSON string in a form-urlencoded body, which the server parses
differently. Read the bundle for the exact call shape (`$.ajax({`, `url:`, `type:`, `contentType:`) and
replicate it. A `200` `{"result":"error"}` with `access-control-allow-origin: *` and no field detail is
usually a Content-Type mismatch (or a score-gated captcha) — test BOTH `application/json` and
`application/x-www-form-urlencoded` before concluding the body is wrong. Real case: an endpoint rejected
JSON with a generic error for hours, then returned `{"result":"ok","leadId":...}` on the same body sent as
form-urlencoded.

### R10. Target's own surface locked → pivot to the third-party SaaS that holds its data
A hardened target (IP-whitelisted origin, F5/Cloudflare WAF blocking you) still leaks its vendor through the
page: `<script src>` and link domains point at the landing-page builder / lead-capture / marketing SaaS that
actually stores the target's customer & lead data. That vendor is usually weaker — unauth endpoints, admin
login without captcha or rate-limit, leaked nonces/keys. Run the R1/R2 sweep there.

Recon that pays off first:
- Mine page source for leaked client config: `wp_localize_script`-style blocks
(`var xxxData = {"ajaxUrl":"...","nonce":"<hex>","stock":"<id>"}`) leak the endpoint URL + a live nonce +
object IDs. `grep -oE 'var [A-Za-z]+Data = \{'`.
- WordPress: enumerate plugin versions from `wp-content/plugins/<name>/...?ver=X.Y.Z` and `/wp-json/`
namespaces, then `web_search "<plugin> vulnerability CVE"`. Login/SMS/OTP and custom plugins are the most
likely to have pre-auth auth-bypass (a phone-login plugin with weak OTP = full admin takeover); version ≤
the CVE's "up to and including" is vulnerable. A WAF can block the exploit path (admin-ajax.php POSTs) even
when the plugin is unpatched — record that as a mitigation, not a deadend.
- **Mine the operator's own announcement channel.** Grey-market platforms publish a public Telegram channel
(`t.me/s/<channel>` renders server-side, no login, and paginates with `?before=<msg_id>`) that lists every
live domain, the brand portfolio (multiple white-labels sharing one backend), the self-hosted mail system
and its registration entry, and the server/label names users type at login. Read it before subdomain
guessing — it hands you the whole estate and tells you what the login form's "server id" actually means.
Cross-match what it names against your dump (`@<domain>` emails ↔ accounts) to bind brand accounts to ids.

### R11. JWT/token auth: fingerprint the verifier before forging
A backend answering `401` (JSON) on every path still reveals its auth mechanics through error shape.
Send `Authorization: Bearer <base64({"alg":"none"}).base64({"sub":"admin","exp":NOW+86400}).` and vary:
- a NON-JWT token → `500 Internal server error` = the server tried to parse/verify (JWT auth is present);
- a well-formed JWT with a past or HUGE `exp` (e.g. `9999999999`, which some verifiers overflow to "past")
  → `"Token expired"` = `exp` is checked, likely before the signature;
- a well-formed JWT with FUTURE `exp` but `none` alg → `401/403 "invalid signature"/"Authentication failed"`
  = the signature IS verified (none rejected) — brute HS256 weak keys next; if every key returns the same
  "expired"/"invalid", the token is stateful (DB-backed) and JWT forgery is a dead end, pivot.

Layer fingerprinting: an app-level `401` has a JSON body; a CDN/ALB-level `403` has an HTML body
(`<title>403 Forbidden</title>`). `.git`/`.env`/`config.*` returning 403 (not 404) means the WAF/ALB blocks
them — the file may exist on the origin, but `%2e`/double-slash/case bypasses re-normalise and still hit
the WAF or the app's auth middleware.

**A WAF `403` on a guessed path is not evidence the endpoint exists.** Before recording "endpoint exists,
WAF-blocked" — the most expensive wrong conclusion available, because it aims every later step at a route
that may never have existed — fire three requests in one batch: a known-good route, a nonsense route
(`/<prefix>/zzzNothingXyz`), and the suspect. All three 403 = the WAF is an **endpoint whitelist** (only the
routes the client actually calls are permitted) and your suspect is simply absent: a boundary, not a target.
404 on the nonsense path with 403 on the suspect = a real keyword/pattern rule, worth a bypass battery.
Never infer the rule's *shape* from the suspect alone — a keyword list read off a handful of 403s looked
certain until names avoiding every blocked-looking word also 403'd.

**Classify the TOKEN before attacking authorization.** Fire one route with (a) no token, (b) a random token,
(c) each candidate token, and sort by the string: `token 不能为空` / `missing token` = the pre-filter rejected
you (real auth work still ahead); `登录状态已过期` / `session expired` = signature verified but the server-side
session key is dead (re-auth, do not re-verify); `access deny` / `权限不足` = **you are fully authenticated and
only authorization failed.**

The third state ends the auth phase outright. Once it appears, path mutation (`//`, `;.js`, `%2f`, case
mangling), internal-flag headers (`X-Forwarded-For`, `X-Real-IP`, a client-id header, an internal port
header) and a freshly cleared browser session all return that identical string — requests spent there are
pure waste, and a long bypass battery fired after `access deny` is the classic self-inflicted time sink. It
It also proves the two deployments share a signing key *and* a session store: a user-facing app token accepted
by an operator gateway means the remaining lever is a **privileged identity** (a token whose `user_id`/scope
carries the role), never a bypass — pivot to harvesting a privileged session, or to an authenticated route
that skips the role check, and name that as the wall in the report.

**Opaque server-signed tokens: stop forging, find the mint.** Once a structurally decoded token
(`base64("{uid}_{ts}:{sig}")`) returns one identical rejection across the whole forge matrix (empty sig,
zeros, same-length junk, uid swap, ts swap), the signature is server-side — further payload juggling is
waste. Pivot to the MINT: the client/console bundle usually contains the enter-game/create-session call that
answers a full URL carrying a fresh token (e.g. `{game_url, game_reason}`), often on a sibling vendor app.
The minted URL is itself a credential — harvest it per account/session instead of cracking.

**A token that renders with `...` in the middle is usually YOUR OWN output redaction, not server-side
masking — verify at the byte level before pivoting.** A printed `len()` of 161 beside a 14-character
rendering, plus every segment base64-decoding to valid JSON, means the token is complete and the ellipsis is
only the agent's secret filter. Confirm with `wc -c <file>` and decode in a script that writes the payload to
a file instead of printing the token. Only literal `2e 2e 2e` in the raw bytes together with a failed decode
proves real masking (a deliberate anti-leak control — then pivot to another auth path and report it as a
control, not a broken token). Never infer "WAF/app masking" from a rendered string: the direct-origin
comparison also passes through the same redaction, so it cannot distinguish the two.

**Uniform server-side `500` on EVERY authenticated route is a broken middleware/downstream, not a bad
token.** Measured: 115 distinct business routes all answered one identical generic 500 with a null trace id,
while `/login` kept returning valid data — a handler panic before trace-id assignment. Re-running the
dictionary, re-forging the token, or rotating auth headers there is pure waste; record "authenticated surface
unavailable (5xx)" and pivot to routes served by a different service.

**Verify an HS256 secret OFFLINE against one known token; never probe it online.**
`hmac.compare_digest(hmac.new(candidate.encode(), f"{h}.{p}".encode(), sha256).digest()[:len(sig)], sig)`
tests thousands of candidates per second — built-ins plus rockyou's top 200k finish in seconds. Zero hits
means the secret is strong: record the negative and do not spend the same dictionary on the login endpoint.

### R12. A passwordless low-priv role still reads the full entity set (BFLA)
Roles minted with no credential (`requires_code=false` scanner/guest entry, a QR-checkin role) are meant
for one narrow function, but the token usually still reads every entity the SPA lists and writes on the one
it touches (e.g. `check-in` flips `is_arrived`). The moment you hold a low-priv token: pull the entity
list from the JS bundle — the client references entities PascalCase (`he.entities.Registrant`) — then
`POST /entities/<PascalCase>/filter` and dump each. If `filter` demands a tenant/institution param and only
returns that tenant's rows, also hit `GET /entities/<Entity>/list?limit=N` — the list endpoint often has NO
tenant filter and returns every tenant's records (the IDOR that turns one tenant's dump into the whole
platform). Lowercase names return `"Unknown entity"` (400), which
proves the entities route exists and is reachable, distinct from `auth_required` (401). Verify any write by
reading the object back — `{"success":true}` without a read-back is not proof the data changed.

### R13. Enumeration at scale: one oracle, many egresses
When a sequential-ID endpoint hands out *another* principal's session (e.g.
`GET /api/userApi/getUserAccessToken/{uid}` → a live JWT for an arbitrary user), the ID space becomes a
full-record exporter while you hold no credential of your own. Before mass-scanning:
- **Map the three-state response first.** Distinct answers for "token returned" / "exists but no session"
  (`""`) / "ID unallocated" (`null`) bound the live ID space — without this you scan millions of dead IDs.
- **Measure density, then allocate workers.** Sample every ~1000th ID per candidate band: freshly-issued IDs
  run 60–70% hits, older bands 2–6%. Weight thread count by density and retire a band when its hit rate
  collapses instead of grinding it to completion.
- **Never share one egress between scanners and oracle probes.** A saturated egress answers 429 to
  *everything*, so the probe comes back "blocked" and you falsely conclude the endpoint is WAF-rejected.
  Give probing its own egress, or pause scanning for the probe's duration. Same-IP windowed throttles count too — an in-flight background spray from your IP consumes a login route's N/90s window, and fresh probes then read as instant rejections; stop your own jobs before interpreting refusals.
- **Multiply egresses; do not serialize them — and validate each one first.** Per-IP rate limits mean N
  independent egresses ≈ N× the throughput. Run local SOCKS/Tor circuits *and* a VPS/jump host direct **at the
  same time**, merging into one dump dir; serial rotation burns the whole budget for a fraction of the yield.
  But an egress is not automatically an egress: a Cloudflare-fronted API commonly 403s **every Tor exit** on the
  authenticated paths while the direct IP answers fine, and a jump host earns its own ban under concurrency
  ≥16. Probe one request per egress and keep only those returning real data — do not assume anonymising
  networks are unbannable.
- **Measure the sustained rate; do not set it by appetite.** On a CF-fronted API ~25 back-to-back requests is
  enough to earn a long `429` window that then blocks your probe path as well; a paced ~2.5 req/s direct run
  keeps answering for hours. Sweep scope beats sweep speed: narrow the field first (R14, R16) so the paced rate
  is actually sufficient, and give probing its own egress from scanning (below).
- **Compute saturation; do not feel it.** A set-difference of already-captured IDs against the target bands
  surfaces the un-scanned gaps — a band you consider "drained" routinely hides thousands of uncovered IDs.
  Only an empty gap list means the space is exhausted.
- **The captured session corpus is itself a lever.** Blast the harvested user tokens at ONE role-gated
  endpoint (a backend `getInfo` that answers `access deny` for ordinary users) from the fast egress to hunt a
  privileged session. A completed sweep with zero hits is a definitive, reproducible negative — record
  `checked=<N>, found=0` and retire that lever rather than re-running it later.
- **Decode the captured token locally for identity fields first.** A JWT payload is free to read and usually
  carries the login name plus an opaque session key. That is a second, request-free identity channel over the
  same corpus — it tells you which fields exist and what shape they take *before* you spend a request per ID
  enriching them, and it doubles the effective sweep rate.

Operating recipe (egress matrix, detached jump-host scans, merge/deliverable layout):
`references/mass-enumeration-throughput.md`.

### R14. Prove the target literal can exist in the field before scanning for it

Hunting one named account is a **field-choice** problem before it is a throughput problem. Sampling what you
already hold costs seconds; a sweep in the wrong field costs days and is guaranteed zero-yield.

- **Character-set gate.** Before mass-scanning for a literal (a CJK nickname, a specific prefix, a formatting
  rule), count non-conforming values over the records you already have. One `re` pass over the dump: if
  `appid`/`email`/login-name never contain non-ASCII, then a CJK target cannot be any of them, and no number
  of IDs will produce a hit. Redirect to the field that can hold it — or say so and stop.
- **Layer gate — a display name is usually not the account name.** Establish which layer owns the name you
  were given and whether *any* unprivileged endpoint returns it:

| Field | Typical owner | Reachable via |
|---|---|---|
| account id / appid / login name | business table, charset-validated | ID→record endpoints, enumeration |
| registration nickname (`nickName`-style) | business table column | usually a **role-gated** list endpoint |
| IM display name (Tencent TIM, etc.) | the IM SDK, not the web API | needs an IM credential (userSig) |
| payment-profile nickname | business table, owner-scoped | the owner's own `myPaymentWay`-style read |
| group name / group member name | group tables | group and member endpoints |

- **Sweep scope before sweep volume.** Role-gate results are cheap to obtain and decisive: fire the
  nickname-filtered list call once. `access deny` on that single request retires "search by display name"
  for the whole campaign, and what you report is that error plus the mechanism.
- When every reader of the name column is gated, **stop scanning and ask the user for a hard identifier**
  (numeric id, phone, email, account id). One id turns the whole chain back on in a single request; burning
  an ID space on a field that cannot hold the string answers nothing.
- **Never aim a campaign at a role asserted by a display string.** An IM profile `ownerID` field, a group
  member's nickname (`<brand>-group-owner`), and any client-cached label are cosmetic; the relation is owned by
  whichever API stores it. Re-read it from that API (the group-info `Owner_Account` field, the member list
  `Role`) *before* spending a dictionary on the account the UI named — the authoritative read costs one
  request, and a whole night of spraying aimed at a member the UI called the owner is unforced waste.

### R15. Calibrate an oracle against known-good and known-bad inputs before trusting any answer

An error differential is only an oracle after it has been validated in **both** directions. Unvalidated ones
manufacture both false positives and false negatives, and each one costs a whole campaign in the wrong place.

- **Fire the identical request at an input you KNOW exists and one you know does not.** Same answer for both =
  generic error, no oracle: a login endpoint answering `account or password incorrect` for existing *and*
  nonexistent accounts tells you nothing, while a friend-add endpoint answering `user not found` for genuinely
  existing accounts is a false negative — its lookup was scoped to the caller's tenant/server.
- **A differentiated login message set IS a clean 4-state oracle**, when the platform bothers to distinguish:
  `password incorrect` (exists) / `no such email` (absent) / `account disabled` (exists, blocked) /
  `account deactivated` (existed once). Confirm the states against accounts you can independently resolve, then
  use it. Ratchet that into R5: if no lockout appears after N× the wrong-password count, the same endpoint is
  also a brute-force surface — establish the limit before budgeting a dictionary.
- **Tenant/shard parameters lie.** A `serverId`-style parameter answering identically for `0`, `-1` and `9999`
  is not validated — it is a routing label, not proof of namespace separation. Settle separation with a *known
  object*: re-read an ID whose owner you already established, once per parameter value (header and query).
  Identical result = same namespace; the parameter moved nothing, so never report it as a boundary.
  A routing label still routes **credentials**, though: the same account that answers `账号或密码错误` on one
  `serverId` logs in clean on another, because the account row is visible on every shard while the
  password/registration lives on one. Before retiring a credential, replay it across every shard id the client
  sends (read the default out of the bundle) — and take the shard from the session you actually receive, since
  the reply carries the authoritative shard/app id.
- **Verify a write against the TARGET's record, not your own.** An update endpoint that accepts a target
  identifier (`userId`, `accid`, `appid`) and answers `修改成功` may have silently written to the caller:
  re-read the *victim's* object. Victim unchanged + your own record now holding the new value = the parameter
  is decorative, record it as the fake-IDOR shape. These endpoints often also carry a one-shot limit
  (`您已修改过APPID，不可再次修改`), so a follow-up attempt can never disprove it in either direction —
  decide from the first read-back.
- **Scoped lookups read as absence.** "Not found" from a lookup endpoint for an object you can read directly
  means the lookup is scoped (tenant/server/IM-app), not that the object is missing. Record it as
  scoped-with-mechanism instead of "does not exist".
- **Control-group a differential across input CLASSES before believing it.** A two-valued split that looks stable per-input (message language, wording, branch) can be a display/replica artifact, not an existence oracle: fire random nonexistent literals spanning both classes (ASCII vs CJK) plus any real account (R5). If the split tracks the input's script/class instead of existence, it is noise — stop, record it, and retire the surface. Confirm any candidate oracle with a timing payload (`SLEEP`/`WAITFOR`/`BENCHMARK`: zero delay = never executed) and keep the control evidence with the negative.

### R16. Endpoints that render a "user card" are identifier-resolution oracles

Every social/IM-flavoured API has a call the client uses to show someone else's card before you are friends
with them — add-friend preview, member search, transfer/gift recipient lookup. It resolves **any** identifier
the platform issues (account id, IM id/`accid`, phone) and returns the others, which makes it two things at
once:

- a **perfect existence oracle** when it answers an empty object for an unallocated value (allocated →
  `{"appid":"...","accid":"..."}`; unallocated → `{"data":{}}`), usable at the R13 scan rates; and
- an **identity bridge** — one request turns a leaked IM `accid` (all a chat roster gives you) into the
  platform account id, and a leaked phone into both. That is what re-joins a harvested roster (R12) to a
  business dump keyed on a different column.

Name-shape is not scope: a route named `<x>Friends<Y>` frequently resolves *any* account, friend or not, while
its sibling `<x>FriendsAppid` is genuinely friendship-scoped and silently answers `{}`. Fire both at an account
you can independently resolve before trusting either (R15).

Spend it on identifiers you already hold — dump columns, roster rows, leaked profile fields — rather than
brute-forcing an id space. Resolution is cheap, enumeration is not, and the first confirmed pairs usually
reveal the id format (brand prefix, leading-zero padding) well enough to narrow any later sweep by orders of
magnitude.

**Referral/invite platforms have their own resolution primitive.** The registration endpoint (usually no SMS
check) accepts an arbitrary invite/referral code and echoes the resolved ancestor chain back in the new
account's record (`listOfSuperiors`-style, root first): it validates codes on demand, rebuilds the upstream
spine, and controls account PLACEMENT (register directly under any node you name). Use it to confirm a spine
code exists before hunting its owner.

### R17. One object, several keys: enumerate key FORMS before declaring a field absent

The same entity is addressable by several keys (`account`/phone, numeric `id`/`accid`, nickname), and the
serializer differs per route. Measured on one platform: the **account-keyed** read returned `password` (hash),
`tradePwd` (**plaintext**), `wyToken`, device string and IP; the **id-keyed** sibling returned the identical
object with exactly those fields stripped. Read one route and you record "secret not exposed" — wrong. Fire
every key form the bundle (or your dump) shows at the same object and diff the field sets. A plaintext
trade/payment password in a leaked object is a **credential**, not a datum — test it as a login password (R18).

### R18. Cross-system reuse beats cracking a hardened store; budget cracking by cohort

The same population registers on several systems (old app + new IM/chat) — the phone list is shared. Harvest
from the side that leaks more (plaintext trade passwords; account-keyed object reads, R17) and test each value
against the target side: offline first when you hold that phone's hash
(`hashlib.pbkdf2_hmac('sha1', pw.encode(), base64.b64decode(salt), 10000, dklen=32) == base64.b64decode(hash)`
is ~1 ms/candidate), then a single online login as confirmation/fallback. Measured reuse of custom trade
passwords ≈ **4%** (small sample) — batch the whole pool; that is a login per ~25 candidates for zero
dictionary spend.

Cracking economics: the weak-password rate is a property of the **registration cohort**, not the platform.
Early users ≈64% on `123456` alone; later waves ≈0%. Sample ~20 hashes per cohort before budgeting a
dictionary — mass-cracking a late cohort is a sunk cost; spend that budget on reuse + spraying instead. And
benchmark the tool on the box before a multi-hour run: "standard" implies nothing about speed here (a hashcat
run measured ~45 H/s on one engagement where `multiprocessing` + `hashlib` did thousands).

### R19. A reset token echoed in the RESPONSE is a leak, not a bypass — close the flow first

Weak deployments return the password-reset token in the JSON body (`POST /forgot-password {"account":"admin"}` →
`{"resetToken":"..."}`) instead of mailing it. That is one report line — then stop and close the flow before
writing anything stronger:

- Fire a KNOWN-BAD token at the reset endpoint first to learn the taxonomy: a missing-field error
  (`field "newPassword" is not set`) proves the handler is reachable and names the real field; a token error
  (`invalid or expired token`) proves the token is genuinely verified server-side.
- Fire a FRESH token, minted and used in the same second. The same `invalid/expired` answer = the token is a
  display/flow artifact, not the decisive credential — the reset path needs a step you don't hold (an emailed
  code, another flow state). Record it as **token leak with unclosed flow**, never as takeover.
- Walk the required-field chain one field at a time, reading the NEXT missing-field error — it reconstructs the
  exact schema. Nested objects walk one key at a time (`deviceInfo` → `deviceInfo.name` → `deviceInfo.platform` →
  `deviceInfo.key`); each round proves the previous keys were accepted and pins the login payload shape.
- Only a completed reset PLUS a login with the NEW password justifies takeover language; the leak alone is an
  unauthenticated info disclosure.

### R20. Unauthenticated license/config endpoints hand you the operator's legal identity

Private-deployment platforms (a commercial IM/OA product sold to a company) expose `/…/user/license` or
`/…/clientConfig` WITHOUT auth more often than not, and the payload names the buyer: company name, unified
social credit code, edition, bound domain. That is an attribution goldmine — resolve the credit code in a
business-registry lookup instead of fighting WHOIS/CDN chains, and it names the exact legal entity behind a
segment you are scoping. On a mixed-stack deployment (Flutter Web app + React/Vite site+admin under one
domain), the Flutter `main.dart.js` is obfuscated with no literal paths — `manifest.json` states the product's
own description, and the React entry bundle plus its `assets/<route>-<hash>.js` chunks carry the real endpoint
table (step 1); pull both stacks' bundles before concluding the API is hidden.

### R21. A balance/credit refusal proves auth+ownership passed — price it, don't forge it

A write answering a domain code for insufficient funds (`-600`, `余额不足`, `insufficient balance`, a
`-40.00` debit estimate) has already passed authentication, ownership and schema validation. Parameter
mutation at that point (`feePayType` variants, negative/oversized amounts, injecting the server's own fee
fields) returns the identical code because the balance check executes first — that whole matrix is a retired
lever, not a bypass, and every extra attempt there is waste.

Before budgeting attempts, call the platform's own **calculate/quote** endpoint
(`.../CalculateFee?cardBinCode=&amount=&feeType=`, `quote`, `preview`, `estimate`) and read
`feeItems[].{feeName,feeAmount}` / `accountChangeAmount`: it returns the authoritative price breakdown, shows
whether the catalog's displayed fee (`openCardFee: 0.00`) is a lie, and tells you exactly what funding unlocks
the next phase. When the client cannot fund it, report the fee model as the finding and mark every downstream
object read (card / CVV / export) **untested without an owned object** — never "hardened".

### R22. A valid account TOTP is not object authorization — check which owner the factor is bound to

Sensitive object reads on card/fintech platforms often require a TOTP (`google_code`) next to the object id.
The code may be verified against the **object owner's** secret rather than the caller's, which makes a valid
account factor useless against other people's objects — an intentional anti-IDOR gate, not a bypass bug.

Discriminate in three requests before spending a bypass battery:
1. Use your TOTP on a plain login step (`login/step/two`-style). Success proves the secret, clock and
   encryption are right.
2. Fire the same fresh code at an object you do **not** own. A verification error (`100028`, "verification
   code error/reused") while login works = the endpoint is checking the owner's factor. Record it as the
   mechanism and pivot; no code offset, encryption variant or body/query flip will change it.
3. If you can create an object you own, repeat against it: success there and failure on others confirms the
   owner binding.

**Parameter placement is per-endpoint, not per-platform.** A generic "invalid request parameters" on a
complete-looking body means try the other placement before concluding the fields are wrong: JSON body ↔ query
string, and form-urlencoded vs JSON (R9). Measured on one platform: the bind endpoint read `valid_code` +
`google_code` from the **query string** (JSON body → 100004), while the card endpoints read `card_id` +
`rsa_pub` + `google_code` from the **JSON body** (query → 100004).

### R23. SockJS/STOMP chat backends: use the app's own frames, driven from a real browser

Grey-market/IM platforms expose a SockJS endpoint (`/api/ws/`, `/ws/`) whose `/info` answers
`{"origins":["*:*"],"cookie_needed":false,"websocket":true}`. Hand-rolling the xhr transport fails
(session `404`/`400` on `xhr_send`) and Node's `sockjs-client` dies on the handshake — the reliable
transport is the real browser.

1. Read the app's chat chunk for the exact STOMP frames: `client.connect({name, "X-Token": token})`,
   `client.subscribe("/mass/getResponse/"+roomId)`, `client.send("/app/massRequest/"+roomId,
   {"X-Token": token}, body)`. The token header name lives there, not in the HTTP interceptor.
2. Write a local HTML file that loads `sockjs-client` + `stompjs` from a CDN, connects to the target's
   SockJS URL, and open it with the browser tool; collect results in a `window.logs` array.
3. A successful CONNECT echoes `CONNECTED {"user-name":"<uuid>@m<id>"}` — the authenticated principal.
   The `user-name`/`login` headers are ignored when forging; the token is the whole auth.

What it buys, and its limits: subscription destinations are usually not ACL-checked (any `/topic/...`
subscribes without error) but only the app's own per-room channel carries traffic; SEND is silently
dropped when the account fails a business precondition (zero balance). Before building the socket, check
the HTTP aggregate endpoint the same page uses (`/api/mem/agg?...&rc=1`) — it often returns the same room
chat, paginated and cheaper, and it is the right place to prove the data leak.

### R24. Random-sampled/masked list endpoints: sample, dedupe, report coverage — never call it the DB

A list endpoint whose **same page returns different rows on repeat** is sampling with replacement, not
pagination. Confirm in three calls: identical IDs = stable; different sets = randomized — `page`/`sort`/
`order` may all be accepted and ignored. Fixed page counts then produce heavy duplicates: with N reachable
rows and D draws, unique ≈ N(1−e^(−D/N)) — one pass of D=N ≈63% (measured ~67% on a team tree), two ≈86%.
Measure unique/total per pass, dedupe by primary id, and stop when marginal gain collapses; never report
the row count as the table count.
- **Masking is per-depth**: direct (L1) rows often return full phone/name while deeper levels are
  server-masked (`138****6053`, `吕*凤`). Probe `type`/`level`/filter params for a variant that returns
  unmasked data; otherwise the only unmask path is holding the *direct upline's* account — each extra
  spine login adds its L1, not the tree.
- **A sampled, partly-masked API extract is never "the database".** Report unique-reachable vs stated
  total, full-field vs masked counts, and the endpoint/tier behind each. When the user asks "is this the
  complete DB?", answer with those numbers plus the missing tables (orders, capital, realname, admin) —
  do not dress a sample up as a dump.

### R25. "Change every link" is a per-surface mutation with a mandatory read-back

A mass link/redirect change is never one batch call. Inventory every URL-bearing surface first: the product
`url` is the click target; ads often carry no URL and link by product id; channel entries expose a derived
`channelLink` (domain + entry path + number), not an editable field; global settings (`WEB_DOMAIN`,
`LANDING_DOMAIN`, `LANDING_DOWNLOAD_DOMAIN`) are separate knobs; old static `/<cid>.html` pages are generated
and cached separately from the live `/entry/<cid>` page. After every write, re-read every object and count
exact matches. `code:0,data:0` from an edit endpoint is a success-with-no-op, not proof; a computed/read-only
field can return 200 and keep the old value, and changing the global domain does not rewrite stored rows.
Test one object, re-read it, then either broadcast or retire the field. For static pages compare file size,
MD5 and target-string count before/after — a generator that returns `data:0` and leaves the file byte-identical
is dead. Report a per-surface table (`products N/N`, `entry/<cid> N occurrences`, `channelLink 0/N`, `old static 0`)
and name each unchanged surface with its mechanism; never report "all redirects" while one
surface still resolves old. Adjacent file-write primitives: an injector that only replaces a placeholder in an
existing file is not a file-*creation* primitive — test a fresh filename before building a chain that needs a
fixed path. See `references/mass-link-hijack-and-write-verification.md`.

## Output conventions for this user
- Deliver a Markdown report at a stable path under the target directory, with an **executive summary first**
  (risk table: level + "verified?" + one-line impact), then per finding: reproducible command, actual observed
  output, impact, fix. Include a cleanup/verification section for anything you created.
- **Never declare a platform dead/shut down from a subset of components.** A dead app-side API coexists with a
  fully live web platform, admin backend, control plane and download/distribution path. Probe each component
  separately with timestamps (web root, business API, admin API, control-plane WS plus a live entity count,
  download/build endpoint, vendor console) and report per-component status; a "platform is winding down"
  conclusion inferred from one dead backend was disproven within minutes by the live re-check.
- **Cleanup is a checklist, not a verb.** Before closing: delete victim-PII logs and token dumps, strip
  base64 image/wallpaper fields from device dumps, redact test-account credentials from the report, kill
  egress fleets and leftover workers, and remove multi-hundred-MB samples; then re-run an audit that greps
  the report for residual credentials (expect 0), prints the case-dir size and checks for leftover
  processes. Report the before/after numbers — the user asks "is it really cleaned up?" and expects proof.
- Mark every conclusion row as **verified** or as a deadend **with its reason**.
- Do not stop at the first wall: rotate to the next surface and keep dictionaries/scanners alive in the
  background between turns; only an explicit stop ends them. A campaign is finished when every lever is
  either exploited or retired with a recorded negative — not when the first wall appears.
- **Once the user says they have no more credentials, stop asking.** Keep rotating self-service
  surfaces (unauthenticated endpoints, config files, file-write primitives, auxiliary panels) and report only the
  hard external blockers with evidence — a component/file the platform never deployed, or a random secret
  with no leak path. Re-requesting the same token/credential after a refusal is a trust loss, not a recon
  step. End a blocked turn with the per-surface matrix and the named missing component, never with a request
  for the same secret.
- A long-throttle spray (hours of ETA at the measured window) is a **background side-channel**, never the
  campaign's headline: keep it alive with a logged resume point and keep the non-credential surface moving
  in the meantime. When the user asks "is brute force all you have?", answer with the endpoint × auth-state
  matrix plus the post-access action list — a spray progress bar is not an answer.

## Support files
- `scripts/classify_api_auth_surface.py` — re-runnable: classifies every OpenAPI operation by auth state
  (empty body → schema-shaped body retry → table + JSON), embodying R1 and R2.
- `references/tg-cloud-farm-platform-chain.md` — worked platform instance: TG cloud-control / phone-farm
  SaaS (ungated task engine on 8001, timestamp IDs, plaintext SVG captcha, AES-GCM panel↔worker channel,
  origin vhost matrix, full deadend list with discriminators).
- `references/mass-enumeration-throughput.md` — multi-egress campaign engineering: egress comparison table,
  jump-host detached-scan recipe, scanner start/stop process control (self-matching `pkill`), progress-cadence
  maths, 429 cooldown, UID-gap math and the count/file/report deliverable shape.
 - `references/im-platform-identity-oracles.md` — worked instance: IM-overlay platform family (white-label
 platform fronting several Tencent-TIM universes). Client-bundle schema extraction, the identifier
 cross-resolution endpoints, member-session roster+role reads, platform config hidden in IM group metadata,
 WAF whitelist shape, and the recorded deadends.
- `references/credential-pool-tree-extraction.md` — invite/referral-tree platforms: generation-slice team APIs
  (level semantics, ignored pagination, 3-generation cap), the rolling credential-pool engine (puller / cracker /
  syncer over a file bus), coverage histograms (ID buckets, ancestor-code frequency) and the cross-system reuse flow.
- `references/audit-queue-xss-and-ssrf.md` — non-brute pivots when the admin panel is strong: SSRF via
  image-URL fields, stored XSS in operator audit queues (column-length oracle, bucket-hosted JS),
  object-storage upload-token abuse, kefu/IM visitor API, admin-vhost XFH gating and egress budgeting.
- `references/virtual-card-fee-and-bin-model.md` (in the `card-issuing-platform-pentest` skill) — virtual-card/
  BIN issuing platforms: scenario→bin→open chain, `CalculateFee` pricing oracle, negative-code map.
- `references/mass-link-hijack-and-write-verification.md` — per-surface inventory and read-back verification for
  "change every link/redirect" jobs: product/ad/channel/static-page split, derived fields, CDN/legacy checks,
  file-create vs file-update test, and the exact-count report shape.
