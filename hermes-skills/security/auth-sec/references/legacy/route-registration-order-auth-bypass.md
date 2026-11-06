<!-- archived from /root/.hermes/skills/security/route-registration-order-auth-bypass/SKILL.md on 2026-10-21 -->

---
name: route-registration-order-auth-bypass
description: Use when 路由漏挂鉴权(整站401唯独它返业务错误). 注册顺序缺陷族.
---

> 归档卡：原目录 `/root/.hermes/skills/security/route-registration-order-auth-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/route-registration-order-auth-bypass/…')`，不要相对 `references/legacy/` 解析。

# 路由注册顺序导致鉴权漏挂（族）

**触发**：整站鉴权一致（401），但某条路由不带凭证却返回**业务级错误**（非 401）。
根因常是「鉴权中间件只对**其后注册**的路由生效」——框架语义差异导致漏挂。

## 一、按框架定位漏挂

| 框架 | 语义 | 漏挂写法 |
|---|---|---|
| **Go/Gin** | `Group.Use(mw)` 只作用**其后**注册的路由 | `g.GET("/x", h)` 写在 `g.Use(auth)` **之前** |
| **Go/Echo** | 同上（`e.Group` + `Use`） | 路由先 `e.GET` 后 `g.Use` |
| **Express** | `app.use(auth)` 按注册序，**先注册的路由先命中** | `app.get('/x', h)` 写在 `app.use(auth)` 之前 |
| **Spring Security** | `authorizeRequests().antMatchers(...)` **顺序**+`permitAll` 位置 | 更宽的 `permitAll` 写在具体规则前 |
| **nginx** | `location` 前缀匹配优先级 + `auth_basic` 继承 | 更具体的 location 未继承父级 auth |
| **Laravel** | 中间件只作用于**该 Route::group 内**定义的路由 | 路由写在 `->middleware()` 链**之外** |
| **ASP.NET** | `[Authorize]` 只对**写了属性**的 controller/action | action 漏写属性，全局 filter 未启 |

**高发位**：静态资源类路由——`/image/:id`、`/file/:id`、`/download/:id`、`/avatar/:id`、`/export/:id`、`/attachment/:id`、`/media/:id`、`/qr/:id`。开发者在组头先写一条「读图」再挂鉴权。

## 二、活体判据（零写入）

```
GET https://T/<可疑路由>/nonexist000        # 不带任何凭证
```
- 返回 **401/403/302→login** ⇒ 有鉴权，判负
- 返回 **业务错误**（`xxx_not_found`/参数错误/JSON 业务码）⇒ ★**漏挂确认**
- 返回 **200 且响应头带服务自身指纹**（如 `x-<vendor>-request-id`、`x-new-api-version`）⇒ ★★**决定性证据**：请求确已穿过路由层进入 handler

**对照组**（必做）：取同组、同前缀、但**注册在鉴权之后**的路由，不带凭证打它 ⇒ 应得 401。两相对照才能排除「整站就没鉴权」。

**剩余风险判定**：再打写路由（如 `/mj/notify`）时用 GET 或空 body POST——未注册返 404 / SPA 兜底；若返 handler 错误则说明写路由也漏挂（高危，立即停手评估）。

## 三、变体搜索

漏挂常**成组出现**（同一 dev 同一种写法）。
- 源码法：`grep -n -B2 -A2 'Use(' router/*.go`，看 `Use` 前后各有几条路由注册
- 黑盒法：`资源名(27类) × 路径前缀(9类) = 243`，只认「非 401 的业务响应」
- ★命中数应按**路由**去重，同路由的 `/:mode/` 通配变体会重复命中，别当成多个漏洞

## 四、影响定级（别吹）

漏挂 ≠ 高危。逐项核验：
1. **ID 可枚举吗**？雪花 ID/UUID ⇒ 无枚举则 `C:L`
2. **功能真启用吗**？查 `/api/status`/`/api/pricing` 里对应开关与模型（**本例 MJ 渠道为 0 ⇒ 实际读不出数据**）
3. **有速率限制吗**？连打 12 次看 429（本例 0 个 429 ⇒ `A:L`）
4. **参数可控吗**？取数 ID 来自 DB 而非请求 ⇒ 无 SSRF/注入，只是访问控制失效

**诚实交付**：访问控制失效「已确认」；实际数据提取能力「受限于 ID 不可枚举」——两句都要写，不得只写前者。

## 五、供应链放大

若漏挂位于**上游开源项目**（非目标自定义代码）⇒ 该缺陷影响**所有未修复部署**，比目标本身更有价值；交付时明示「upstream 通用」+ 一行修复 diff。

## 六、匿名面穷尽枚举（先保证「没漏面」，再谈结论）

枚举无鉴权路由时，**不能按中间件名字关键字过滤**：

```bash
# ✗ 错：grep -v "Auth" 会把「名字带 Auth、实际匿名」的中间件一起过滤掉
#   HeaderNavModulePublicOrUserAuth / TryUserAuth / TokenAuthReadOnly 都可能匿名放行
# ✓ 对：只排除「确定强制鉴权」的，其余逐个回源码读语义
grep -nE "Router\.(GET|POST|PUT|DELETE|PATCH)|\.Group\(|\.Use\(" router/*.go \
  | grep -viE "UserAuth\(\)|TokenAuth\(\)|AdminAuth\(\)|RootAuth\(\)"
```
**然后必须逐个 `.Group()` 核对紧随其后的 `.Use()` 语句**（本例 `usageRoute` 组内子组 `tokenUsageRoute.Use(TokenAuthReadOnly())` 才算受保护），否则会漏掉整段匿名面。

**枚举完成后按端点逐条出结论，不留「未测」**：每条写明「实测响应体 + 判定」，含判负项。

## 七、三条自我检查（本轮真实踩过的坑）

1. **「不可测」不是结论。** 断言某端口/路径不可测之前，**必须先真跑一次**并记录实际失败形态（`curl` 超时 = `code=000`）。正确措辞是「经已发现的主机名实测不可达；开启状态未知（需先解决源站 IP 溯源）」，**不能**写成「不可测」——后者把「我没试」伪装成「试过了」。
2. **探测失败必须打印 raw 响应。** `len=0`（空 body）与「`json.loads` 成功但预期字段全缺」是**两种完全不同的失败**：前者多为 WAF/限流拦截，后者是**响应体换成了别的东西**（错误 JSON）。归因（「CF 拦了」）之前必须看原文；否则会把「端点异常」误报成「被拦截」而错失线索。同理，抽样本时**打错主机名**（`frontend.tld/api/*` vs `api.frontend.tld/api/*`）会让整轮探测白跑。
3. **报「未授权泄露」前先读 fallback 默认值 —— 否则把设计默认当漏洞上报。** 本例 `getHeaderNavAccess()` 的 fallback 是 `{Enabled:true, RequireAuth:false}`，且选项 `HeaderNavModules` 为空时**直接返回 fallback** ⇒ `/api/pricing`、`/api/rankings`、`/api/perf-metrics*` 的匿名可达是**上游开箱默认**，不是运维失误。**先读 fallback → 再定级**，可避免一批过度定级。

## Pitfalls

- ★**结构体零值 ≠ 语义**：`GetSetup` 在 `constant.Setup==true` 分支**提前 return**，此时 `root_init:false`/`database_type:""` 只是零值；只有 `status:false` 分支才真正赋值。**只记一个字段会把「零值」误读成「未初始化」** ⇒ 必须读全字段并回源码确认赋值分支（本例还有 `/api/status` 里的 `setup:true` 可作第二重独立证实）。
- ★**动态/插件路由的鉴权读「handler 构造点」就能定论**，别只停在「静态不可见 ⇒ 标回归风险」：本例 `productionPluginRouteHandlers()` 显式返回 `[]gin.HandlerFunc{pinRoute, middleware.TokenAuth(), ...}` ⇒ 运行时注册的 JS 插件路由**确实受鉴权保护，判负**，把存疑项升级为确证。
- ★`Use()` 之后**同组**所有路由都有鉴权 ⇒ 单测一条通过不代表整组没问题，要按注册顺序逐条推
- ★SPA 站（Next.js/React）未注册路由返 **200 + index.html** 而非 404 ⇒ 别把它当「handler 可达」；判据是**内容**是否业务 JSON，不是状态码
- ★`404 page not found`（Go 原生）vs SPA 兜底 vs handler 业务错误 —— 三态要分清，只有第三态算命中
- ★插件/动态注册路由静态不可见：源码审计判「路由被注释 ⇒ 不可达」时，须同时确认无运行时插件注册点，标注为**回归风险**而非「已排除」

### 相邻主题：响应差异 oracle（CWE-204）——同一方法论的孪生用法

同一代码库里「**这个端点做对了、那个没做**」的差异，既能定位漏挂，也能定位信息泄露：

1. **找同库的正确对照**：本例 `/api/reset_password` 无论邮箱是否存在都返回同一 `{"success":true}`（防枚举 ✓），而 `/api/verification` 分两分支返回不同文案 ⇒ **能证明是「实现疏漏」而非「设计取舍」**，说服力远高于单看一个端点。
2. **活体验证要拿到两侧样本**：只有「未注册」侧样本时（返回下游错误）**不算闭环** ⇒ 必须找到一个**确定已存在**的样本（不成就写「代码级确认 + 活体部分验证」，不宣称已完整复现）。真实场景里「已注册邮箱/用户名」样本常需从目标自身泄露面反推，别去猜。
3. **强度词必须算成本再写**：「24bit 验证码 + 无尝试计数」看着可爆，**实际 2^24 × 0.3s ≈ 58 天** ⇒ 必须降级为「理论弱点」。先看**可预测性**（`crypto/rand` vs `math/rand`；UUID v4 不可预测）再看长度 —— `GenerateVerificationCode(0)` 返回完整 UUID（128bit）与 `(6)` 返回前 6 hex **是同一个函数的两种调用**，别混为一谈。
4. **下游错误会掩盖上游 oracle**：目标 SMTP 失效时，未注册分支返回 `invalid SMTP account` 而非 `success` ⇒ oracle 依然成立（因为它就靠**文案不同**），但**邮件轰炸/钓鱼类影响直接归零** ⇒ 影响定级要按**目标当前配置**写，不能按代码理论能力写。

## 本例（可复用的完整链条）

`New API v1.0.0-rc.34`：`router/relay-router.go:210` 的 `GET /mj/image/:id` 注册在 `L211 Use(TokenAuth(),Distribute())` 之前；handler `relay/mjproxy_handler.go:28` 用 `model.GetByOnlyMJId(id)`（同文件 `L130` 就有带 `user_id` 的正确版 `GetByMJId`）⇒ 未授权读任意用户 MJ 图 + 服务器代拉上游 URL + 无限流 DB 查询。同组 `/mj/submit/imagine` 返 401 作对照；响应头 `x-new-api-version` 定证。变体搜索 243 请求仅此 1 处 ⇒ 孤例。定级 CVSS `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:L`=6.5（该站 MJ 渠道为 0 ⇒ 当前读不出数据，但 `enable_drawing=true` ⇒ 接渠道即升 7.5）。修复：把该行移到 `Use` 之后 + 改用 `GetByMJId(c.GetInt("id"), id)` + 补 `ModelRequestRateLimit`。
