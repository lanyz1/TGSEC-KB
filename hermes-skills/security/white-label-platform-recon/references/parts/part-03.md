# white-label-platform-recon 全文 第 3/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

