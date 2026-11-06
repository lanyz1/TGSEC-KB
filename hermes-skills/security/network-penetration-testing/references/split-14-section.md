## 十三、工具链

### 13.1 信息收集
```bash
nmap/masscan/RustScan  # 端口扫描（RustScan 速度快）
subfinder/amass        # 子域名枚举
crt.sh/certsh          # 证书透明日志
Shodan/Censys/Fofa     # 互联网测绘
theHarvester/Hunter.io # OSINT
trufflehog/gitdorker   # 泄露扫描
cloud_enum             # 云存储桶枚举
```

### 13.2 渗透与 C2 框架
```bash
Metasploit          # 漏洞利用框架
Cobalt Strike       # 商业 C2（Malleable C2 Profile / BOF / Aggressor）
Sliver              # 开源 Go C2（跨平台植入体，10.3 节）
Havoc               # 开源 C2（免杀友好）
```

### 13.3 AD 渗透与凭据
```bash
impacket            # AD 攻击套件（GetNPUsers/GetUserSPNs/ticketer/psexec/wmiexec/ntlmrelayx/secretsdump/Coercer）
BloodHound CE       # AD 攻击路径图分析（SharpHound/bloodhound-python 采集）
mimikatz/pypykatz   # Windows/Linux 凭据提取
Rubeus              # Kerberos 攻击（kerberoast/asreproast/s4u/dump）
Certipy 5.1.0       # ADCS 全谱攻击（ESC1-16 + 黄金证书 + 证书映射）
Certify              # ADCS 枚举（Windows 端）
Responder/Inveigh   # LLMNR/NBT-NS/mDNS 投毒
mitm6               # IPv6 投毒
crackmapexec/netexec # 内网横向瑞士军刀（前身为 crackmapexec）
evil-winrm          # WinRM 客户端
PowerView/BloodyAD  # ACL 滥用/域枚举
ADFSpoof/shimit/ADFSDump # Golden SAML 攻击
AADInternals        # Azure AD/Entra ID 攻击套件
```

### 13.4 隧道代理
```bash
frp/Chisel/rpivot/ligolo-ng  # TCP/SOCKS 隧道
Neo-reGeorg/Tunna             # WebShell 代理
dnscat2/iodine                # DNS 隧道
ptunnel/icmpsh                # ICMP 隧道
proxychains                   # 代理链
```

### 13.5 提权与自动化
```bash
WinPEAS/LinPEAS     # 信息收集+提权建议
PowerUp             # Windows PowerShell 提权
GTFOBins            # Linux 二进制提权
Caldera             # ATT&CK 对抗模拟编排
Atomic Red Team     # 原子测试（Invoke-AtomicTest）
Watson/Windows-Exploit-Suggester # 补丁差集提权建议
```

