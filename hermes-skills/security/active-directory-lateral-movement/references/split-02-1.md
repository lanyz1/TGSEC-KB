## 1. 核心概念与攻击生命周期

Active Directory 是 Windows 域环境的目录服务，存储用户、计算机、组、服务、策略等对象，并通过 Kerberos/NTLM/LDAP 提供认证与授权。AD 渗透的本质是**身份与信任链的横向滥用**——攻击者获取一个低权限凭据后，沿信任关系逐层攀升至域管理员(Domain Admin)，最终控制域控(DC)接管全域。

### 1.1 AD 核心对象与信任概念

| 概念 | 说明 | 攻击相关性 |
|------|------|-----------|
| Domain Controller (DC) | 运行AD DS的服务器，存储NTDS.dit域数据库 | 最终目标，含所有NTLM哈希 |
| NTDS.dit | DC上的域数据库文件，存储所有用户哈希 | 拿下DC后导出即获全域哈希 |
| krbtgt 账户 | DC上签发TGT的特殊账户，其哈希用于签名所有TGT | Golden Ticket的核心——拿到krbgt哈希可伪造任意TGT |
| TGT (Ticket Granting Ticket) | Kerberos第一步票据，向KDC证明身份 | 伪造TGT=Golden Ticket |
| TGS (Ticket Granting Service) | Kerberos服务票据，访问具体服务用 | Kerberoasting的核心——离线爆破TGS |
| SPN (Service Principal Name) | 服务与账户的映射标识 | Kerberoasting需先定位有SPN的账户 |
| 委派 (Delegation) | 允许服务代表用户访问其他服务 | 非约束/约束/基于资源的委派三类滥用 |
| SID History | 账户历史SID，跨域迁移保留 | 注入高权限SID=权限提升 |
| DCSync | 通过DRSUAPI模拟DC同步复制 | 拉取任意账户哈希(含krbgt)，无需登录DC |

### 1.2 AD 渗透攻击生命周期

```
外网初始立足 (Phishing/Web漏洞/暴露服务)
   │
   ▼
[1] 域信息侦察 ─── BloodHound图分析/PowerView枚举/ADModule查询
   │  定位高价值账户、委派配置、ACL路径、域控位置
   ▼
[2] 初始凭据获取 ─── AS-REP Roasting(无需凭据)/密码喷洒/Kerberoasting/本地凭据提取
   │  获得首批可用凭据(明文密码/NTLM哈希/票据)
   ▼
[3] 横向移动 ─── Pass-the-Hash/Pass-the-Ticket/WMI/PsExec/WinRM/DCOM
   │  在主机间移动，扩大控制面，搜集更多凭据
   ▼
[4] 权限提升 ─── ACL滥用(ForceChangePassword/GenericAll)/委派攻击/ADCS ESC
   │  从普通域用户攀升至高权限(如DNS Admins/Server Operators)
   ▼
[5] 域控接管 ─── DCSync拉取krbgt/Golden Ticket/PetitPotam+ADCS/S4U2Self滥用
   │  获得Domain Admin等效权限
   ▼
[6] 持久化与全域控制 ─── Golden/Silver Ticket/Diamond Ticket/SID History/DCShadow
   │  铸造伪造票据，绕过密码修改，建立长期后门
   ▼
[7] 跨域/跨林移动 ─── 信任关系滥用/ SID Filtering绕过
```

### 1.3 关键判断：是否在域环境

渗透进入一台 Windows 主机后，首要判断其是否加入域及域信息：

```powershell
# 1. 判断是否加域
systeminfo | findstr /B "Domain"          # DOMAIN: corp.local 则加域
echo %USERDOMAIN%                          # 当前用户域
echo %LOGONSERVER%                         # 登录的DC主机名

# 2. 查询域基本信息
nltest /dclist:corp.local                  # 列出所有域控
nltest /domain_trusts                      # 域信任关系
net group "domain admins" /domain          # 域管组成员
net user /domain                           # 域用户列表

# 3. 判断当前权限与票据
whoami /groups                             # 当前用户所属组(含SID)
whoami /priv                               # 当前特权
klist                                      # 当前持有的Kerberos票据
```

> **要点**：拿到shell后第一件事是 `whoami /all` + `klist` + 判断域。这是后续所有攻击路径选择的依据。

---

