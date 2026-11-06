---
name: bb-local-toolkit
description: "Use for bug-bounty end-to-end: recon, 30+ hunt classes, chaining, reporting."
---


# Bug Bounty Master Workflow

Full pipeline: Recon -> Learn -> Hunt -> Validate -> Report. One skill for everything.

## THE ONLY QUESTION THAT MATTERS

> **"Can an attacker do this RIGHT NOW against a real user who has taken NO unusual actions -- and does it cause real harm (stolen money, leaked PII, account takeover, code execution)?"**
>
> If the answer is NO -- **STOP. Do not write. Do not explore further. Move on.**

### Theoretical Bug = Wasted Time. Kill These Immediately:

| Pattern | Kill Reason |
|---|---|
| "Could theoretically allow..." | Not exploitable = not a bug |
| "An attacker with X, Y, Z conditions could..." | Too many preconditions |
| "Wrong implementation but no practical impact" | Wrong but harmless = not a bug |
| Dead code with a bug in it | Not reachable = not a bug |
| Source maps without secrets | No impact |
| SSRF with DNS-only callback | Need data exfil or internal access |
| Open redirect alone | Need ATO or OAuth chain |
| "Could be used in a chain if..." | Build the chain first, THEN report |

**You must demonstrate actual harm. "Could" is not a bug. Prove it works or drop it.**

---

## CRITICAL RULES

1. **READ FULL SCOPE FIRST** -- verify every asset/domain is owned by the target org
2. **NO THEORETICAL BUGS** -- "Can an attacker steal funds, leak PII, takeover account, or execute code RIGHT NOW?" If no, STOP.
3. **KILL WEAK FINDINGS FAST** -- run the 7-Question Gate BEFORE writing any report
4. **Validate before writing** -- check CHANGELOG, design docs, deployment scripts FIRST
5. **One bug class at a time** -- go deep, don't spray
6. **Verify data isn't already public** -- check web UI in incognito before reporting API "leaks"
7. **5-MINUTE RULE** -- if a target shows nothing after 5 min probing (all 401/403/404), MOVE ON
8. **IMPACT-FIRST HUNTING** -- ask "what's the worst thing if auth was broken?" If nothing valuable, skip target
9. **CREDENTIAL LEAKS need exploitation proof** -- finding keys isn't enough, must PROVE what they access
10. **STOP SHALLOW RECON SPIRALS** -- don't probe 403s, don't grep for analytics keys, don't check staging domains that lead nowhere
11. **BUSINESS IMPACT over vuln class** -- severity depends on CONTEXT, not just vuln type
12. **UNDERSTAND THE TARGET DEEPLY** -- before hunting, learn the app like a real user
13. **DON'T OVER-RELY ON AUTOMATION** -- automated scans hit WAFs, trigger rate limits, find the same bugs everyone else finds
14. **HUNT LESS-SATURATED VULN CLASSES** -- XSS/SSRF/XXE have the most competition. Expand into: cache poisoning, Android/mobile vulns, business logic, race conditions, OAuth/OIDC chains, CI/CD pipeline attacks
15. **ONE-HOUR RULE** -- stuck on one target for an hour with no progress? SWITCH CONTEXT
16. **TWO-EYE APPROACH** -- combine systematic testing (checklist) with anomaly detection (watch for unexpected behavior)
17. **T-SHAPED KNOWLEDGE** -- go DEEP in one area and BROAD across everything else

> **For the full hunting methodology** — 5-phase non-linear workflow, developer psychology framework, session discipline, command-line routing by phase, and Wide/Deep route selection — see **`skills/bb-methodology/SKILL.md`**.

---

## A->B BUG SIGNAL METHOD (Cluster Hunting)

**When you find bug A, systematically hunt for B and C nearby.** This is one of the most powerful methodologies in bug bounty. Single bugs pay. Chains pay 3-10x more.

### Known A->B->C Chains

| Bug A (Signal) | Hunt for Bug B | Escalate to C |
|----------------|---------------|---------------|
| IDOR (read) | PUT/DELETE on same endpoint | Full account data manipulation |
| SSRF (any) | Cloud metadata [REDACTED_IP] | IAM credential exfil -> RCE |
| XSS (stored) | Check if HttpOnly is set on session cookie | Session hijack -> ATO |
| Open redirect | OAuth redirect_uri accepts your domain | Auth code theft -> ATO |
| S3 bucket listing | Enumerate JS bundles | Grep for OAuth client_secret -> OAuth chain |
| Rate limit bypass | OTP brute force | Account takeover |
| GraphQL introspection | Missing field-level auth | Mass PII exfil |
| Debug endpoint | Leaked environment variables | Cloud credential -> infrastructure access |
| CORS reflects origin | Test with credentials: include | Credentialed data theft |
| Host header injection | Password reset poisoning | ATO via reset link |

### Cluster Hunt Protocol (6 Steps)

```
1. CONFIRM A     Verify bug A is real with an HTTP request
2. MAP SIBLINGS  Find all endpoints in the same controller/module/API group
3. TEST SIBLINGS Apply the same bug pattern to every sibling
4. CHAIN         If sibling has different bug class, try combining A + B
5. QUANTIFY      "Affects N users" / "exposes $X value" / "N records"
6. REPORT        One report per chain (not per bug). Chains pay more.
```

### Real Examples

**Coinbase S3->Bundle->Secret->OAuth chain:**
```
A: S3 bucket publicly listable (Low alone)
B: JS bundles contain OAuth client credentials
C: OAuth flow missing PKCE enforcement
Result: Full auth code interception chain
```

**Vienna Chatbot chain:**
```
A: Debug parameter active in production (Info alone)
B: Chatbot renders HTML in response (dangerouslySetInnerHTML)
C: Stored XSS via bot response visible to other users
Result: P2 finding with real impact
```

---

# TOP 1% HACKER MINDSET

## How Elite Hackers Think Differently

**Average hunter**: Runstools, checks checklist, gives up after 30 min.
**Top 1%**: Builds a mental model of the app's internals. Asks "why does this work the way it does?" Not "what does this endpoint do?" but "what business decision led a developer to build it this way, and what shortcut might they have taken?"

## Pre-Hunt Mental Framework

### Step 1: Crown Jewel Thinking
Before touching anything, ask: "If I were the attacker and I could do ONE thing to this app, what causes the most damage?"
- Financial app -> drain funds, transfer to attacker account
- Healthcare -> PII leak, HIPAA violation
- SaaS -> tenant data crossing, admin takeover
- Auth provider -> full SSO chain compromise

### Step 2: Developer Empathy
Think like the developer who built the feature:
- What was the simplest implementation?
- What shortcut would a tired dev take at 2am?
- Where is auth checked -- controller? middleware? DB layer?
- What happens when you call endpoint B without going through endpoint A first?

### Step 3: Trust Boundary Mapping
```
Client -> CDN -> Load Balancer -> App Server -> Database
         ^               ^              ^
    Where does app STOP trusting input?
    Where does it ASSUME input is already validated?
```

### Step 4: Feature Interaction Thinking
- Does this new feature reuse old auth, or does it have its own?
- Does the mobile API share auth logic with the web app?
- Was this feature built by the same team or a third-party?

## The Top 1% Mental Checklist
- [ ] I know the app's core business model
- [ ] I've used the app as a real user for 15+ minutes
- [ ] I know the tech stack (language, framework, auth system, caching)
- [ ] I've read at least 3 disclosed reports for this program
- [ ] I have 2 test accounts ready (attacker + victim)
- [ ] I've defined my primary target: ONE crown jewel I'm hunting for today

## Mindset Rules from Top Hunters

**"Hunt the feature, not the endpoint"** -- Find all endpoints that serve a feature, then test the INTERACTION between them.

**"Authorization inconsistency is your friend"** -- If the app checks auth in 9 places but not the 10th, that's your bug.

**"New == unreviewed"** -- Features launched in the last 30 days have lowest security maturity.

**"Think second-order"** -- Second-order SSRF: URL saved in DB, fetched by cron job. Second-order XSS: stored clean, rendered unsafely in admin panel.

**"Follow the money"** -- Any feature touching payments, billing, credits, refunds is where developers make the most security shortcuts.

**"The API the mobile app uses"** -- Mobile apps often call older/different API versions. Same company, different attack surface, lower maturity.

**"Diffs find bugs"** -- Compare old API docs vs new. Compare mobile API vs web API. Compare what a free user can request vs what a paid user gets in response.

---

# TOOLS


---

## 切片路由（原文 77KB，按行切）

| 片 | 内容 | 行范围 | 取法 |
|---|---|---|---|
| part1 | 工具链/侦察/源码/IDOR/SSRF/OAuth/上传/竞态/逻辑/XSS/SQLi/GraphQL/LLM/缓存/走私/移动/CI-CD | 175-1123 | `skill_view(name="bb-local-toolkit", file_path="references/part1_tools_and_webclasses.md")` |
| part2 | SSTI/子域接管/ATO 全谱/云配置/7 问闸/坑/CVSS/报告模板/提交清单 | 1124-1622 | `skill_view(name="bb-local-toolkit", file_path="references/part2_infra_ato_report.md")` |
