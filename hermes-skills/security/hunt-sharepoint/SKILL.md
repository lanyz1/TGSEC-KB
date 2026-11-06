---
name: hunt-sharepoint
description: Hunt Microsoft SharePoint Server (2013/2016/2019/Subscription Edition) on-prem farms — anonymous endpoint enumeration, version disclosure, legacy SOAP login bypass (Authentication.asmx), ToolShell precondition chain (CVE-2025-53770), SafeControl reflection enumeration via Picker.aspx, NTLM Type-2 AD topology disclosure, custom-branding module discovery, EoL farm permanent-CVE-window exploitation, FormDigest anonymous issuance, file-extension blocklist NOT-an-oracle pattern, custom-zone Forms auth bridging on-prem AD. Use when target has SharePoint headers (SPRequestGuid, X-MS-InvokeApp, X-SharePointHealthScore, MicrosoftSharePointTeamServices) or paths (/_layouts/15/, /_vti_bin/, /_api/, /_catalogs/).
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [sharepoint, hunt, redteam, microsoft]
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='hunt-sharepoint', file_path='references/full.md')`


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
- [Cross-references](references/split-09-cross-references.md)
- [Verification](references/split-10-verification.md)
- [Pitfalls](references/split-11-pitfalls.md)
- [Related Skills & Chains](references/split-12-related-skills-chains.md)
