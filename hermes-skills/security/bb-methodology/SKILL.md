---
name: bb-methodology
description: Use at the START of any bug bounty hunting session, when switching targets, or when feeling lost about what to do next. Master orchestrator that combines the 5-phase non-linear hunting workflow with the critical thinking framework (developer psychology, anomaly detection, What-If experiments). Routes to all other skills based on current hunting phase. Also use when asking "what should I do next" or "where am I in the process."
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [bug-bounty, methodology, recon, redteam]
---

# Bug Bounty Methodology: Workflow + Mindset

Master orchestrator for hunting sessions. Combines the 5-phase non-linear workflow with the critical thinking framework that separates top 1% hunters from the rest.

---

## PART 0: MODE CONFIRMATION (Before Anything Else)

**Confirm the engagement type before deciding what counts as a finding.** The same target produces a different report shape depending on which mode applies. Getting this wrong is the single biggest waste of time in this workflow — answer it explicitly before Phase 0.

| Engagement type | What counts as a finding | What gets rejected |
|---|---|---|
| **Bug bounty** (H1 / Bugcrowd / Intigriti / private VDP) | Impact-demonstrated bugs ONLY. Full chain to attacker-attainable harm. | Hygiene (EoL software alone, permissive CSP alone, stack traces, info disclosure without concrete impact, "best practice" violations) |
| **Red team** (external client engagement) | Hygiene findings + recon + IoCs + defensive-state observations are ALL deliverables | Nothing — even "no finding here" is reportable as a positive defensive observation |
| **Pentest** (signed SoW / WAPT) | Depends on SoW. Read scope explicitly. Usually accepts hygiene + impact + recon | Out-of-scope assets, unsigned testing |
| **Internal audit** | Compliance-mapped findings (PCI / ISO / NIST / DPDPA / GDPR) | Findings without a control-mapping |

**Hard rule:** Before Phase 0 runs, write the engagement type as the first line in your hunt notes. If you can't answer it from the user's instruction, ASK once. Don't assume — the mistake costs both you and the triager.

**Lesson from an authorized engagement:** First-pass on this target produced 5 hygiene findings (SP2013 EoL, permissive CSP, stack traces) shipped in red-team format. The engagement was bug-bounty. Findings would have been N/A'd as "informational, no impact demonstrated." After the corrected pass with hygiene-as-context-not-finding, the same target yielded 11 impact-demonstrated bugs including 3 Critical.

---

## PART 1: MINDSET (How to Think)

### Core Principle

Hunting is not "find a bug" -- it is "prove an attack scenario." Think like an attacker with a specific goal, not a scanner looking for patterns.

### Daily Discipline: Define, Select, Execute

Before touching any command:

1. **Define**: "Today I target [feature/domain] to achieve [CIA impact]"
2. **Select**: Choose 1-2 vuln classes (IDOR, Race Condition, etc.)
3. **Execute**: Focus ONLY on selected techniques. No wandering.

### 5 Ultimate Goals (Pick One Per Session)

1. **Confidentiality** -- steal data the attacker shouldn't see
2. **Integrity** -- modify data the attacker shouldn't change
3. **Availability** -- disrupt service (app-level DoS only)
4. **Account Takeover** -- control another user's account
5. **RCE** -- execute commands on the server

### 4 Thinking Domains

#### 1. Critical Thinking (deep analysis)

**Question trust boundaries:**
- Frontend control disabled? Send request directly via proxy
- `user_role=user` cookie? Change to `admin`
- `price=1000` in POST? Change to `1`
- `<script>` blocked? Try `<img onerror=...>`

**Reverse-engineer developer psychology:**
- Feature A has auth checks -> Similar feature B (newly added) probably doesn't
- Complex flows (coupon + points + refund) -> Edge cases have bugs
- `/api/v2/user` exists -> Does `/api/v1/user` still work with weaker auth?

**What-If experiments:**
- Skip checkout -> hit `/checkout/success` directly
- Skip 2FA -> navigate to `/dashboard`
- Send coupon request 10x simultaneously -> Race condition?
- Replace `guid=f8a2...` with `id=100` on sibling endpoint -> IDOR?

#### 2. Multi-Perspective (multiple angles)

| Perspective | What to check |
|------------|---------------|
| Horizontal (same role) | User A's token + User B's ID -> IDOR |
| Vertical (different role) | Regular user -> `/admin/deleteUser` |
| Data flow (proxy view) | Hidden params in JSON: `debug=false`, `discount_rate` |
| Time/State | Race conditions, post-delete session reuse |
| Client environment | Mobile UA -> legacy API with weaker auth |
| Business impact | "What's the $ damage if this breaks?" |

#### 3. Tactical Thinking (pattern detection)

- **Naming anomaly**: `userId` everywhere but suddenly `user_id` -> different dev, weaker security
- **Error diff**: Same 403 but different JSON structure -> different backend systems
- **Environment diff**: Prod vs Dev/Staging -> debug headers, CSP disabled
- **Version diff**: JS file before/after update -> new endpoints, removed params
- **Supply chain**: Check framework/library versions for known CVEs
- **Third-party integration**: Stripe/Auth0/Intercom -> webhook signature missing?

#### 4. Strategic Thinking (big picture)

- **Asymmetry**: Defender must patch ALL holes. You only need ONE.
- **Intuition engineering**: Log why something "feels wrong." Verify later. Update mental DB.
- **Unknown management**: Can't understand something? Add to "investigate later" list. Just-in-Time Learning.

### Amateur vs Pro: 7-Phase Comparison

| Phase | Amateur | Pro |
|-------|---------|-----|
| Recon | Main domain only | Shadow IT, dev environments, all assets |
| Discovery | Look for errors | Look for design contradictions, business logic flaws |
| Exploit | Give up when blocked | Build filter-bypass payloads |
| Escalation | Report the phenomenon only | Chain to real harm (session steal, ATO) |
| Feasibility | Include unrealistic conditions | Minimize attack prerequisites |
| Reporting | State facts only | Quantify business risk |
| Retest | Check if old PoC fails | Analyze fix method, find incomplete patches |

### Two Approach Routes

- **Route A (Feature-based)**: "This feature is complex" -> deep-dive its input handling -> find vuln
- **Route B (Vuln-based)**: "I want IDOR" -> find endpoints with sequential IDs -> test access control

### Anti-Patterns (Stop Doing These)

- **Program hopping**: Stick with one target minimum 2 weeks / 30 hours
- **Tool-only hunting**: Automation finds duplicates. Manual testing finds unique bugs.
- **Rabbit hole**: Max 45 min per parameter. Set a timer. If stuck, sleep on it.
- **No goal**: "Just looking around" = wasted time. Always Define first.

---

## Pitfalls

- **Mode confusion** — treating a bug-bounty engagement as a red-team exercise wastes time on hygiene findings that get N/A'd. Confirm the engagement type (PART 0) before any recon.
- **Non-unique markers** — using `test`, `marker`, or `javascript` as test strings triggers false positives. Always use 8+ char random alphanumeric markers and verify against baseline.
- **Status-code-only bypass claims** — 200 OK with byte-identical body is NOT a bypass. Always diff response bodies before claiming success.
- **Single-sample timing conclusions** — one 2× outlier is network jitter, not signal. Minimum n=10 interleaved trials, 2σ threshold for timing-based claims.
- **Shell loops for >5 iterations** — zsh array expansion can silently produce zero iterations. Use Python with try/except for any loop iterating a list, file, or computed range.
- **Linear phase assumption** — the 5-phase flow is non-linear. New APIs discovered during Phase 3 require returning to Phase 2 mapping. WAF blocking in Phase 4 requires origin-IP recon from Phase 1.
- **20-minute rule violations** — continuing past 20 minutes without progress on a single endpoint burns session time. Rotate: endpoint → subdomain → vuln class → target.
- **Ignoring the A→B signal** — finding one bug means the same developer made more mistakes nearby. Always spend 20 minutes hunting siblings after a confirmed finding.
- **Report-first, validate-later** — writing the report before confirming the bug still reproduces wastes hours on retracted findings. Always re-test minutes before submission.
- **Premature pushback** — when the user says "find more," they are usually correct. Exhaust 3 additional hunt-* skill checklists before claiming coverage is complete.
- **45-minute sunk cost on dead candidates** — if a finding won't reproduce on a second account after 4+ hours, document the retraction and move on. Don't sink more time into making it work.

---


## 全文导航（已拆分）

主卡保留前 3 节；其余 7 节在 `references/full.md`：

- PART 2: WORKFLOW (What to Do)
- PART 3: NAVIGATION & TIMING
- PART 4: METHODOLOGY DISCIPLINE (False-Positive Prevention)
- Verification
- 2026 Field Additions (from The-XSS-Rat guide)
- Related Skills & Chains
- Operator Notes

加载：`skill_view(name='bb-methodology', file_path='references/full.md')`

> 全文较大（26506 字符），已分 3 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
