# MACAO66 API Encryption Reverse Engineering — Full Case Study

**Date**: July 10, 2026
**Target**: `www142421549828364.00226944.com:6899`
**Platform**: Vue.js SPA gambling platform (casino, sports, lottery)
**Alias**: `macao66` (base64: `bWFjYW82Ng==`)

## Discovery Chain

### 1. Find the Alias

In the HTML source (`/web/`), an inline script contained:
```html
<script>
var __cdnUrl__ = 'https://e1.jwkphb.com';
var alias = 'bWFjYW82Ng==';  // ← base64 encoded
var xrayUrl = 'https://www77235.ats.elegancepath.online:3637/api/info';
</script>
```

Base64 decode: `bWFjYW82Ng==` → `macao66`

### 2. Locate Encryption Code

In `chunk-common.c0606628.js` (80KB), at positions 73747 and 74074:

**Encryption function:**
```javascript
n(e){
  if(0===Object.keys(e).length) return null;
  var t=JSON.stringify(e),
      n=a.a.MD5(window.alias),
      i=a.a.AES.encrypt(t, a.a.enc.Utf8.parse(n), {mode: a.a.mode.ECB}),
      o=a.a.enc.Utf8.parse(i),
      r=a.a.enc.Base64.stringify(o);
  return r
}
```

**Decryption function:**
```javascript
r=function(e,t){
  var i=e,
      o=a.a.enc.Base64.parse(i),
      r=a.a.enc.Utf8.stringify(o);
  if(n) return r;  // raw mode bypass
  var c=a.a.MD5(window.alias),
      s=a.a.AES.decrypt(r, a.a.enc.Utf8.parse(c), {mode: a.a.mode.ECB}),
      u=s.toString(a.a.enc.Utf8);
  return t?u:JSON.parse(u)
}
```

### 3. Key Derivation

```
MD5("macao66") = "acf1d6c68fbb92ba0d79b58dcbb67e23"
Key = Utf8.parse("acf1d6c68fbb92ba0d79b58dcbb67e23")  // 32 bytes = AES-256
```

### 4. Encoding Flow (Confirmed by Roundtrip)

```
PLAINTEXT → JSON.stringify → AES-ECB-encrypt → toString() (base64 ct)
  → Utf8.parse(base64_ct) → Base64.stringify(Utf8_bytes) → FINAL requestData
```

**Double-base64**: The final output is base64(base64(ciphertext)).

### 5. CryptoJS Implementation

```javascript
const CryptoJS = require('crypto-js');
const alias = 'macao66';
const key = CryptoJS.enc.Utf8.parse(CryptoJS.MD5(alias).toString());

function encrypt(obj) {
  const ct = CryptoJS.AES.encrypt(JSON.stringify(obj), key, {mode: CryptoJS.mode.ECB});
  return CryptoJS.enc.Base64.stringify(CryptoJS.enc.Utf8.parse(ct.toString()));
}

function decrypt(data) {
  const inner = CryptoJS.enc.Utf8.stringify(CryptoJS.enc.Base64.parse(data));
  const pt = CryptoJS.AES.decrypt(inner, key, {mode: CryptoJS.mode.ECB});
  return CryptoJS.enc.Utf8.stringify(pt);
}
```

Roundtrip test result: encrypt → decrypt returned original input ✅

### 6. API Endpoints Discovered

**Main API**: `/entrance/api` (encrypted, POST)
**Unencrypted endpoints**:
- `/entrance/twostep/ubauth/userInfo.json` → returns `{"status":"N","code":"111031201","message":"请重新登入","data":[]}`
- `/web/config/common.json` → site configuration
- `/web/config/sport.json` → game provider list
- `/web/config/aio-download.json` → download config

**Other encrypted endpoints** (from JS source):
- `/infe/user/pwdlogin/getData` — login
- `/infe/user/pwdlogin/changPassword` — password change
- `/infe/user/pwdforget/*` — password reset flow
- `/entrance/offer/*` — offers, bonuses, sign-in
- `/entrance/common/*` — basic info, game lists
- `/entrance/casino/*` — casino game data
- `/entrance/page/*` — content pages

### 7. Authentication Flow

```
1. Browser loads /web/ → inline script reads xrayUrl
2. GET xrayUrl → receives XID cookie:
   {"data": "a/bIdH37Sm6XdMSw8HNnHw=="}
3. Three POSTs to /entrance/api with encrypted payloads:
   - Language data
   - Site initialization data
   - Configuration data
4. Vue.js SPA mounts, makes further API calls with XID cookie
```

### 8. GeoIP Behavior

The site uses GeoIP-based CDN switching:
- **Non-China IP** (207.168.55.31): All API calls return `<script>location.href='/entrance/page/noservice'</script>`
- **China IP** (113.25.74.208): API returns actual encrypted data

Xray URL also changes per CDN endpoint:
- `g4.cldfvn.com` → `www77235.ats.elegancepath.online:3637`
- `e1.jwkphb.com` → `www77235.ats.homeward-journey.com:3637`

### 9. Admin Backend Search Results

The admin panel is NOT in the frontend code. Attempted and failed:
- Subdomain enumeration: admin/root/manage/panel on `.00226944.com` — all "SubDomain Not Exist"
- Port scanning (30+ ports): only 443/6899/8888 serve the same frontend
- CDN chunk analysis: no admin JS modules found
- Vue router paths: no admin routes in the SPA
- Virtual host probing: only the known hostname works

**Conclusion**: Admin is either on a completely different domain or internal network.

## Key Technical Takeaways

1. **CryptoJS's `Utf8.parse(WordArray)` implicitly calls `toString()` on the WordArray first**, which produces hex output. This is the most common mistake when reimplementing: you can't pass the raw MD5 bytes — you need the hex string as UTF-8.
2. **The response encryption may differ from request encryption.** Some endpoints return unencrypted JSON while others use the same AES scheme. The `if(n) return r` branch in the decrypt function suggests a raw/passthrough mode.
3. **Dynamic CDN + GeoIP means the encryption key stays the same** (alias is baked into the HTML), but the proxy/CDN infrastructure changes per request.
