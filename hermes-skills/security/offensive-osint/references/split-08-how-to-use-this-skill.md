## How to use this skill

This skill is a **lean operational index**. Most concrete data (wordlists, regexes, dorks, endpoint catalogs, severity examples) lives in the `references/` subfolder, organized by topic.

**Workflow when this skill triggers:**

1. Read this SKILL.md to anchor on principles (§0-5), scoring rubrics (§20-21), attack-path templates (§39), and the references index below.
2. For task-specific data, **read only the reference file(s) you need** — do NOT pull all 15. Each reference is self-contained.
3. Use the `bug-bounty` skill for the local toolkit at `~/security-research/bug-bounty-resources/` and `osint-methodology` for the planning framework.

**Loading rules of thumb:**
- Single-class question (e.g., "what's the regex for AWS keys?") → load `secret-patterns.md` only.
- Multi-class engagement (e.g., "do an external recon on target.com") → load `probes-and-wordlists.md` first, then add others as the engagement narrows.
- Severity / triage question → load `severity-matrix.md`.

---

