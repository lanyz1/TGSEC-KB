## 一、攻击面与注入点

### 1.1 注入点全景
| 场景 | 示例查询 | 危害等级 |
|------|---------|---------|
| 用户登录（XML用户库） | `//user[username/text()='INPUT' and password/text()='INPUT']` | 严重（认证绕过） |
| 用户/商品搜索 | `//user[contains(name,'INPUT')]` | 高（数据泄露） |
| 数据查询 | `/products/category[@name='INPUT']/item` | 高 |
| 权限检查 | `//user[@id='INPUT']/isAdmin/text()` | 严重（越权） |
| XML配置解析 | 动态XPath读取配置值 | 高（配置含密钥/凭据） |
| SOAP/XML Web Service | Web Service中XPath查询 | 高 |
| SAML断言解析 | XPath提取NameID/Attribute | 严重（SSO认证绕过） |
| XSLT转换参数 | 用户输入嵌入XSLT | 严重（可能RCE） |
| XML数据库（BaseX/eXist/MarkLogic） | XQuery/XPath查询 | 严重（CWE-652） |
| 文档管理系统 | XPath检索XML文档 | 中高 |
| APT/防火墙管理面（OPNsense等） | XPath操作config.xml | 严重（CVE-2026-53582） |
| 低代码/SaaS目录（Plesk APS等） | XPath搜索应用目录 | 严重（CVE-2026-44962，XPath→RCE） |

### 1.2 XPath特殊字符
```
'        字符串定界
"        字符串定界
/        路径分隔
//       任意深度后代
*        通配符（任意节点）
@        属性前缀
[]       谓词（条件）
|        多路径（XPath的"UNION"）
()       分组
.        当前节点
..       父节点
and or   逻辑运算（=为比较，AND优先级高于OR）
= !=     比较
< > <= >= 比较（XML文档中需转义&lt; &gt;）
+ - * div mod 算术（除法用div，*为通配符/乘法需上下文）
:        命名空间
comment() 注释节点
text()   文本节点
node()   任意节点
```

### 1.3 注入点识别要点
- **参数扫描**：所有进入XPath求值函数的参数（`xpath()`/`evaluate()`/`selectNodes()`/`query()`/`SelectSingleNode()`）
- **输入法**：`'` 触发语法错误/空响应 → 候选注入点；`' or '1'='1` 返回异常多数据 → 确认
- **盲注判定**：构造真/假条件观察响应差异（登录成功/失败、页面长度、状态码）
- **注意**：XPath字符串比较区分大小写；XML属性值中`<`、`>`、`&`需实体编码

