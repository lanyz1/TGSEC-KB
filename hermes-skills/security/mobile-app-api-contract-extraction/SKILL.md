---
name: mobile-app-api-contract-extraction
description: Use when an APK must yield its API contract or keys.
---

# Mobile App API Contract Extraction

Goal: from an APK alone recover base URLs, endpoint lists, auth header scheme, signing/crypto algorithms and hardcoded keys — enough to call the backend directly.

## Step 0 — get the APK

If the store/distribution link is dead, look for a "官方下载链接公示" article inside the app's own content API (article list -> detail). Those pages are often served by the same unauthenticated content endpoint and carry 3-5 rotating CDN short links. Signed download URLs usually have a millisecond `t=` param and expire in minutes: fetch the short link and follow redirects in one curl (`-L`), never save the signed URL for later.

## Path A — Flutter (libapp.so)

1. `unzip -o app.apk -d x`; real code is `lib/arm64-v8a/libapp.so` (Dart AOT). `classes.dex` is only the shell.
2. `strings -n 6 libapp.so | grep -oE 'https?://[a-zA-Z0-9._:/-]{5,100}'` → hosts and ports first (fast win).
3. Full recovery: `python3 /opt/tools/blutter/blutter.py <lib/arm64-v8a dir> <out dir>` (needs dartsdk bundled).
4. In `out/asm/`, the two files that matter are `openim_common/src/apis.dart` and `openim_common/src/urls.dart`:
   - `grep -oE 'r16 = "[^"]+"' urls.dart | sort -u` → **complete endpoint list**
   - `grep -n -B10 -A25 '<fieldName>' apis.dart` → exact JSON body keys
   - `grep -rn 'chatTokenOptions\|operationID' asm/` → auth header scheme
5. JWT/auth: dynamic `operationID` (ms % 60) and `token: DataSp.chatToken` means the server issues the JWT — no client-side key to steal. Confirm by testing: standard HS256 `{"sub":"1","exp":...,"iat":...}` returns `signature is invalid` (format ok), `{"userId":...}` returns Malformed (payload shape wrong).

## Path B — uni-app (plaintext)

1. `unzip`; code lives at `assets/apps/__UNI__*/www/app-service.js` — **not obfuscated**.
2. `grep -oE '"(https?://[^"]+|/[a-z]+/[a-zA-Z]+)"' app-service.js` → base URLs and every `A("/path",...)` call = full API list (100+ endpoints typical).
3. `grep -oiE '.{200}(apiKey|appKey|encryptData|sign=).{300}' app-service.js` → keys and crypto:
   - AES-CBC: `key = apiKey`, `iv = apiKey.substring(0,16)`, PKCS7 — reimplement in Python with `cryptography`
   - signature: `md5(sha1(params sorted joined by '&'))`
4. Check whether the crypto is actually wired up: if `encryptData(` has **no call sites**, it is dead code and the real transport is plaintext JSON + `Authorization` + `X-App-Version`.
5. `manifest.json` holds only app version/metadata; the API base may be hardcoded to `http://127.0.0.1:9001/api` in a dev build — that APK cannot talk to production, but its **endpoint list is still valid against the production API** (verify each path on the live host).

## Step 2 — turn the contract into findings

- Replay every recovered path against the live API with a real token; new paths often expose IDOR (`user/check?mobile=` -> realname), mass-assignment (usually ignored), upload without type check, or "export" endpoints.
- **List endpoints: recover the real pagination param names before believing a row count.** A list returning a flat 10 rows regardless of `page`/`limit` usually means those names are ignored — probe `pageNum`/`pageSize` (Go/GORM convention) and read `totalNum` from the body as ground truth. Two calls with `pageSize=50` on page 1 and 2 confirm paging is real and reveal the full corpus (e.g. 78 articles where the naive call showed 10).
- For file/attachment endpoints, check whether the upload path is fixed server-side: send `filename=../../x`, and `dir`/`path`/`folder`/`prefix` form fields, then compare the returned `picurl`. If it always comes back as `uploads/YYYYMMDD/<md5>.<ext>`, the path is server-generated and traversal is dead — stop there.
- If an endpoint takes an int ID and returns 500 on strings, it is type-validated Go — stop probing for SQLi there.
- If auth uses `token` + `operationID` headers and every path (even login) demands a token, the server-side JWT is unbypassable from the client: record it and move on instead of brute-forcing HS256 secrets online (>1M guesses at 2/s is useless).

## Pitfalls

- `strings` on `classes*.dex` of a packed APK yields SDK noise; do not conclude "no domains" before checking `libapp.so` and `assets/`.
- Cert SAN / crt.sh only shows hosts that got certificates — a vhost can live on an IP with no DNS (test `curl -H 'Host: <domain>' https://<ip>/`).
- Signed CDN links expire mid-analysis; re-request the short link rather than retrying the saved signed URL.
- Authorization header (not cookie) means even a permissive CORS (`reflect any Origin` + credentials) cannot auto-authenticate a cross-site request — rate it medium, not critical.
- **A payload stored in a field is not an XSS finding until a render sink exists.** `meetName`-style setters may accept `<script>` verbatim, but before writing it up count the sinks in the admin bundle (`grep -c 'v-html' adm_app.js`, inspect `innerHTML` hits) and remember Flutter `Text` never parses HTML. Zero sinks = storage-only, medium/low — say so instead of implying admin takeover.
- **Code-host searches for the brand acronym return same-name false positives.** A repo matching `lvzhuan` may be an unrelated legal-job AI project; verify description, language and file tree before pivoting the engagement onto it.
