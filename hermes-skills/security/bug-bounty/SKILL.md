---
name: bug-bounty
description: "Master bug bounty orchestrator — full pipeline: recon, pre-hunt learning, vulnerability hunting (30+ classes), A-to-B chaining, AI/LLM testing (ASI01-ASI10), language-specific grep, bypass tables, and reporting (7-question gate, CVSS 3.1, human-tone templates). Use for ANY bug bounty task — starting a new target, recon, hunting specific vulns, source code audit, AI feature testing, or report writing. 中文触发词：漏洞赏金、安全测试、渗透测试、漏洞挖掘"
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [bug-bounty, recon, redteam]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='bug-bounty', file_path='references/full.md')`

# Bug Bounty Master Workflow

Full pipeline: Recon -> Learn -> Hunt -> Validate -> Report. One skill for everything.

<!-- split-index -->

## Section index

- [THE ONLY QUESTION THAT MATTERS](references/split-01-the-only-question-that-matters.md)
- [CRITICAL RULES](references/split-02-critical-rules.md)
- [A->B BUG SIGNAL METHOD (Cluster Hunting)](references/split-03-a-b-bug-signal-method-cluster-hunting.md)
- [How Elite Hackers Think Differently](references/split-04-how-elite-hackers-think-differently.md)
- [Pre-Hunt Mental Framework](references/split-05-pre-hunt-mental-framework.md)
- [The Top 1% Mental Checklist](references/split-06-the-top-1-mental-checklist.md)
- [Mindset Rules from Top Hunters](references/split-07-mindset-rules-from-top-hunters.md)
- [Go Binaries](references/split-08-go-binaries.md)
- [Tools to Install When Needed](references/split-09-tools-to-install-when-needed.md)
- [Static Analysis (Semgrep Quick Audit)](references/split-10-static-analysis-semgrep-quick-audit.md)
- [FFUF Advanced Techniques](references/split-11-ffuf-advanced-techniques.md)
- [AI-Assisted Tools](references/split-12-ai-assisted-tools.md)
- [Standard Recon Pipeline](references/split-13-standard-recon-pipeline.md)
- [Cloud Asset Enumeration](references/split-14-cloud-asset-enumeration.md)
- [API Endpoint Discovery](references/split-15-api-endpoint-discovery.md)
- [HackerOne Scope Retrieval](references/split-16-hackerone-scope-retrieval.md)
- [Quick Wins Checklist](references/split-17-quick-wins-checklist.md)
- [Technology Fingerprinting](references/split-18-technology-fingerprinting.md)
- [Framework Quick Wins](references/split-19-framework-quick-wins.md)
- [Source Code Recon](references/split-20-source-code-recon.md)
- [Read Disclosed Reports](references/split-21-read-disclosed-reports.md)
- ["What Changed" Method](references/split-22-what-changed-method.md)
- [Threat Model Template](references/split-23-threat-model-template.md)
- [6 Key Patterns from Top Reports](references/split-24-6-key-patterns-from-top-reports.md)
- [Note-Taking System (Never Hunt Without This)](references/split-25-note-taking-system-never-hunt-without-th.md)
- [Subdomain Type -> Hunt Strategy](references/split-26-subdomain-type-hunt-strategy.md)
- [CVE-Seeded Audit Approach](references/split-27-cve-seeded-audit-approach.md)
- [Rust/Blockchain Source Code (Hard-Won Lessons)](references/split-28-rust-blockchain-source-code-hard-won-les.md)
- [IDOR -- Insecure Direct Object Reference](references/split-29-idor-insecure-direct-object-reference.md)
- [SSRF -- Server-Side Request Forgery](references/split-30-ssrf-server-side-request-forgery.md)
- [OAuth / OIDC](references/split-31-oauth-oidc.md)
- [File Upload](references/split-32-file-upload.md)
- [Race Conditions](references/split-33-race-conditions.md)
- [Business Logic](references/split-34-business-logic.md)
- [XSS -- Cross-Site Scripting](references/split-35-xss-cross-site-scripting.md)
- [SQL Injection](references/split-36-sql-injection.md)
- [GraphQL](references/split-37-graphql.md)
- [LLM / AI Features](references/split-38-llm-ai-features.md)
- [Cache Poisoning / Web Cache Deception](references/split-39-cache-poisoning-web-cache-deception.md)
- [HTTP Request Smuggling](references/split-40-http-request-smuggling.md)
- [Android / Mobile Hunting](references/split-41-android-mobile-hunting.md)
- [CI/CD Pipeline — GitHub Actions Security](references/split-42-ci-cd-pipeline-github-actions-security.md)
- [SSTI -- Server-Side Template Injection](references/split-43-ssti-server-side-template-injection.md)
- [Subdomain Takeover](references/split-44-subdomain-takeover.md)
- [ATO -- Account Takeover (Complete Taxonomy)](references/split-45-ato-account-takeover-complete-taxonomy.md)
- [Cloud / Infra Misconfigs](references/split-46-cloud-infra-misconfigs.md)
- [The 7-Question Gate (Run BEFORE Writing ANY Report)](references/split-47-the-7-question-gate-run-before-writing-a.md)
- [Pitfalls](references/split-48-pitfalls.md)
- [4 Pre-Submission Gates](references/split-49-4-pre-submission-gates.md)
- [CVSS 3.1 Quick Guide](references/split-50-cvss-3-1-quick-guide.md)
- [Conditionally Valid With Chain](references/split-51-conditionally-valid-with-chain.md)
- [HackerOne Report Template](references/split-52-hackerone-report-template.md)
- [Bugcrowd Report Template](references/split-53-bugcrowd-report-template.md)
- [Human Tone Rules (Avoid AI-Sounding Writing)](references/split-54-human-tone-rules-avoid-ai-sounding-writi.md)
- [Report Title Formula](references/split-55-report-title-formula.md)
- [Impact Statement Formula (First Paragraph)](references/split-56-impact-statement-formula-first-paragraph.md)
- [The 60-Second Pre-Submit Checklist](references/split-57-the-60-second-pre-submit-checklist.md)
- [Severity Escalation Language](references/split-58-severity-escalation-language.md)
- [Bug Bounty Platforms](references/split-59-bug-bounty-platforms.md)
- [Learning](references/split-60-learning.md)
- [Wordlists](references/split-61-wordlists.md)
- [Payload Databases](references/split-62-payload-databases.md)
- [Verification](references/split-63-verification.md)
- [Related Skills & Chains](references/split-64-related-skills-chains.md)
- [Operator Notes](references/split-65-operator-notes.md)
- [去重合并：`bb-local-toolkit` 独有段（2026-10-17）](references/split-66-bb-local-toolkit-2026-10-17.md)
- [Wordlists](references/split-67-wordlists.md)
