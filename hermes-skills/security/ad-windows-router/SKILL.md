---
name: ad-windows-router
description: >-
  Windows/AD 域渗透与后渗透场景分流路由。已拿到域内 shell 或发现 AD 环境时，
  根据具体场景分流到对应专用 Skill。用户提到 AD、域渗透、BloodHound、AD CS、
  Windows 提权、SMB 横向、Kerberos、持久化 时使用本路由。（含 58 张归档子卡索引）
---

# Windows / AD 域渗透分流（Router）

<!-- MERGED-INDEX:START -->
## 归档子卡（已合并 58 张）

- 索引：`references/index.md`
- 加载：`skill_view(name='ad-windows-router', file_path='references/legacy/<name>.md')`
- 子卡脚本/字典仍在原目录（索引里给了绝对路径），可直接 `read_file` / `terminal`。
- **先按本卡判据决策**；本卡不够时才展开对应子卡，不要一次全读。
<!-- MERGED-INDEX:END -->


**适用时机**：已在授权域内机器上有 shell，或发现 Active Directory 环境。

## 场景 → Skill 速查表

| 场景 | 触发特征 | 走哪张卡 |
|------|----------|----------|
| **域信息枚举** | 首次拿到域内机器 shell | `ad_surface_check.py` + `windows-ad-pentest` |
| **AD 域渗透完整链** | BloodHound / ACL / 域控 | `windows-ad-pentest` |
| **AD CS 证书滥用** | ESC1-13、`certify`、ADCS、证书模板 | `adcs-pentest` |
| **Exchange** | autodiscover、ProxyLogon/ProxyShell、privexchange | `intranet-penetration-testing` + 本卡侦察；先 `ad_surface_check.py` |
| **SCCM / MECM** | SMS_SITE、sccmhunter、NAA、PXE | `intranet-penetration-testing`；NAA/DPAPI 在已授权域内做 |
| **混合身份 / Entra** | AAD、ADFS、云身份、PRT | `windows-ad-pentest`（混合段）+ `identity-federation` |
| **Kerberos 攻击** | Kerberoasting、AS-REP Roasting、Silver/Golden Ticket | `kerberos-attack` |
| **SMB 横向移动** | Pass-the-Hash、WMI、impacket、psexec | `smb-lateral-movement` |
| **Windows 持久化** | 计划任务、服务注册、注册表 Run、DLL 劫持 | `windows-persistence` |
| **内网隧道建立** | 出网受限、需要代理链、SOCKS | `internal-tunnel` |
| **内网扫描** | 横向扫端口/服务 | `internal_scan.py`（`ad_surface_check.py` 附带） |
| **Linux 提权** | 低权 shell → root，SUID/sudo/cron | `linux_lpe_checker.py`（本卡 AD 场景优先） |
| **Windows 提权** | 低权 → SYSTEM，UAC/SeImpersonatePrivilege | `windows_lpe_checker.py` |
| **容器逃逸 → K8s** | 容器内 ServiceAccount / privileged | Playbook `容器逃逸手法.md` + K8s特权Pod手法 |
| **主机应急响应** | 已入侵后门排查、IR | `host_ir_check.py` |
| **C2 落地验证** | Sliver / 授权主机回连 | `host-c2-verify` |

## 五阶段（无 shell 也能开）

| 阶段 | 做什么 | 命令 / 卡 |
|------|--------|-----------|
| 1 侦察 | DC 端口 88/389/445/5985、空会话、LDAP 匿名、kerbrute | `ad_surface_check.py` |
| 2 凭据 | AS-REP / Kerberoast / 喷洒（先看锁定策略）/ netexec 横扫 | `kerberos-attack` |
| 3 域接管 | DCSync、krbtgt、金/银票 | `windows-ad-pentest` |
| 4 高级 | 委派/RBCD、ADCS ESC1-13、ACL 链、混合 AAD | `adcs-pentest` |
| 5 横向 | PTH/PTT、evil-winrm、chisel/SSH 隧道 | `smb-lateral-movement` · `internal-tunnel` |

版本命中 CVE（如 PetitPotam 类）必须证明协议可达，不能只报版本。

## 决策流程

```
已拿 shell
   │
   ├─ Linux？→ linux_lpe_checker.py 并行 host_ir_check.py
   ├─ Windows？
   │   ├─ 看域加入状态 → ad_surface_check.py
   │   ├─ 域内机器 → windows-ad-pentest → BloodHound → ACL
   │   ├─ 发现 ADCS → adcs-pentest（ESC 系列）
   │   ├─ Kerberos 服务账号 → kerberos-attack
   │   ├─ 想横向 → smb-lateral-movement
   │   └─ 想持久 → windows-persistence
   ├─ 容器？→ 容器逃逸手法.md → K8s ServiceAccount
   └─ 需要内网代理 → internal-tunnel
```

## 前置工具

```bash
# 初始化 AD 环境侦察
python3 tools/ops/ad_surface_check.py --host 目标IP --case <案卷>
# 自动化 LPE 检查
python3 tools/ops/linux_lpe_checker.py --case <案卷>          # Linux
python3 tools/ops/windows_lpe_checker.py --case <案卷>       # Windows
```

## 禁止

- 拿到域控权限后立刻改 KRBTGT 密码（先问）
- 在不出网的靶机上用需要 Internet 的工具
- 未授权内网 IP 随意横向（先确认 scope 涵盖内网段）

## 真源

- Playbook：`docs/playbooks/域渗透分流手法.md` · `内网扫描与横向.md` · `内网隧道与代理链.md` · `Windows提权手法.md` · `Linux主机提权手法.md`
- Skill 详细命令见各子卡


---

## 外部库增量（2026-10-11 分享包）

## 工具别名（找不到卡时先换名）

| 上游/别称 | 本库对应 |
|-----------|----------|
| `nxc` / `crackmapexec` / CME | `netexec`（凭据横扫、`--lsassy`） |
| `rpcclient` / `enum4linux-ng` | `windows-ad-pentest` 枚举段 |
| `GetNPUsers` / `GetUserSPNs` | impacket 的 AS-REP / Kerberoast 实现，走 `kerberos-attack` |
| `session_matrix`（双会话差分矩阵） | `object-matrix-authz` |
| `procdump` + `pypykatz` | `credential-harvest` LSASS 段 |

