---
name: m365-entra-attack
description: Microsoft 365 / Entra ID red-team attack chain — current 2026 reality. AADSTS code reference, user enumeration vectors (with hardening status), Smart Lockout math, Conditional Access bypass options, ROPC + SAML SSO browser flow, Burp/Playwright templates. Built from authorized red-team work where ROPC spray surfaced pre-existing lockouts and CA-blocked credentials, plus real-time external attacker activity correlation. Use for any M365/Entra credential attack, password spray, user enumeration, CA-bypass exploration, or active-attacker-detection scenario.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [m365, entra, azure, attack, redteam]
---

## When to use this skill

Trigger when:
- Target uses M365 / Entra ID (autodiscover.* records, login.microsoftonline.com redirects, "Microsoft Office 365" in tech-stack notes)
- You have a list of corporate emails or stealer-leaked creds
- Engagement involves "credential spray", "password spray", "Entra attack", "ATO via M365"
- You see `*.onmicrosoft.com`, `*-my.sharepoint.com`, `enterpriseregistration.*`, `enterpriseenrollment.*` in recon
- Client mentions "Conditional Access", "MFA bypass", "compliant device"

DO NOT use for:
- On-prem-only Active Directory (use a separate AD-attack skill)
- Service-to-service token attacks (different threat model)
- Phishing-required attack chains (covered by phishing skills) — but you can prep for the credential-validation step here

---

## Tenant discovery (msftrecon)

```bash
# For each owned domain
msftrecon -d client.example
msftrecon -d clientltd.example
msftrecon -d sister-brand-school.example
```

Key fields in output:
- **Tenant ID** (different domains may share OR have separate tenants — always test all owned domains)
- **Federation Information.Namespace Type** = `Managed` (cloud-only, ROPC works) | `Federated` (ADFS, different attack)
- **SharePoint Detected** (Yes = OneDrive enum vector available)
- **Communication Services Teams/Skype** (post-auth lateral targets)
- **Admin Consent Endpoint accessible** (consent-phishing surface)

**Red flag:** if the org has multiple Entra tenants for sister domains, each is a separate attack surface with its own user list, lockout policy, and CA configuration. Don't assume one spray covers all.

---

## AADSTS code reference (memorize)

| AADSTS | Meaning | Lockout impact | What to do |
|---|---|---|---|
| 50034 | User does not exist | None | Skip; remove from spray list |
| 50126 | Invalid username/password | +1 attempt counter | User exists — try alternate password later (within cap) |
| 50053 | Account locked (Smart Lockout) | None (already locked) | Pre-existing → flag to SOC; don't retry |
| 53003 | CA blocked token issuance | +1 attempt counter | **PASSWORD VALID** — STOP, password is correct |
| 50076 | MFA required | +1 attempt counter | **PASSWORD VALID** — second factor needed |
| 50079 | Strong auth required | +1 attempt counter | **PASSWORD VALID** — same as 50076 |
| 50158 | External auth required | +1 attempt counter | **PASSWORD VALID** — federated MFA |
| 530003 | Device-state required | +1 attempt counter | **PASSWORD VALID** — needs compliant device |
| 65001 | Consent required | +1 attempt counter | App-consent issue, not auth |
| 700016 | App not in tenant | None | User in different tenant — adjust target |
| 90002 | Tenant does not exist | None | Tenant typo / dead tenant |

**Critical insight:** any code in {53003, 50076, 50079, 50158, 530003} means **the password is correct** — Microsoft only returns these AFTER successful credential validation. Document as a confirmed-valid finding even if you can't get a token.

---

## Smart Lockout math (the cap discipline)

**Microsoft default policy:**
- 10 failed sign-ins in 10 minutes → 1-minute lockout
- 20 failed sign-ins → progressively longer lockouts (exponential backoff)
- Counter shared across **ALL auth flows** (ROPC + SAML + IMAP + EWS + SMTP + device-code)

**Engagement discipline:**
- Hard cap: ≤2 password attempts per user **lifetime per engagement** (some engagements: 1)
- State file with atomic writes — never let two test runs race the counter
- Kill switch: stop run if more than N LOCKED responses observed (suggests pre-existing attacker activity OR you miscounted; either way pause)

**Mathematical guarantee:** with 1 attempt per user, **you cannot cause Smart Lockout** (1 < 10). Any AADSTS50053 you see is therefore pre-existing → use this for active-attacker detection (see `mid-engagement-ir-detection` skill).

---

## User enumeration — vectors + hardening status (May 2026)

### ❌ HARDENED (no longer differential)

```http
GET /getuserrealm.srf?login=<email>&xml=1
```
Returns identical XML for any email matching tenant's owned domain. **Tenant-level only, not user-level.**

```http
POST /common/GetCredentialType
{"username":"<email>", "isOtherIdpSupported":true, ...}
```
Returns `AADSTS1659001` (missing flowToken) without proper session — can't enumerate.

```http
GET /autodiscover/autodiscover.json/v1.0/<email>?Protocol=AutodiscoverV1
```
Returns identical 200 + same JSON body for any address. Hardened ~2024.

### ✅ STILL WORKS (May 2026 — track shelf life)

**OneDrive personal-site differential:**
```http
GET /personal/<user>_<domain>_com/_layouts/15/onedrive.aspx HTTP/1.1
Host: <tenant>-my.sharepoint.com
```
- **302 → user EXISTS** (auth-required redirect to Authenticate.aspx)
- **404 → user does NOT exist** (404 FILE NOT FOUND)
- ZERO authentication attempt → ZERO lockout impact
- Bonus: `Sprequestduration` header faster (~40ms) for existing users vs ~600ms for non-existent — secondary timing oracle

**Caveats:**
- Only works if SharePoint is provisioned for the tenant (check msftrecon `SharePoint Detected: Yes`)
- Microsoft is hardening these endpoints over time — re-verify before relying on it
- Some users may exist in Entra without OneDrive provisioning (license-dependent) — false negatives possible

**2026-05-17 re-verification (authorized-engagement revalidation):** The OneDrive enum primitive STILL WORKS as of 2026-05-17. Calibration: licensed users return HTTP 200 with ~57KB body; nonexistent users / shared-mailbox accounts return 404 with 0 bytes. The /personal/ root path (without /_layouts/15/onedrive.aspx) returns the same differential.

**Killer use case: license differential = account-class signal.** Cross-reference OneDrive 200/404 with ROPC AADSTS50034/50126:

| OneDrive | ROPC | Classification |
|---|---|---|
| 200 | AADSTS50076 (MFA req) or 50126 | **Licensed regular user** (real employee, MFA enforced) |
| 200 | AADSTS50034 | (shouldn't happen — inconsistency, investigate) |
| 404 | AADSTS50126 | **Shared mailbox / functional / service account** (no OneDrive license, has password) — historic MFA-exempt class, prime target for password guessing |
| 404 | AADSTS50034 | Doesn't exist in tenant |
| 404 | AADSTS50076 | Edge case (functional account WITH MFA enforced — rare) |

The OneDrive-404 + ROPC-50126 combination is **the signal for "functional account that might bypass MFA"** — admins frequently exempt these from CA policies because they're used by automation that can't satisfy MFA. Discovered usefulness on authorized-engagement revalidation: identified `noreply@`, `purchase@`, `accounts@`, `postmaster@`, `transport@` as functional-account candidates (typical for any conglomerate tenant).

**ROPC AADSTS50034 / AADSTS50126 differential:**
- AADSTS50034 (user not exist) does NOT increment Smart Lockout counter
- AADSTS50126 (wrong password) DOES increment
- So a 1-attempt-per-user spray can be used as a coarse user-existence enumerator (each AADSTS50034 = miss, each AADSTS50126 = hit + 1 attempt burned)

---

## Conditional Access bypass options (most blocked, document anyway)

| Vector | Status (2026) | Notes |
|---|---|---|
| Different ROPC client_id (Microsoft Graph PowerShell vs Azure CLI vs Office) | Sometimes works | CA can be per-app; try `1b730954-1685-4b74-9bfd-dac224a7b894` (Graph PS), `04b07795-8ddb-461a-bbee-02f9e1bf7b46` (Azure CLI), `d3590ed6-52b3-4102-aeff-aad2292ab01c` (Office) |
| Different resource (graph.microsoft.com / outlook.office.com / management.azure.com) | Sometimes works | CA scope can be per-resource |
| EWS / IMAP / POP3 / SMTP Basic Auth | Mostly disabled | MS deprecated Basic Auth Oct 2022; per-account exceptions exist |
| FOCI (Family of Client IDs) | Token-refresh path | Use a refresh token from one FOCI client to mint tokens for another |
| Device-code phishing | Works | Requires user-side interaction (OOS for many engagements) |
| Compliant-device emulation | Hard | Requires Intune device registration — high effort, often impossible without insider |
| AiTM session-cookie steal | Works (with phishing) | Modern primary technique — out of scope for non-phishing engagements |
| FOCI + Family Refresh Token Theft | Post-auth | Requires already having a token |
| SAML SSO via different SP | Sometimes | Each enterprise app has its own CA policy; an app with weaker CA = pivot |
| Geo-bypass via VPN | Sometimes | If "trusted location" CA policy includes corp HQ IPs, use a VPN exit there |

**Key insight from this engagement:** in a tenant with universal CA policy (compliant device + MFA), all the above paths return AADSTS53003 with the same flow. The cred is valid, but unusable from external. **Phishing-completed cookie steal is the only realistic adversary path.** Document this clearly so the client understands the threat model.

---


## 全文导航（已拆分）

主卡保留前 6 节；其余 12 节在 `references/full.md`：

- ROPC password validation (the canonical test)
- SAML SSO browser flow (for definitive cred validation when CA blocks ROPC)
- Active-attacker detection via lockout differential
- Common password patterns to spray (multi-brand enterprise targets)
- Engagement journaling (mandatory)
- Real-world findings template (from authorized-engagement)
- Anti-patterns (don't do these)
- Tooling
- Verification
- Pitfalls
- Related Skills & Chains
- 2026-10 ConnectWise Cloud Backup（原 SkyKick）凭证滥用

加载：`skill_view(name='m365-entra-attack', file_path='references/full.md')`
