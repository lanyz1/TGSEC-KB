---
name: api-crypto-analysis
description: >-
  测绘引擎·Reverse-engineer custom API encryption from frontend JavaScript source code. Covers
  locating encryption keys in minified JS, identifying AES mode and key derivation,
  implementing decrypt/encrypt with CryptoJS roundtrip verification, and probing API
  endpoints with cracked encryption.
owned: true
tier: ops
pack: survey-skill
---

# api-crypto-analysis（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/api-crypto-analysis/`

溯源（仅标记）：`hermes/software-development`

---

# API Cryptography Reverse Engineering

## Overview

Modern web applications sometimes implement custom client-side encryption for API calls. This is common in gambling platforms, financial apps, and high-security SPAs. The encryption logic lives in the frontend JavaScript (often minified) and can be extracted, analyzed, and reproduced.

## Step-by-Step Methodology

### 1. Locate the Encryption Code

The encryption function is typically in one of the Vue.js/React chunk files loaded from a CDN. Search for these patterns in the minified JS:

```javascript
// Common encryption library indicators:
CryptoJS      // Full CryptoJS library
AES.encrypt   // AES encryption call
AES.decrypt   // AES decryption call
MD5(          // Key derivation
enc.Utf8.parse  // String-to-bytes conversion
enc.Base64.stringify  // Output encoding
mode.ECB      // Block cipher mode (ECB, CBC, etc.)
```

Also search for these variable name patterns in minified code:

```javascript
// Key derivation typically looks like:
n = a.a.MD5(window.alias)
i = a.a.AES.encrypt(t, a.a.enc.Utf8.parse(n), {mode: a.a.mode.ECB})
o = a.a.enc.Utf8.parse(i)
r = a.a.enc.Base64.stringify(o)
```

### 2. Identify the Key

The encryption key is usually derived from a value accessible in the HTML/JS runtime:

| Key Source | Where to Find It |
|------------|-----------------|
| `window.alias` | Inline `<script>` tag in the HTML, often base64-encoded |
| `window.__cdnUrl__` or similar config | Also in inline script |
| Hardcoded string | In the JS bundle itself |
| API response value | From a pre-auth endpoint |

**Common pattern**: `alias` is base64-encoded. Decode it with:

```python
import base64
decoded = base64.b64decode("bWFjYW82Ng==").decode()  # → "macao66"
```

Then the key is derived as:

```javascript
// Key = MD5(alias) as hex string, then UTF-8 encoded
const key = CryptoJS.enc.Utf8.parse(CryptoJS.MD5(alias).toString());
```

### 3. Understand the Encoding Flow

**Encryption (client → server):**

```
1. Plaintext JSON object
2. JSON.stringify() → string
3. AES.encrypt(plaintext, key, {mode: ECB}) → CipherParams object
4. CipherParams.toString() → base64 string of ciphertext
5. Utf8.parse(base64String) → WordArray of UTF-8 bytes
6. Base64.stringify(WordArray) → FINAL request data (double-base64)
```

**Decryption (server → client, or your own verification):**

```
1. Response data (base64 string)
2. Base64.parse(response) → WordArray of UTF-8 bytes
3. Utf8.stringify(WordArray) → inner base64 ciphertext string
4. AES.decrypt(innerBase64, key, {mode: ECB}) → WordArray
5. Utf8.stringify(WordArray) → plaintext JSON string
```

### 4. Implement with CryptoJS (Node.js)

Write a self-contained Node.js script for roundtrip verification:

```javascript
const CryptoJS = require('crypto-js');

// Configuration
const alias = 'macao66';           // From HTML base64 decode
const key = CryptoJS.enc.Utf8.parse(CryptoJS.MD5(alias).toString());

function encrypt(obj) {
    const jsonStr = JSON.stringify(obj);
    const encrypted = CryptoJS.AES.encrypt(jsonStr, key, {
        mode: CryptoJS.mode.ECB,
        padding: CryptoJS.pad.Pkcs7
    });
    const b64Ciphertext = encrypted.toString();
    const utf8Bytes = CryptoJS.enc.Utf8.parse(b64Ciphertext);
    return CryptoJS.enc.Base64.stringify(utf8Bytes);
}

function decrypt(requestData) {
    const utf8Bytes = CryptoJS.enc.Base64.parse(requestData);
    const b64Ciphertext = CryptoJS.enc.Utf8.stringify(utf8Bytes);
    const decrypted = CryptoJS.AES.decrypt(b64Ciphertext, key, {
        mode: CryptoJS.mode.ECB,
        padding: CryptoJS.pad.Pkcs7
    });
    return CryptoJS.enc.Utf8.stringify(decrypted);
}

// Roundtrip test
const test = encrypt({test: "hello"});
console.log('Encrypted:', test);
console.log('Decrypted:', decrypt(test));
// Output should match input
```

### 5. Verify with Roundtrip Test

Always verify your encryption implementation matches the server's by doing a roundtrip test:

1. Encrypt a known object
2. Decrypt the output
3. Confirm the decrypted result matches the original input

If the roundtrip fails:
- **Wrong key derivation** — try MD5 hex string vs raw MD5 bytes vs SHA256
- **Wrong AES mode** — try ECB vs CBC vs CTR
- **Wrong key length** — AES-128 (16 bytes) vs AES-256 (32 bytes)
- **Wrong padding** — Pkcs7 vs ZeroPadding vs NoPadding
- **Different encoding** — double-base64 vs hex vs raw bytes

### 6. Probe API Endpoints

Once encryption is cracked, probe endpoints with crafted encrypted data:

```python
import urllib.request, json, subprocess

# Use the Node.js encrypt script to encode payloads
def encrypt_payload(obj):
    # Call the Node.js encrypt function via subprocess
    js = f'...'  # Same encrypt function as above
    proc = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    return proc.stdout.strip()

# Send encrypted request
url = "https://target.com/entrance/api"
data = f"requestData={encrypted}".encode()
req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
req.add_header('Cookie', f'XID={xid}')  # If auth required

resp = urllib.request.urlopen(req)
response_body = resp.read().decode()

# Decrypt response
plaintext = decrypt(response_body)
```

### 7. Complete the Authentication Chain

API encryption almost always coexists with a multi-step auth/proxy chain. The full flow is usually:

```
1. Fetch HTML page → extract from inline <script> tags:
   ├─ alias/base URL (for encryption key)
   ├─ __cdnUrl__ (CDN base for JS chunks)
   └─ xrayUrl (session/proxy token endpoint)

2. GET xrayUrl → receive XID cookie:
   GET https://proxy-domain:3637/api/info
   Response: {"data": "base64-session-token"}
   → Use as Cookie: XID=<token> on all subsequent API calls

3. Three parallel POSTs to /entrance/api (encrypted):
   - Language data
   - Site initialization data
   - Configuration data
   → These populate window.basicLangData, window.basicInitData, window.basicConfigData

4. Vue.js/React SPA mounts → makes further authenticated API calls
```

**Token procurement steps:**
- **XID cookies**: Issued by a proxy/CDN endpoint before API calls work. Always fetch this first.
- **Token refresh**: Some tokens expire; the xray endpoint issues fresh ones on each page load.
- **GeoIP gating**: The proxy/CDN may reject non-local IPs before requests reach the API. See pitfall below.

### 8. Handle GeoIP-Aware CDN/Proxy Switching

Some platforms use GeoIP-based load balancing that changes CDN domains and proxy endpoints based on requester location. Symptoms:

- Different `__cdnUrl__` and `xrayUrl` values returned depending on source IP
- API calls return redirect scripts (`location.href = '/noservice'`) instead of encrypted data
- Frontend HTML structure is identical but infrastructure URLs differ

**Diagnosis:**
```python
import urllib.request
# Check your current IP
resp = urllib.request.urlopen('http://httpbin.org/ip')
print(resp.read())  # → {"origin": "your.ip.here"}

# If not in the expected region, the site won't serve real data
# Solutions:
# 1. Run requests from a machine in the expected region
# 2. Use a proxy/VPN in the target region
# 3. Accept that some endpoints may be unreachable
```

**Fingerprint:** Compare the inline script values between requests to detect GeoIP-based switching:

## Common Pitfalls

- **Don't assume the key is in the first JS chunk** — search all chunks in order: `index.js` → `chunk-common.js` → `chunk-vendors.js`
- **Don't assume single-base64** — the encryption output is often double-base64 encoded (ciphertext → base64 string → UTF-8 bytes → base64 again)
- **MD5 vs raw bytes** — the JS code `Utf8.parse(n)` where `n` is MD5 result: CryptoJS's MD5 returns a WordArray. Calling `Utf8.parse(n)` implicitly converts `n.toString()` (hex string) to UTF-8 bytes. This means the key is the MD5 hex representation as UTF-8, NOT the raw 16 MD5 bytes.
- **All encrypted requests return the SAME base64 string** — this means the server isn't decrypting/processing your payload at all. The response is a generic error rather than a computed result. Root causes: missing or expired session token (XID cookie), IP blocked by GeoIP/CDN, server in maintenance mode returning a redirect script (`<script>location.href='/noservice'</script>`), or the encryption key/format doesn't match what the server expects (verify roundtrip first).
- **Some endpoints return unencrypted JSON** — not all API paths go through the encryption layer. Check `/entrance/twostep/ubauth/userInfo.json` and similar paths for plain JSON responses.

## Environment Setup

```bash
npm install crypto-js
# crypto-js provides: AES, MD5, enc.Utf8, enc.Base64, mode.ECB, pad.Pkcs7
```


## 全文导航（已拆分）

主卡保留前 4 节；其余 5 节在 `references/full.md`：

- Required Tools
- Additional References
- Session Case Study
- Extended Techniques: Non-Crypto Algorithm Extraction
- 2026-07-22 Update: DeepSeek Bypass Pattern Added

加载：`skill_view(name='api-crypto-analysis', file_path='references/full.md')`
