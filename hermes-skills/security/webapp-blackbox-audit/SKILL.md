---
name: webapp-blackbox-audit
description: Use for authorized black-box audits of live web apps.
---

# Web App Black-box Audit

Class-level playbook distilled from real audits (tgpool console, 讯飞号铺 store, CCNOW agent panel).
Assumes authorized scope. Zero-destructive posture: no brute-force campaigns, no data tampering.

## 0. Environment-Constrained Toolchain

When nmap/gobuster/subfinder are missing, do NOT stall — substitute:

```python
# Full TCP port scan: socket + ThreadPoolExecutor(500), 1.5s timeout, ~2-3 min for 65535 ports
import socket, concurrent.futures
def chk(p):
    s=socket.socket(); s.settimeout(1.5)
    try: s.connect((ip,p)); return p
    except: return None
    finally: s.close()
```

- DNS records without `dig`: Google DoH JSON API `https://dns.google/resolve?name=&type=`
- Subdomain pass: batch `socket.gethostbyname` over common prefixes (www/api/admin/dev/test/panel/db/bot/cdn...)
- Content discovery: curated path list + Python urllib loop; wordlist files may not exist on the box

## 1. Initial Contact Fingerprinting

One curl round answers most questions:
1. HTTPS direct-to-IP (`curl -k -i`) → app type, framework header (`X-Powered-By: Express` etc.), CDN presence
2. HTTP:80 behavior (404 = unbound site; 302 = redirect)
3. **Cert SAN/CN** — IP-direct certs leak real domain names; resolve and confirm same-IP association
4. Version markers in asset query strings (`styles.css?v=20260803-feature-name`) leak internal iteration info

## 2. Frontend JS as the API Blueprint

The single highest-yield technique. Download every `<script src>` then extract:
- `/api/...` paths (regex over template literals too — `` `...${id}` `` forms)
- Form field names via `<input name=...>` — **payload fields often differ from guesses** (e.g. required `contact`, confirm field named `passwordConfirm` NOT `confirmPassword`). Read the form template before constructing register/login payloads.
- localStorage keys (`tgpool_api_token`, `tgpool_jwt`) → token storage location finding
- Custom headers (`X-API-Token`), EventSource/WebSocket usage, hardcoded secrets regex sweep

## 3. Auth Testing Sequence

1. Unauth sweep ALL openapi.json endpoints with forged credentials (empty/null/Bearer null) — expect uniform 401
2. Register flow: probe error messages first; duplicate username 409 vs login unified 401 = username enumeration via register (M-level finding)
3. Rate-limit check: ~8 rapid wrong logins in one session; 429/lockout vs all-401 = unlimited brute-force surface (H/M finding). Response ~0.7s per attempt suggests slow hash (bcrypt) — note as mitigating factor.
4. Type confusion / extra fields (`is_admin:true`) on login/register — expect Pydantic-style 422 rejection
5. Password change must require old password (test both authed & unauth)

## 4. Authenticated Deep Test via Self-Owned Accounts

Register 2 throwaway accounts (A, B) when registration is open. This enables clean IDOR testing WITHOUT touching third-party data:
- Account B requests account A's resource IDs (payment no, order id) → 404 = ownership scoping ✅, 200 = IDOR ❌
- Probe ID predictability (sequential timestamps) but rely on ownership isolation as the real control

Session pitfall: `http.cookiejar` does NOT persist across process invocations — login AND tests must run in ONE script/process. Build a small `sess.py` helper (mkop()/req()) and reuse; remember `req()` default method is GET, POSTs need explicit `method="POST"`.

## 5. Payment / Business Logic Checks

- Amount boundaries: `0, -100, 0.01, "100" (string), 1e9` → server-side validation confirmed if all rejected with bounds error
- payType whitelist enumeration (alipay/wechat/wxpay/usdt variants)
- Callback endpoint discovery: try `/api/payments/notify|callback|status`, `/pay/notify`, provider-convention paths; forged callback params → business-matching error (not signature error) = missing signature verification (CWE-345)
- Payment number predictability + ownership isolation together determine exploitability
- Order purchase: verify server-side balance check (409 INSUFFICIENT_BALANCE) not client-trusted quantity/price

## 6. Exposed Dev Infrastructure Patterns

High-value combo seen on AI-agent panel targets:
- **Vite dev server public** (7719-7722): `/@vite/client` accessible = dev mode in production → full source leak; test `/@fs/etc/passwd` (403 Restricted = newer patched Vite); HMR websocket exposure
- **File Browser**: index HTML embeds full config JSON `window.FileBrowser={...,"Version":"2.62.1","NoAuth":false}` → version + auth mode free
- Single-user-mode panels (`multiUserEnabled:false`): one password is the entire perimeter — missing rate limit becomes critical
- Multi-port scan is mandatory: components hide on 77xx/3xxxx high ports

## 7. Positive Verification (report the ✅ list too)

An audit report's credibility rests on verified-negative findings:
- All protected endpoints reject forged creds (count them: "94/94 returned 401")
- CORS: arbitrary Origin → no ACAO echo; preflight 403
- Security headers presence (HSTS/CSP/XFO/XCTO) — absence is its own M finding
- TLS version, cert validity, .env/.git leakage, frontend hardcoded-key regex sweep

## 8. Report Format

Findings table: severity | ID | issue | evidence (raw response excerpt) | CVSS score+vector.
Then positive-verifications section, then Top-3 prioritized fixes. Note test footprint honestly
(accounts created, login attempts made, zero data touched) so the operator can clean up.

## Routing

See also `recon-for-sec` (broader recon: subdomains, Wayback, CT logs, WAF ID) and
`api-recon-and-docs` (JS bundle mining overlap). FastAPI quirks and payment-callback detail
live in memory notes.
