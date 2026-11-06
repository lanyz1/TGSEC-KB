---
name: hunt-auth-bypass
description: Hunting skill for auth bypass vulnerabilities. Built from 12 public bug bounty reports across SAML XSW / parser-differential (GitHub Enterprise CVE-2025-25291/25292), SAML signature stripping (Uber, Rocket.Chat, samlify CVE-2025-47949), SAML domain enforcement bypass via control characters (HackerOne 2024), partner-portal cross-IdP assertion reuse (Slack), WordPress XMLRPC bypassing SSO (Uber), JWT alg-confusion HS256/RS256 (Jitsi), JWT signature-validation skip (Linktree, Newspack), and token-audience confusion (Argo CD CVE-2023-22482). Use when hunting auth bypass — see the Legacy-Protocol Matrix for branded-UI vs legacy-endpoint patterns.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [auth, bypass, hunt, redteam]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='hunt-auth-bypass', file_path='references/full.md')`


<!-- split-index -->

## Section index

- [Crown Jewel Targets](references/split-01-crown-jewel-targets.md)
- [Attack Surface Signals](references/split-02-attack-surface-signals.md)
- [Step-by-Step Hunting Methodology](references/split-03-step-by-step-hunting-methodology.md)
- [Legacy-Protocol Matrix (Probe These First on Any Custom-Branded Login)](references/split-04-legacy-protocol-matrix-probe-these-first.md)
- [Payload & Detection Patterns](references/split-05-payload-detection-patterns.md)
- [Common Root Causes](references/split-06-common-root-causes.md)
- [Bypass Techniques](references/split-07-bypass-techniques.md)
- [Gate 0 Validation](references/split-08-gate-0-validation.md)
- [Real Impact Examples](references/split-09-real-impact-examples.md)
- [Disclosed Report Citations (Backfill +8 — 2016-2025)](references/split-10-disclosed-report-citations-backfill-8-20.md)
- [Duende BFF — Token-Confusion & Session-Fixation (2024-2026 surface)](references/split-11-duende-bff-token-confusion-session-fixat.md)
- [Function-Level Access Control (Broken Authorization)](references/split-12-function-level-access-control-broken-aut.md)
- [Verification](references/split-13-verification.md)
- [Pitfalls](references/split-14-pitfalls.md)
- [Related Skills & Chains](references/split-15-related-skills-chains.md)
