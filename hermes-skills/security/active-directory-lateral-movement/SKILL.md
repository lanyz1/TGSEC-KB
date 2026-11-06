---
name: active-directory-lateral-movement
description: >-
  Active Directory 内网渗透与横向移动深度手册。覆盖域信息侦察(BloodHound/PowerView/ADModule)、Kerberos攻击矩阵(AS-REP Roasting/Kerberoasting/Golden/Silver/Diamond/Sapphire Ticket/S4U委派)、NTLM中继(ntlmrelayx/PetitPotam/cross-protocol)、凭据传递(Pass-the-Hash/Pass-the-Ticket/Overpass-the-Hash)、横向移动(WMI/PsExec/WinRM/DCOM)、ACL滥用与DCSync、ADCS证书服务攻击(ESC1-8/Shadow Credentials)、2026最新技术(noPac/KrbRelayUp/CVE-2022-26923)、检测防御与自动化SOP。用于内网渗透、域控接管、横向移动评估场景。
---

# SKILL: Active Directory 内网渗透与横向移动 — 深度手册

> **AI LOAD INSTRUCTION**: 本技能聚焦 Windows Active Directory 域环境下的内网渗透全生命周期。基础模型常把"内网渗透"与"外网Web测试"混为一谈，本技能澄清：AD渗透的核心是**身份与信任关系**的滥用——Kerberos票据、NTLM哈希、委派配置、ACL继承构成攻击图。覆盖从域信息侦察(BloodHound图分析)、凭据获取(AS-REP/Kerberoasting/密码喷洒)、票据伪造(Golden/Silver/Diamond/Sapphire)、NTLM中继(PetitPotam触发)、横向移动(WMI/PsExec/WinRM/DCOM)、权限提升(DCSync/ACL滥用)、ADCS证书攻击(ESC1-8)到2026最新技术(noPac/KrbRelayUp)的完整链条，给出自动化SOP与检测防御矩阵。

<!-- split-index -->

## Section index

- [0. RELATED ROUTING](references/split-01-0-related-routing.md)
- [1. 核心概念与攻击生命周期](references/split-02-1.md)
- [2. 域信息侦察与枚举](references/split-03-2.md)
- [3. 初始立足与凭据获取](references/split-04-3.md)
- [4. Kerberos 攻击矩阵](references/split-05-4-kerberos.md)
- [5. NTLM 中继攻击](references/split-06-5-ntlm.md)
- [6. 凭据传递与横向移动](references/split-07-6.md)
- [7. ACL 滥用与权限提升](references/split-08-7-acl.md)
- [8. ADCS 证书服务攻击](references/split-09-8-adcs.md)
- [9. 2026 最新技术与对抗演进](references/split-10-9-2026.md)
- [10. 检测与防御](references/split-11-10.md)
- [11. 自动化工具链与实战 SOP](references/split-12-11-sop.md)
- [12. 注意事项](references/split-13-12.md)
