# Vite SPA API Discovery Technique (Vue3 + React)

## Target Pattern
Chinese web apps built with **Vite + Vue 3** or **Vite + React 18.x**, often obfuscated with mangled variable names. Both share the same Vite output patterns (hashed asset names, modulepreload, __vite__mapDeps).

## Steps

### 1. Download the main Vite entry chunk
```bash
curl -s "https://target.com/assets/index-XXXX.js"
```

### 2. Find all lazy-loaded JS chunks
**Vue3 pattern** — look for `__vite__mapDeps`:
```javascript
const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/AdminPage-XXXX.js","assets/mock-XXXX.js"])))=>i.map(i=>d[i]);
```

**React pattern** — look for `p.lazy(() => Ge(() => import("./Xxx-xxx.js")))`:
```javascript
const ny = p.lazy(() => Ge(() => import("./SelfStoreShell-CjXWTBHc.js"), __vite__mapDeps([0,1])));
```
Extract all chunk filenames and download each.

### 3. Search for API action dispatcher
The API wrapper function is mangled. Common patterns:
- `W("action_name", {method:"POST", body:{...}})` — action-based dispatch
- `export{..., qy as W, ...}` — export alias mapping
- `await fetch(\`/api/?${i.toString()}\`, ...)` — URL construction with query params

In **React bundles**, the wrapper is often alongside React hooks:
```javascript
// Likely names: W, w, F, V — test each with W("login",...)
await W("login", {method:"POST", body:{username:e, password:t}, auth:!1})
```

### 4. Extract all API action names
```bash
# In each chunk, regex for W("action_name")
grep -oP 'W\("([a-zA-Z0-9_-]+)"' chunk.js | sort -u
# Or for fetch("/api/...")
grep -oP 'fetch\(`/api/\?action=[^`]+`' chunk.js | sort -u
```

### 5. Identify the API routing pattern
- `query-parameter-based`: `/api/?action=XXX` — non-REST, common in Chinese apps
- `standard REST`: `/api/resource/{id}`
- `hybrid`: Some paths return health check catch-all, actual routing is via query param

### 6. Multi-domain cross-referencing
When a subdomain is found (e.g., `app.target.com`):
```bash
for path in /api/config /api/feedback /api/admin /api/generate; do
  curl -s "https://pk.target.com$path"       # Often returns generic health check catch-all
  echo "---"
  curl -s "https://app.target.com$path"       # May return different behavior
done
```
**Why this works:** different subdomains often share the same backend infrastructure but serve different frontends. API endpoints discovered in one domain's JS may be accessible on another.

### 7. Action fuzzing
```bash
for action in login register logout redeem-code admin status config check; do
  echo "--- $action ---"
  curl -s -X POST "https://target.com/api/?action=$action" -H "Content-Type: application/json" -d '{}'
done
```
**Important:** try both GET and POST — some actions accept GET but require POST, giving different error messages that reveal the endpoint is real.

### 8. Test for unauthenticated admin sub-actions
Check `/api/admin/?action=XXX` with various action names:
```bash
for action in status config users info health check checkRelogin; do
  curl -s "https://target.com/api/admin/?action=$action"
done
```
Some admin actions may be unintentionally left unprotected (e.g., `checkRelogin`).

## Traps & Pitfalls

### ⚠️ Source map trap
`.js.map` files return HTTP **200** but serve the SPA `index.html`, NOT the actual source map:
```bash
curl -s "https://target.com/assets/index-XXXX.js.map"
# Returns: <!doctype html><html lang="zh-CN">... (SPA index.html)
```
Don't waste time on source maps for Vite SPAs unless explicitly enabled in production.

### ⚠️ SPA catch-all means all paths return 200
Because the SPA uses client-side routing, ALL paths on the server return HTTP 200 with `index.html`:
```bash
curl -s "https://target.com/random-nonexistent-path"    # Returns index.html (200)
curl -s "https://target.com/assets/nonexistent.js"       # Returns index.html (200)
```
**You CANNOT use HTTP status codes to distinguish real vs fake endpoints on SPA sites.** Always examine the response body content.

### ⚠️ /api/ health check catch-all
Some backends return a generic health check response for ALL API paths:
```json
{"ok":true,"data":{"service":"xianyu-rival-api","status":"ok","database":"ok"}}
```
This does NOT mean the endpoint exists — it means everything routes to the same handler. You need to find the actual action-based routing via JS analysis.

## Response Analysis

| Response Pattern | Meaning |
|-----------------|---------|
| `{"ok":true, "data":{...}}` | Endpoint exists |
| `{"ok":false, "code":"NOTFOUND", "msg":"Unknown action: XXX"}` | Action doesn't exist |
| `{"ok":false, "code":"ERR_AUTH", "msg":"账号或密码错误"}` | Action exists, auth failure |
| `{"ok":false, "code":"ERR_PARAM", "msg":"login requires POST"}` | Action exists, wrong method |
| `{"error":"只支持 POST 请求"}` | Wrong HTTP method |
| `{"error":"请先登录", "code":"LOGIN_REQUIRED"}` | Action exists, needs auth |
| `{"error":"未授权访问"}` | Admin action exists, needs auth |
| `{"ok":true, "data":{"service":"xxx", "status":"ok"}}` | Generic health check catch-all |
| `{"error":"该手机号已注册"}` | User enumeration leak (bad) |

## Chinese Rate Limiting & Lockout Messages
Recognize these to avoid false negatives:
- `"登录失败次数过多,请 15 分钟后再试"` — login brute force lockout
- `"尝试次数过多,请 15 分钟后再试"` — code/register brute force lockout
- `"兑换码无效或已被使用,请核对后重试;确认无误请联系卖家"` — invalid activation code

## Tools Used
- `curl` for downloading chunks and API probing
- `grep -oP` for regex extraction from JS bundles
- Python `re.findall()` for multi-file pattern extraction
- Browser (headless) for form interaction when SPA state matters
