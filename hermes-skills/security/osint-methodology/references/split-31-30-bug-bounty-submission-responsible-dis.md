## 30. Bug Bounty Submission & Responsible Disclosure

When you find an issue on a bug-bounty target (HackerOne, Bugcrowd, Intigriti, YesWeHack) or on a non-program target where you choose to disclose responsibly.

### 30.1 Platform-specific basics

| Platform | URL | Notes |
|---|---|---|
| HackerOne | hackerone.com | Largest; strong scope-tracking; CVSS-based reward calc. |
| Bugcrowd | bugcrowd.com | VRT (Vulnerability Rating Taxonomy) instead of CVSS for severity. |
| Intigriti | intigriti.com | EU-strong; flexible scope models. |
| YesWeHack | yeswehack.com | EU-headquartered; growing. |
| HackenProof | hackenproof.com | Crypto/blockchain-focused programs. |
| Open Bug Bounty | openbugbounty.org | Free for sites without official programs (only XSS/SSRF disclosure). |
| security.txt | rfc9116 | Universal: every site should publish `/.well-known/security.txt`. |

### 30.2 Report structure (works on any platform)

```
Title: [Severity] [Affected component] Brief description
   Example: [HIGH] [api.acme.com] Unauthenticated SSRF via /v1/proxy

Summary
   2-3 sentences explaining what was found and why it matters.

Steps to Reproduce
   1. Numbered, copy-pasteable.
   2. Include exact URLs, payloads, expected vs actual response.
   3. Reproduce the issue from a fresh state where possible.

Proof of Concept
   - Screenshot showing the vulnerability triggered.
   - HTTP request/response (sanitize sensitive data; redact other users' data).
   - Or short video/GIF for complex multi-step issues.

Impact
   Quantify: what data is at risk, how many users, what business functions break.
   Tie to the program's impact criteria where defined.

Severity (per program criteria)
   - CVSS v3 vector: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
   - Score: 9.8 (Critical)
   - Justification: <1-2 sentence reasoning>

Remediation
   - Concrete recommendation. "Validate the URL parameter against an allowlist before fetching."
   - If a quick fix: WAF rule, header check.
   - If a structural fix: refactor recommendation.

Affected component
   - URL: https://api.acme.com/v1/proxy
   - Date discovered: 2026-04-27 14:23 UTC
   - Method: HTTP GET / POST / etc.
```

### 30.3 Severity inference per program

- HackerOne uses CVSS v3 with program-specific multipliers (some programs cap at HIGH; some pay 10x for CRITICAL).
- Bugcrowd VRT: P1 (Critical) → P5 (Informational); maps roughly to CRIT/HIGH/MED/LOW/INFO.
- Intigriti uses `Exceptional / Critical / High / Medium / Low` tiers.
- For programs that pay flat rates per severity tier, **don't inflate**. Conservative severity → trust → repeat awards.

### 30.4 Disclosure for unprogrammed targets (CVD)

If the target has no bug bounty program but you found a real vulnerability during authorized testing (e.g., a customer's external assessment surfacing a third-party vendor's bug):

1. Check for `<target>/.well-known/security.txt` — if present, follow its `Contact:` and `Encryption:` (PGP) instructions.
2. If absent, try `security@<target>` then `abuse@<target>`.
3. If those bounce, escalate via the registered abuse contact in WHOIS.
4. CERT/CC (cert.org) and national CERTs (CISA, CERT-EU, JPCERT) for coordination if vendor unresponsive.
5. Standard 90-day disclosure window before public release (Project Zero norm).

### 30.5 Cloud provider / SaaS-specific channels

- AWS abuse: `<EMAIL-REDACTED>`. For exposed AWS keys: also notify the account owner if discoverable via WHOIS/contact.
- GCP: `<EMAIL-REDACTED>`.
- Azure: Microsoft Security Response Center (MSRC) at `https://msrc.microsoft.com/`.
- GitHub: secret-scanning auto-revokes most published secrets via GitHub's partner program; if you find one, the scanning is usually faster than manual disclosure but back-up notify GitHub at `<EMAIL-REDACTED>`.
- npm / PyPI / Docker Hub: each has an `abuse@` or `security@` channel; npm specifically auto-revokes leaked tokens via their secret scanner.

### 30.6 Things to avoid in reports

- Don't include anyone else's PII / passwords / data in the report (redact).
- Don't post the report or PoC publicly until the disclosure window expires.
- Don't escalate via social media first (always direct channel first).
- Don't demand a specific bounty amount; let the program decide.
- Don't submit the same finding to multiple programs (duplicates can hurt your reputation).

---

