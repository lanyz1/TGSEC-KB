## 2. 域信息侦察与枚举

AD 渗透的胜负往往取决于侦察的深度。BloodHound 将域内对象关系可视化为攻击图，是侦察的核心工具。

### 2.1 BloodHound：攻击图分析

BloodHound 用图数据库(Neo4j)存储域对象及其关系(成员关系/ACL/会话/委派)，自动计算从当前立足点到Domain Admin的最短攻击路径。

```bash
# 1. 启动Neo4j与BloodHound (Kali)
neo4j start                                # 启动图数据库
bloodhound                                 # 启动Web界面 http://localhost:7474

# 2. 数据采集 — SharpHound (C#收集器，最常用)
# 在域内主机执行，采集会话/ACL/对象/委派/ADCS等全量数据
SharpHound.exe -c All                      # 全量采集(会话+ACL+对象+GPO+委派+证书)
SharpHound.exe -c Session --loop           # 仅采集会话(循环，提高命中率)
SharpHound.exe -c ACL --collectionmethod Session  # 组合采集

# 3. 上传zip到BloodHound，运行预置查询
#   - Find All Domain Admins               列出所有域管
#   - Shortest Paths to Domain Admins      到域管的最短路径(核心)
#   - Find Kerberoastable Users            可Kerberoasting的账户
#   - Find AS-REP Roastable Users          可AS-REP Roasting的账户
#   - Find Principals with DCSync Rights   有DCSync权限的账户
#   - List All Kerberos Delegations        所有委派配置
```

**BloodHound攻击路径解读**——图中的边(Edge)代表可利用的信任关系：

| 边(Edge)类型 | 含义 | 利用方式 |
|-------------|------|---------|
| `MemberOf` | 账户属于某组 | 继承组权限 |
| `HasSession` | 用户在某主机有登录会话 | 攻击该主机提取用户凭据 |
| `AdminTo` | 账户对主机有管理员权限 | 可远程执行/提权 |
| `GenericAll` | 对对象有完全控制 | 可改密码/改ACL/加组成员 |
| `GenericWrite` | 可写对象属性 | 可改SPN(触发Kerberoasting)/改scriptPath |
| `ForceChangePassword` | 可强制改密码 | 直接重置目标密码 |
| `AllowedToDelegate` | 配置了约束委派 | S4U2Self/S4U2Proxy滥用 |
| `GetChangesAll` | 有DCSync复制权限 | 直接拉取全域哈希 |

### 2.2 PowerView：命令行枚举

PowerView 是 PowerShell 域枚举神器，适合无 BloodHound 界面时的快速查询：

```powershell
# 域基本信息
Get-Domain                                  # 当前域信息
Get-DomainController                        # 域控列表
Get-DomainUser -IdentityAdministrator       # 管理员账户

# 高价值账户定位
Get-DomainUser -PreauthNotRequired          # AS-REP Roasting候选(未启用预认证)
Get-DomainUser -SPN                         # Kerberoasting候选(有SPN)
Get-DomainUser -AllowDelegation             # 可被委派的用户

# 组与权限
Get-DomainGroup -AdminCount                 # AdminCount=1的高权限组
Get-DomainGroupMember -Identity "Domain Admins"  # 域管成员
Get-NetGroupMember -GroupName "Domain Admins" -Recurse  # 递归(含嵌套组)

# 主机与会话
Get-NetComputer -OperatingSystem "Windows Server*"  # 所有服务器
Get-NetSession -ComputerName fileserver01   # 某主机的登录会话(定位域管在哪登录)
Find-DomainShare -CheckShareAccess          # 可访问的共享

# ACL查询
Get-ObjectAcl -ResolveGUIDs | ?{$_.ActiveDirectoryRights -eq "GenericAll"}  # 所有GenericAll
Find-InterestingDomainAcl                   # 异常ACL(可能有提权路径)

# 委派
Get-DomainComputer -TrustedToAuth           # 非约束委派的主机
Get-DomainUser -TrustedToAuth               # 约束委派的用户
```

### 2.3 ADModule 与原生工具

企业环境常受限 PowerShell Constrained Language Mode 或无 PowerView，此时用 ActiveDirectory 模块与原生 net 命令：

```powershell
# AD模块(需RSAT，部分环境预装)
Import-Module ActiveDirectory
Get-ADUser -Filter * -Properties ServicePrincipalName | ?{$_.ServicePrincipalName}  # Kerberoasting候选
Get-ADUser -Filter {DoesNotRequirePreAuth -eq $true}                                 # AS-REP候选
Get-ADComputer -Filter * -Properties OperatingSystem                                 # 所有计算机
Get-ADGroupMember "Domain Admins" -Recursive                                          # 域管递归

# 原生net命令(最受限环境也可用)
net user /domain                              # 域用户
net group "domain admins" /domain             # 域管
net group "domain controllers" /domain        # 域控
nltest /dclist:corp.local                     # DC列表
```

### 2.4 ADSI/LDAP 查询

最底层方式，通过 LDAP 直接查询 AD 目录，绕过 PowerShell 限制：

```powershell
# 通过ADSI搜索所有用户
$searcher = New-Object System.DirectoryServices.DirectorySearcher(
    [ADSI]"LDAP://DC=corp,DC=local")
$searcher.Filter = "(&(objectClass=user)(servicePrincipalName=*))"  # 有SPN的用户
$searcher.FindAll() | ForEach-Object { $_.Properties.samaccountname }

# 查询未启用预认证的用户
$searcher.Filter = "(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))"
# UAC位 4194304 = DONT_REQ_PREAUTH

# ldapsearch (Linux/Kali)
ldapsearch -x -H ldap://dc01.corp.local -D '<EMAIL-REDACTED>' -w 'Pass123!' \
  -b 'DC=corp,DC=local' '(servicePrincipalName=*)' sAMAccountName servicePrincipalName
```

---

