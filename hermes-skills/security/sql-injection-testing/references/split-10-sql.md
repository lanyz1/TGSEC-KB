## 九、SQL注入测试检查清单

### 9.1 注入点发现
- [ ] 所有HTTP参数测试（GET/POST/Header/Cookie/JSON/XML）
- [ ] 所有注入点类型验证（Union/Boolean/Time/Error/Stacked/Second-Order）
- [ ] 多参数组合测试（参数间逻辑关系）
- [ ] 二次注入测试（存储后触发）

### 9.2 数据库指纹
- [ ] 确定数据库类型（MySQL/MSSQL/Oracle/PostgreSQL/SQLite）
- [ ] 确定数据库版本
- [ ] 确定当前用户及权限
- [ ] 确定WAF类型（如有）

### 9.3 WAF绕过
- [ ] 编码绕过（URL/Unicode/Hex/Double URL）
- [ ] 空白字符绕过（空格/Tab/换行/注释）
- [ ] 关键字变形（大小写/内联注释/拆分）
- [ ] 语法绕过（数据库版本特有函数/语法）
- [ ] sqlmap Tamper组合测试
- [ ] AI语义级绕过（CTE/JSON函数/窗口函数）

### 9.4 数据提取与利用
- [ ] 数据库列表提取
- [ ] 表/列结构提取
- [ ] 敏感数据提取（用户/密码/密钥）
- [ ] 权限评估（DBA/FILE/命令执行）
- [ ] RCE路径验证（xp_cmdshell/INTO OUTFILE/UTL_FILE等）

### 9.5 外带通道
- [ ] DNS外带测试（DNSLog）
- [ ] HTTP外带测试
- [ ] SMB外带测试（Windows/MSSQL）

