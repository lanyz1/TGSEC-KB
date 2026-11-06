# RuoYi + Sa-Token (non-JWT) + Druid Intelligence Chain

When RuoYi uses Sa-Token in **random token mode** (not JWT), the token is a 64-char random string stored server-side. Cannot forge — no signing key to crack.

## Detection
- Token format: 64 alphanumeric chars, no dots (JWT has 3 dot-separated segments)
- Header name may be `satoken` or `Authorization: Bearer <token>`
- Login returns `saToken` field in response body
- Invalid token → `{"msg":"登录令牌已失效，请重新登录!","code":403}`
- Missing token → `{"msg":"请求访问：/path，认证失败，无法访问系统资源","code":401}`

## Front/Back Auth Isolation
RuoYi deployments commonly serve both `/app/` (mobile API) and `/system/` (admin) from the SAME Spring Boot JAR. Sa-Token enforces role separation:
- APP user token works on `/app/*` endpoints only
- Admin endpoints (`/system/*`, `/getInfo`, `/getRouters`, `/monitor/*`) return 401 even with a valid APP token
- The two namespaces share the same Sa-Token instance but different permission scopes
- Implication: compromising an APP user gives zero admin access; must find the admin login separately

## Druid Console as Intelligence Source
Default credentials to try: `ruoyi:123456`, `admin:admin`, `admin:123456`, `druid:druid`.

What Druid exposes (HIGH value):
- **MySQL connection string**: `jdbc:mysql://HOST:PORT/DB?...` with username (NOT password)
- **Full SQL monitoring**: every query executed, with table/column names → complete DB schema
- **JAR path**: `JavaClassPath` in `/druid/basic.json` → reveals deployment path (e.g. `/www/wwwroot/zhzs/ruoyi-app1003.jar` = 宝塔)
- **Java version, Druid version, start time**
- **WebURI stats**: all accessed API paths with hit counts → reveals admin activity patterns
- **Active sessions**: session IDs, IPs, last access URIs (but usually empty/anonymous)

What Druid does NOT expose:
- Database password (masked in datasource config)
- Sa-Token secret key
- Application.yml contents

Druid SQL endpoint (`/druid/sql.json`) returns SQL execution STATISTICS, not a SQL console — cannot execute arbitrary queries through it.

## Password Hash Leak via getUser API
Some RuoYi forks return password hashes in the user profile response:
```json
{"passWord": "<base64>", "passwordSalt": "<base64>",
 "payPassword": "<base64>", "payPasswordSalt": "<base64>"}
```
Common algorithm: **PBKDF2-SHA1, 10000 iterations, 16-byte salt, 32-byte output**.
Verification: `hashlib.pbkdf2_hmac('sha1', password.encode(), base64.b64decode(salt), 10000, dklen=32)` should match `base64.b64decode(passWord)`.

This is a CRITICAL info leak — enables offline cracking of any user's password including potential admin accounts.

## Actuator Bypass Attempts (all failed against Sa-Token)
When Sa-Token intercepts ALL paths globally (not path-prefix filtered), these bypass patterns are dead:
- Semicolon trick: `/actuator;.js/env` → "非法请求" (Spring rejects malformed URL)
- URL encoding: `/%61ctuator` → still intercepted
- Null byte: `/actuator%00` → 400 Bad Request
- Path traversal: `/..;/actuator/env` → 400 Bad Request
- Fragment: `/actuator/env%23` → still 401
- Query string: `/actuator/env?.js` → still 401

Sa-Token's global interceptor runs before Spring's path matching, making all URL normalization tricks ineffective.

## APK Source Mining for Auth Flow
UniApp/Vue APK `app-service.js` reveals:
- Token header name: look for `header.token = ` or `header.satoken =`
- Response encoding: `decodeURIComponent(atob(t.data))` = base64-encoded responses
- `/auth/` prefix endpoints may use different token header than `/app/` endpoints
- IM initialization: `apiAddr` and `wsAddr` parameters reveal OpenIM server domains
- `listOfSuperiors` field in user profile exposes the full MLM/referral tree including admin invite code at root
