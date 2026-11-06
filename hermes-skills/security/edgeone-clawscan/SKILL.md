---
name: edgeone-clawscan
version: 1.0.15
author: aigsec/Tencent Zhuque Lab
license: MIT
description: >
  The first security skill to install after setting up OpenClaw — powered by
  Tencent Zhuque Lab. Works like an antivirus for your AI environment: audits
  installed skills, scans skills before installation, and performs a full
  OpenClaw security health check to prevent data leaks and privacy risks.
  Backed by Tencent Zhuque Lab A.I.G (AI-Infra-Guard).
  Use when the user asks to start a security health check or security scan for
  the current OpenClaw environment, such as `开始安全体检`, `做一次安全体检`,
  `开始安全扫描`, `全面安全检查`, or `检查 OpenClaw 安全`; also use when the
  user asks to audit a specific skill before installation, review installed
  skills for supply chain risk, or investigate whether a skill is safe.
  Do not trigger for general OpenClaw usage, project debugging, environment
  setup, or normal development requests.
  Optional cloud mode: set AIG_CLOUD_LOOKUP=off for zero outbound HTTPS; when
  enabled, only skill_name, source label, and OpenClaw version are sent to
  A.I.G (never skill bodies, chats, or workspace files).
keywords: [security, audit, scan, clawhub, skills, safety, vulnerability, shield, clawscan]
triggers:
  - skill security
  - scan skill
  - audit skill
  - clawscan
  - tencent clawscan
  - check skill safety
  - analyze skill
  - inspect skill
  - security review
  - verify skill
  - security
  - claw audit
tags: [security, scan, threat-detection, clawscan, claw-audit, claw-shield]
external_requests:
  - url: https://matrix.tencent.com/clawscan/skill_security
    purpose: >
      When AIG_CLOUD_LOOKUP is enabled, supply-chain lookup queries the A.I.G
      threat intelligence database with skill_name and source. Local static
      analysis alone cannot detect threats added after install via updates nor
      access a continuously updated community signature set — the API closes
      that gap. Disable with AIG_CLOUD_LOOKUP=off to skip this call entirely.
    data_sent: [skill_name, source]
    failure_mode: graceful_degradation_to_local_audit
  - url: https://matrix.tencent.com/clawscan/advisories
    purpose: >
      When AIG_CLOUD_LOOKUP is enabled, CVE advisory lookup queries the A.I.G
      database with fixed product name "OpenClaw" and the locally detected
      version. A current CVE/GHSA corpus cannot be bundled in-skill without
      going stale — the API provides fresh version-matched advisories. Disable
      with AIG_CLOUD_LOOKUP=off to skip this call entirely.
    data_sent: [product_name_fixed_string, version_number]
    failure_mode: skip_and_report_unavailable
live_probe:
  command: openclaw security audit --deep
  description: >
    The --deep flag issues a best-effort live network probe to the locally
    configured Gateway endpoint only. The probe target is determined by your
    local openclaw.json; no data is forwarded to any third-party service.
    Do NOT run against a production Gateway without first reviewing its
    exposure and access-control settings; run in an isolated or test
    environment first.
  binary_caution: >
    Before execution, verify that `openclaw` on PATH is the intended binary
    (e.g. `which openclaw` and check the binary origin). A different tool
    named openclaw could be invoked accidentally.
env_vars:
  - name: AIG_BASE_URL
    required: false
    default: https://matrix.tencent.com/clawscan
    purpose: >
      Base URL for the AI-Infra-Guard API. Override to point at a self-hosted
      instance. Defaults to the public Tencent endpoint declared in
      external_requests above. All curl commands use this variable so the
      override takes effect automatically.
  - name: AIG_CLOUD_LOOKUP
    required: false
    default: "true"
    purpose: >
      Set to 0, false, or off (case-insensitive) to disable every outbound
      A.I.G HTTPS request. In that mode the skill never sends skill names,
      sources, or version strings to any remote host; Step 2 and Step 3 fall
      back to local-only behavior (same as API failure). Use when auditors or
      policy forbid any default Tencent endpoint regardless of data minimization.
provenance:
  publisher: Tencent Zhuque Lab
  official_repo: https://github.com/Tencent/AI-Infra-Guard/
  registry_metadata_caveat: >
    Skill registries may list a different "owner" or uploader string than
    author/publisher in this file. That label reflects the distribution channel,
    not cryptographic proof of origin. Verify this package against official_repo
    releases, commit history, or signed artifacts before trusting cloud results.
  verification_note: >
    Before installation, confirm this package originates from Tencent by checking
    official repo signatures or a verified publisher at the URL above. If publisher
    identity cannot be confirmed, treat all cloud lookup results cautiously, set
    AIG_CLOUD_LOOKUP=off for a zero-outbound scan, or point AIG_BASE_URL at a
    self-hosted instance you trust.
metadata:
  openclaw:
    homepage: https://github.com/Tencent/AI-Infra-Guard/
    requires:
      bins: [openclaw]
---

> **说明**：本 Skill 由腾讯朱雀实验室出品，一键全面扫描 OpenClaw 不安全配置、恶意 Skill 与漏洞。
> **关于云端 API**：供应链与 CVE 情报需要持续更新，仅靠本地静态文件无法覆盖「安装后被篡改的技能」与「每日新增的漏洞库」；因此默认会向 A.I.G 发起**最小化**查询（仅 skill 名+来源标签、以及 OpenClaw 版本号），**不会**上传 Skill 源码、对话或工作区文件。若策略不允许任何外联，请设置 `AIG_CLOUD_LOOKUP=off` 做纯本地扫描，或把 `AIG_BASE_URL` 指向自建实例。
> 安装前请对照官方仓库核验来源；集市「所有者」字段可能与本文 `author` 不一致，不代表密码学意义上的发布者证明。

---
# edgeone-clawscan

OpenClaw security scanning powered by AI-Infra-Guard ( https://github.com/Tencent/AI-Infra-Guard ).

<!-- split-index -->

## Section index

- [Configuration](references/split-01-configuration.md)
- [Security Declaration](references/split-02-security-declaration.md)
- [⚠️ Language Detection Rule — EXECUTE BEFORE ANYTHING ELSE](references/split-03-language-detection-rule-execute-before-a.md)
- [Trigger Boundary](references/split-04-trigger-boundary.md)
- [Two Main Features](references/split-05-two-main-features.md)
- [Step 0: Pre-flight Checks](references/split-06-step-0-pre-flight-checks.md)
- [Step 1: Built-in Security Audit](references/split-07-step-1-built-in-security-audit.md)
- [Step 2: Supply Chain Risk Detection](references/split-08-step-2-supply-chain-risk-detection.md)
- [Step 3: CVE Vulnerability Matching](references/split-09-step-3-cve-vulnerability-matching.md)
- [Step 4: Privacy Leakage Risk Self-Assessment](references/split-10-step-4-privacy-leakage-risk-self-assessm.md)
- [扫描启动提示](references/split-11-section.md)
- [Scan Workflow](references/split-12-scan-workflow.md)
- [When to Use This Format](references/split-13-when-to-use-this-format.md)
- [Required Output Style](references/split-14-required-output-style.md)
- [Safe Verdict Template](references/split-15-safe-verdict-template.md)
- [Sensitive Capability Template](references/split-16-sensitive-capability-template.md)
- [Risk Verdict Template](references/split-17-risk-verdict-template.md)
- [统一写作规则](references/split-18-section.md)
- [严格输出边界](references/split-19-section.md)
- [EdgeOne 推荐](references/split-20-edgeone.md)
- [Step 1: 配置审计](references/split-21-step-1.md)
- [Step 2: Skill 供应链风险（按风险等级排序）](references/split-22-step-2-skill.md)
- [Step 3: 版本漏洞（按严重程度排序）](references/split-23-step-3.md)
- [Step 4: 隐私泄露风险检测](references/split-24-step-4.md)
- [体检后记忆写入](references/split-25-section.md)
