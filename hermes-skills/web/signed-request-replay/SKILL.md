---
name: signed-request-replay
description: "Use when a site 403s/301s API calls but works in-browser."
version: 1.0.0
tags: [waf, cdn, anti-bot, request-signing, browser, replay]
---

# Signed-Request Replay (front-end / CDN request signing)

When a bare HTTP client gets 301/403/rejected but the same call succeeds in a
browser, the block is usually a **client-computed anti-bot signature**, not a
broken endpoint. Identify it, extract the algorithm, replay.

## Signal: you are being signed-gated, not blocked

- A POST with a JSON body to an otherwise-working endpoint returns a **bare 301
  with no `Location`** (or a generic CDN rejection) while GETs pass.
- Response headers name a CDN (`Server: Xcdn`, `X-Cache`, `CF-`, 加速乐/Jsl,
  瑞数) rather than the application stack.
- The page loads a crypto lib (`crypto-js`, `jsencrypt`, `elliptic`, `sm-crypto`)
  plus a bundle referencing `sign` / `nonce` / a timestamp.
- Worked example: **Xcdn** enforces `X-CDN-TIMESTAMP` (unix seconds) +
  `X-CDN-VERIFY-CONTENT` (the signed content, e.g. account + encrypted password)
  + `X-CDN-SIGNATURE`. Miss one and the CDN rejects the request — which reads
  exactly like "bare requests fail, the browser works fine".

Same shape applies to Akamai sensor data, custom HMAC headers, and
kuaishou/maotai-style `X-Sign` schemes.

## Ladder: cheapest replay first

1. **Run the request inside the page (most reliable — do this first).** With the
   target page loaded in a real browser session, `fetch()`/`XHR` from the page
   context inherits the site's own signing, cookies, and origin. No
   reimplementation, no key extraction, no reverse engineering.
2. **Capture what the page actually sends.** Wrap the send path
   (`XMLHttpRequest.prototype.setRequestHeader`, `window.fetch`) *before* the
   app's JS runs, trigger the app's own call, and read the exact header set and
   body. This yields the header names, the signed content, and the signer's
   identity without reading any obfuscated code.
3. **Read the signing function's source from the live page.** The definition is
   usually obfuscated and **not where the bundle suggests** — do not burn time
   grepping bundles for it. Ask the loaded page:
   ```python
   js("typeof buildLoginSignHeaders")
   js("buildLoginSignHeaders.toString()")   # algorithm + any embedded key
   ```
   If it is not a global, get it from the step-2 hook (capture the producing
   function from the call stack).
4. **Reimplement only when you need bulk/headless replay.** Transplant the
   extracted algorithm + key, then **verify against a request the page itself
   just made** before trusting it. Do not assume transplant fidelity.

## Pitfalls

- **Your HTTP client silently rewrote the request.** `urllib` follows redirects
  by default and converts a redirected POST into a **GET**, so the server answers
  "unsupported request method: GET". You will then spend an hour "discovering"
  that the endpoint rejects POST when in fact your own client demoted it. Use a
  no-redirect opener (`HTTPRedirectHandler` subclass returning `None`) or raw
  `http.client`, and read the raw 301 before interpreting any application error.
- **Classify the failure before fixing it.** Client-side rewrite (above), CDN
  rejection (bare 301 / CDN `Server` header), and application error (JSON
  `code`/`scode` body) are three different problems with three different fixes;
  the error text alone will not tell you which one you have.
- **Try the unsigned channel before reimplementing crypto.** If the CDN only
  fronts 80/443 and forwards other ports transparently (L4) or the origin IP is
  directly reachable with the right `Host` header, the signed layer may be
  absent there entirely.
- **A signature is not an exploit.** It grants the same API access the browser
  already had — replay, not privilege. Keep every request within the role the
  session actually holds.

## Login endpoints: the signer is where the credential verdicts live

Login pages carry the signer call literally — `headers:
Object.assign(buildLoginSignHeaders(account, encryptedPassword))` — and every
panel of one product (customer / reseller / admin) ships the **same copy**.
Read the app's own call site before concluding a password is wrong, and A/B it
before rebuilding a signer:

1. **A/B the login endpoint itself, signed vs bare, before investing in the
   signer.** The app's JS naming the signer does not prove the server enforces
   it: on the platform this came from, bare requests logged in just as well.
   Inferring "no signature = cannot log in" from the call site alone burns a
   whole round reinventing a signer you never needed. The same applies the
   other way — see the 判断价值 step above; A/B decides, the code does not.
2. **Business error codes only mean something once the request is well-formed.**
   A login that discriminates `wrong password` / `enter the code` / `code
   invalid` is the best oracle on the target — but the same vocabulary shows up
   for a malformed request, so you can misread it as "password correct, only
   TOTP missing". Calibrate first: send a **known-existing account with a
   deliberately wrong password**, confirm you get the wrong-password code, then
   interpret every other code against that baseline.
3. **Encrypt → sign → send in one process.** The signature covers the real RSA
   ciphertext and PKCS1v15 output is randomized per call, so a ciphertext
   produced in an earlier run cannot be signed in a later one.
4. **Fingerprint the public key across panels.** An identical sha256 prefix in
   the customer / reseller / admin bundles means one family-wide keypair —
   extract it once; a different fingerprint means that panel decrypts on a
   different key (seen: the reseller panel carried its own).
5. **A stubbed crypto lib turns the ciphertext into plaintext, and the server
   disguises it as bad credentials.** Bundles routinely write `encryptPassword`
   as `try{...}catch(e){return password}` — stub the library and it silently
   returns the plaintext, the server's RSA decrypt crashes, and you get a
   generic `500 系统异常` that reads exactly like a wrong key. **Judge by
   length**: 2048-bit RSA in base64 is ~344 chars; a dozen chars means nothing
   was encrypted. Fix it by doing that step with the platform's native
   primitive (`crypto.publicEncrypt({padding: RSA_PKCS1_PADDING})`) and using
   the bundle only to produce the signature headers.
