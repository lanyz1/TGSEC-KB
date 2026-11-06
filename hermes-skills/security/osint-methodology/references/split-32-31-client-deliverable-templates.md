## 31. Client Deliverable Templates

Operator-facing artifacts (asset graph, JSONL log, finding DB) are not the same as **client-facing artifacts** (exec summary, technical report). Build deliverables intentionally.

### 31.1 Executive summary template

```
ENGAGEMENT: <Client Name>
ASSESSMENT TYPE: External Attack Surface Assessment
ENGAGEMENT WINDOW: <start date> – <end date>
SCOPE: <one-line scope description, e.g., "All internet-facing assets of acme.com and its 3 brand domains">
LEAD: <your name / team>

----- KEY FINDINGS -----

1. [CRITICAL] <One-line title>
   Business impact: <one sentence in business language>
   Estimated remediation effort: <hours / days / weeks>
   Recommended action: <verb + object, e.g., "Rotate the exposed AWS access key and audit CloudTrail">

2. [CRITICAL] <One-line title>
   …

3. [HIGH] <One-line title>
   …

(Top 3-5 findings only; full list in technical report)

----- POSTURAL OBSERVATIONS -----

- Email security (SPF/DMARC): <2-3 sentences on posture, e.g., "DMARC is set to p=none, allowing spoof of <target>.com email; tightening to p=reject would block external spoofing.">
- Identity fabric (SSO): <2-3 sentences>
- Cloud surface (S3/GCS/Azure): <2-3 sentences>
- Mobile attack surface: <2-3 sentences if applicable>

----- AGGREGATE METRICS -----

- Assets discovered: <N> (<breakdown>)
- Findings: <N CRIT, M HIGH, P MED, Q LOW, R INFO>
- Live credentials confirmed: <N>
- Detectability of our operations: <90% low / 8% medium / 2% high>

----- RECOMMENDED NEXT STEPS -----

1. Address P0 findings in next 7 days.
2. Address P1 findings in next 30 days.
3. Schedule re-test for: <date>.
4. Consider follow-on assessments: <if applicable, e.g., authenticated app testing, internal pentest>.
```

### 31.2 Per-finding report card template

Each finding in the technical report uses this card:

```
═══════════════════════════════════════════════════════════
FINDING #<N>: <Title>
SEVERITY: <CRIT / HIGH / MED / LOW / INFO>
CONFIDENCE: <CONFIRMED / FIRM / TENTATIVE>
ASSET: <typed asset key>
DISCOVERED: <UTC timestamp>
═══════════════════════════════════════════════════════════

DESCRIPTION
  <2-5 sentence technical explanation>

EVIDENCE
  - URL: <where it was found>
  - Tool: <how it was discovered>
  - Screenshot: <attachment ref>
  - Raw HTTP: <sanitized capture>
  - Hash (SHA-256): <of any downloaded artifact>

REPRODUCTION
  Step 1: <command or action>
    Expected: <output>
  Step 2: …

IMPACT
  <Business-language impact statement>
  Affected systems: <list>
  Affected user populations: <if applicable>

REMEDIATION
  Immediate (within hours):
    - <action>
  Short-term (within days):
    - <action>
  Long-term (within weeks):
    - <action>

REFERENCES
  - <CVE-ID, advisory URL, OWASP top-10 link, vendor doc>

ATTACK PATH HINT
  <If applicable, the one-sentence hint from companion skill §39>
```

### 31.3 Risk translation matrix

Engineers think in CVSS. Executives think in business outcomes. Translate.

| Technical finding | Business-language impact |
|---|---|
| Listable S3 bucket with PII | "Customer records publicly downloadable. Potential GDPR/CCPA notification trigger if accessed. Estimated cost of disclosure: 30-day notification + credit monitoring + legal review." |
| Exposed `.env` with DB credentials | "Database access to all customer data. Pivots to backups, billing systems, employee PII. If exploited: full data breach scope." |
| Live AWS access key with admin scope | "Full cloud account compromise. Attacker can spin up cryptominers, exfiltrate all data, lateral-move to connected accounts. If exploited: 6-figure cloud bill + complete environment rebuild." |
| Open GraphQL introspection on prod | "API attack surface fully mapped by attackers. Enables more precise follow-on attacks; not directly exploitable but attacker reconnaissance is now zero-effort." |
| Subdomain takeover possible | "Attackers can host content under your trusted domain. Phishing emails from this domain bypass brand-impersonation defenses; users will trust them." |
| Open Firebase Realtime Database | "Mobile app's backend database is publicly readable. All user data, possibly writable. If exploited: full data breach + potential service disruption." |
| Missing HSTS on /login | "Login pages can be downgraded to HTTP via active network attacks. Credentials potentially captured by anyone with network access (coffee shop, conference WiFi)." |
| DMARC `p=none` | "Anyone on the internet can send email appearing to be from your domain. Phishing campaigns become trivially convincing for both customers and employees." |
| ≥10 employees in breach corpus | "Stolen credentials for your staff are circulating; attackers can attempt these against your SSO. Even if SSO has MFA, password reuse against other services puts those at risk." |
| `android:debuggable=true` | "Mobile app can be reverse-engineered and modified by anyone. Trust boundary between app and server is undermined; backend assumes app integrity that doesn't exist." |
| Vendor product (Citrix/F5/Pulse) version with KEV CVE | "Network appliance has a known-exploited vulnerability. Attackers are actively scanning the internet for this exact issue. Patch immediately." |

### 31.4 Reporting cadence for engagements > 1 day

- **Day 1 EOD** — short kickoff confirmation: "Stage 1 complete. Identified <N> assets so far. Initial posture: <one paragraph>."
- **Mid-engagement check-in** — when you find your first CRITICAL OR at the 50% time mark, whichever first. Heads-up to engagement lead: "Found <CRIT description>; recommend you alert <client contact> now to begin remediation prep."
- **End-of-engagement preliminary** — same day as last probe: top 5 findings + plan for full report delivery within X business days.
- **Final report** — formal deliverable; both exec summary + technical report.
- **Re-test offer** — proactive: "We're available for a re-test in <window>; recommend re-testing CRITICAL/HIGH findings after remediation."

### 31.5 Reproduction package contents

Deliver alongside the report:

```
<engagement-id>-reproduction-package.zip
├── README.md                    # how to use the package
├── engagement-metadata.json     # client, dates, scope, lead
├──tools-used.txt               # command-line name + version, one per line
├── run-log.jsonl                # every event during engagement
├── assets.db                    # SQLite of all discovered assets
├── findings.db                  # SQLite of all findings
├── evidence/
│   ├── screenshots/             # PNG, named by finding-id
│   ├── http/                    # raw HTTP captures (sanitized)
│   ├── downloads/               # any binary artifacts (with .sha256 alongside)
│   └── code/                    # any extracted source (sanitized)
├── re-test-script.sh            # reruns probes for the CRIT/HIGH findings
└── disclosure/                  # if applicable: bounty submissions, vendor notifications
```

The package is the source of truth — the report is the human-readable view. Anyone with the package can reproduce the engagement and verify findings.

---

