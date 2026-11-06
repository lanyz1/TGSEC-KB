# Reversing an SPA's embedded crypto/session protocol (and reusing it)

Source case: `www.opensms.cc` / `www.opensms.xin` "SMS panel" — Vue SPA on CF Pages + CF Worker in front of a hidden origin. The client protocol was fully recovered; the server-side session gate still refused every scripted login. Both halves are reusable.

## 1. Finding the protocol in the bundle
- Vite/webpack builds keep lazy route chunks under `/assets/` (`Login-*.js`, `sysConfigStore-*.js`, ...). A grep pass that only hits the root path misses every chunk — always fetch the chunk map from the entry bundle and re-request with the `/assets/` prefix.
- High-yield grep tokens: `fetch(`, `axios`, `/api/`, `handshake`, `encrypt`, `decrypt`, `AES`, `subtle`, `pubKey`, `sessionId`, `randomString`, `token`.
- Anchor-then-window: locate the anchor string, then dump `s[i-2200:i+900]` around it. Reading the whole **function window** (not the call site) is what exposed the full handshake, the crypto primitives and the header set.
- Developer comments leak topology. The shipped bundle contained a note that the CF **Worker `ORIGIN` must point at the real API, not the Pages domain** — i.e. the origin is intentionally hidden behind a Worker. Bundles also leak hardcoded hosts (a dead IM host `smsb3.1sms.co` was found this way).

## 2. The recovered protocol (pattern class: JS-crypto + challenge-token panel)
- Handshake: `POST /csapi/crypto/handshake` body `{"clientPubKey": <P-256 SPKI b64>}` + header `CF-Turnstile-Token: <token>` → `200 {sessionId, serverPubKey}` plus `Set-Cookie: __hs=` (HttpOnly, Max-Age 300).
- Key derivation: ECDH P-256 → shared secret → HKDF-1 (`HMAC(zero32, shared)`, then `HMAC(prk, "sms-im-ecdh-session-v1" || 0x01)`) → 32-byte AES-256 key; 16 random bytes prepended as IV.
- Business requests: `X-Session-Id: <sessionId>`, `Content-Type: text/plain`, body = base64(IV || AES-256-CBC-PKCS7(plaintext)), sent with `credentials: "include"` so the `__hs` cookie rides along.
- Responses carry `X-Encrypted: true`; the **whole body** (not a JSON envelope) is base64(IV || CT) — decrypt first, then JSON-parse. A parser that expects `{"code":..,"data":"<b64>"}` will look "correct" and fail.
- **Gate headers name the gate that rejected you** — `X-Whitelist-Block`, `X-Turnstile-Block`, `X-RateLimit-Block`, `X-Handshake-Block`, `X-Origin-Block`. Read them before blaming credentials: `X-Handshake-Block` = session unrecognized, and "请先完成人机校验" in the UI maps to that header (the login request itself carries no captcha field).
- Turnstile is enforced on the **handshake**, not only on page load: each login = its own handshake = its own token. Tokens are single-use and ~300 s, but **portable across egress IPs** (mint in a browser, use immediately from Python).
- SPAs built on CryptoJS use pure-JS AES: `crypto.subtle` hooks capture nothing. Hook the JS function itself, or better, capture wire traffic.

## 3. Observing the SPA without breaking it
- Never install a `window.fetch`/`crypto` hook **before** the captcha widget has produced a token — the hook breaks widget setup and every later read returns `token 0`.
- Prefer CDP / Playwright response listeners (`page.on("response")`) over JS hooks: zero interference, still gives headers + bodies.
- Playwright-Firefox: `add_script_tag` executes in the **main world**, `page.evaluate` in an **isolated world**; they cannot see each other's globals (all reads return `UNSET`). Bridge values through the DOM (hidden attribute / dataset) instead of globals.
- Captcha widgets are usually route-scoped (`/login`); loading `/` reports `widgets 0` and looks like a bypass failure when it is only a wrong URL.

## 4. When a fully reversed protocol still fails: the server-side session gate
Symptom sequence: handshake 200 → correct cookie → correct crypto → login still returns the app's `4011 会话已失效`; same result when the request is issued **from inside the page**, and the SPA's own UI spins forever on "登录中...". Diagnosis: the origin's session store is keyed on state a replayed client cannot satisfy (client IP *as the origin sees it*, plus registration at challenge time).
Operating rule: after ~2 clean reproductions fail while the real UI works, **stop re-implementing and start reusing** — drive the real browser UI as the session factory (log in via UI, lift the resulting session/token for scripted API calls), and pin the egress so browser and script share one IP.

## 5. Pinned egress (validated)
- Tor `HTTPTunnelPort 8118` + a **fixed SOCKS proxy username/password** = circuit-isolation key ⇒ exit IP pinned for every client presenting that credential. Verified: two requests returned the same exit, and a browser-minted Turnstile token was accepted from Python when both used the pin.
- Tor `ControlPort 9051` with `CookieAuthentication 0` allows `SIGNAL NEWNYM` for on-demand IP rotation (needed when a lockout is per-IP).
- Without proxy auth Tor also reuses one circuit per destination, so the exit is stable per destination — but browser and CLI can land on *different* circuits, which is exactly why the pin is needed.
- Datacenter exits frequently pass CF's edge yet **never yield a Turnstile token** (`widgets 0` on `/login`); residential and Tor exits do. Test the exit against the captcha before building on it.

## 6. Adjacent: detecting an origin hidden behind a CF Worker
(These belong to `security/cdn-origin-tracing`, which is user-owned — run `hermes curator adopt security/cdn-origin-tracing` to let them be written there.)
- `site.ip138.com/<domain>/` was the last-resort historical A-record source after the Western free PDNS all failed or blocked; it only carries history for the apex, not subdomains.
- **CF-egress probe**: fetch a candidate IP through a service that itself runs on Cloudflare's network (a CF-Worker-hosted fetcher, e.g. Microlink) — an origin that is merely firewalled to CF ranges answers, a dead host returns `statusCode: null`. Include a known-live control IP in the same run or the null proves nothing.
- **Check `whois` Creation/Updated date early.** The target domain had been re-registered the day before; the historical A-record trail (3 Alibaba-HK IPs from 3 months earlier) belonged to the *previous* registration and was entirely dead. A /24 neighbourhood sweep with per-IP `Host:` spoofing confirmed no live target, but the creation date is what explained why.
- Domain re-registration reframes the whole hunt: "the origin moved" is not the same as "the origin is hidden".
