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

