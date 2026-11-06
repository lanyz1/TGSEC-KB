# Capturing a live SPA's wire format (browser side)

Goal: exact ciphertext body, custom headers, cookies and negotiated crypto from a page whose
protocol you cannot read statically.

## Prefer driver-level network capture
`page.on("request")` / `page.on("response")` (Playwright, or raw CDP) hands you the real
request body (base64 ciphertext included), every custom header and every Set-Cookie — with
zero page modification, so nothing you are observing can break.

## JS hook injection: order and isolation rules
- `page.evaluate` runs in an **isolated world**. You cannot pass `ArrayBuffer`/`TypedArray`
  across that boundary (Xray "Permission denied to access property"), so crypto helpers that
  "have to run in page context" will not work from evaluate.
- A script injected with `add_script_tag` runs in the **main world** and cannot hand values
  back to your sandbox through `window.*` (separate JS contexts — `window.__res` stays
  undefined). **Use the DOM as the channel**: the injected script writes an attribute/text
  node, the sandbox polls it with `evaluate`. This was verified working where every
  `window.*` handoff failed.
- **Inject hooks AFTER the anti-bot widget has produced its token.** Installing a fetch/XHR
  wrapper before the challenge widget initialises breaks it (`widgets: 0`, no token ever).
  If you need request capture from the very first byte, use driver-level capture instead.
- On `about:blank` / `data:` / `file://` there is no cookie jar — inject only on the real
  http(s) origin.

## Anti-bot token farming
- Single-use + short TTL (Turnstile ~300 s) => run a farm: N tabs on the route that actually
  renders the widget (often `/login`, not `/`), poll the hidden
  `input[name="cf-turnstile-response"]` value, append each new value to a file.
- **Tokens are portable across IPs**: a token minted in the real browser passes the server
  handshake when replayed from plain Python/curl on a different egress (verified HTTP 200).
  So the heavy client can be pure Python and the browser only a token factory.
  Caveat: if the server binds its session to the client IP (see the `__hs` cookie in
  `references/ecdh-wrapped-json-api.md`), mint and use from one fixed egress.
- Headless: run the anti-detect engine under `Xvfb :99` when there is no display, and make
  sure that venv has the crypto deps (`cryptography`) alongside the browser package.

## Egress notes that actually decide success
- Rotating residential pools look great for reaching the page and terrible for anything
  session-bound: every connection leaves from a different IP. Fix one exit for the whole
  flow, and confirm with `https://<host>/cdn-cgi/trace` (`ip=` line) that the chain is pinned.
- Some onshore proxies fronted by nginx/Tengine answer a bare `CONNECT host:443` with HTTP
  500 and work fine once a normal browser `User-Agent` is attached to the CONNECT request.
  If a chained proxy "works for curl but fails for the browser", suspect upstream concurrency
  or slowness before blaming the protocol — and try the provider's other ports.
