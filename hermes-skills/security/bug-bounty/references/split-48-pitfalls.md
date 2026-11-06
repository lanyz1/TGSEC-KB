## Pitfalls

- **Over-automation without understanding** — running nuclei, ffuf, and dalfox on every subdomain triggers WAF blocks, rate limits, and IP bans. Use `-rate` and `-t` flags. Manual probing finds bugs that automated scanners miss.
- **5-Minute Rule violations** — lingering on a target returning only 401/403/404 wastes time. MOVE ON after 5 minutes of nothing.
- **"Could" is not a bug** — theoretical attacks without demonstrated impact get rejected. Prove it works or drop it. Every finding must show actual harm: stolen funds, leaked PII, account takeover, or code execution.
- **Source maps without secrets** — finding `.map` files is reconnaissance-grade, not a vulnerability. Only report when paired with extracted credentials or API keys.
- **SSRF with DNS-only callback** — DNS pingbacks alone don't prove impact. Need data exfiltration, internal service access, or cloud metadata retrieval.
- **Open redirect alone** — without an OAuth chain or ATO escalation path, this is informational at best. Build the full chain before reporting.
- **Spraying without method** — jumping between XSS, IDOR, SSRF, and cache poisoning in one session guarantees shallow findings. Pick ONE bug class per session and go deep.
- **Report-first, validate-later** — writing the report before confirming the bug still works at time of submission. Always re-test minutes before submitting.
- **One test account testing itself** — IDOR/ATO bugs need two accounts (attacker + victim). Testing with one account against itself proves nothing.
- **Not reading disclosed reports first** — spending hours hunting a class that's out of scope or already hard-mitigated wastes time. Read 3+ disclosed reports before hunting.
- **Scope creep via subdomain enumeration** — verify every subdomain is owned by the target. Third-party services are typically out of scope.
- **New features == unreviewed** — anything launched in the last 30 days has the lowest security maturity and highest bug density.

---

