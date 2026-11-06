---
name: security-arsenal
description: Security payloads, bypass tables, wordlists, gf pattern names, always-rejected bug list, and conditionally-valid-with-chain table. Use when you need specific payloads for XSS/SSRF/SQLi/XXE/NoSQLi/command injection/SSTI/IDOR/path-traversal/HTTP smuggling/WebSocket/MFA bypass, bypass techniques, or to check if a finding is submittable. Also use when asked about what NOT to submit.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [arsenal, tools, security, redteam]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='security-arsenal', file_path='references/full.md')`

# SECURITY ARSENAL

Payloads, bypass tables, wordlists, and submission rules.

---

<!-- split-index -->

## Section index

- [XSS PAYLOADS](references/split-01-xss-payloads.md)
- [SSRF PAYLOADS](references/split-02-ssrf-payloads.md)
- [SQL INJECTION PAYLOADS](references/split-03-sql-injection-payloads.md)
- [XXE PAYLOADS](references/split-04-xxe-payloads.md)
- [PATH TRAVERSAL PAYLOADS](references/split-05-path-traversal-payloads.md)
- [IDOR / AUTH BYPASS PAYLOADS](references/split-06-idor-auth-bypass-payloads.md)
- [AUTHENTICATION BYPASS PAYLOADS](references/split-07-authentication-bypass-payloads.md)
- [NOSQL INJECTION PAYLOADS (MongoDB)](references/split-08-nosql-injection-payloads-mongodb.md)
- [COMMAND INJECTION PAYLOADS](references/split-09-command-injection-payloads.md)
- [SSTI DETECTION PAYLOADS (All Engines)](references/split-10-ssti-detection-payloads-all-engines.md)
- [HTTP SMUGGLING PAYLOADS](references/split-11-http-smuggling-payloads.md)
- [WEBSOCKET PAYLOADS](references/split-12-websocket-payloads.md)
- [MFA / 2FA BYPASS PAYLOADS](references/split-13-mfa-2fa-bypass-payloads.md)
- [SAML ATTACKS](references/split-14-saml-attacks.md)
- [GF PATTERN NAMES (tomnomnom/gf)](references/split-15-gf-pattern-names-tomnomnom-gf.md)
- [ALWAYS REJECTED — NEVER SUBMIT](references/split-16-always-rejected-never-submit.md)
- [CONDITIONALLY VALID — REQUIRES CHAIN](references/split-17-conditionally-valid-requires-chain.md)
- [WORDLISTS (Installed in ~/wordlists/)](references/split-18-wordlists-installed-in-wordlists.md)
- [Verification](references/split-19-verification.md)
- [Pitfalls](references/split-20-pitfalls.md)
- [Related Skills & Chains](references/split-21-related-skills-chains.md)
- [Operator Notes](references/split-22-operator-notes.md)
