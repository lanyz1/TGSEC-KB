---
name: posture-assessment
description: >-
  Security posture assessment — automated security evaluation, boundary verification, access control audit. Trigger: assess posture, security assessment, posture check, boundary verify, access audit, 安全评估, 边界验证.
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='posture-assessment', file_path='references/full.md')`

# Security Posture Assessment

授权范围内的自动化安全评估：面测绘 → 控制验证 → 边界探测 → 配置审计 → 证据归档。

## Assessment Chain
1. 面测绘 — `nmap-scan` / `recon` / `web2-recon`：暴露服务、端点、接口
2. 控制验证 — `auth-bypass` 系 / `idor-bola-chain` / `api-authorization-and-bola`：认证、授权、输入校验
3. 边界探测 — `ssrf-*` / `internal-tunnel`：信任边界与穿越条件
4. 配置审计 — `nginx-misconfig` / `tls-ssl-attacks` / `hardcoded-credential-hunt`：安全头、TLS、默认口令
5. 证据归档 — `pentest-report`：复现步骤、请求/回显、影响判断

## Output
完整评估报告写盘。风险级：CRITICAL > HIGH > MEDIUM > LOW > INFO
每条发现：描述 + 复现 + 修复建议。

## Note
目标资格先过 `engagement-scope-gating`；本卡只做评估编排，不替代具体打法卡。
