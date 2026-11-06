---
name: supply-chain-attack-recon
description: External recon for software supply-chain attack surface — package-namespace squatting candidates, dependency-confusion vulnerabilities, GitHub Actions injection openings, container image registry exposure, SBOM mining, internal-package-name leakage, and CI/CD configuration exposure. Reconnaissance and identification ONLY — actual package publishing / typosquat attacks are EXTERNAL-OFFENSIVE and require explicit written sign-off because they can affect the entire npm/PyPI ecosystem. Use when the target has a public GitHub org, when their build artifacts/SBOMs are reachable, when their docker images are on Docker Hub/GHCR, or when you find internal package names in their JS bundles.
sources: alex-birsan-dependency-confusion, supply-chain-research, github-actions-security, cisa-advisories, mandiant-tag, github-security-blog, snyk-research
report_count: 12
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='supply-chain-attack-recon', file_path='references/full.md')`


<!-- split-index -->

## Section index

- [When to use](references/split-01-when-to-use.md)
- [The supply-chain attack surface map](references/split-02-the-supply-chain-attack-surface-map.md)
- [Step 1 — GitHub org discovery](references/split-03-step-1-github-org-discovery.md)
- [Step 2 — Enumerate public repos for sensitive artifacts](references/split-04-step-2-enumerate-public-repos-for-sensit.md)
- [Step 3 — Internal package-name discovery](references/split-05-step-3-internal-package-name-discovery.md)
- [Step 4 — Dependency-confusion vulnerability check](references/split-06-step-4-dependency-confusion-vulnerabilit.md)
- [Step 5 — Typosquat candidates (around external dependencies)](references/split-07-step-5-typosquat-candidates-around-exter.md)
- [Step 6 — GitHub Actions workflow injection scan](references/split-08-step-6-github-actions-workflow-injection.md)
- [Step 7 — Docker / container image registry mining](references/split-09-step-7-docker-container-image-registry-m.md)
- [Step 8 — SBOM / artifact metadata leakage](references/split-10-step-8-sbom-artifact-metadata-leakage.md)
- [Step 9 — Internal registry URL leakage](references/split-11-step-9-internal-registry-url-leakage.md)
- [Step 10 — npm/PyPI organizational presence](references/split-12-step-10-npm-pypi-organizational-presence.md)
- [Step 11 — Frontend and third-party dependency checks](references/split-13-step-11-frontend-and-third-party-depende.md)
- [Tooling](references/split-14-tooling.md)
- [Severity scoring guidance](references/split-15-severity-scoring-guidance.md)
- [Anti-patterns](references/split-16-anti-patterns.md)
- [What constitutes a deliverable finding](references/split-17-what-constitutes-a-deliverable-finding.md)
- [Bridge to neighboring skills](references/split-18-bridge-to-neighboring-skills.md)
- [External-only boundary check](references/split-19-external-only-boundary-check.md)
- [Real-world references](references/split-20-real-world-references.md)
- [Disclosed-case catalogue (citations)](references/split-21-disclosed-case-catalogue-citations.md)
- [Related Skills & Chains](references/split-22-related-skills-chains.md)
