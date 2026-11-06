## 十四、工具链

| 工具 | 用途 |
|------|------|
| Burp Suite（Intruder+Active Scan） | 注入点发现、payload批量fuzz、SAML重放 |
| XCat | XPath盲注自动数据提取 |
| xxetri | XPath注入探测与利用 |
| xpath-blind-explorer | 盲注数据提取 |
| XSLT Fuzzer / xsltproc | XSLT转换与扩展函数测试 |
| xmlstarlet | 命令行XPath查询验证（本地样本） |
| Oxygen XML / BaseX GUI | XPath/XQuery表达式调试 |
| basex（本地服务） | XQuery注入本地复现环境 |
| SAML Burp扩展（SAML Raider） | SAML断言修改、XSW测试、重放 |
| Python requests脚本（见5.6） | 自定义盲注提取 |

```
# xmlstarlet 本地验证payload效果
echo '<users><user><name>admin</name><pass>abc</pass></user></users>' > t.xml
xmlstarlet sel -t -v "//user[name='' or '1'='1' and pass='x']" t.xml

# XCat（POST盲注示例）
xcat -m POST -t "<user><user>u</user><pass>p</pass></user>" \
  http://target.com/login user=u pass=p -c "//user"
```

