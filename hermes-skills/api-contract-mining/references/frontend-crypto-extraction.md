# Frontend crypto extraction (read a SPA's encrypted API off-line)

Use when the bundle you mined shows the app encrypting requests and/or decrypting responses
(`AES.decrypt`, `CryptoJS`, `JSEncrypt`, `setPrivateKey`, `mode: CryptoJS.mode.CBC`, `iv:` …).
The point is to stop fighting the UI and talk to the API directly, at full speed, in plaintext.

## Step 1 — locate the crypto in the bundle
Grep the chunks (and the *live* bundle served today, not just the version you downloaded):

```
AES\.decrypt|AES\.encrypt|CryptoJS|mode\s*:|padding|setPrivateKey|JSEncrypt|RSA
enabled\s*:\s*!0\s*,\s*key|\biv\s*:|baseURL\s*:
```

Look for a config object holding `key`/`iv`. Keys are frequently hardcoded literals (a real
finding — client-side crypto with a shipped key is obfuscation, not security). Also look for RSA
key pairs; finding a *private* key in a frontend bundle means the dev pasted the wrong half.

## Step 2 — copy literals programmatically, never by hand
Do not retype a base64 key. Transcribing adjacent characters wrong (`t+` vs `+t`, `l` vs `I`) is
extremely easy and produces the most misleading symptom in this whole workflow: **short responses
decrypt fine, long ones fail, and the failure starts with constant garbage** — which reads like
"per-session keys" and can burn hours. Write the extracted value straight to a file from the script
that parsed the bundle, and reload the file for every later step.

## Step 3 — pin down the algorithm
- Mode/padding: CBC + PKCS7 is the common default; ECB shows up in older code.
- Key length: 16/24/32 bytes → AES-128/192/256. Base64 decode: 32 bytes = AES-256.
- Static vs per-request: check whether the same (key, iv) decrypts two different requests. If the
  IV changes per request, find where it is transmitted or derived.

## Step 4 — replicate in Python and VERIFY against ground truth
```python
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

def aes_cbc_dec(b64_ct: str, key: bytes, iv: bytes) -> bytes:
    ct = base64.b64decode(b64_ct)
    d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    pt = d.update(ct) + d.finalize()
    u = padding.PKCS7(128).unpadder()
    return u.update(pt) + u.finalize()
```
**Verification that actually proves the key:** decrypt a request body *you generated through the
UI* (or captured from the browser) whose plaintext you already know — e.g. a login payload. If it
comes out as `{"username": ..., "password": ...}`, the key and mode are correct. Never validate a
key only with a response whose plaintext you cannot independently predict.

## Step 5 — when the static key does not decrypt a response
Before concluding "per-session keys": re-check the key literal (step 2), then test whether only
*some* bodies fail (a size threshold or a differently-encoded envelope is far more likely than a
rotating key). If it still fails, stop fighting it and **hook the app's own decryptor**: inject a
real `<script>` into the MAIN world that wraps `JSON.parse` (or the axios response interceptor) and
flushes cleartext into the DOM, then read it from outside.

> Firefox/Camoufox note: `page.evaluate` and `add_init_script` run in an **isolated world** — they
> see the DOM but not page globals (no `webpackJsonp`) and cannot intercept the page's
> `JSON.parse`. Inject a genuine `<script>` element (`page.add_script_tag(content=...)`) and use the
> shared DOM as the return channel. Vite builds have no `webpackJsonp`; use the app's own axios
> instance / response interceptor instead of guessing chunk ids.

## Step 6 — turn the bundle into an API contract
- Derive real endpoints from the app's own authorization strings. In RuoYi (若依)-style backends the
  permission code `module:controller:action` maps to the API path
  (`devicemessage:config:list` → `/api/devicemessage/config/list`). Probing those guesses with a
  valid session surfaced live data the UI never rendered.
- RuoYi API model, for orientation: token in the `Admin-Token` cookie and/or `Authorization`;
  `GET /getInfo` returns the caller's permission list; `/system/user/profile` returns identity flags
  (`admin`, `agentUser`); `/monitor/server` exposes `computerIp` for admins. Auth failures use the
  original strings `请求访问：<path>，认证失败，无法访问系统资源` (401) and `没有权限，请联系管理员授权`
  (403) — treat them as an oracle. Logins lock after 5 failures for 15 minutes ("帐户锁定15分钟").
- Lazy chunks you never loaded hold the admin/test pages. Either enumerate via the permission list,
  or capture network traffic while clicking every menu item.

## Pitfalls
- An SPA that returns a 200 HTML fallback for every path makes route enumeration useless. Confirm a
  route exists with an authenticated request, and keep "route exists" (401/403 on a real path),
  "auth rejected", and "permission denied" distinct.
- Grep the live bundle: the deployed build can differ from the copy you dumped an hour ago. Compare
  key/iv between the two before trusting a failure.
- Don't ship a 500-request loop against a proxy-gated endpoint in the foreground; shard it and run
  it in the background with progress written to disk.
