# bb-methodology 全文 第 3/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## 2026 Field Additions (from The-XSS-Rat guide)

Four small items that are **not** already covered by the hunt-* cards:

- **Poisoned registration.** When signing up for a target, put a unique XSS/SSTI canary in *every* profile field (name, company, address, bio). Trigger the "admin reviews your account" workflow; the canary lands in the staff/admin view. Unique strings beat generic payloads — you can grep for them later.
- **GUID IDOR amplification.** A GUID is not automatically safe. If the app exposes any endpoint that *lists* GUIDs (feed, export, "shared with me", notification payload), collect them and replay the object endpoints. Also try the same GUID with `?fields=owner_id` / `?expand=owner`.
- **API version downgrade.** When `v2` is hardened, replay the same request against `v1` (`/api/v1/...`), and vice versa. Old versions often keep the same auth model but weaker authorization; a 404 on v1 is not proof it is gone — try `Accept: application/vnd.api.v1+json`.
- **Barracuda/embedded webmail XSS.** If `<svg onload>` is filtered, try `onwheel`, `oncontextmenu`, `onshow`, and `<details open ontoggle=...>`; these survive several older HTML sanitizers.

Platform notes: Intigriti has no negative karma for duplicates; some H1 programs pay a small duplicate bonus (check the program policy); VDP-only programs are worth a private-invite ask after 2–3 solid reports. GDPR/data-exposure findings can carry a separate multiplier — read the program's policy before filing as a plain IDOR.

## Related Skills & Chains

- **`hunt-dispatch`** — When PART 0 mode is confirmed (redteam / wapt + blackbox|greybox). Workflow primitive: after the engagement-type answer is locked, hand off to `hunt-dispatch` to fingerprint the target and load the matching platform + hunt-* skill set; this skill stops being the active context once dispatch prints its taxonomy.
- **`bug-bounty`** — When the user asks a generic "what should I do" or starts a new target. Workflow primitive: `bug-bounty` is the orchestrator that names which `hunt-*` skills to load by topic; this skill (`bb-methodology`) provides the 5-phase workflow that orchestrator runs against.
- **`triage-validation`** — When a finding completes Phase 4 and is about to be written up. Workflow primitive: Phase 5 explicitly calls `/validate` (the 7-Question Gate); only findings that pass all 7 questions get handed off to `report-writing`.
- **`offensive-osint`** + **`web2-recon`** — When Phase 1 (Recon) is active. Workflow primitive: Phase 1's "Wide approach" delegates to `offensive-osint` for asset arsenal and `web2-recon` for the live-host + URL pipeline.

---

## Operator Notes

> Engagement-derived additions to the vendored foundation. Wisdom from real
> authorized engagements + Phase 2 verification across this repo's 31+
> skill-area live tests. The upstream methodology covers the WHAT; this
> layer covers the WHEN-IT-ACTUALLY-WORKS and the FAILURE-MODES.

### What the methodology doesn't tell you

The vendored 5-phase workflow is a checklist; real engagements are improvisation. Sometimes you skip phases entirely — a client hands you a single URL and a JWT, recon was already done by their internal team, and Phase 1 collapses to a 10-minute fingerprint. Sometimes you spend 80% of the engagement in Phase 1 because the scope is a 200-asset financial-services parent org and asset discovery IS the work. The methodology is a map of terrain that exists in every engagement, not a sequence you traverse uniformly.

### Mode-confirmation, in practice

PART 0 (the bug-bounty vs WAPT vs red-team gate at the top of this file) is a hard rule, but the answer isn't always handed to you. Read the scope language:

- **"in-scope assets"** + **"out-of-scope assets"** + **"safe harbor"** → bug-bounty discipline. Validation-heavy, OOB-required, no exfil.
- **"kill chain"** + **"objectives"** + **"flag capture"** + **"adversary emulation"** → red-team. Stealth, persistence, lateral movement valid.
- **"compliance"** + **"PCI"** + **"HIPAA"** + **"executive report"** + **"remediation timeline"** → WAPT. Coverage-driven, deliverable-focused, all findings count regardless of exploitability.

When the language is mixed (common — clients often write WAPT-shaped SOWs and call them red-team engagements), default to bug-bounty discipline until proven otherwise. It's the most validation-strict mode; you can always relax later if the client confirms red-team. The reverse — assuming red-team latitude on what turns out to be a WAPT — gets findings retracted at delivery.

### Phase priority shifts by target type

The 5 phases are not equal-weight. Engagement type dictates the time allocation:

| Engagement | Recon | Hunt | Validate+Report |
|---|---|---|---|
| SaaS bug-bounty (defined scope) | 10% | 70% | 20% |
| External red-team (wide scope) | 40% | 30% | 30% |
| WAPT (asset list provided) | 0% | 60% | 40% |
| Enterprise on-prem (single product) | 5% | 50% | 45% |

If you find yourself spending 50% of a SaaS bug-bounty engagement in recon, you're procrastinating on the hunt. If you're spending 10% of an external red-team engagement on recon, you've already lost — the attack surface map IS the deliverable on those.

### When to break the methodology

If you find a Critical in the first 30 minutes of recon, **stop reconning, validate the Critical fully, report it, then return to recon.** The methodology says "complete the phase before moving on" — the value-per-hour curve disagrees. A confirmed Critical paying out within 24h of engagement start is worth more than a comprehensive asset list you'll never get to chain.

The same applies in reverse: if you've been hunting a candidate for 4+ hours and it won't reproduce on a second account, the candidate is dead. Don't sink another 4 hours into making a dead candidate reproduce. Drop it, document the retraction in your notes, move on.

### The discipline rules are non-negotiable

The discipline rules in this file — OOB Gate, Marker Discipline, Body-Diff Rule, Statistical-Sample Rule, Server-Policy-vs-State, Pre-Severity Gate, Shell-Loop Ban — are not methodology. They are quality gates. Methodology is the order of operations; these are the validation guarantees at each step.

Verified across Phase 2D's hardened-lab campaign: 8/8 discipline rules fired correctly against fake-bug-shaped behavior (URL echo dressed as XSS, word collision dressed as reflection, status-code-only "bypasses" with byte-identical bodies, 200-OK leak-claims with no actual leak data). Validation rates fall sharply when these rules get skipped. The friction is the feature — if a rule feels obstructive, that's it doing its job. The findings it kills are the half that would have come back N/A anyway.
- **`evidence-hygiene`** — When Phase 5 is collecting PoC screenshots / HARs. Workflow primitive: before any cookie / PII appears in a screenshot, hand off to `evidence-hygiene` for the redaction protocol.

