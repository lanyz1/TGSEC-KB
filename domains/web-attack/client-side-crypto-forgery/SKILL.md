---
name: client-side-crypto-forgery
description: Use when frontend JS decrypts data client-side.
---

# Client-Side Crypto Forgery

## When to use
- A URL parameter or page payload is encrypted/signed by frontend JS (`?data=`, `?token=`, `sign=`).
- A cashier/checkout page renders order details from a client-decrypted blob.
- You must decide whether the server trusts client data or the client only renders it.

## Procedure
1. **Get the right bundle.** Download the page's lazy chunk, not just the entry bundle. Payment pages are usually a separate chunk (`home.<hash>.js`). Grep for crypto calls:
   ```bash
   grep -oE '\.(decrypt|encrypt)\(|CryptoJS|JSEncrypt|sm2|sm4|atob|mode\.|padding\.' page.js | sort | uniq -c
   ```
2. **Read the caller, not the library.** Library source dominates the noise. Find the call site where the key is a literal:
   ```bash
   grep -n 'decrypt(' page.js
   ```
   Record algorithm, mode, padding, key, IV, and what feeds the input (e.g. `Base64.decode(query.data)`).
3. **Map encoding layers.** Common shape: `data = base64(base64(ciphertext))` because `Base64.decode()` returns a UTF-8 string that CryptoJS then base64-parses again. Detect: decode once; if the result is 100% printable ASCII and itself base64, decode again; require `len % 16 == 0` for AES.
4. **Replicate in Python.**
   ```python
   raw = base64.b64decode(base64.b64decode(data))
   pt = Cipher(algorithms.AES(key), modes.ECB()).decryptor().update(raw)
   out = padding.PKCS7(128).unpadder().update(pt) + ...finalize()
   ```
   If unpadding fails, try byte offsets 0..15, CBC with zero/key IV, key variants (md5/sha256/reversed), and the single-base64 layer before concluding the key is wrong.
5. **Verify the key on the LIVE build.** Do not trust docs samples: docs are often generated with an older key. Encrypt your own minimal JSON, open the live page, and compare against a wrong-key control. Right key renders content, wrong key renders blank.
6. **Recover the schema from the component.** Grep the chunk for `type==="..."`, prop names, and branches (`QRIS`, `VA`, `bankCode`, `originalCurrency`). Empty render for both sample and forged payload usually means a missing branch field, not a wrong key.
7. **Assess server-side impact.** Watch network requests and read the component. If the page only renders (QR, amount, account number), impact is display forgery/phishing. If it calls an API with the decrypted data, test SSRF (notifyUrl/callback), open redirect, and order creation.
8. **Evidence.** Screenshot the forged page on the production domain, save the exact payload, and record key/mode in the report.

## Pitfalls
- **Do not claim open redirect** just because a data field feeds `location.href`; read the component. Many fields are interpolated into a fixed template (`alipays://...&qrcode=<enc>`), leaving only an encoded suffix controllable.
- **Base64 in docs is split by HTML syntax highlighting.** Strip tags first, then whitespace, then regex; verify `len % 4 == 0` and ciphertext `% 16 == 0`.
- **CryptoJS string decrypt re-parses base64.** Passing a js-base64 decoded string means double base64 — that is why block alignment appears broken.
- **Wrong key vs missing field both render blank.** Always include a wrong-key control and a branch-complete payload.
- **Stay in scope.** Upstream issuers/processors identified from BINs or docs are separate companies; do not credential-attack them without explicit authorization.

## References
- `references/dpay-cashier-forgery.md` — worked example: DPAY payment page key, double-base64 scheme, payload schema, production verification.
