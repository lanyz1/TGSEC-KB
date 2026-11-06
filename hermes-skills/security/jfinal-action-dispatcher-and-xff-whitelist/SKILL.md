---
name: jfinal-action-dispatcher-and-xff-whitelist
description: Use when JFinal 动作分发站或 RuoYi IP白名单登录. 裸 context 分发入口探测+三态判别.
---

# JFinal 动作分发站 与 XFF 白名单绕过

## 触发
- 响应形如 `{"success":true,"msg":"success","code":200,"data":{...,"sign":"<32HEX>"}}`（JFinal 风格）
- 路径形如 `/zf/<module>/<action>`、`/<controller>/<action>`
- 未知动作回 `no such api`（业务 JSON），非 404
- RuoYi 系后台登录回 `ip不在白名单范围内：<你的出口IP>`

## 一、动作名真伪 oracle（核心方法）
1. **模块段被 dispatcher 忽略**：同一动作在 `/zf/xcoinApi/`、`/zf/usdt/`、`/zf/vestApi/` 都能通 ⇒ 只认**末段动作名**。发现判据：一次探测里同一动作在 3 个模块都 200。
2. **分类判据**：`no such api` = 假名；其它任何响应（含业务报错、415、参数校验错）= 真名存在。
   - `415 Unsupported Media Type` **不代表**动作真名存在——可能只是 Spring 内容类型过滤器（须换 JSON 体重测，仍 `no such api` 即假名）。
3. **前端拼接的动作名多为伪名**：`apiAdmin*`/`apiExt*`（改余额/重置密码类）在活会话下仍全 `no such api` ⇒ 不要因「405 = 路由存在」就认定动作存在。
4. **真名常带拼写变体**：实测真名 `apXCoinGetUserInfo`（少一个 `i`）与假名 `apiXCoinGetUserInfo` 并存 ⇒ 拼写变体（删字母/换大小写）成组测。
5. **命名空间不止一个**：除 `/zf/**` 外，`/masterControl/**`、`/telegram/**`、`/pfv2/**`、`/api/**` 各有独立控制器。未认证 302 = 带认证门的独立控制器（值得枚举其特有真动作）；`no such api` = 落同一 JFinal dispatcher。
6. **零伤害写类探测**：对 `Set*`/`Reset*`/`Del*` 类动作，目标参数填**不存在的 id**（如 `999999999`）——回 `用户不存在` ⇒ 动作真实且有参数契约，且零副作用。

## 二、IDOR 判负的快速法
同一动作跑参数矩阵：`{} / {id:1} / {userId:1} / {uid:1} / {userName:admin} / {mobile:..} / {keyword:..}`。
**比对特征字段**（不是原始字节——响应含 `sign`/`timestamp` 每次不同）：抽 `userName/mobile/agent/total/rows[]` 再比。全部与 baseline 同 ⇒ **端点绑会话身份、忽略入参 ⇒ IDOR 判负**（此类站常见，别耗时间）。

## 二·五、若依/RuoYi 认证过滤链 后缀白名单绕过（GET 面，实测有效）

判据：RuoYi SecurityConfig 常见 `requestMatchers(HttpMethod.GET, "/**/*.js", "/**/*.css", "/**/*.html").permitAll()`，且按**原始 URI 后缀**判定。

必跑矩阵（无后缀为基准）：
```
GET  /tool/gen/list          -> code:401 认证失败            <- 基准
GET  /tool/gen/list.js       -> 业务级报错、无 401           <- 穿过滤链且抵达控制器
     .css .html %2ejs .js/   -> 同上（编码/斜杠变体都试）
     .json .xml %20 .js%20   -> 仍 401（证明是后缀白名单，不是接口无鉴权）
POST/PUT/DELETE + .js        -> 仍 401 => 白名单限 GET
```
「真抵达控制器」的判据：响应是**业务级**错（如 `参数[tableId]要求类型为 'java.lang.Long'，但输入值为 'list.js'`）；若是通用 Spring 错误页或 0B，则只是跳过了过滤链、未命中处理器。

天花板：Spring Boot 3 默认关闭 suffix pattern matching ⇒ `.js` 不映射到精确路径处理器，**只有「以宽松路径变量收尾」的处理器才真命中**；若目标是 Boot 2.x（`useSuffixPatternMatch=true`），所有取数型 GET 端点未认证可读 ⇒ 直接升为高危。因白名单限 GET，写类/RCE 原语（`createTable`/`PUT gen`/`upload`）不可达。

### ★ 假阳性陷阱：分号变体必用「无处理器路径」做对照
`;.js` / `%3B.js` / `.js;` 在 GET/POST/PUT/DELETE 上**都不返回 401**，但响应恒为**无 message 的通用 Spring 500**（`{"timestamp":…,"status":500,"error":"Internal Server Error","path":…}`）。
**验证：拿确定无处理器的路径（如 `/monitor/job;.js`）同跑 —— 若它也是同一 500，则该 500 发生在进入控制器之前，是框架处理分号的产物，不是绕过。** 仅凭「没有 401」宣布绕过 = 误判。

## 六·五、上传面取真契约与判据纪律（实测）

- **上传面先从客户端源码取契约**：页面里 `<script src="/js/components/busi-component-*-upload.js">` ⇒ 拉组件读 `formUploadImg` 与 `$http.post(...)`。B 侧上传全是 **JSON+base64**（`resultImgBase64`/`imgBase64`），**不是 multipart**；字段名枚举无效（实测 55 名全拒）。
- **JSON 参数大小写敏感**：`Txid`(大写) 不绑定 / `txid`(小写) 绑定 ⇒ **报错文案发生变化本身就是绑定成功的信号**。
- **扩展名白名单体现在错误码**：`.png` → 走订单校验错；`.jsp`/穿越名 → `IMG_UPLOAD_ERROR` ⇒ 扩展名先于业务校验。
- **前端网关自塞 charset**：手搓不带 charset 的 multipart，服务端回显仍带 `;charset=UTF-8` ⇒ 415 非 payload 形态问题，是该层结构行为。
- **判据纪律（血泪）**：①SSTI/回显类**必须用唯一大数**（如 `${7777*7777}`=60481729），**禁用子串**（曾用 "49" 命中响应里本有的金额/时间戳 ⇒ 误报 SSTI）②**无会话时 302 不得**当作动作可达性判据，脚本须先自证会话（真动作响应 >300B）③**多个不同出口返回同一限流文案 ⇒ 账号级限流**（非 IP 级，换出口无用，须等 24h）。

## 七、XFF 伪造绕过 IP 白名单（真实高频缺陷）
差分两条请求，唯一变量是头：
```bash
curl -sk https://<host>/prod-api/login -H 'Content-Type: application/json' \
  -d '{"username":"<u>","password":"<p>","code":"000000","uuid":"x"}'
# → {"msg":"ip不在白名单范围内：<出口IP>","code":500}
curl -sk https://<host>/prod-api/login -H 'Content-Type: application/json' \
  -H 'X-Forwarded-For: 127.0.0.1' \
  -d '{"username":"<u>","password":"<p>","code":"000000","uuid":"x"}'
# → {"msg":"谷歌验证码错误，还剩N次机会","code":500}   ← 白名单已过
```
- 也试 `X-Real-IP`、`Client-IP`、`X-Originating-IP`、`True-Client-IP`，以及 `127.0.0.1, <真IP>` 链式值；白名单常只含 `127.0.0.1`。
- **修复写法**（报告里给）：nginx `set_real_ip_from` + `real_ip_header`，应用只认 TCP 对端地址做白名单。

## 四、纪律（血的教训）
- **GA/TOTP 是每账号计数**：错一次回 `还剩N次机会`，耗尽后锁 2–3 分钟。**探测账号存在性/白名单时先用「已确认不存在」或自己的 test 账号做 oracle；不要拿 admin/真实运营账号试头**，否则耗掉对方 GA 次数（不可逆、属越界，报告里须如实交代）。
- 单设备登录站（`data.token` 在响应里回吐）：二次登录顶掉首会话 ⇒ 打点必须**串行单会话**。
- RuoYi 静态白名单放行 `*.html`：`/prod-api/swagger-ui/index.html` 会 200 而 `/v3/api-docs` 401 ⇒ **只是静态壳，定级低**，别写成「Swagger 全量泄露」。
- 默认 vhost 可能是拦截页：`Host` 换任意值回同一小体积 JSON（如 TG 渠道闸门）⇒ 不是隐藏后端，别误判。

## 裸 context 分发入口（实测：`/{context}` 无路径）

★ **JFinal filter 挂根 context `/*`**：任何 `<任意>.jsp` 都进 JFinal 并回它自带的 235B 404（`Powered by JFinal 5.2.2`）⇒ **应用在 ROOT，`/{context}` 只是 JFinal 注册的 route 前缀**；`/{context}` 裸路径能回业务 JSON 说明它是活 action，而 `/{context}/index` = 另一 actionKey ⇒ 404 不代表「无 index 方法」。
★ **`/{context}` 恒回「参数异常」= 要信封密文**：无论 query 传 `service/method`、`c/a`、`act/op` 全是同字 ⇒ 不是参数名错，是缺 `encryptParams`（同厂商前台 RSA-key + AES-ECB 信封）。⇒ 先用信封算法造密文再打，别枚举参数名。
★ 旧描述（保留参考）：

JFinal 站（`Powered by JFinal 5.2.2`，容器 Tomcat 8.5.100）有三条实测规律：
- `GET /{context}`（**无路径、可带任意 query**）→ `{"msg":"参数异常","status":"1000"}`：**分发入口存在**，且**文案与 query 参数名/值完全无关**（试过 `service/method`、`c/a`、`act/op`、`controller/action`、`mod/act` 全同字）⇒ **GET 无判定力，真实契约走 POST body**。
- `GET /{context}/api`（第二分发入口，无 query）→ 同一「参数异常」；一旦挂 query 或子路径 → JFinal 235B 404。
- `GET /{context}/<任意子路径|.jsp|index|api/x|sys>` → `404 Not Found / Powered by JFinal 5.2.2`（235B）⇒ 只有裸 context 是活的。
- 参数数组用 `[]` 会被 **Tomcat 400** 拒（`Invalid character found in the request target`，RFC 7230）⇒ 数组参数改用 POST body 或逗号串。

★ 判别三态：**110310B = WAF 挑战页**、**235B + JFinal 字样 = 框架 404（请求确实到应用）**、**789B 英文 Tomcat 404 = context 失配**。

## Pitfalls
- `requests` 务必 `trust_env=False`，否则回落环境里已死的代理。
- 走 SOCKS 池偶发 `HTTPSConnectionPool ...` 异常 ⇒ 关键判据必须重放一次再下结论。
- `.json` 后缀在 RuoYi 上**不**能脱出 permitAll 匹配（别沿旧经验硬套）。
- 输出逐行 flush + 后台跑，长任务被 demote 时仍能从日志文件取回。
