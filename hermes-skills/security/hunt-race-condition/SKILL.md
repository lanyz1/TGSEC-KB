---
name: hunt-race-condition
description: Hunting skill for race condition vulnerabilities. Built from 12 public bug bounty reports including modern HTTP/2 single-packet attack cases (James Kettle DEF CON 2023 "Smashing the State Machine"; RyotaK / Flatt Security 10,000-request first-sequence-sync expansion 2024). Covers coupon double-redemption, gift-card double-spend, MFA-OTP-validate race, account-create race, faucet/crypto token double-mint, email-activation race, vote/upvote inflation, password-reset token race, rate-limit bypass via concurrent requests. Use when hunting race conditions, TOCTOU bugs, MFA-bypass-via-timing.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [race-condition, hunt, redteam]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='hunt-race-condition', file_path='references/full.md')`


<!-- split-index -->

## Section index

- [Crown Jewel Targets](references/split-01-crown-jewel-targets.md)
- [Attack Surface Signals](references/split-02-attack-surface-signals.md)
- [Step-by-Step Hunting Methodology](references/split-03-step-by-step-hunting-methodology.md)
- [Payload & Detection Patterns](references/split-04-payload-detection-patterns.md)
- [Common Root Causes](references/split-05-common-root-causes.md)
- [Bypass Techniques](references/split-06-bypass-techniques.md)
- [Gate 0 Validation](references/split-07-gate-0-validation.md)
- [Real Impact Examples](references/split-08-real-impact-examples.md)
- [Disclosed Report Citations (Backfill +9 — 2016-2024)](references/split-09-disclosed-report-citations-backfill-9-20.md)
- [HTTP/2 Single-Packet Attack — Deep Reference](references/split-10-http-2-single-packet-attack-deep-referen.md)
- [Turbo Intruder Full Templates — Complete Python Code](references/split-11-turbo-intruder-full-templates-complete-p.md)
- [Verification](references/split-12-verification.md)
- [Pitfalls](references/split-13-pitfalls.md)
- [Related Skills & Chains](references/split-14-related-skills-chains.md)
