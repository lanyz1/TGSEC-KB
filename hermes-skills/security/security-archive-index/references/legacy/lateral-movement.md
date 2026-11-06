<!-- archived from /root/.hermes/skills/security/lateral-movement/SKILL.md on 2026-10-21 -->

---
name: lateral-movement
description: "内网横向移动(授权)：凭据复用 + 远程执行 + 隧道。Trigger: lateral movement, psexec, wmi, winrm, pth, pass-the-hash, rdp, 横向移动, 跳板."
---

> 归档卡：原目录 `/root/.hermes/skills/security/lateral-movement`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/lateral-movement/…')`，不要相对 `references/legacy/` 解析。

# 横向移动（内网 / 授权）

前提：一组可用凭据 + 一个立足点。先画可达性（端口/网段/域结构），再挑执行方式，**每一跳都留痕**。

## 0. 凭据从哪来

- `credential-harvest`（LSASS / LaZagne / token / 浏览器 / 配置文件）
- Kerberoasting、AS-REP、委派滥用 → `kerberos-attack`、`windows-ad-pentest`
- 中继与强制认证 → `ntlm-relay-coercion`

## 1. Windows 远程执行矩阵

| 方式 | 端口/通道 | 主要留痕 | 手段 |
|---|---|---|---|
| SMB 服务执行 | 445 | 7045 服务创建 | PsExec、impacket smbexec、`sc.exe create` |
| WMI | 135/445 | WMI-Activity 日志 | `wmic /node: process call create`、impacket wmiexec |
| WinRM | 5985/5986 | WSMan 日志 | `Enter-PSSession`、evil-winrm |
| DCOM | 135 | MMC20/Mmc 进程 | impacket dcomexec（MMC20.Application）|
| 计划任务 | 任务服务 | 4698 | `schtasks /create /s` |
| RDP | 3389 | 4624 type 10 | xfreerdp；会话劫持 |
| 共享落地 | 445 | 文件读写 | `\\host\C$` + 服务/计划任务拉起 |

## 2. 凭据复用

- PTH（NTLM）：impacket psexec/smbexec `-hashes`；nxc/CrackMapExec 批量碰撞
- PTT（Kerberos）：导出票据（Rubeus/Mimikatz）→ kirbi → 注入
- Overpass-the-hash / pass-the-key（含 AES key）
- 顺序：先 `nxc smb` 探活与权限，再挑噪声最低的执行方式

## 3. Linux 与跳板

- SSH 密钥复用（`~/.ssh`、known_hosts、agent 转发）、Ansible/Salt 跳板滥用
- 隧道与代理：`ssh -D/-L`、chisel、frp、ligolo-ng、Stowaway（多级级联）→ `internal-tunnel`

## 4. 别被打回：检测点自检

- 4624 type 3/10、4625 爆破、7045 服务、4698 计划任务、WMI-Activity、PsExec 服务名 `PSEXESVC`、admin$ 写入
- 命令行 `-enc`/Base64、异常时序与频次 → `redteam-opsec`（低慢小、限速、单发）

## 关联

`smb-lateral-movement`（批量与工具细节）、`ad-windows-router`（域内分流）、`internal-tunnel`、`egress-proxy-pool`、`intranet-penetration-testing`
