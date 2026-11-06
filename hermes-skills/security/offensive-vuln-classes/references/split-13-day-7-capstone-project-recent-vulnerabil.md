## Day 7: Capstone Project — Recent Vulnerability Triage and PoC Validation

- **Goal**: Apply the week's concepts by selecting several 2024–2025 vulnerabilities, correctly classifying and understanding them, locating and safely testing PoCs, and explaining what the vulnerability is, how it works, and how it can be chained.
- **Activities**:
  - **Select Targets (4–6 CVEs)**:
    - Choose recent CVEs from 2024–2025 spanning at least 3 categories: memory corruption, logic/auth, parser/media, kernel/drivers, networking/protocol, boot/supply chain.
    - Prefer items with public advisories and PoCs or detailed technical analyses.
  - **For Each CVE, Complete the Following**:
    1. **Identify**: Product/component, affected versions, vulnerability class (CWE), primary impact (RCE/LPE/Info Leak/DoS). Collect links to vendor advisory, NVD, and KEV (if listed).
    2. **Understand**: Summarize the root cause and vulnerable code path or state machine. Capture the key preconditions and trust boundaries.
    3. **PoC Discovery and Test**: Find a public PoC; verify authenticity; pin to a commit or release tag; note all prerequisites. If no PoC exists, move on we will get to it later on. try to understand how does that poc works
    4. **Explain (what/how/chain)**: In ~150–250 words, explain:
       - What the vulnerability is (class, component, versions, impact)
       - How it works (root cause and exploit path)
       - How it could be chained (e.g., info leak → ASLR bypass → RCE; sandbox escape → LPE)
    5. **Risk & Priority**: Provide CVSS v3.1/v4 estimate, EPSS (if available), KEV status, and remediation priority in a realistic enterprise context.
  - **Chaining Exercise (At least 1 chain)**:
    - Design a plausible multi-step chain using two or more selected CVEs (or one CVE plus a generic primitive), describing preconditions, boundary crossings, and final impact.

### Deliverables

- A short report (“Vulnerability Card”) per CVE and one chaining write-up.
- PoC references pinned to commit SHA/tag; note any modifications you made.

### Report Template (use per CVE)

```markdown
# CVE-YYYY-NNNNN – Title

- Class / CWE:
- Impact (RCE/LPE/Info Leak/DoS):
- Affected product & versions:
- Sources: [Vendor advisory], [NVD], [KEV], [PoC link]
- Lab environment:
  - Host OS / kernel / packages:
  - Target build/version:
  - Isolation controls (snapshot, no outbound):
- Reproduction steps:

1. ...
2. ...

- How it works (root cause and exploitation path):
- Chaining opportunities (with what and why it works):
- Risk rating: CVSS v3.1/v4 (your calc), EPSS, KEV status
```

### Suggested Sources

- NVD, CISA KEV, vendor advisories and security bulletins
- Google Project Zero, ZDI, ICS-CERT advisories
- Exploit-DB, GitHub code search (e.g., `CVE-2025 poc`, `proof-of-concept`)
- Academic/industry blogs with technical write-ups

### Submission Checklist

- `report.md` with one Vulnerability Card per CVE and one chain write-up
- Links to advisories/NVD/KEV, PoC URLs with commit SHAs/tags
- Environment details and exact reproduction steps
- Evidence artifacts (logs/PCAPs/crash traces/screenshots)
- Mitigation/detection guidance and remediation priority

<!-- Written by AnotherOne from @Pwn3rzs Telegram channel -->

