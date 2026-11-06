# triage-validation — 全文续篇

> 主卡保留前 6 节；本文件从第 7 节起。原文件：`/root/.hermes/skills/security/triage-validation/SKILL.md`

## KILL FAST RULES

The goal is to QUICKLY disqualify bad leads so you hunt real bugs:

1. **5-minute rule**: If you can't fill in Q1's template in 5 minutes → move on
2. **Precondition count**: More than 2 preconditions simultaneously required → kill it
3. **Impact test**: "What does attacker walk away with?" — if nothing tangible → kill it
4. **Admin bypass**: "Admin can do X" is NEVER a bug → kill it immediately
5. **Design doc test**: If it's documented behavior → kill it immediately
6. **Rabbit hole signal**: 30+ min on Q6 with no reproducible PoC → kill it

---

## PRE-SEVERITY GATE

Before labelling any finding **Critical** or **High** anywhere in your notes or report — write out the answer to each of these as a one-liner. If you can't answer concretely, **the severity is wrong**.

1. **Have I validated the FULL chain to attacker-attainable impact, or only one primitive in the middle?**
   — "Primitive confirmed at layer N" ≠ exploitable. Multi-stage chains require ALL stages validated before the severity matches the chain's top end.
2. **What does the attacker walk away with, in one concrete sentence?**
   — "RCE on the SP front-end web server" is concrete. "Could lead to RCE" is not — that's High at best, often Medium.
3. **Have I personally reproduced the full chain end-to-end at least twice?**
   — Twice = once during discovery, once for the report screenshot/PoC. Not "I'm sure it would work."
4. **Is there an inheritance gate, signature check, audience check, or other validation step still gating the chain?**
   — If yes, the chain is not Critical. Document it as "primitive present" at lower severity until the gate is bypassed.
5. **Has the program rejected this severity class before?**
   — Many programs cap "info disclosure with no concrete impact" at Low/Info regardless of the data type. Read the program scope.

**Lesson from an authorized engagement:** JWT `alg:none` was initially labelled **Critical** based on the signature-bypass primitive being confirmed at the audience-validation layer. Subsequent testing showed the issuer-trust check still rejected unsigned tokens — the full ATO chain did not complete. Finding had to be retracted. If the Pre-Severity Gate had been run on the original draft, Q1 would have killed the Critical label before submission.

---

## ANTI-PATTERNS THAT LOSE MONEY

```
Writing a report before confirming the bug exists (most common)
Submitting theoretical impact without proof
"The API returns more fields than necessary" (sensitivity matters — is it actually sensitive?)
Chaining A+B into one report when they're separate bugs (two separate payouts)
Reporting B saying "similar to A in my other report" — fresh Gate 0 for every bug
Overclaiming severity — triagers trust you less next time
Under-describing impact — triager doesn't understand why it matters
```

---

## RETRACTION DISCIPLINE

When a previously-claimed finding fails reproduction — **never silently drop it.** Document the retraction in the report's appendix. This proves to the triager that you validate your own work, and it saves them from chasing a phantom you've already disproved.

**Retraction entry template:**

```markdown
### Retracted: <finding name>

- **Original signal:** <one-line description of what looked like a bug>
- **Disproving evidence:** <concrete reproduction-step + observation that disproves it>
- **Why it looked like a bug:** <root cause of the false positive — e.g., natural marker collision, network jitter, status-code-only confidence>
- **Retraction date:** <YYYY-MM-DD>
```

**Concrete retractions from an authorized engagement — pattern reference:**

- **X-Forwarded-Proto reflection** — looked like header reflection across 4 pages; was the literal word `javascript` in SP help-link hrefs. Cause: non-unique marker.
- **Host header `:80@evil` bypass** — 200 OK on a path that normally 403s; body byte-identical to baseline (8341 bytes). Cause: status-code-only confidence; ELB Host normalisation dropped the `@evil` portion.
- **`download.aspx` file-existence oracle** — looked like a file-existence differentiator across path types; was SP's file-extension blocklist (`.ashx`/`.asmx`/`.svc`/`.config` always blocked regardless of existence). Cause: confusing server-side policy with file state.
- **`Administrator` timing leak** — single-shot 1527 ms vs ~700 ms control on Authentication.asmx Login; n=80 interleaved reproduction collapsed every group to 685-716 ms. Cause: single-sample statistical claim.

**Why this matters:** retracted findings put in an appendix demonstrate methodological honesty. Silently dropping them looks like you cherry-picked. A clean 11-finding report with a retraction appendix is more trustworthy than a 13-finding report where 2 fall apart at triage.

---

## Related Skills & Chains

- **`report-writing`** — When all 7 questions pass and the Pre-Severity Gate is clean. Workflow primitive: this skill is the gate that runs BEFORE `report-writing`; only findings that clear all 7Q + 4 pre-submission gates get the report-template handoff.
- **`bugcrowd-reporting`** — When a Bugcrowd VRT mapping is needed for an accepted finding. Workflow primitive: after this skill validates the finding, `bugcrowd-reporting` decides the VRT category and severity-request paragraph.
- **`evidence-hygiene`** — When the validated finding needs PoC evidence captured. Workflow primitive: this skill says "Q6 requires proof of impact"; `evidence-hygiene` provides the capture-and-redact protocol for that proof.
- **`security-arsenal`** — When checking the always-rejected / conditionally-valid tables. Workflow primitive: this skill's "Never Submit List" and `security-arsenal`'s "Always Rejected" table are aligned; either entry-point lookup decides whether a primitive is reportable alone or only with a chain.
- **`bb-methodology`** — When Phase 5 (Validate & Report) starts. Workflow primitive: Phase 5's pre-report gate explicitly invokes `/validate` (this skill's 7Q gate) before any report is drafted.

---

## Operator Notes (Claude-BugHunter)

> Engagement-derived additions to the vendored foundation. Wisdom from real
> authorized engagements + Phase 2 verification across this repo's 31+
> skill-area live tests. The upstream methodology covers the WHAT; this
> layer covers the WHEN-IT-ACTUALLY-WORKS and the FAILURE-MODES.

### 7-Question Gate at scale

The 7Q gate is the single highest-ROI artifact in this skill. Phase 2D's hardened-lab campaign verified it kills four distinct false-positive shapes:

1. **URL echo dressed as reflection** — payload appears in the response body because the response IS the URL. Q1 (is this a real HTTP request that does something on the server) kills it.
2. **Word collision dressed as marker hit** — the canary string `XSS-test` matched a CSS class name, not your injection. Marker Discipline + Q1 kill it.
3. **Server policy mistaken for state oracle** — `download.aspx?file=foo.config` always returns "blocked" regardless of whether the file exists. Q6 (impact beyond technically possible) kills it: there's no oracle, just a deny-list.
4. **200 OK without leak** — status code differs from baseline 403; body is byte-identical. Body-Diff Rule + Q6 kill it.

Without the 7Q gate, expect 10-20% submission validity loss across an engagement. With it, retraction rates trend to single digits.

### Pre-Severity Gate before reporting Critical

A authorized SharePoint engagement nearly submitted a Critical when the chain didn't actually complete end-to-end — a primitive that read auth state was conflated with a primitive that mutated it. The Pre-Severity Gate (run all 7 questions specifically against the **Critical claim**, not the generic "is this a bug" claim) would have caught it.

Process: write your draft Critical title. Take each of the 7 questions and answer them with the Critical claim substituted for "the bug." If Q6 (impact beyond technically possible) returns "I have a primitive that should let me do X, but I haven't demonstrated X end-to-end on a test account," downgrade. Critical means impact-demonstrated, not impact-inferable.

### Retraction discipline

If a finding stops reproducing 24h after submission — retract preemptively. Two reasons:

1. **Triagers retract for you with downgraded scoring.** A self-retraction reads "the researcher validates their own work." A triager-retraction reads "the researcher submitted noise."
2. **Validation rate is platform-tracked.** Self-retractions don't hit the same metric as triager-closed-as-N/A. Your reputation signal stays cleaner.

The retraction template in the RETRACTION DISCIPLINE section above is the canonical format. Don't silently delete — append a retraction appendix to the engagement report instead.

### When the 7Q feels obstructive

The friction is the gate working. The half of findings that get killed by the 7Q are the half that would have come back as Informative or N/A. Take the friction. Your average payout per submission goes up when low-confidence findings stop diluting the funnel.

The exception: if the 7Q kills a finding but you still believe it, the answer is **gather more evidence**, not **bypass the gate**. The gate is a "do you have proof" check. Get proof, then re-run the gate.

### Validation discipline rules cross-link

The 7 questions are the umbrella; the discipline rules from `bb-methodology` are the implementation:

| 7Q Question | Discipline Rule (bb-methodology) |
|---|---|
| Q1 (real HTTP request that does something) | Reproducibility Gate |
| Q2 (impact beyond informational) | Pre-Severity Gate |
| Q3 (server-side state change or data leak) | Server-Policy-vs-State |
| Q4 (cross-tenant / cross-user demonstrated) | OOB Gate (for blind class), Marker Discipline (for reflective class) |
| Q5 (not already known / dup) | disclosed-reports/ index + HackerOne hacktivity check |
| Q6 (impact beyond technically possible) | OOB Gate + Body-Diff Rule + Statistical-Sample Rule |
| Q7 (in scope per program rules) | scope.md lookup (engagement scaffold) |

When a question is hard to answer "yes" to, the cross-linked rule tells you which artifact to produce to make the answer yes. Q6 is the one most engagements stumble on; that's why three discipline rules back it.

