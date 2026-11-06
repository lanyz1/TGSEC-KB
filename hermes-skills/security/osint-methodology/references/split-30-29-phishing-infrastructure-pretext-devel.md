## 29. Phishing Infrastructure & Pretext Development

Authorized red team engagements often include phishing. The **OSINT side** of phishing — building the phishing-feasibility shortlist and the pretext list — is in scope here. Crafting actual phishing payloads is **out of scope** (operational tradecraft, separate domain).

### 29.1 Phishing-feasibility shortlist

For an authorized engagement, the operator typically wants three lists:

**A. Already-registered typosquats** — these are *findings* (someone is squatting; client should know).

**B. Available-for-registration typosquats** — these are the *operator's phishing-domain shortlist* for the engagement.

**C. Cert-SAN impersonation patterns** — domains the operator could register that would make convincing certs (e.g., `acme-secure.com`, `acme-login.com`, `acme-vpn-portal.com`).

**Generation pattern:**
1. Run dnstwist (or equivalent) on the target's primary domain → get all variations (homoglyph, typosquatting, bit-flip, hyphenation, addition).
2. Check WHOIS for each: registered = list A, unregistered = list B.
3. For list C: combine target stem + plausible service words (`secure`, `login`, `vpn`, `portal`, `mail`, `helpdesk`, `it`, `account`, `verify`, `support`, `password`, `auth`, `sso`).

### 29.2 Subdomain takeover for trusted-domain phishing

If you found a takeover-able subdomain (companion skill §16.12), you can host phishing content **on a subdomain of the actual target**. This bypasses every brand-impersonation defense the user has.

**Procedure:**
1. Confirm takeover signature on the candidate (`<sub>.target.com` CNAMEd to unclaimed `<x>.herokuapp.com`).
2. Register the unclaimed resource (`<x>.herokuapp.com` on Heroku).
3. Now `<sub>.target.com` serves your content.
4. **Stop and consult the engagement lead before going live with phishing content.** Even in authorized engagements, the takeover step itself may need explicit client sign-off.

### 29.3 Email spoof feasibility

Use email security analysis (companion skill §16.14) to determine spoof feasibility:

| SPF policy | DMARC policy | Spoof feasibility |
|---|---|---|
| `~all` (softfail) or absent | `p=none` or absent | **HIGH** — direct spoof of `<anything>@<target>` likely lands. |
| `~all` | `p=quarantine` | MEDIUM — lands in spam folder, but lands. |
| `-all` (hardfail) | `p=quarantine` | LOW — most providers reject; some still deliver to spam. |
| `-all` | `p=reject` | VERY LOW — spoof rejected by major providers. Requires lookalike domain. |

If spoof is hard, fall back to lookalike (list B) or compromised-third-party (different engagement). Document the postural finding regardless.

### 29.4 Pretext development from OSINT

Pretexts work when they tap a target's existing context. Build pretexts from harvested OSINT.

**Pretext sources:**

- **Job titles + reporting structure** (LinkedIn) — "Hi <name>, this is <CFO-name>'s assistant; can you look at this finance file?"
- **Recent corporate events** (press releases, news, careers page) — "We're following up on the layoffs / new acquisition; please confirm your benefits info."
- **Vendor relationships** (job postings mentioning "experience with Workday/Salesforce/etc.") — "Workday password reset required by EOD."
- **Public conferences / travel** (LinkedIn posts, conference pages) — "Hi <name>, we met at <conference last week>; following up on what we discussed."
- **GitHub commits / open-source work** — "I saw your fix in <repo>; want to collaborate on a related PR?"
- **Office locations** (LinkedIn) — "On-site IT for the <city> office requires a quick auth check."

**Per-role pretext templates** (the ones operators use most):

- **End-users (general staff):** IT helpdesk password reset, Workday HR action required, Microsoft 365 storage full, package delivery confirmation.
- **Executives:** finance authority (BEC-style "wire approval needed"), board materials shared, M&A NDA review, executive assistant request.
- **Developers / engineers:** GitHub security alert, CI build failed, package security advisory, conference CFP follow-up.
- **HR / Finance:** payroll vendor change, expense report rejection, benefits enrollment deadline, vendor invoice discrepancy.
- **IT / Security:** vendor security update notification, on-call escalation, monitoring command-line alert.

### 29.5 Operational discipline for phishing infrastructure

- All phishing infrastructure must be approved by the engagement lead **before** going live.
- Document every domain registered + every email sent (sender, recipient, subject, timestamp UTC).
- Keep phishing infrastructure isolated from your normal recon infrastructure (different IPs, different personas, different domain registrar accounts).
- Use dedicated payment methods for phishing-domain registration (engagement-specific corporate card; don't use personal).
- Tear down promptly after engagement; transfer/expire all domains; close all hosting accounts.

---

