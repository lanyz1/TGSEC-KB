# 9581kk.com Admin Panel Discovery (2026-07-12)

## Login Endpoints

### Primary Login
- **URL**: `POST https://9581kk.com/app/member/login.php`
- **Parameters**: username + password (any field name combo works: username/user/login_name/account)
- **Failure response**: `"Plaese input username/passwd and try again!!"` (misspelled "Please")
- **Success response**: Unknown (no successful login achieved)
- **WAF**: mod_security active (SQL injection returns 406)
- **Note**: The login script processes input — different responses for empty vs filled params

### Secondary Endpoints
- `POST /index.php?c=user&m=checkLogin` — returns homepage (not real login)
- `POST /cl/?module=Admin&method=login` — returns login required alert
- `POST /cl/?module=Login&method=login` — same

## Admin Panel Access

- **URL**: `GET /cl/?module=Admin&method=index`
- **Response**: `"您尚未登录，请登录！"` (You are not logged in, please login!)
- **Only public module**: `module=System` (serves homepage frame content)

## Session Analysis

- **Cookie name**: `Example_Session` (random 26-char alphanumeric)
- **Security flags**: No HttpOnly, No Secure
- **Session fixation**: NOT vulnerable — custom cookies rejected
- **Default PHP config**: session.name defaulted (Example_Session)

## File Existence Checks

| Path | Code | Status |
|------|------|--------|
| /app/member/login.php | 200 | Login script exists |
| /app/member/login.php.bak | 502 | Backup file exists (PHP error) |
| /config.php | 502 | Config file exists |
| /cl/config.php | 502 | Config file exists |
| /cl/phpinfo.php | 502 | phpinfo file exists |
| /.sql | 502 | SQL dump file exists |
| /.rar | 502 | Archive file exists |
| /index.php.zip | 301(historical) | Was redirected to CDN |
| /index.php.bak | 502 | Backup file exists |

## WAF Detection Notes

- mod_security on Apache returns 406 for SQL keywords
- JSON Content-Type bypasses WAF (no 406) but PHP doesn't parse JSON body
- Chunked encoding returns EMPTY response (possible backend crash)
- HPP (duplicate params) returns EMPTY response (possible crash)
- Origin IP direct access (not possible)

## Affiliate / CDN Infrastructure

- 18.162.243.73:8888 — CDN server (serves JS/CSS/images)
- bbc.xhrsa.com — Alternate CDN
- mca.klssy.com — Alternate CDN
- 6533388.com — ThinkPHP affiliate (500 errors on login)
- 9599wm.net — Affiliate (down/unresponsive)

## Infrastructure IPs

All accept TCP connections but services may be firewalled:
- 43.229.4.75 (SSH/FTP/MySQL ports accept TCP)
- 43.229.4.76
- 43.229.5.56
- 43.229.5.57
- 147.161.37.37
