---
name: offensive-osint
description: "Operational arsenal for authorized external red-team and bug-bounty recon. Concrete probes, wordlists, regexes, dorks, curl one-liners for: subdomain enum, GraphQL/Swagger/REST discovery, identity fabric (Entra/Okta/ADFS/Google/SAML/M365 deep — Teams/SharePoint/OneDrive), cloud bucket enum (S3/GCS/Azure), CDN/WAF bypass, origin discovery, vendor fingerprinting (Citrix/F5/Pulse/Fortinet/PaloAlto/Cisco/VMware), CI/CD exposure, 48-pattern secret-scan catalog (AWS/GCP/GitHub/Stripe/Slack/Anthropic/OpenAI/Atlassian/DataDog/npm/PyPI), Postman workspaces, breach correlation (HudsonRock/HIBP/DeHashed/IntelX), TLS/JA3 audit, certificate transparency, JS endpoint extraction, package registry leaks, mobile/APK recon, sat imagery, sector-specific recon (healthcare DICOM, finance SWIFT, ICS/SCADA Modbus/BACnet). Detail content in 15 modular reference files, loaded on demand. Use for any authorized recon: scoping, asset discovery, attack-path mapping, secret triage, severity scoring."
sources: hackerone_public, community, public_research
version: 3.0.0
triggers:
  - external recon
  - external red team
  - red team external
  - attack surface management
  - ASM
  - bug bounty recon
  - bug bounty
  - reconnaissance
  - footprinting
  - asset discovery
  - swagger discovery
  - openapi discovery
  - graphql introspection
  - graphql discovery
  - subdomain enumeration
  - subdomain takeover
  - cloud bucket enumeration
  - bucket enum
  - S3 enum
  - GCS enum
  - Azure blob enum
  - identity fabric
  - SSO discovery
  - IdP fingerprinting
  - tenant fingerprinting
  - okta enum
  - entra enum
  - azure AD enum
  - ADFS enum
  - SAML metadata
  - mobile recon
  - APK analysis
  - mobile attack surface
  - secret scanning
  - secret leak
  - leaked credential
  - github dorking
  - google dorking
  - bing dorking
  - DDG dorking
  - postman workspace
  - stack exchange OSINT
  - breach lookup
  - have I been pwned
  - HudsonRock cavalier
  - infostealer
  - dehashed
  - intelx
  - shodan recon
  - censys recon
  - certificate transparency
  - crt.sh
  - JARM
  - favicon mmh3
  - JS endpoint extraction
  - sourcemap leak
  - copy paste probes
  - curl one-liner
  - email security analysis
  - SPF DMARC DKIM
  - origin discovery
  - CDN bypass
  - WAF bypass
  - vendor product fingerprints
  - Citrix Netscaler
  - F5 BIG-IP
  - Pulse Secure
  - FortiGate
  - PaloAlto GlobalProtect
  - Cisco AnyConnect
  - VMware vCenter
  - cloud native fingerprint
  - Lambda function URL
  - Cloud Run
  - kubernetes exposure
  - kubelet
  - etcd
  - CI CD exposure
  - Jenkins recon
  - GitLab self-hosted
  - GitHub Actions secrets
  - documentation leak
  - Notion public
  - Confluence anonymous
  - Trello board
  - WHOIS RDAP
  - DNS record catalog
  - Wayback CDX
  - LinkedIn enumeration
  - job posting tech stack
  - Slack workspace discovery
  - Discord server discovery
  - npm token leak
  - PyPI token leak
  - Docker Hub leak
  - sat imagery physical recon
  - TLS deep audit
  - JA3 JA4
  - reverse DNS sweep
  - IPv6 enumeration
  - CVE prioritization
  - EPSS scoring
  - CISA KEV
  - vulnerability prioritization
  - tooling install
  - sector specific recon
  - healthcare DICOM
  - finance SWIFT
  - ICS SCADA
  - Modbus
  - BACnet
  - post discovery workflow
  - JWT triage
  - AWS key triage
  - GraphQL field suggestion
  - Anthropic API key
  - OpenAI API key
  - Microsoft 365 deep
  - Teams federation
  - SharePoint enum
  - OneDrive enum
  - hackerone reference
  - h1 hacktivity
  - disclosed reports
  - community bug reports
  - prior disclosures
  - bug bounty reference
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='offensive-osint', file_path='references/full.md')`

# Offensive OSINT — External Red-Team Arsenal

> **v3.0** — Refactored 2026-05-02 from a 4,168-line monolith into a lean SKILL.md (~400 lines) plus 15 modular reference files in `references/`. Detail content loads on demand — Claude reads only the reference files relevant to the current task.

<!-- split-index -->

## Section index

- [0. When to use / When NOT](references/split-01-0-when-to-use-when-not.md)
- [1. Authorization & Legal Posture](references/split-02-1-authorization-legal-posture.md)
- [2. Confidence Levels](references/split-03-2-confidence-levels.md)
- [3. Output Format Conventions](references/split-04-3-output-format-conventions.md)
- [4. Source Hygiene & Citations](references/split-05-4-source-hygiene-citations.md)
- [5. Do NOT](references/split-06-5-do-not.md)
- [6. General OSINT (curated tool refs)](references/split-07-6-general-osint-curated-tool-refs.md)
- [How to use this skill](references/split-08-how-to-use-this-skill.md)
- [References Index](references/split-09-references-index.md)
- [20. Endpoint Interest Score — 0–100 rubric](references/split-10-20-endpoint-interest-score-0-100-rubric.md)
- [21. Mobile App Ownership Confidence — 0–100 rubric](references/split-11-21-mobile-app-ownership-confidence-0-100.md)
- [39. Attack-Path Hint Patterns](references/split-12-39-attack-path-hint-patterns.md)
- [49. Skill Self-Test](references/split-13-49-skill-self-test.md)
- [50. Changelog](references/split-14-50-changelog.md)
- [Related Skills & Chains](references/split-15-related-skills-chains.md)
