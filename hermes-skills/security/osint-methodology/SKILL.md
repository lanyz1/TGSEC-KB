---
name: osint-methodology
description: "Comprehensive OSINT methodology for external red-team operations and authorized attack-surface assessments. Covers the 5-stage recon pipeline (seed discovery, asset expansion, enrichment, exposure analysis, reporting), asset-graph discipline with 29 asset types, severity rubric (CRITICAL/HIGH/MEDIUM/LOW/INFO), confidence upgrade workflows, time budgeting, asset-level triage rules, scale-based tactics, identity-fabric mapping (Entra/Okta/ADFS/Google/SAML/M365 Teams+SharePoint+OAuth), API and auth-map methodology, JavaScript deep analysis, mobile attack surface, cloud attack surface, breach×identity correlation, detectability tagging, detection-aware probing (back-off, persona rotation), read-only validator discipline, WAF/CDN bypass + origin discovery, vulnerability prioritization (CVE/EPSS/KEV), phishing infrastructure planning + pretext development, bug bounty submission templates, client deliverable templates with risk translation, threat-actor investigation (incl. RU/CN pivots), cryptocurrency tracing, image/video forensics, chronolocation. Use when planning or executing reconnaissance against authorized targets, mapping an organization's external attack surface, investigating a person/entity, tracing crypto flows, geolocating media, or performing attribution work."
license: MIT
revision_date: 2026-07-25
category: redteam
tags: [osint, methodology, recon, redteam]
version: 2.1
triggers:
  - external recon
  - external red team
  - red team external
  - attack surface management
  - attack surface mapping
  - ASM
  - perimeter recon
  - target reconnaissance
  - bug bounty recon
  - asset discovery
  - footprint
  - attack path
  - identity fabric
  - SSO discovery
  - IdP fingerprinting
  - tenant fingerprinting
  - M365 enumeration
  - Microsoft 365 recon
  - API discovery
  - GraphQL introspection
  - mobile recon
  - APK analysis
  - cloud bucket enumeration
  - bucket enum
  - breach correlation
  - secret leak hunt
  - origin discovery
  - CDN bypass
  - WAF bypass
  - vulnerability prioritization
  - CVE prioritization
  - EPSS
  - CISA KEV
  - phishing infrastructure
  - pretext development
  - bug bounty submission
  - responsible disclosure
  - client report
  - exec summary
  - risk translation
  - confidence upgrade
  - time budget
  - engagement profile
  - asset triage
  - detection-aware probing
  - back-off strategy
  - persona rotation
  - OSINT methodology
  - open source intelligence
  - target profiling
  - data correlation
  - OSINT workflow
  - intelligence collection
  - OSINT campaign
  - recon methodology
  - threat actor investigation
  - attribution
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='osint-methodology', file_path='references/full.md')`

# OSINT Methodology — External Red-Team Edition

<!-- split-index -->

## Section index

- [0. When to use this skill / When NOT](references/split-01-0-when-to-use-this-skill-when-not.md)
- [1. Authorization & Legal Posture](references/split-02-1-authorization-legal-posture.md)
- [2. Confidence Levels](references/split-03-2-confidence-levels.md)
- [3. Output Format Conventions](references/split-04-3-output-format-conventions.md)
- [4. Source Hygiene & Citations](references/split-05-4-source-hygiene-citations.md)
- [5. Do NOT (hard rules)](references/split-06-5-do-not-hard-rules.md)
- [6. OpSec](references/split-07-6-opsec.md)
- [7. External Red-Team Recon Pipeline](references/split-08-7-external-red-team-recon-pipeline.md)
- [8. Asset Graph Discipline](references/split-09-8-asset-graph-discipline.md)
- [9. Findings Rubric & Severity Mapping](references/split-10-9-findings-rubric-severity-mapping.md)
- [10. Bug-Bounty / Red-Team Pivot Modes](references/split-11-10-bug-bounty-red-team-pivot-modes.md)
- [11. Identity Fabric Mapping](references/split-12-11-identity-fabric-mapping.md)
- [12. API & Auth-Map Methodology](references/split-13-12-api-auth-map-methodology.md)
- [13. JavaScript Deep Analysis](references/split-14-13-javascript-deep-analysis.md)
- [14. Mobile Attack Surface](references/split-15-14-mobile-attack-surface.md)
- [15. Cloud Attack Surface](references/split-16-15-cloud-attack-surface.md)
- [16. Cryptocurrency Investigation](references/split-17-16-cryptocurrency-investigation.md)
- [17. Image Analysis](references/split-18-17-image-analysis.md)
- [18. Video Analysis](references/split-19-18-video-analysis.md)
- [19. Chronolocation and Time Analysis](references/split-20-19-chronolocation-and-time-analysis.md)
- [20. Threat Actor Investigation](references/split-21-20-threat-actor-investigation.md)
- [21. People & Social Media Investigation](references/split-22-21-people-social-media-investigation.md)
- [22. Breach × Identity Correlation](references/split-23-22-breach-identity-correlation.md)
- [23. Infrastructure OSINT](references/split-24-23-infrastructure-osint.md)
- [24. Automation & Case Management](references/split-25-24-automation-case-management.md)
- [25. Synthetic Media Verification](references/split-26-25-synthetic-media-verification.md)
- [26. Anti-Patterns & Common Failure Modes](references/split-27-26-anti-patterns-common-failure-modes.md)
- [27. WAF / CDN Bypass & Origin Discovery](references/split-28-27-waf-cdn-bypass-origin-discovery.md)
- [28. Vulnerability Prioritization (CVE / EPSS / KEV)](references/split-29-28-vulnerability-prioritization-cve-epss.md)
- [29. Phishing Infrastructure & Pretext Development](references/split-30-29-phishing-infrastructure-pretext-devel.md)
- [30. Bug Bounty Submission & Responsible Disclosure](references/split-31-30-bug-bounty-submission-responsible-dis.md)
- [31. Client Deliverable Templates](references/split-32-31-client-deliverable-templates.md)
- [32. Skill Self-Test](references/split-33-32-skill-self-test.md)
- [33. Changelog](references/split-34-33-changelog.md)
- [Verification](references/split-35-verification.md)
- [Pitfalls](references/split-36-pitfalls.md)
- [Related Skills & Chains](references/split-37-related-skills-chains.md)
