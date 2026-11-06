## 十五、测试检查清单

### 15.1 发现与确认
- [ ] 识别所有XPath求值入口（登录/搜索/查询/权限/SAML解析/XSLT参数）
- [ ] 单引号/双引号闭合测试（语法错误/空响应）
- [ ] 布尔差异确认注入（`' or '1'='1` vs 正常输入）
- [ ] 数字上下文测试（`1 or 1=1`）
- [ ] 属性上下文测试（`'] | //* | foo['`）

### 15.2 认证与逻辑
- [ ] 永真条件认证绕过（经典/双引号/谓词注入三形态）
- [ ] 权限字段提取（首个返回节点的role/isAdmin）
- [ ] 越权读取其他用户数据

### 15.3 数据提取
- [ ] 节点枚举（*/node()/text()/comment()/@*）
- [ ] 根节点/节点名指纹（name()/starts-with）
- [ ] `|`联合多路径输出
- [ ] 布尔盲注长度二分提取
- [ ] 布尔盲注字符集二分提取
- [ ] 位运算/码点提取（XPath 2.0）
- [ ] string-join批量拼接输出
- [ ] XPath 2.0函数（doc()/unparsed-text()/collection()）文件读取
- [ ] 时间盲注（doc()不可达地址/大计算）
- [ ] OAST外带（DNS/HTTP监听）

### 15.4 高级面
- [ ] XQuery注入（BaseX/eXist/MarkLogic REST或参数）
- [ ] FLWOR表达式注入与批量导出
- [ ] XXE/XInclude联动（XML结构注入点）
- [ ] XSLT扩展函数RCE
- [ ] 现代语言库差异适配（lxml/PHP/.NET/Java参数化差异）

### 15.5 业务/协议面
- [ ] SAML断言解析XPath注入（NameID/Attribute）
- [ ] SAML文档级XPath缺陷测试（CVE-2026-18092模式）
- [ ] XSW签名包装测试（副本断言/双根/ID重用）
- [ ] 属性提权（role注入）

### 15.6 绕过与纵深
- [ ] XML实体编码/URL编码绕过
- [ ] 等价表达式（true()/not(not())/translate/concat/codepoints）
- [ ] 空白打散（空格/TAB/换行）
- [ ] 命名空间local-name()绕过
- [ ] 流量层绕过（chunked/Content-Type/压缩）
- [ ] 错误信息泄露收集（堆栈/库版本）

