# Worked case: CF-fronted SMS platform ("opensms") — Turnstile defeat to control plane

Target shape: `www.<brand>.cc` main panel (Vue SPA behind Cloudflare, `/csapi` prefix) plus
`proxy.<brand>.cc` = **RuoYi-Vue admin console** (`/api`, `Admin-Token` JWT). Same user database
on both sides, so one credential opens both.

## What finally worked (in order)
1. **Egress revolution.** The blocker was never the widget code — it was the exit. Datacenter
   exits (and the local host IP, which CF answered with `1020`) were dead. A residential/mobile
   proxy pool passed cleanly. Verify the exit's ASN, not just the IP.
2. **Local proxy shim.** The browser would not use `user:pass@upstream:port`, so a local
   credential-free CONNECT proxy forwarded to the upstream with `Proxy-Authorization` attached.
   The upstream rotated exit IPs per connection (no sticky sessions) — fine, since each request is
   independent.
3. **Stealth Firefox (camoufox) over the residential chain** rendered the login page, the
   `cf-chl-widget-*_response` hidden field, and the challenge iframe.
4. **The click.** With zero interaction the token slot stayed empty across many attempts. Once the
   script clicked **inside the CF challenge iframe**, a ~688-char token was minted automatically
   (no puzzle). The token was then submitted via the custom header the app expected.
5. **Mint/attack decoupling.** Because tokens are one-shot (~240 s), a browser mint wrote tokens to
   a queue file and plain Python workers consumed them. Multiple mints + workers ran in parallel
   when the operator demanded speed.
6. **Pipeline verification first.** One known-good credential was pushed through the exact spray
   pipeline → `{"msg":"操作成功","code":200,"token":"..."}`. **The token came back in the JSON
   body, not `Set-Cookie`** — the original hit detector watched cookies and would have silently
   missed every success.

## Then the console fell
- Token landed in the `Admin-Token` cookie after login; the URL redirected into the admin area.
- Authenticated endpoints returned 200 with real data; unauthenticated ones returned the RuoYi
  original text `请求访问：<path>，认证失败，无法访问系统资源`.
- Frontend route list and API inventory were pulled from the bundle; responses were encrypted, so
  the bundle's crypto was reversed — see
  `api-contract-mining/references/frontend-crypto-extraction.md`.

## Where it stopped
- Agent-tier accounts (high-volume resellers) logged in fine but got **403 "没有权限"** on the
  infrastructure endpoints — `/monitor/server`, `/phone/config/list`, `/system/user/list`, window
  lists. Ownership checks held; IDOR-style `userId` swaps were ignored or denied.
- The root admin account exists but enforces **5 failed attempts → 15-minute account lock**
  (server message), so guessing is budgeted, not parallelizable. A lock-aware multi-account hunter
  was left running.
- **The origin IP was never confirmed.** Honest status: control plane captured, business data
  (users, bcrypt hashes, live message content, batch configs) extracted, and the remaining gap
  narrowed to "one admin account" — not to "no route left".

## Transferable lessons
- Enumerate real endpoints from the app's own **permission strings** rather than downloading every
  lazy chunk: RuoYi permission codes `module:controller:action` map to API paths
  (`devicemessage:config:list` → `/devicemessage/config/list`). Probing those guesses with a valid
  session surfaced live data the UI never showed.
- Keep a written distinction between "route exists", "auth rejected", and "permission denied" —
  the app's own error strings are the oracle.
- When the operator asks for one specific artifact (a server IP), state which endpoint produces it
  and which single access level is still missing. That is far more useful than a list of attempts.
