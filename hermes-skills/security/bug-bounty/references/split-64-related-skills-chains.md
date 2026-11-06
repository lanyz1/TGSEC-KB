## Related Skills & Chains

- **`bb-methodology`** — When a hunting session starts and the user is "lost about what to do next." Workflow primitive: this skill is the orchestrator; `bb-methodology` is the 5-phase workflow it routes to. Load `bb-methodology` FIRST, then this skill names the topic-matched hunt-* skills.
- **`hunt-dispatch`** — When PART 0 mode (red team / WAPT) has been confirmed. Workflow primitive: this skill's "what should I do" routing hands off to `hunt-dispatch` for the platform fingerprint + skill-set load.
- **`web2-recon`** + **`offensive-osint`** — When Phase 1 (recon) starts. Workflow primitive: this skill's "Standard Recon Pipeline" section delegates the live execution to `web2-recon` and the operational arsenal (probes / wordlists / regexes) to `offensive-osint`.
- **`triage-validation`** + **`report-writing`** — When a finding completes Phase 4. Workflow primitive: this skill routes to `triage-validation` (7Q gate) → only if all 7 pass, hand off to `report-writing` for the platform-specific body.

---

