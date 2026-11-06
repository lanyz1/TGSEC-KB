---
name: vmware-vcenter-attack
description: VMware vSphere / vCenter Server external attack matrix — version fingerprinting, the high-impact CVE chain (CVE-2021-21972 vRealize unauth file upload, CVE-2021-21985 vSAN plugin RCE, CVE-2022-22954 Workspace ONE SSTI, CVE-2023-20887 Aria RCE, CVE-2024-37085 ESXi AD bypass, CVE-2023-34048 vCenter DCERPC OOB write APT-exploited), default credentials, SSO configuration disclosure, vmdir LDAP enumeration, ESXi Open SLP RCE history. ONLY for vCenter / Workspace ONE / Aria instances exposed to the internet — internal-network vCenter is out of scope per the external-only boundary. Use when recon shows port 443 with vCenter banner, `/ui` redirect, `/websso/SAML2/Metadata`, or VMware product fingerprints.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [vmware, vcenter, attack, redteam]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='vmware-vcenter-attack', file_path='references/full.md')`


<!-- split-index -->

## Section index

- [When to use](references/split-01-when-to-use.md)
- [Step 1 — Version fingerprinting](references/split-02-step-1-version-fingerprinting.md)
- [Step 2 — CVE matrix (external-exploitable, sorted by historical impact)](references/split-03-step-2-cve-matrix-external-exploitable-s.md)
- [Step 3 — CVE-2021-21972 probe (still common on stale appliances)](references/split-04-step-3-cve-2021-21972-probe-still-common.md)
- [Step 4 — CVE-2022-22954 (Workspace ONE SSTI) probe](references/split-05-step-4-cve-2022-22954-workspace-one-ssti.md)
- [Step 5 — Default credentials (frequently still valid on lab/staging vCenters)](references/split-06-step-5-default-credentials-frequently-st.md)
- [Step 6 — SSO / vmdir LDAP enumeration](references/split-07-step-6-sso-vmdir-ldap-enumeration.md)
- [Step 7 — Managed Object Browser (MOB) — frequently leaks data](references/split-08-step-7-managed-object-browser-mob-freque.md)
- [Step 8 — vSphere REST API enumeration (post-cred)](references/split-09-step-8-vsphere-rest-api-enumeration-post.md)
- [Step 9 — Workspace ONE Access specific paths](references/split-10-step-9-workspace-one-access-specific-pat.md)
- [Step 10 — Aria / vRealize specific paths](references/split-11-step-10-aria-vrealize-specific-paths.md)
- [Tooling](references/split-12-tooling.md)
- [Detection patterns (what defenders/SOC will see)](references/split-13-detection-patterns-what-defenders-soc-wi.md)
- [External-only boundary check](references/split-14-external-only-boundary-check.md)
- [Severity scoring guidance (red-team deliverable context)](references/split-15-severity-scoring-guidance-red-team-deliv.md)
- [Anti-patterns](references/split-16-anti-patterns.md)
- [Bridge to neighboring skills](references/split-17-bridge-to-neighboring-skills.md)
- [Verification](references/split-18-verification.md)
- [Pitfalls](references/split-19-pitfalls.md)
- [Related Skills & Chains](references/split-20-related-skills-chains.md)
- [Disclosed CVEs & coordinated-disclosure citations](references/split-21-disclosed-cves-coordinated-disclosure-ci.md)
- [Key meta-references (cross-CVE)](references/split-22-key-meta-references-cross-cve.md)
