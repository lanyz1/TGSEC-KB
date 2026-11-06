## 九、现代语言库差异与利用

| 语言/库 | XPath求值入口 | 参数化支持 | 注入利用注意点 |
|--------|--------------|-----------|--------------|
| Python lxml | `etree.XPath()`/`element.xpath()` | 支持变量绑定`$var` | 扩展函数可注册；`extensions`可被滥用 |
| Python xml.etree | `ElementTree`弱XPath | 无 | 仅1.0子集，注入面有限 |
| Java JAXP | `XPathFactory.newInstance().newXPath().evaluate()` | 需`XPathVariableResolver` | Xalan vs Saxon扩展函数差异大 |
| PHP | `DOMXPath::query()`/`evaluate()` | 无原生参数化 | 需手动转义；`registerPhpFunctions()`危险 |
| .NET | `XPathNavigator.Select()/Evaluate()`、`SelectSingleNode()` | 无内置（可用`XslCompiledTransform`+`XsltArgumentList`） | LINQ to XML相对安全 |
| Node.js | `xpath`库+`xmldom`/`@xmldom/xmldom` | 部分支持 | 解析器差异（如xmldom历史CVE） |
| BaseX/eXist | REST+XQuery | 外部变量绑定成熟 | 见第七章 |

### 9.1 Python lxml（审计要点）
```python
# 脆弱：字符串拼接
xpath = f"//user[name='{username}' and password='{password}']"
doc.xpath(xpath)

# 安全：变量绑定（数据与查询分离）
doc.xpath("//user[name=$u and password=$p]", u=username, p=password)

# 高危：注册扩展函数（等价于XSLT扩展）
from lxml import etree
def evil(ctx, arg): return os.popen(arg).read()
etree.FunctionNamespace("urn:evil")["exec"] = evil
doc.xpath("//a[evil:exec('id')]", namespaces={"evil": "urn:evil"})
```

### 9.2 Java XPathFactory（审计要点）
```java
// 脆弱：字符串拼接（CVE高发模式）
String expr = "//user[username='" + username + "' and password='" + password + "']";

// 安全：XPathVariableResolver 参数化
XPath xpath = XPathFactory.newInstance().newXPath();
xpath.setXPathVariableResolver(new SimpleVariableResolver());
String expr = "//user[username=$user and password=$pass]";
xpath.evaluate(expr, doc, XPathConstants.NODESET);

// 注意：Saxon实现支持更多扩展（EXPath file模块等）
```

### 9.3 PHP DOMXPath（审计要点）
```php
// 脆弱
$q = "//user[name='{$_POST['user']}' and pass='{$_POST['pass']}']";
$xpath->query($q);

// 缓解：转义单引号
$user = str_replace("'", "&apos;", $_POST['user']);

// 高危：注册PHP函数（php:function('system',...)）若可被用户触发XSLT
```

### 9.4 .NET XPathNavigator（审计要点）
```csharp
// 脆弱
string q = $"//user[username='{user}' and password='{pass}']";
nav.Select(q);

// .NET无内置XPath参数化；安全写法：先取节点再比较值
// 或 XslCompiledTransform + XsltArgumentList 参数绑定
```
**审计通用信号**：`+ user`、`+ password`、`$"//..."`、`f"//..."`、`sprintf("//%s")`拼接进XPath求值函数，均为CWE-643信号。

