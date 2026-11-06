<!-- archived from /root/.hermes/skills/security/privilege-escalation/SKILL.md on 2026-10-21 -->

---
name: privilege-escalation
description: "Privilege escalation encyclopedia — Linux SUID/capabilities/cron, Windows token/service/driver, UAC bypass, SeImpersonate. Trigger: privesc, privilege escalation, root…"
---

> 归档卡：原目录 `/root/.hermes/skills/security/privilege-escalation`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/privilege-escalation/…')`，不要相对 `references/legacy/` 解析。

# Privilege Escalation

## Windows LPE: Microsoft Defender 提权链(Nightmare Eclipse 系列, 2026)
一条持续更新的真机 SYSTEM 提权链(PoC 公开,部分**至今无补丁**):
- 演进: **RoguePlanet**(2026-06 披露,7 月修)→ **ShieldBreak CVE-2026-69414**(2026-09 修)→ **ShieldCrash**(绕过 ShieldBreak 补丁的 0day)
- ShieldCrash 现状: Win10/11/Server **打全 9 月补丁也可**提权到 SYSTEM(当前公开 PoC 为 `arbitrary file read as SYSTEM` 骨架,作者称或升级为完整 SYSTEM 写)
- 系列其余: LegacyHive(Windows 提权)/ BlueHammer / RedSun / YellowKey(BitLocker 0day 访问受保护盘)/ GreenPlasma / MiniPlasma / UnDefend —— 官方仍未全部修
- PoC: https://github.com/MSNightmare/ShieldCrash ;UnDefend https://github.com/Nightmare-Eclipse/UnDefend
- 打法: 目标机跑 Defender 时,Windows 提权面里**优先试这条有公开 PoC 的链**(尤其补丁落后的 Server);即便只拿到 `SYSTEM 读` 也能用于读 SAM/LSA/浏览器凭据
- 来源: https://www.bleepingcomputer.com/news/security/new-microsoft-defender-shieldcrash-zero-day-grants-system-access/

## 基础矩阵(占位,后续按 intel-ingest 增量补全)
Privilege escalation encyclopedia — Linux SUID/capabilities/cron, Windows token/service/driver, UAC bypass, SeImpersonate. Trigger: privesc, privilege escalation, root, system, suid, sudo, uac bypass.
- 自带脚本: scripts/linpeas.py(Linux 枚举)/ scripts/winpeas.py(Windows 枚举)
