# Hardened code-split SPA + JSON API panel: exhausting the perimeter

Worked case: `n70jb8b.shop` ("Telegram鱼苗系统" — Telegram account-farm / phishing
C2). Vue3+Vite SPA behind nginx, JSON API with a uniform `{"message","success"}`
envelope, Go-ish router (net/http style trailing-slash `301`s). Outcome: **no
unauth entry existed**; the whole engagement came down to naming the one gate.
Everything below is measured, not assumed.

## 1. Build the complete route inventory from the SPA — never guess it

- `index.html` names one module bundle; the app is code-split, so fetch **every**
  `assets/*.js` chunk and grep each for API paths in `'`/`"`/backtick strings
  **and** for template literals: `` `/api/sessions/${id}/messages/${n}` `` →
  substitute `1` for every `${...}` to get a probeable path.
- **Check `/assets/` for autoindex** (`200` + `<pre><a href=`). It yields the full
  build file list with hashes: proof nothing was missed, plus a stable signature
  for change monitoring (new build hash ⇒ new endpoints). Same for any real dir.
- Result here: **83 endpoints** across sessions (import / `tdata-export` / passkey
  create|export|reuse), chats+messages (read **and** `send`), intercept
  (address-library / keys / upload-qr), listening-alert, data-center (AI scoring,
  extract-all), login-bots (mass account login), users/settings/logs.

## 2. Establish both oracles before any fuzzing

- **SPA fallback trap**: every unknown *non-`/api/`* path returns `200` with the
  same ~773 B `index.html`. Store the shell's first bytes and treat a byte-identical
  body as "not a hit" — otherwise every fuzz row reads as a 200 and you learn nothing.
- **API oracle**: unknown `/api/*` → `404 {"message":"API not found"}`;
  a real route → `401 {"message":"未授权访问"}` (or `405` for a method mismatch).
  `401`-vs-`404` is a clean, high-signal existence oracle.

## 3. Prove completeness with a 2-D matrix (this is a deliverable, not busywork)

`/api/<module>/<action>` over ~45 modules × ~44 actions × GET+POST ≈ 3.5k requests,
12 threads, plus a flat wordlist (1159 paths) and a dedicated per-port dictionary.
Here: **zero new routes** → the report can state "inventory complete, 4 public
endpoints, all others enforce auth", which bounds the panel from the outside.

## 4. Login timing side-channel = username directory (needs direct egress)

- Baseline: median of ≥5 requests with a random username. Candidate: median of 8.
- Existing user ⇒ backend performs the slow-hash compare: **+280 ms** here —
  `admin` 753 ms vs 429–458 ms for 24 other names, reproducible on every run.
- Cost: each probe consumes login rate-limit budget, so only test ~25 plausible
  names (3 samples, spaced). This found that the panel had **exactly one account**
  (`admin`) and no agent/customer logins — a real CWE-208 finding *and* the input
  to a targeted spray.
- Caveat: needs direct (non-WAF/Tor) egress and a slow hash. Over jittery egress
  it is noise — see `password-spray-lockout-bypass`.

## 5. Rate limiter: find its key, then decide honestly

- Rapid burst → `429` at ~10; spaced requests pass; **no permanent lockout**.
  Measured: 10 attempts / short window, keyed per IP.
- Test spoofability with header variants — `X-Forwarded-For`, `X-Real-IP`,
  `Client-IP`, `X-Client-IP`, `True-Client-IP`, `Forwarded`, `X-Originating-IP`,
  `X-Remote-Addr`, `X-Forwarded`, `CF-Connecting-IP`, `X-Forwarded-For: a, b`,
  `127.0.0.1` — **all still 429** ⇒ bound to the real IP, not bypassable.
- **Test each public endpoint separately.** `login` and `verify-code` were limited;
  `web-login/send-code` was **not** (30 rapid calls, zero 429) ⇒ report as an abuse
  primitive (unlimited Telegram login-code triggering) rather than as "rate limited".

## 6. One pass for each auth-bypass class (all clean here)

- Forged tokens: `alg=none`, HS256 over 10 common secrets, plain base64 claims,
  empty/`null`, 5 alternative header names → all `401`.
- Header trust injection, 31 variants: `X-Internal`, `X-Debug`, `X-Admin`,
  `X-Api-Key`, `X-User`/`X-Username`/`X-Remote-User`/`X-Forwarded-User`,`X-Impersonate`,
  `X-Original-URL`/`X-Rewrite-URL`, `X-HTTP-Method-Override`, `Basic YWRtaW46YWRtaW4=`,
  `Cookie: is_admin=true` → all `401`.
- Path/method: `//`, `;`, case flips, `%2e`, `..;/`, trailing `/`, PUT/DELETE/OPTIONS,
  absolute-URI request line (`GET http://127.0.0.1:8080/...`) with an internal `Host`
  → normalized to `404`/SPA. Path tricks do not move an **app-level** middleware.
- Smuggling: raw-socket CL.TE / TE.CL / a smuggled internal request → nginx `400`,
  no desync, single response.
- Cache: `x-cache: MISS` on every repeat (never `HIT`) ⇒ caching effectively off,
  no web-cache-deception path; also proves the IP you hit *is* the origin.
- Static/scaffolding sweep: `.git`/`.env`/`*.js.map`/`*.zip`/`*.sql`/`phpinfo`,
  runtime config (`env.js`, `runtime-config.json`), service worker + precache
  manifest, `/assets/` subdirs, `.php` paths, backup/config filenames → all absent.

## 7. Criminal-SaaS logic: the phishing flow is the only unauth surface

```
POST /api/sessions/web-login/send-code {phoneNumber, agentId, inviteToken}
   -> 200 {data:{loginId}}            # triggers a Telegram login code to the victim
POST /api/sessions/web-login/verify {phoneNumber, code, password,
        agentId, inviteToken, loginId, tempSessionId}
   -> account taken over
```

`inviteToken` is issued per agent (`/api/settings/invite-token?agentId=`) and is the
single gate: wildcard/regex/SQL-ish/type-confusion attempts all return the same
`403 邀请链接无效或已过期`. Front-end strings leak the true purpose ("我们已将验证码发送
到您其他设备上的 Telegram 应用程序", "验证期间请勿频发消息…以免触发官方风控") and the
targeted countries (Uzbekistan / Kyrgyzstan / Kazakhstan / Indonesia / Algeria /
Saudi / Albania).

**Consequence for the engagement:** when every other surface is closed, the entry
is *distribution-side* — a real invite link from a phishing SMS/TG message. Ask the
user for it explicitly, and have a one-shot client ready that parses the link,
validates it, walks send-code → verify and reports whether `verify` hands back
victim session data (`n70_phish_flow.py` pattern).

## 8. OSINT on the kit itself — cheap, and it closes or opens a whole branch

- Sourcegraph public code search / GitHub / Gitee for distinctive frontend strings
  and localStorage keys (`web_login_phone_form`, `defaultInterceptConfig`,
  `recent-fish-records`, `web-login/send-code`, the product name) → **zero hits =
  private kit ⇒ no vendor default credentials to borrow**. Say that explicitly
  instead of leaving the branch vague.
- Phishing/malware URL feeds (URLhaus, OpenPhish, `Phishing.Database` full dump)
  and urlscan for the domain → no entries ⇒ the platform is still **unflagged**,
  which is itself a report line (and explains why no invite link is indexed).
- RDAP/CT/passive DNS for attribution: registrar, registration date, cert renewal
  cadence (a 4-month-old domain with renewing certs = actively operated).

## 9. Reporting when the perimeter genuinely holds

Per layer, state **what was measured** (counts + status codes), list the real
weaknesses found — here: timing-based username enumeration, `/assets/` autoindex,
an unlimited public phishing endpoint, 10/window limiting with no lockout — then
converge on "the only remaining entry is X and it requires Y". Never conclude "no
way in"; name the exact input you need from the user (an invite link) or the exact
authorisation (a bounded credential run) and stop there.
