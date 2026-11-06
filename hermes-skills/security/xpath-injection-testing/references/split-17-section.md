## 十六、修复建议

- **参数化XPath（根治）**：查询骨架与数据分离——Java用`XPathVariableResolver`，lxml用`$var`绑定，XQuery用`declare variable $x external`，.NET用`XsltArgumentList`；无参数化能力时（PHP DOMXPath）用预编译查询+严格转义
- **输入白名单校验**：用户名/ID按业务格式白名单（`^[a-zA-Z0-9_.-]{1,64}$`），拒绝XPath元字符
- **转义兜底**：单引号替换为`&apos;`（OWASP推荐），双引号替换为`&quot;`；注意同时处理`[`、`]`等结构字符
- **禁用危险函数**：XPath/XSLT处理器禁用`doc()`/`document()`/`unparsed-text()`/`collection()`；XSLT禁用扩展函数（Java/PHP/.NET扩展）
- **安全解析器配置**：禁用XXE（`DOCTYPE`）、禁用XInclude；XML解析器feature安全化（如Java `XMLConstants.FEATURE_SECURE_PROCESSING`+`ACCESS_EXTERNAL_DTD`）
- **XSLT沙箱**：安全模式运行、限制加载协议（file/http）、最小权限账户
- **SAML专项**：身份字段必须从签名覆盖子树内提取（禁止文档级`//`XPath取第一个）；签名验证与业务处理用同一解析器/视图；校验断言唯一性防重放
- **错误处理**：统一错误页，不返回XPath异常堆栈与查询片段
- **最小权限**：运行XQuery/XSLT的账户低权限；XML数据库按用户隔离集合
- **WAF纵深**：拦截XPath元字符组合+等价表达式特征；对SAML/XML参数单独解码后检测

