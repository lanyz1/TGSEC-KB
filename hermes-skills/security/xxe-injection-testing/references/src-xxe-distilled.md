# SRC 实战报告提炼 — xxe

> 来源：蚂蚁SRC榜一Clown的 6 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（6 份）

### 众测困住你的那些问题_jkgh006

众测困住你的那些问题 jkgh006 | 众测资深玩家，多家众测平台TOP白帽 前 言       安全趋势的发展，现在已经变成三大阵容，一个是代表过去的传统漏洞平台，第二个是以乙方为 首的众测平台，以及以甲方主导的SRC平台 ，  传统的漏洞平台慢慢的淡出视野，现在最火的莫过于 SRC和众测，所有的类型终将归为一种方法，所以对于其中众测也是有一套方法论，怎么分析，怎 么去绕，怎么去获取证据，等等都是有章可循，我们重点关注众测困住你的那些问题。 目录  01 拦截框架下注入的过程拆解 02 基于三方调用框架分析利用 03 趣味的SESSION和EXCEL 01 拦截框架下注入的过程拆解 越来越

### 众测困住你的那些问题_jkgh006

众测困住你的那些问题 jkgh006 | 众测资深玩家，多家众测平台TOP白帽 前 言       安全趋势的发展，现在已经变成三大阵容，一个是代表过去的传统漏洞平台，第二个是以乙方为 首的众测平台，以及以甲方主导的SRC平台 ，  传统的漏洞平台慢慢的淡出视野，现在最火的莫过于 SRC和众测，所有的类型终将归为一种方法，所以对于其中众测也是有一套方法论，怎么分析，怎 么去绕，怎么去获取证据，等等都是有章可循，我们重点关注众测困住你的那些问题。 目录  01 拦截框架下注入的过程拆解 02 基于三方调用框架分析利用 03 趣味的SESSION和EXCEL 01 拦截框架下注入的过程拆解 越来越

### 医科大学漏洞xxe (1)

医科⼤学漏洞 - 1 xxe 医科⼤学漏洞 fcmit.cc 医科⼤学漏洞 - 2 接⼝信息泄露 这种最简单 进⼊到后台之后找那些数据交互的点 然后 f12 刷新⽹络 ⼀个⼀个查看 fcmit.cc 医科⼤学漏洞 - 3 fcmit.cc

### YzmCMS v3.6 csrf

YzmCMS v3.6 csrf  一、漏洞简介  二、漏洞影响  YzmCMS v3.6  三、复现过程  1、文件位置: /application/admin/controller/sql.class.php 第 10-42 行中：  public function init() {        if(isset($_POST[’sqlstr’])){            if(!C(’sql_execute’)) showmsg(’根据系统配置，不允许在线执行SQL 命 令！’, ’stop’);            $sqlstr = MAGIC_QUOTES_GPC ? str

### 20-聊聊XML注入攻击

聊聊XML注入攻击 安全小课堂第二十期 XML注入通过构造恶意内容，可导致权限绕过及伪造、读取任意文件、执行系统命 令、探测内网端口（SSRF等）、攻击内网网站等危害，后果严重，本期我们来聊一聊 XML注入攻击。 本期邀请到了 安识科技安全专家神奇四侠 唯品会安全专家feng 大家欢迎~ 1   豌豆妹 能说说XML注入的攻击原理么？ 葫芦娃   XML 指可扩展标记语言，XML 被设计用来传输和存储数据。XML注入一般指在请求 的XML数据中插入攻击利用代码，根据不同的场景，可能会形成以下的漏洞形式： 1、xee  XML Entity Expansion； 2、xxe XXE Inject

### 网易云信_sql

From: <Saved by Blink> Snapshot-Content-Location: https://aq.163.com/vulDetail/?id=c9ac3d8605216cd1012df4a277ba9dfd Subject: =?utf-8?Q?=E7=BD=91=E6=98=93=E5=AE=89=E5=85=A8=E4=B8=AD=E5=BF=83?= Date: Mon, 20 Jun 2022 15:39:17 -0000 MIME-Version: 1.0 Content-Type: multipart/related; 	type="text/html"; 

## 实战 Payload 集（3 条去重）

### XSS

```
javascript:fireForms()
```

### URL

```
http://www.0-sec.org/admin/index/login.html
http://127.0.0.1:80/admin/adm
```

## 技术手法统计

- WAF/过滤绕过: 1 次

