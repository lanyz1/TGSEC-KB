---
name: gateway-authfilter-whitelist-oracle
description: Use when 打网关AuthFilter(401统一句)过闸绕白名单时。
---

# gateway-authfilter-whitelist-oracle

适用：目标前置网关有认证过滤器（AuthFilter），回统一句
`{"msg":"请求访问：<path>，认证失败，无法访问系统资源","code":401}`，或 Spring Security 的 `403 Forbidden`。
要回答的四个问题：**路径存在吗 / 能不能过闸 / 白名单里有什么 / 免认证面怎么榨**。

## 0. 纪律（先定，再打）

- **零写入探测优先**：能用 GET / method-override 做的 oracle 就别用写请求；写接口只在用户明确授权后打，
  且**先摸清界面功能结构再谈全量外带**。
- **账号枚举一律用「不存在的账号」**：不锁死真账号。★很多注册/枚举端点在**空参 POST 下会真建号**
  ⇒ 零写入探测只用「缺字段 / 错类型」形状，永远不用空参 POST 当探针。
- **一次只改一个变量**（path / suffix / method / header 分轮），否则无法归因。
- **票据单张活跃**：同一账号别并行铸票，探测中途不重铸。
- **认证闸类资源有次数上限**（GA / 支付密码 / OTP）：未拿到密钥前**一次都不试**，盲试 = 自毁。

## 1. 先判「谁在答」——层属判定

任何一批绕过探针之前，先各发基准请求，确认这一跳是 **WAF / 网关过滤器 / 应用 / CDN** 哪一层在答：

- **JS 挑战型 WAF**（ACW 等）在网关之前就拦 ⇒ 回挑战页 / XHR-ERR。`;` 路径参数、`..;/`、编码变体这一整批矩阵
  会在 WAF 层全灭，**白跑**；把「WAF 拦」记成「过滤器拦」会让判断全歪。
- **网关过滤器**：统一句 401，体极短，带业务 code，模板一致。
- **应用层**：Spring Boot 原生 404 JSON、`Required request body is missing`、完整 Java 异常原文。
- **CDN / 静态层**：GET 直接 404 ⇒ **GET 的 404 不能否定路径在源站存在**。

## 2. 判存在性：必须用目标真实的 method + 信封

| 形态 | 响应 | 含义 |
|---|---|---|
| 无后缀 + 真 POST | 网关统一句 401 | 被拦，但**证明路由在网关里存在** |
| 带后缀 + GET | 应用原生 404 / Spring 异常原文 | **已过闸到应用** |

两者同现 = 网关真实路由已确认 + 后缀钥匙有效。反之：

- 被包装过的 `200` 里裹 `401` **不证明路径存在**。
- 目标要加密信封（`X-Encrypted` / `encrypt-key` / `encryptParams` …）时，**判存在性也必须带信封**：
  不带信封的 403 是「缺签名」而不是「无权限」——把正解（补信封）误判成「打不动、停手」是最贵的误判。

## 3. 免认证白名单测绘

白名单常以路径模式 + 后缀模式混写（形如
`/,/login,/register,/captchaImage,/profile/**,/common/upload,/common/download/**,/favicon.ico,/**/*.html,/**/*.css,/**/*.js,/**/*.png`）。三条定则：

1. **后缀白名单只在 GET 上成立**：`GET /<真实管理端路径>.js` → 应用原生 404（过闸）；同路径**真 POST → 401**；
   带 `X-Http-Method-Override: GET` 的 POST 也过闸。⇒ 后缀法是**路径存在性 / 白名单构成的 oracle**，
   不等于写接口能被调用。
2. **白名单文本里写了的后缀 ≠ 线上放行的后缀**：实测常只有 `.html/.js/.css` 放行，`.ico/.png/.json/.txt` 被拦
   （即使文本明写 png/jpg/gif/svg/ico）⇒ **逐后缀实测**，不照抄 bundle 里的白名单原文。
3. **过闸 ≠ 挑到接口**：Spring Boot 2.6+/3 已移除后缀模式匹配 ⇒ `/api/real/path.js` 不会路由到 `/api/real/path`，
   过闸后一律应用原生 404。后缀法的价值 = 确认路由 + 找**真实带后缀资源**
   （Swagger UI / knife4j / Druid / SPA 入口 / 静态资源）。

## 4. 白名单里最肥的两个面

- `/common/upload`、`/common/download`、`/common/download/resource` ⇒ 任意文件读 / 写候选（RuoYi 系默认放行）。
- 自研 `verifyAuthToken` 类校验口 ⇒ 免认证 token oracle，常见「任意 token 也 PASS + 回吐业务数据」
  （商户列表 / 押金 / 客服链接 / 新运营域 —— 顺带就是归属情报）。
  **若「一次得手、之后复现失败」**：先怀疑注入/回放通道（见 references），**复现前不计战果**——
  记「待定论」+ 原始响应 + 时间点 + 复现条件。

## 5. 应用异常原文是情报

让免认证接口吃**错误形状**的 body（缺字段 / 错类型 / 空体），Spring 回 `MethodArgumentNotValidException` /
`Required request body is missing`，常带**完整 Java 签名**：

```
com.x.web.controller.common.CommonController.verifyAuthToken(com.x.cp.domain.bo.XxxBo, javax.servlet.http.HttpServletRequest)
```

⇒ controller 类名 + 参数 BO + 自研模块名，用来反推白名单里还有哪些免认证接口、以及 BO 的字段名（进而构造正确 body）。

## 6. RuoYi-Cloud 管理端登录契约（零风险枚举）

- 登录端点 = 管理后端 host 上的 `/prod-api/login`（网关真实路由：GET 404、带信封 POST 401）。
- body：`{clientId, tenantId, grantType:"password", uuid, code, username, password}`；`uuid`/`code` 来自 `/captchaImage`。
- 响应可区分「不存在 / 验证码错误 / 用户名或密码错误」⇒ **用不存在的账号做枚举 oracle**。
- 找不到独立管理端 host 时：管理端后端往往就在**业务域同族的某个 `int*` / `api*` 主机**上
  （同 CDN IP、同一套 RuoYi 网关 + JWT 体系，但**票据不同源** ⇒ 业务票打管理端必 401，别据此判「不是管理端」）。
- 管理端 SPA bundle 可能多族共用、内里写着别家运营域 ⇒ **不能据 chunk 内的域名串判归属**，API host 由各域入口 HTML 的运行时配置决定。

## 7. 页内注入 oracle

网关 / 挑战 WAF 后面跑探测时，可靠通道常是「真浏览器页内 XHR + 页内注入」。
注入纪律、通道选择（XHR vs fetch）、跨源导航陷阱、结果可信度分级见
`references/inpage-cdp-oracle-discipline.md`。

## 8. 自研网关 / ThinkPHP 系（非 Spring）的同类闸门

统一句形态可能是 `{"code":401,"msg":"请先登录！"}`（框架父类构造函数里判登录），白名单 = 父类里免登录的那几个方法。
四条实测通则:

- **★ 路径闸门可能读 `X-Forwarded-Host`**:把 XFH 设成一个**非本站的假域**,路径校验整段放行,请求直达鉴权层
  (回「系统未授权或已过期」);不带 XFH 时同一路径回 404/框架默认体。
  ⇒ 管理前缀打不动时先做 **XFH 变更 × 路径** 的双上下文对照:多数端点要「XFH≠本站」,
  而登录端点反而**只在不带 XFH 的上下文可达**(带 XFH 被更前置的鉴权层截走)⇒ 两套上下文各打各自可达的那几条,
  别用一套打全部。★ 过闸后统一句从「404」变成「未授权」**是进展**(证明路由存在且已到鉴权层),不是失败。
- **★ 限流按 `X-Forwarded-For` 的取值逐个记账,不是全局**:同一 XFF 值打 6 发即 `操作频繁`,换一个新 XFF 立刻恢复
  ⇒ 登录/枚举端点的「次数上限」形同虚设。★ 先自证再依赖:同 XFF 连打 + 换 XFF 各一组,看到「锁 → 解锁」才下结论
  (有的目标是 XFF 与真实源 IP 复合记账)。
- **★ WAF 规则是「端点上下文相关」的,不是全站一致**:同一份弱口令载荷在 `/adminApi/auth/login` 被拦(回 WAF 页),
  在 `/merchantApi/user/login` 原样放行;连 `{"password":123456}` 这种 JSON 数字型也会被解出来拦。
  ⇒ **判定「WAF 拦弱口令」之前,必须把同一载荷 A/B 打到同族的每个前缀**(admin / merchant / shop / api …),
  一刀切放弃凭据爆破是最贵的误判。反情报:哪条前缀不拦,哪条就是更松的入口。
- **★ 鉴权头名从请求拦截器读,不要试**:bundle 里 `interceptors.request.use(e=>{const t=F(); t&&(e.headers["<X-Token>"]=t)})`
  + `withCredentials=true` ⇒ 头名、凭证存储键、是否走 Cookie 一次到手;之后所有 token 注入/越权测试都基于真头名,
  别拿 `Authorization` 盲试(回统一句 401 会让你误判成「token 无效」)。
- **★ 平行路由族常不挂主闸 —— 主 API 闸死时的首选换面**:路径/鉴权闸往往**只挂在主 API 前缀上**(如 `/adminApi/*`),
  而同产品的扩展/插件路由族(`/plugin/<code>/admin/<action>`、`/plugin/<code>/merchant/<action>`、`/plugin/<code>/api/<action>`)
  是各插件自带控制器、**不经过主闸**:实测 `/plugin/<code>/admin/index` 回「请先登录」= **已过闸、只缺票**
  (与主前缀回「请使用正确的后台路径访问」是两个不同的层),而 `/plugin/<code>/api/*` 可**完全免鉴权**(匿名同源可读)。
  ⇒ 主前缀过不去时,先把已装扩展的路由族按 `{admin,merchant,api}` 三段各打一发,再谈换目标。
- **★ bundle 榨出的端点必须分「字面量 / 拼串产物」两类**:`"/api/x/Y"` 这类字面量是真路由;`"/api/manage."+name` 这类
  拼串在静态扫描里会生成**不存在的伪路径**,打出去只吃框架/前置层 `File Not Found` 404,
  会被误读成「闸挡住了」而在错方向上继续深挖。判据(抽表后先随机抽 2-3 条验证):
  **404/框架默认体 = 路由不存在**;**应用层 JSON 错误(统一句/业务 code)= 路由存在**。
- **★ 弱口令被 WAF 吞掉的判据(不做这一步,「口令已试」是假的)**:同一登录端点要按响应层分开记账 ——
  **403 + WAF 页(宝塔「网站防火墙」一类)= 请求根本没进应用层,既不算命中也不算已覆盖**;
  **200/500 + 应用层 JSON(「用户名或密码不正确」)= 真到了 handler**。实测被吞的不止 top10
  (`123456`/`admin`/`admin123`/`qwe123`/`Aa123456` 全拦),只有「看起来不常见」的拼法(厂商默认口令/站点拼音+年份)进得去
  ⇒ **常规弱口令字典在该端点等于空跑**;统计命中率前先按响应层把 403 从分母里剔出。

**白名单测绘(没有 bundle 时的兜底)**:拿全端点逐个免鉴权空体 POST,与统一句做**整句比对** ——
只有极少数响应的 body ≠ 统一句,那几条即白名单成员/预言机。实测 200 条端点里恰好 5 条免鉴权
(`system/config` / `common/captchaStart` / `upload/file` / 两个 `check*`),逐条榨:config 吐菜单与开关、
upload 拿白名单试、`check*` 读风控开关(如 `safe_mode:0`)。
端点表来源见 `spa-request-contract-extraction`(从 bundle 机械榨全表)。

**★ 框架自带的「运营方有防备」信号也算情报**:免鉴权 config 里预置的 `site_close_tip`(形如「平台遭到恶意网络攻击,
系统升级维护中」)说明运营方已备好被攻击时的对外话术 ⇒ 打穿后默认会进维护态,别把它读成「站挂了」。
★ 免鉴权 config 里的**菜单/权限树**本身就是攻击面清单(它比前端路由表更接近服务端真实授权模型),优先读它。
