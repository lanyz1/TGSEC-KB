# Chinese Scam Platform: ThinkPHP + FastAdmin + UniApp Pattern

MLM/Ponzi scam sites impersonating government programs ("十五五规划", "携手扶幼", "惠民增收"). Stack: ThinkPHP backend + FastAdmin admin panel + UniApp mobile SPA + 极星云CDN (PolestarCloud) or Cloudflare.

## Architecture Fingerprints

- **Frontend**: UniApp compiled Vue SPA at `/static/js/index.*.js` + `/static/js/chunk-vendors.*.js`. Title often mimics government.
- **API**: `/api/index/login`, `/api/user/index`, `/api/nine/*`, `/api/six/*`, `/api/product/*`, `/api/withdraw/*`. UTF-8 BOM in responses (`\xef\xbb\xbf`) — decode with `utf-8-sig`.
- **Admin**: FastAdmin on a separate domain (image/upload CDN domain). Detected by `/assets/js/require-backend.min.js` returning 200 (~950KB). `/runtime/` and `/runtime/session/` return 403.
- **Multi-domain split**: frontend domain (SPA), API domain (same backend), image CDN domain (also the backend with admin), additional mirror domains. All share the same database.
- **CDN**: 极星云 (PolestarCloud) — error page says "650 - 域名不存在". Origin IPs behind CDN may have 19+ open ports.

## Token Passing Quirk (CRITICAL)

**Token goes in POST body, NOT in headers.** All header methods (token, Authorization, Bearer, X-Token, cookie) return `{"code":3,"msg":"请登录"}`. Only `json={'token': TOKEN, ...}` or `data={'token': TOKEN}` in the POST body works. Always test body-token when header-token fails on Chinese ThinkPHP sites.

## Attack Chain

### 1. Phone enumeration
`POST /api/index/check_phone {"phone": "..."}` → `code=0 "已被注册"` vs `code=1 "成功"`. No rate limit, no auth.

### 2. Password spray
Common: `123456`, `Qwer1234`, `Test1234`. Test-pattern phones (13x00000000, 1xx12345678, 1xx88888888) often use weak passwords.

### 3. Full PII extraction (per cracked account)
With token in body:
- `/api/user/index` → id, phone (cleartext), realname (cleartext), share_id chain, team_count
- `/api/user/authinfo` → full ID card number, name, phone
- ShareList names are star-masked but self-queried profiles are cleartext — crack accounts to unmask.

### 4. Mass user dump via shareList
`POST /api/nine/shareList {"token": T, "page": N}` → 15/page (locked), total can reach 25K+. Each entry has `member_id` + star-masked `realname`.

### 5. SVG Stored XSS
Upload SVG via `/api/common/upload` (PHP blocked, SVG allowed). Set as avatar via `/api/user/update_user`. Admin viewing user list triggers XSS. `location.href` in callback **reveals the admin prefix**. Plant across multiple accounts.

### 6. Pack platform
Separate APK packing system (often different port). May leak FTP/MinIO credentials, admin creds (`admin:123456`), and permission-swapping rules (evidence of malicious intent: hiding READ_SMS/RECORD_AUDIO behind INTERNET permission).

## Pitfalls
- `per_page` is server-locked (15) regardless of `size` param
- `xianceList` entries often have `member_id=0` (seeded fake data)
- Auth submission (`authadd`) validates Chinese name format
- Settings dump (`/api/index/get_setting`) requires no auth and leaks all domain URLs, commission rates, chat links
