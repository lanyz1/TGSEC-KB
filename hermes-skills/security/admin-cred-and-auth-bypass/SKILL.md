---
name: admin-cred-and-auth-bypass
description: "admin管理后台打不进去时用:凭据产地14类+登录绕过13族,非弱口令爆破。"
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [pentest, admin-panel, credential-acquisition, auth-bypass, default-credentials, jwt, actuator, cwe-306, cwe-862, surveyengine-absorbed]
    related_skills: [admin-console-discovery, sensitive-dir-credential-hunt, heapdump-credential-hunter, jwt-attacks, frontend-auth-bypass, reset-token-disclosure-ato, api-authz-idor-testing, middleware-unauth-family, cn-admin-framework-pentest, spring-boot-api-pentest, admin-backdoor-persistence, credential-stuffing, vcs-repo-exposure, vendor-doc-default-credentials, server-getshell-playbook]
---

# 管理端凭据获取与登录绕过家族

<!-- split-index -->

## Section index

- [When to Use](references/split-01-when-to-use.md)
- [0. 心法(先立规矩,再谈技术)](references/split-02-0.md)
- [1. 攻击面 × 漏洞形态 总矩阵](references/split-03-1.md)
- [2. 凭据产地 14 类](references/split-04-2-14.md)
- [3. 登录绕过 13 族](references/split-05-3-13.md)
- [4. 国内后台框架专项(默认值 = 第一顺位)](references/split-06-4.md)
- [5. 执行决策树](references/split-07-5.md)
- [6. 工具](references/split-08-6.md)
- [7. Pitfalls](references/split-09-7-pitfalls.md)
- [8. Verification](references/split-10-8-verification.md)
- [支持文件](references/split-11-section.md)
