# ECDH-wrapped JSON APIs (encrypted body + session handshake)

Class: SPA/API where every business call is encrypted with a per-session key negotiated by a
handshake, and the handshake itself is gated by an anti-bot token.
Reference case: opensms 短信系统 SPA (`/csapi/*` behind Cloudflare).

## Mining order (bundle first)
1. Pull the entry bundle + its lazy chunks (Vite/Webpack split chunks included).
2. grep the bundle for: `handshake`, `sessionId`, `X-Session-Id`, `X-Encrypted`, `AES`,
   `CBC`, `Hkdf`, `SubtleCrypto`, `turnstile`, and any custom `X-*-Block` string literals.
3. Those constants give you: the handshake path, the anti-bot token header NAME (often
   custom, e.g. `CF-Turnstile-Token` — do NOT assume the default `cf-turnstile-response`),
   the error-code table, and the retry policy.
4. Read the request wrapper function end to end before firing anything — it encodes the
   retry/abort rules (see 4011 below) and the content type it posts ciphertext under.

## Recovered protocol shape (concrete, verified)
- Handshake: `POST <base>/crypto/handshake` body `{"clientPubKey":"<base64 P-256 pub>"}` +
  token header -> `{"sessionId": ..., "serverPubKey": ...}`.
- Key: P-256 ECDH -> HKDF-SHA256(ikm = shared secret, info = <ASCII tag from the bundle> || 0x01)
  -> 32-byte AES key (case tag: `sms-im-ecdh-session-v1`).
- Request body: AES-256-CBC / PKCS7, random 16-byte IV prepended, base64, sent as
  `Content-Type: text/plain` + header `X-Session-Id: <sessionId>`; cookie bag via
  `credentials: "include"` carries the session cookie.
- Response: header `X-Encrypted: true` -> base64, split IV(16) + ciphertext, same AES key,
  decrypt -> JSON `{code,msg,data}`.
- Server gates surface as custom response headers, one per gate (`X-Whitelist-Block`,
  `X-Turnstile-Block`, `X-Handshake-Block`, `X-RateLimit-Block`, `X-Origin-Block`). Read those
  headers FIRST — they name the gate that rejected you.
- One-request gate classifier: send ANY value in the app's own auth header (e.g.
  `sa-token: x`). A `X-Whitelist-Block` that turns into the app's own `401 token invalid` means
  the gate is header-presence, not IP/network. Cheap and decisive.

## Pitfalls
- **The session cookie is IP-bound.** The handshake response set
  `Set-Cookie: __hs = base64("hs|<client-ip>|<ts>:<HMAC>")` — the origin signs the client IP
  into the session. If the egress IP changes between handshake and the follow-up call, the
  server answers `4011 session invalid` (or the SPA just spins on "logging in"). Decode the
  session cookie to see which IP the server recorded, and pin one egress IP for the whole
  flow (mint token -> handshake -> encrypted call).
- **Anti-bot tokens are single-use with a short TTL** (Turnstile ~300 s). Mint -> use
  immediately; a stale token produces the same answer as no token.
- **4011 is route-dependent.** The wrapper silently re-handshakes and retries on normal
  routes, but treats `4011` on `/login` as terminal (clears session, error toast). Never read
  a login-side session error as "wrong credentials".
- Do not hand-transcribe key/IV literals from a screenshot of the code — copying the literal
  bytes out of the source file saves a full debug cycle (one `+`/`t` swap cost one).
- Keep the pure-Python client and the browser token factory separate: the browser only mints
  tokens (see `references/browser-side-protocol-capture.md`), the Python client does the crypto.

See also `references/hidden-origin-recon.md` when the API you are mining is only reachable
through a CDN and its real host is still unknown.
