---
name: cloudflare-turnstile-bypass
description: Use when Cloudflare Turnstile gates a login or API.
---

# Cloudflare Turnstile bypass (getting past the widget to a real session)

Goal: stop treating the widget as the problem and instead produce a real, server-accepted
token so the authenticated session can be attacked normally.

## When to use
- A login page, admin panel or API soft-blocks with a Turnstile widget: `403`, text like
  "请先完成人机校验" / "please complete the human check", an `x-turnstile-block: 1` response
  header, a `cf-chl-widget-*_response` hidden field, or `challenges.cloudflare.com/turnstile/v0/api.js`
  in the page source.
- A scripted login works by hand but never headless / never from a script.
- You need an AUTHENTICATED session (not merely a page load) on a CF-fronted target.

## Hard facts (all learned the hard way — do not relitigate these)
1. **Turnstile is verified server-side.** Fake tokens, Cloudflare's own test keys, and
   path/method/Content-Type mutations are all rejected (returning an in-between string like
   "人机校验未通过" rather than the "not completed yet" one) — the backend really calls
   `siteverify`. Do NOT spend rounds building a bypass matrix. If you need in, mint a real token.
2. **Egress ASN is the first-class variable, not the browser.** Datacenter/cloud exits are
   judged dead nearly every time; residential/mobile exits pass. Verify the exit IP **and its
   ASN** before blaming fingerprinting.
3. **The token only appears after you interact with the challenge frame.** Injecting the widget
   and polling is not enough — you must click inside the CF iframe (frame handle `click("body")`,
   or a coordinate click). Without that, the response field stays empty forever. The second
   common cause of "no token": the widget's lazy chunk hasn't run — reload once.
4. **Tokens are single-use and short-lived** (commonly ~240 s). One token = one submit. This is
   why "solve once, then fire 500 requests" scripts produce a wall of 403s.
5. **Token transport is app-specific:** a custom header (`CF-Turnstile-Token` / `cf-turnstile-token`),
   the intrinsic field `cf-turnstile-response`, or a body param. Read it out of the bundle — a
   missed header looks exactly like a wrong password.
6. **The block marker is usually a response header** (`x-turnstile-block: 1`) or a distinct message
   string. Distinguish it from the bad-credentials message: different strings = different gates.
7. **A 200 is not a session.** The login response may be a client-encrypted blob, a redirect back
   to `/login`, or an error envelope. Confirm by calling a known authenticated endpoint and
   checking for real data.

## Decision flow
1. **Fingerprint the gate.** Edge-enforced (all static assets 403 for non-browser clients,
   `cf-mitigated: challenge`) vs application-layer middleware (assets load, one API path is gated,
   custom block header). Panels/CRMs are usually app-layer — that matters, because it means the
   rest of the API is reachable once a token is supplied.
2. **Fix egress.** Use a residential/mobile pool. Browsers generally will NOT accept
   `user:pass@host:port` for an HTTP proxy (Chrome/Firefox/Playwright strip or ignore it) — run
   `scripts/localproxy.py`, a local credential-free CONNECT shim that attaches
   `Proxy-Authorization` for the upstream hop, and point the browser at `http://127.0.0.1:8899`.
   Confirm with `curl -x http://127.0.0.1:8899 https://api.ipify.org` before blaming anything else.
3. **Stealth browser.** A hardened Firefox build (camoufox) or Chromium with a coherent
   fingerprint. Keep GPU/WebGL/WebGPU alive — never `--disable-gpu` (it destroys the exact
   fingerprint you need). Align `locale`/`timezone` with the exit's geography.
4. **Load `/login`, find the challenge frame, click it, poll for the token** (hundreds of chars).
5. **Decouple minting from attacking.** The browser is a token mint, not the spray driver: have it
   append tokens to a queue file; plain Python workers read the queue and fire requests. One
   browser then supports N parallel workers (measured ~6-12 s per token).
6. **Scale only after a known-good credential proves the pipeline end to end** (next section).

## Pitfalls
- **Validate the success detector before scaling.** A long spray is worthless if the hit detector
  watches the wrong channel — e.g. `Set-Cookie`, while the server returns the token in the JSON
  body. Push one known-good credential through the exact pipeline first; if it reports "no hit",
  the detector is broken, not the credential. (This exact bug nearly buried a working session.)
- **Never `--disable-gpu`** — kills WebGL/WebGPU, instant bot verdict.
- **The widget lives in a cross-origin iframe (often under shadow DOM).** Ordinary page-level
  selectors will not find it; use the frame handle or click by coordinates.
- **Firefox/Camoufox page hooks run in an ISOLATED world.** `page.evaluate` / `add_init_script`
  can read the DOM but cannot see page globals (e.g. `webpackJsonp`) and cannot intercept the
  page's `JSON.parse`. To hook app internals, inject a real `<script>` element
  (`add_script_tag(content=...)`) and pass results back through the shared DOM. See
  `api-contract-mining/references/frontend-crypto-extraction.md`.
- **Account-level lockouts** (e.g. RuoYi: "密码输入错误5次，帐户锁定15分钟") cap guessing at ~5
  attempts per account per window. More workers do not help; slow to the lock's budget or spread
  across accounts.
- A spray run is not "done" just because workers are alive — check for lock messages and for
  whether the credential list is even reachable behind the gate.
- Don't tell the operator the gate is defeated until an authenticated endpoint returns real data.
- **Do NOT re-inject `api.js` yourself — the console error it produces is a red herring.** If your harness
  adds the Turnstile script while the page already loads it, the console says
  `[Cloudflare Turnstile] Turnstile already has been loaded` and `window.turnstile` stays undefined. That
  message is evidence of YOUR OWN double-load, not of an ASN ban — do not use it to declare the egress dead.
  The only valid verdict channel is the hidden field (`input[name="cf-turnstile-response"]` /
  `cf-chl-widget-*_response`) after a real click on the challenge frame; pair it with the exit-IP/ASN check.
- **Cheap pre-flight before any token work: sweep the API surface with plain GETs.** Classify the statuses —
  `401` = exists, needs login · `403` = exists, gate/role refusal (may carry the block header) ·
  `404` = absent here (try the sibling host) · `200` = FREE. Do that first: if the objective's data sits behind
  an authenticated endpoint only, minting a token is mandatory and failing fast saves a whole round; if the
  endpoints return `401` (not `403`), the gate is a plain session cookie check, not Turnstile on every call.
- **A proxy can fail open.** `curl -x http://127.0.0.1:8899 https://api.ipify.org` returning YOUR OWN IP means
  the upstream is transparent/broken — the pool is dead, not the fingerprint. (Re-measured this session: a
  "residential" pool answered with the operator's datacenter IP on three consecutive tries.) Declare the
  resource gap instead of rewriting the browser harness again.
- **SOCKS/Tor takes no credentials.** `proxy={"server":"socks5://127.0.0.1:9050","username":…,"password":…}`
  makes Firefox fail with `Browser does not support socks5 proxy authentication`; pass the bare
  `socks5://127.0.0.1:9050` for Tor and keep `scripts/localproxy.py` for authenticated HTTP upstreams.

## Operator expectations for this class of work
- **Chase the session, not the token.** Turnstile gates only the LOGIN call: once the app hands back its
  session cookie (e.g. `Admin-Token`) or bearer, every subsequent API call is a plain authenticated request.
  So when the clean egress is missing, the cheapest ask is a **session handoff** — "log in once in your own
  browser and paste the cookie value" — not "find me a residential proxy". State the two levers explicitly
  (residential/mobile exit to mint a token · session cookie from the operator) rather than reporting a dead end;
  check the session TTL (30 min in this class) so the handoff window is big enough for the dump.
- When the operator locks a single objective, pursue only the path that produces it. A gated
  control plane that yields the answer beats more broad enumeration.
- If asked for speed/parallelism, actually shard and parallelize (N workers, queue-file
  decoupling) rather than re-explaining why it is slow.
- State what is still missing plainly (e.g. "needs an admin account") instead of implying
  completion, and lead with what was newly broken open.

## Files
- `references/opensms-turnstile-case.md` — worked case: CF-fronted SMS platform, Turnstile defeat,
  RuoYi admin console, AES key extraction, lockout budget, what stayed blocked.
- `references/opensms-gate-reanalysis-2026-09.md` — second pass on the same case: full authenticated-API
  sweep results (401/403/404 map), ECDH-handshake sibling console, sitekey/header/TTL extraction, why
  token minting failed from both a datacenter and a Tor exit, and the session-handoff ask.
- `scripts/localproxy.py` — credential-free local CONNECT proxy chaining to an authenticated
  upstream proxy (the browser-compatible egress shim).
