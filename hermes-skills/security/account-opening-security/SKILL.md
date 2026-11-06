---
name: account-opening-security
description: >-
  开户安全测试全栈技能 — 覆盖金融/证券/银行/支付/加密货币平台的远程开户安全测试，
  包括KYC绕过、身份认证缺陷、活体检测绕过、虚拟摄像头注入、合成身份欺诈、
  证件伪造与OCR绕过、批量注册API滥用、券商开户漏洞、2026最新AI驱动的开户攻击技术。
  当用户需要测试开户流程安全、KYC绕过、身份验证缺陷时使用。
version: 1.0.0
---

# SKILL: 开户安全测试 — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: 此技能覆盖金融/证券/银行/支付/加密货币平台的远程开户安全测试全栈方法。
> 从KYC（身份验证）绕过、活体检测注入、证件伪造、合成身份欺诈到批量注册API滥用，
> 包含2026年最新的AI驱动开户攻击和虚拟摄像头注入攻击技术。
> 与 `business-logic-vulnerabilities`（业务逻辑漏洞）、`mobile-app-security-testing`（移动端安全测试）、
> `authbypass-authentication-flaws`（认证绕过）互补。
> 当测试目标涉及远程开户、KYC身份验证、人脸识别、OCR证件识别流程时，加载此技能。

### Companion files
| 文件 | 何时加载 |
|---|---|
| [CHECKLIST.md](./CHECKLIST.md) | 逐项检查开户流程安全时 |
| [SCENARIOS.md](./SCENARIOS.md) | 需要实战CVE案例和攻击场景时 |

---

<!-- split-index -->

## Section index

- [0. RELATED ROUTING](references/split-01-0-related-routing.md)
- [1. 开户安全攻击面总览](references/split-02-1.md)
- [2. 身份信息认证绕过](references/split-03-2.md)
- [3. 证件OCR识别绕过](references/split-04-3-ocr.md)
- [4. 人脸识别与活体检测绕过](references/split-05-4.md)
- [5. 合成身份欺诈](references/split-06-5.md)
- [6. 移动端开户安全测试](references/split-07-6.md)
- [7. 批量注册与API滥用](references/split-08-7-api.md)
- [8. 视频见证/面签绕过](references/split-09-8.md)
- [9. 风险测评与适当性管理绕过](references/split-10-9.md)
- [10. 2026 EMERGING TECHNIQUES](references/split-11-10-2026-emerging-techniques.md)
- [11. TESTING CHECKLIST](references/split-12-11-testing-checklist.md)
- [12. 生物特征模板注入攻击](references/split-13-12.md)
- [13. 声纹验证绕过](references/split-14-13.md)
- [14. 国内主流KYC SDK逆向分析](references/split-15-14-kyc-sdk.md)
- [15. eKYC与NFC芯片验证绕过](references/split-16-15-ekyc-nfc.md)
- [16. 2026 ADVANCED — 深度攻击链与防御穿越](references/split-17-16-2026-advanced.md)
- [附录A: 证据收集模板](references/split-18-a.md)
- [附录B: 工具速查](references/split-19-b.md)
- [17. 身份信息查询API攻击面](references/split-20-17-api.md)
