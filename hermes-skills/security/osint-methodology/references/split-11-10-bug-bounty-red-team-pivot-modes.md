## 10. Bug-Bounty / Red-Team Pivot Modes

Existing investigative work (threat-actor research, doxxing investigations, attribution) operates under different posture than offensive recon. Switch posture explicitly.

| Aspect | Investigative Mode | Offensive Recon Mode |
|---|---|---|
| **Probing rate** | Slow, single-threaded, blend with normal traffic. | Bursts, parallel, but rate-limited per provider. |
| **OpSec posture** | Sock-puppet only, never reveal investigator. | Persona may be the engagement persona; team may notify SOC. |
| **Evidence handling** | Court-grade chain of custody; hashes, timestamps, screenshots. | Engagement-grade; same hashing/timestamp discipline but evidence is for the client report. |
| **Severity in scope** | All severity levels relevant for context. | CRIT/HIGH/MED matter; LOW/INFO often dropped from exec summary. |
| **Authorization posture** | Public-record / OSINT-only; no probing private resources without authorization. | Written rules of engagement; explicit scope; explicit out-of-scope list. |
| **Reporting format** | Narrative + sourced timeline. | Per-asset findings + remediation + reproduction steps. |
| **Stop conditions** | When the question is answered. | When the engagement window closes OR when the report is delivered. |

When you're working with the user, ask which mode they're in if it's unclear from context.

### 10.1 Scale-Based Tactics

Org size shapes which techniques pay off.

**Small org (< 100 employees):**
- Executive accounts disproportionately matter; one CEO/CFO compromise often hands you the keys.
- Email harvest is small enough to enumerate exhaustively (10–50 emails total).
- Likely Microsoft 365 or Google Workspace; identity fabric is one tenant.
- Code repos often public on GitHub under personal accounts (founders moved from solo dev).
- Cloud presence often single-account AWS or GCP project.
- Tactics: deep on every email + every identity-fabric finding; full LinkedIn enum; check founders' personal GitHub orgs.

**Medium org (100–1K):**
- Balanced enumeration. Email list is enumerable but not exhaustive.
- Identity fabric likely one IdP but with multiple SaaS tenants (Slack workspace, Notion org, GitHub org).
- Mobile apps possible; check both stores.
- Cloud presence multi-account or multi-region.
- Tactics: full pipeline at standard depth; sample-and-deepen on each asset class; LinkedIn priority by role.

**Large org (1K–10K):**
- Email enum becomes lossy (sample top roles); breach hits scale up.
- Multi-tenant identity fabric (often Entra + Okta + multiple Auth0 customers).
- Mobile apps, multiple Android packages from different teams.
- Cloud presence sprawling; subsidiaries / acquisitions complicate scope.
- Tactics: breadth-first; rely on automation for asset discovery; manual triage on findings.

**Very large org (10K+) or conglomerate:**
- Brand-pivot maps before anything else: enumerate every brand domain, every subsidiary.
- Breach corpus dominates: 10K+ employees mean significant past-breach exposure.
- Identity fabric may differ per business unit (legal entity boundaries).
- Tactics: scope pruning is the most important step; sampling + automation throughout; deep dive only on high-priority findings.

**Cross-scale principle:** the smaller the org, the more individual-account focus pays off. The larger the org, the more systemic posture findings (DMARC gaps, SSO_EXPOSURE breadth, vendor-product version sweeps) pay off.

---

