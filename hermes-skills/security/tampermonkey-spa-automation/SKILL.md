---
name: tampermonkey-spa-automation
description: >-
  测绘引擎·Techniques for writing and debugging Tampermonkey user scripts against Single Page
  Applications (Vue/React) — API interception, token extraction, polling fallbacks, and
  platform-specific patterns.
owned: true
tier: ops
pack: survey-skill
---

# tampermonkey-spa-automation（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/tampermonkey-spa-automation/`

溯源（仅标记）：`hermes/software-development`

---

# Tampermonkey SPA Automation

## Trigger

This skill applies when the user needs a Tampermonkey/Greasemonkey user script to interact with a modern SPA (especially Vue 3 + Vite + Pinia) — gambling platforms, dashboards, or any JS-heavy web app.

## Key Techniques

### 1. Token Extraction from SPA

SPAs store auth tokens in multiple places. Try in order:

```javascript
// Way 1: direct localStorage key
localStorage.getItem('token')

// Way 2: JSON user object
JSON.parse(localStorage.getItem('user') || '{}').token

// Way 3: Pinia store (Vue 3)
var app = document.querySelector('#app');
if (app && app.__vue_app__) {
    var pinia = app.__vue_app__.config.globalProperties.$pinia;
    if (pinia) {
        var state = pinia.state.value;
        // iterate stores to find token
    }
}
```

### 2. API Interception — Fetch vs XHR

**Critical insight**: Vue 3 apps using Axios send requests via **XHR** (`XMLHttpRequest`), NOT `window.fetch`. If you only override `window.fetch`, Axios calls slip through.

```javascript
// Intercept BOTH:
// Fetch
var origFetch = window.fetch;
window.fetch = function(input, init) { ... };

// XHR (Axios)
var origOpen = XMLHttpRequest.prototype.open;
var origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(method, url) {
    this._bfcp_url = typeof url === 'string' ? url : (url && url.href) || '';
    return origOpen.apply(this, arguments);
};
XMLHttpRequest.prototype.send = function(body) {
    var xhr = this;
    xhr.addEventListener('load', function() {
        // intercept response here
    });
    return origSend.apply(this, arguments);
};
```

**Pitfall**: Even with XHR interception, if the page caches the XHR reference before the script runs, interception still fails. In that case, use polling (see 3).

### 3. Fallback Strategies When Interception Fails

#### 3.1 Polling as Primary Strategy
```javascript
setInterval(function() {
    safeFetch('getPreNumber', { gameId: gameId, issue: issue }).then(function(data) {
        if (data && data.data && data.data.preNumber) {
            // process pre-opening data
        }
    });
}, 2000);
```

#### 3.2 Extract gameId/issue from URL
```javascript
var href = window.location.href;
var m = href.match(/(GAME_ID_PATTERN)/i);
if (m) gameId = m[1].toUpperCase();
```

#### 3.3 Watch page's own API calls for state extraction
Instead of hijacking requests just to intercept response data, use request monitoring to extract parameters (gameId, issue number) that the page itself fetches, then use those parameters in your own polling calls.

### 4. Common SPA Issues

| Problem | Solution |
|---------|----------|
| Script runs before SPA mounts | Use `setTimeout(init, 1000)` or `@run-at document-end` |
| Token not found in localStorage | Check `localStorage.key()` list for all stored keys |
| Game data via WebSocket, not HTTP | Cannot intercept via fetch/XHR — must poll API directly |
| Axios using XHR, not fetch | Override XMLHttpRequest.send in addition to window.fetch |
| Page caches fetch/XHR reference | Interception may never work — use polling exclusively |
| Umi.js SPA — token in cookie not localStorage | Use `document.cookie.match(/token=([^;]+)/)` |
| Umi.js SPA — token as custom header | Send as `token:` header, not `Authorization: Bearer` |
| SPA with cross-subdomain API | API on `api.xxx.com`, app on `ib.xxx.com` — update fetch base URL |
| Game returns SPA HTML on API calls | Missing `X-API-VERSION` or `platform` headers |

### 5. Umi.js SPA Authentication

Umi.js (Ant Group's React framework) SPAs have non-standard auth:

**Token in Cookie**: JWT stored in cookie named `token`, NOT localStorage:
```javascript
var token = <REDACTED>;]+)/)[1];
```

**Custom Header Format**: Token sent as custom header, not Bearer:
```
token: eyJhbGciOiJSUzI1NiJ9...
```

**Required Headers** (set by request interceptor):
```
platform: IB                    ← platform identifier
X-API-VERSION: 2.44.0          ← version check
browserfingerprint: <userId>   ← anti-bot
lang: zh-CN                    ← locale
```

**API Route Discovery** from Umi.js bundle:
```bash
grep -oP '"/api/[^"]+' umi.dd814d91.js | sort -u
```

### 6. API Encryption Key Extraction

When SPA uses custom MD5-based request signing:
- Search bundle for hex key strings (e.g. `f47d121e`)
- Look for `encryKey`, `encryValue` function patterns
- Character substitution: `.replace(/2/g,'B').replace(/7/g,'G')`
- Timestamp + random as single-use key: `Date.now() + '' + Math.random()`

### 7. URL Scheme Adaptation (Hash vs Pathname)

When porting a Tampermonkey script designed for hash-routed SPA (`#/NN/xxx`) to a pathname-routed platform (`/lottery/NN/xxx`):

**The getType() dual-matching pattern:**

```javascript
// WRONG — only matches hash routing:
if (/\/NN\//.test(location.hash)) return 'NN';

// RIGHT — matches BOTH hash and pathname:
function m(re) { return re.test(location.hash) || re.test(location.pathname); }
if (m(/\/NN\//) || m(/牛牛/) || m(/niuniu/)) return 'NN';
```

**Script-vs-Platform mismatch diagnosis when "panel loads but doesn't collect data":**
1. ✅ Panel loads → `getType()` works, DOM injection succeeds
2. ❌ No API count incrementing → fetch interceptor never triggers
3. ❌ No data in hand lines → `onPreNum()` never called
4. Diagnosis: Platform uses XHR (Axios) not fetch, OR URL scheme mismatch, OR API endpoint differs

**Common pitfalls:**
- Update ALL regex calls in getType(), not just one
- Test with console: `location.hash`, `location.pathname`, `location.href`
- Pathname route e.g. `/lottery/NN/OGNN` — match on the segment, not position
- After patching getType(), verify script's DOM selectors still match (different platforms render UI differently)

**When to use this pattern:**
- User says "panel loads but doesn't collect data"
- URL has `/lottery/{GameType}/{GameId}` but script expects `#/{GameType}`
- Script from one platform brand used on a different brand of the same underlying platform

## User Delivery Preference

**ALWAYS deliver the complete file for copy-paste replacement.** The user explicitly requires full code, not patch instructions or "find this function and replace it." When a fix is needed, output the entire updated script and say "copy-paste this completely."

## Pitfalls

- **Never wrap `window.WebSocket` for canvas/Cocos games.** Replacing the constructor with a wrapper that re-instantiates `new OrigWS(url)` breaks the app's own connections — symptom: "网站没网络" / page loses all network after script loads. Use ONLY passive `addEventListener('message')` on real instances via `page.on` style hooks, or skip WS entirely and poll the API.
- **Programmatic JS patching mangles regex escapes.** Editing userscripts with Python `.replace()` on `\\/` sequences produces `m(//SH//)` — `//` becomes a JS comment, silently breaking the whole script. After ANY automated patch: (1) count braces `{` vs `}` must balance, (2) grep for `(//` or `//)` leftovers, (3) re-read the patched lines as raw bytes before delivering.
- **Symptom triage:** panel GONE entirely = JS syntax error (brace imbalance / comment-in-regex) — check console; panel shows but type `--` = getType() mismatch; panel shows type but API counter frozen = interception or auth problem. "Panel works, site breaks" = you broke the page's own network (see WebSocket/fetch pitfalls above).
- Opera/Chrome built-in VPN or proxy (Remote Address: 127.0.0.1:10808) can interfere with API calls
- OpenResty servers return `openresty` in Server header
- JSON error: `"code":"error","msg":"取得浮动赔率失败"` = wrong gameId/issue parameters, not API down
