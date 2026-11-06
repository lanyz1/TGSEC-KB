---
name: password-spray-methodology
description: End-to-end password spray playbook. User enumeration, lockout detection, password pattern generation, spray execution across all protocols, error code differentials, and engagement discipline. Unifies M365/Entra, Okta, Exchange, Kerberos, SharePoint, XMLRPC, OIDC, and AD SMB/WinRM spraying into one methodology.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [password, spray, methodology, redteam]
---

# Password Spray Methodology

Password spraying is the highest-ROI credential attack: one (or few) passwords tried against many users. It's quiet, avoids lockouts, and succeeds where traditional brute force fails. This skill consolidates every spray vector, enumeration technique, pattern, and protocol across the entire skill catalog.

**This is a methodology skill.** Protocol-specific details live in their respective skills — cross-reference them for deep dives. This skill covers the **universal spray pipeline** that applies everywhere.

## When to Use

- Starting ANY engagement with a user list but no credentials
- Finding internet-facing login portals (OWA, Okta, ADFS, VPN, SSO, OIDC)
- After `hunt-ntlm-info` reveals AD domain/UPN format — feed into spray
- After `hunt-ldap` enumerates sAMAccountNames — feed into spray
- After `js-secrets-extraction` finds email patterns — feed into spray
- OneDrive 302/404 enum (from `m365-entra-attack`) confirms licensed users — spray them
- Any leaked credential dump from client — validate against all services
- Active-attacker detection via Smart Lockout differential

## Universal Spray Pipeline (5 Phases)

```
Phase 1: ENUMERATE USERS    → valid user list
Phase 2: DETECT LOCKOUT      → max attempts/min, throttle rate
Phase 3: GENERATE PASSWORDS  → 5-20 high-probability candidates
Phase 4: EXECUTE SPRAY       → per-protocol, low-and-slow
Phase 5: INTERPRET RESULTS   → error code differential → finding or discard
```

---

## Phase 1 — User Enumeration

The spray is only as good as the user list. Gather usernames BEFORE touching any auth endpoint.

### Universal Enumeration Sources

| Source | Technique | Lockout Risk | Skill Reference |
|--------|-----------|-------------|-----------------|
| **LinkedIn / company page** | Scrape employee names → `username-anarchy` | Zero | — |
| **OneDrive personal site** | `GET /personal/<user>_<domain>_com/_layouts/15/onedrive.aspx` → 302=exists, 404=no | Zero | `m365-entra-attack` |
| **Kerberos pre-auth** | `kerbrute userenum --dc <DC> --domain <DOMAIN> users.txt` | Zero (KDC_ERR_PREAUTH_REQUIRED does not count as auth failure) | — |
| **NTLM Type-2 decode** | Extract AD domain, NetBIOS name, computer name from anonymous probe | Zero | `hunt-ntlm-info` |
| **Jira user picker** | `/rest/api/2/user/picker?query=` — public on misconfigured instances | Zero | — |
| **Jenkins** | `/asynchPeople/` or `/securityRealm/user/<name>/` | Zero | — |
| **ManageEngine ADManager Plus** | Unauthenticated user listing on exposed instances | Zero | — |
| **WordPress REST API** | `/wp-json/wp/v2/users` — dumps authors with usernames | Zero | `hunt-wordpress` |
| **GitLab** | `/api/v4/users` — public on open instances | Zero | — |
| **O365 Autodiscover** | HARDENED — returns identical 200 for all (2024+) | Zero but dead | `m365-entra-attack` |
| **GetUserRealm** | HARDENED — returns same XML for any email in tenant | Zero but dead | `m365-entra-attack` |

### Username Format Generation

After scraping names, generate all org-likely formats:

```bash
# From a list of real names (First Last, one per line)
./username-anarchy -i names.txt > usernames.txt

# Common formats for enterprise targets:
# firstname.lastname, f.lastname, firstnamelastname, flastname
# firstname_lastname, lastname.firstname, firstname
# Also try: email prefix from known addresses (jdoe@ → jdoe)
```

### CeWL — Target-Specific Word Extraction

```bash
cewl -d 3 -m 6 --lowercase https://target.com -w target_words.txt
# Feeds both username generation AND password patterns
```

---

## Phase 2 — Lockout Detection & Throttle Math

### Four Rate-Limit States (from `hunt-brute-force`)

Before spraying, classify the target endpoint into one of four states:

| State | Signal | Spray Feasible? |
|-------|--------|----------------|
| **Hard lockout** | Account disabled after N fails; correct creds also fail | No (DoS finding instead) |
| **Soft IP throttle** | 429 or increasing latency keyed on source IP | Yes — bypass via IP rotation |
| **CAPTCHA injection** | 200 but body switches to CAPTCHA after N attempts | Maybe — check if API path skips it |
| **Silent shadow-throttle** | 200/401 on every request but submissions are dropped silently | TRAP — inject known-good value at known position to detect |

### Shadow-Throttle Detection (CRITICAL — the biggest false-negative)

```bash
# Inject a known-good credential at position 500
# If it stops working under load, shadow-throttle is active
# Your "no rate limit" conclusion was false
KNOWN_GOOD="<EMAIL-REDACTED>:CorrectP@ss"
for n in $(seq 0 600); do
  code=$(curl --max-time 30 --connect-timeout 10 -sk -u "user${n}@target.com:WrongP@ss" -o /dev/null -w "%{http_code}" \
    "https://TARGET/auth-endpoint")
  echo "$n $code $(wc -c </tmp/bf_body)"
done
# Watch: status flips, time_total climbing, body size changing
```

### Smart Lockout Math (Microsoft Entra ID — from `m365-entra-attack`)

- **Default**: 10 failed sign-ins in 10 minutes → 1-minute lockout
- **Counter shared across ALL auth flows** (ROPC + SAML + IMAP + EWS + SMTP + device-code)
- **Mathematical guarantee**: with ≤1 attempt per user, you CANNOT cause Smart Lockout (1 < 10)
- **Any AADSTS50053 observed = PRE-EXISTING external attacker** → SOC finding

```python
HARD_CAP = 1  # per user per engagement LIFETIME — never higher
```

### Okta Lockout

- **Default**: 10 failed sign-ins (configurable, some orgs: 3)
- Discipline: ≤2 attempts per user lifetime (safer than Entra's 1 because Okta lockout can be 3)

### Exchange/OWA Rate Limit Test

```bash
for i in $(seq 1 5); do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 10 --connect-timeout 10 \
    -X POST "https://$TARGET/owa/auth.owa" \
    -d "destination=https://$TARGET/owa/&username=testuser$<EMAIL-REDACTED>&password=<REDACTED>")
  echo "Attempt $i: HTTP $code"
done
# All same code → no rate limiting on this endpoint
```

### Concrete Throttle References

| Protocol | Safe Rate | Source |
|----------|----------|--------|
| M365 ROPC | ≤30 req/sec to login.microsoftonline.com (per IP) | Authorized engagement |
| M365 Smart Lockout | ≤1 attempt per user LIFETIME per engagement | Mathematical guarantee |
| Okta /authn | ≤2 attempts per user lifetime; slower than Entra (tuner-different anti-automation) | Authorized engagement |
| Exchange OWA | Test 5 rapid attempts first; if uniform, spray slowly | `exchange-owa-attack` |
| SharePoint SOAP | No rate limit observed on SP2013; still go slow | `hunt-sharepoint` |
| Kerberos (Kerbrute) | No lockout risk from pre-auth probe; spray pace: 1 password per full user list per hour | Public research |
| IP Rotation Bypass | `X-Forwarded-For`, `X-Real-IP`, `X-Originating-IP`, `CF-Connecting-IP`, `True-Client-IP` | `hunt-brute-force` |
| NodeZero reference | 2 attempts per hour in production environments | Horizon3.ai (2022) |

---

## Phase 3 — Password Pattern Generation

### The Complexity Backfire (CRITICAL INSIGHT)

Password complexity policies (uppercase + lowercase + digit + special) produce MORE predictable passwords, not less. The human pattern is always the same: **Uppercase first letter + lowercase word + digit at end + ! at end**.

Observations from PACK analysis (Kacherginsky, 2013) across RockYou, LinkedIn, MySpace, Stratfor, Singles.org, FaithWriters, phpBB:

1. **`: ` (no transformation)** — 2-25% of all passwords are straight dictionary words
2. **`$1` (append "1")** — 0.5-5.5% of all passwords
3. **`$1 $2 $3`** — 0.1-0.6%
4. **`$1 $2`** — 0.08-0.5%
5. **Seasonal**: `Summer2024!`, `Winter2025!`, `Spring2026!`
6. **Company**: `<Brand>@2026`, `<Brand>@123`, `<City>@2026`
7. **Default rotation**: `Password@<year>`, `Welcome@<year>`, `Admin@<year>`

### Pattern Generation Recipe

```python
# 1. Company-derived patterns
brand_variants = ["CompanyName", "Company", "COMPANY", "company"]
years = ["2026", "2025", "2024", "2023", "26", "25"]
specials = ["", "!", "@", "#", "1", "123", "123!"]
seasonal = ["Summer", "Winter", "Spring", "Autumn", "Fall"]
passwords = []
for brand in brand_variants:
    for year in years:
        for spec in specials:
            passwords.append(f"{brand}{year}{spec}")
            passwords.append(f"{brand}@{year}")
for season in seasonal:
    for year in years:
        passwords.append(f"{season}{year}!")
        passwords.append(f"{season}{year}")

# 2. Plant/office city names from company website
cities = ["SaoPaulo", "Rio", "BH", "Brasilia"]
for city in cities:
    for year in years:
        for spec in specials:
            passwords.append(f"{city}{year}{spec}")

# 3. Functional account defaults
functional = ["noreply", "purchase", "accounts", "postmaster",
              "transport", "admin", "helpdesk", "support", "info"]
for func in functional:
    passwords.append(f"{func}@123")
    passwords.append(f"{func}{year}")
```

### Wordlist Strategy

| Stage | Wordlist | When |
|-------|----------|------|
| **1. Leaked creds** | Client-provided dump, stealer logs | Always first — each is the strongest guess for that user |
| **2. Company-specific** | CeWL output + brand patterns (Phase 3 recipe) | Every engagement |
| **3. Probable-Wordlists** | Top 100 from berzerk0's frequency-sorted list | When company patterns fail |
| **4. rockyou.txt top-N** | Filter to 8+ chars matching target policy | Fallback |
| **AVOID** | RockYou2024 | 98% garbage (hashes, truncated strings, unicode junk, Russian text) — zero practical value |
| **Custom mutations** | Apply Hashcat rules to company-specific list | Deep engagement |

```bash
# Generate mutated list with common rules
hashcat --stdout -r /usr/share/hashcat/rules/best64.rule target_words.txt | sort -u > mutated.txt
```

---


## 全文导航（已拆分）

主卡保留前 5 节；其余 8 节在 `references/full.md`：

- Phase 4 — Spray Execution Matrix
- Phase 5 — Error Code Differentials
- Engagement Discipline
- Chain Table
- Tool Summary
- Verification
- Pitfalls
- Related Skills

加载：`skill_view(name='password-spray-methodology', file_path='references/full.md')`
