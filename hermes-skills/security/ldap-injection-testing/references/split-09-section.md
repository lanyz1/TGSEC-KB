## 八、框架注入差异与代码审计

### 8.1 主流框架转义机制对比（v3.0新增）
| 框架/语言 | 过滤器转义函数 | DN转义函数 | 易踩的坑 |
|----------|--------------|-----------|---------|
| Spring Data LDAP (Java) | `LdapEncoder.filterEncode()` | `LdapEncoder.nameEncode()` | 两者混用/只做其一；`AndFilter/EqualsFilter`等DSL未用才安全 |
| Spring Security LDAP | `LdapEncoder.filterEncode`（内部） | - | 自定义`FilterBasedLdapUserSearch`时手拼字符串 |
| python-ldap | `ldap.filter.escape_filter_chars(s, escape_mode=0)` | `ldap.dn.escape_dn_chars()` | **escape_mode=1 + 传list/dict时跳过转义（CVE-2025-61911）** |
| ldapjs (Node) | `ldapjs`过滤器类自动转义；手拼用 `\2a` 等 | `ldapjs.dn` 类 | 直接字符串模板拼filter最常见的洞 |
| C# DirectorySearcher | 无内置函数，手动`Replace` | 无 | `searcher.Filter = "(sAMAccountName="+user+")"` 直拼 |
| PHP | `ldap_escape($val, "", LDAP_ESCAPE_FILTER)` | `LDAP_ESCAPE_DN` | 只对值转义、属性名/结构位不转义 |
| Go ldap/v3 | `ldap.EscapeFilter()` | - | 忘记转义即洞 |

**注意：** 框架自带转义函数 ≠ 安全。常见误用：
```
# ① 转义了但用在DN上（过滤器转义≠DN转义，逗号等未覆盖）
# ② 转义了值但属性名/结构由输入决定
# ③ 转义发生在LDAP解析之后（如先decode再拼filter）
# ④ 完全绕过框架API，用裸字符串拼接（最普遍）
```

### 8.2 框架转义缺陷实战
```
# CVE-2025-61911：python-ldap <3.4.5 escape_filter_chars
# 攻击面：应用调用 escape_filter_chars(value, escape_mode=1) 且value可为list/dict
# 原理：escape_mode=1对list/dict不强制str类型检查 → 直接返回未转义内容
# 修复：3.4.5起非str参数直接抛异常；审计时检查 escape_mode 参数是否被业务传成1

# ldapjs手拼示例（漏洞形态）：
const filter = `(&(uid=${username})(userPassword=${password}))`;   // 洞
const filter2 = new ldapjs.AndFilter({filters:[
  new ldapjs.EqualityFilter({attribute:'uid', value:username}),    // 安全
  ...]});

# Spring LDAP直拼（漏洞形态）：
String filter = "(&(uid=" + username + ")(userPassword=" + password + "))";  // 洞
# 正确：ldapTemplate.authenticate(Dn, Filter.encodeEquality("uid", username), ...)
# 或 LdapEncoder.filterEncode(username) 后再拼接
```

### 8.3 快速定位LDAP拼接漏洞的审计模式
```
# ① 检索危险API调用点（grep模式，跨语言通用）：
"ldapTemplate.search|search(" + "userFilter|baseDn"
"(sAMAccountName|uid|cn|mail|userPrincipalName|distinguishedName)(=|+|\")"
"ldap_escape|escape_filter_chars|LdapEncoder|EscapeFilter"  ← 看转义是否覆盖所有输入位
# ② 追踪输入流：HTTP参数 → service层 → LDAP工具类
# ③ 高发位置清单：登录、密码重置、搜索、成员检查、SSO userProfile加载、审计查询
# ④ 静态扫描工具：Semgrep规则(ldap-injection)、CodeQL(ql/java/query/...LDAP)
```

