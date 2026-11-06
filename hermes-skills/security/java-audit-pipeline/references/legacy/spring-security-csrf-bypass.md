<!-- archived from /root/.hermes/skills/security/spring-security-csrf-bypass/SKILL.md on 2026-10-21 -->

---
name: spring-security-csrf-bypass
description: 触发词 CSRF/403 Forbidden/分析台。Spring Security 全站 CSRF 攻坚方法论。
---

> 归档卡：原目录 `/root/.hermes/skills/security/spring-security-csrf-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/spring-security-csrf-bypass/…')`，不要相对 `references/legacy/` 解析。

# Spring Security CSRF 攻坚方法论

## 适用场景
Spring Boot + Spring Security 的"分析台/开放平台/内部后台"(如 `/system/*`、`/open/*` 前缀),所有 POST 统一 403 CSRF,登录/SSO 接口也无豁免。目标:拿到 executeSql / 管理员接口 / 改密接口。

## 第一步:403 错误消息诊断(关键!)

两条消息含义完全不同,决定后续策略:

| 消息 | 含义 |
|---|---|
| `Could not verify the provided CSRF token because your session was not found.` | 首次 POST,**无 session**(token 尚未生成) |
| `Invalid CSRF Token 'null' was found on the request parameter '_csrf' or header 'X-CSRF-TOKEN'.` | **session 已存在**,但提交的 token 为 null |

连续两次 POST(同 cookie jar)后消息从 1 变 2 = session 建立成功、token 在 session 里但**外部读不到值**。

## deferred token 概念(Spring Security 6.1+)

`XorCsrfTokenRequestAttributeHandler` 是 **deferred(延迟)** 的:token 只在**渲染时**才生成。
- GET 请求不触发 token 生成(所有 GET 响应无 JSESSIONID Set-Cookie = 没建 session = 没生成 token)
- POST 建 session + 生成 token,但值存在 session attribute,响应不返回
- **唯一读取途径 = 渲染的 HTML**(`<meta name="_csrf">` 或表单隐藏字段)
- 纯 API 应用无模板 = 无 token = 外部不可达 = **设计级死锁**

**先探测模板**:`GET /xxx/login` 返回 500 + `org.thymeleaf.exceptions.TemplateInputException` = controller 存在但模板缺失;404 + `JSP file [...] not found` = JSP 解析器配置但文件缺失。全 500/404 = 无页面可渲染 → 放弃正面获取 token。

## URL 规范化/变体矩阵(重点:区分防火墙 vs CSRF!)

**所有畸形 URL 变体必须先看异常类型再下结论——500 不等于绕过!**

| 响应 | 含义 |
|---|---|
| 403 + `Invalid CSRF Token` | CSRF 过滤器拦截(正常路径) |
| 500 + `RequestRejectedException: URL was not normalized / potentially malicious String` | **Spring Security 防火墙拦截**(畸形 URL),发生在 CSRF **之前** |
| 500 + Thymeleaf TemplateInputException | 请求穿透了过滤器,但 controller 没匹配(当视图名解析了) |

测试矩阵(全部对目标接口试):
```
//system/decrypt          /system//decrypt        /system/./decrypt
/system/decrypt/          /system/decrypt%2f      /system/%64ecrypt
/system/decrypt;          /system/decrypt;jsessionid=abc
/system/decrypt..;/       /open/api/executeSql..;/
/%2e%2e/system/decrypt    /SYSTEM/decrypt(大小写)
```
**结论模式**:正常路径 → CSRF 403;变体路径 → 防火墙 500。双层防护完整 = 公开面无绕过。`..;/` 组合常被**网宿/WAF 单独拦**(纯 HTML 403 页,区别于应用 JSON 403)。

## 认证层与 CSRF 层的先后

- **CSRF 在认证之前拦截**:带 appId/appSecret/Authorization 头仍先报 CSRF = 密钥与 CSRF 无关,别浪费时间试密钥。
- 前端 env 里常直接内嵌 `VUE_APP_APPID/VUE_APP_APPKEY/VUE_APP_APPSECRET` 明文——但那是给业务接口用的,过不了 CSRF 层。

## 真正出路:网关层(前端 JS 逆向)

应用若有 `/proxy/*` 网关(nginx 反代到后端服务),**网关层通常无 CSRF,只验 Authorization token**:

1. 拉前端 SPA 的 app.js/main.js(几百 KB 到 1.4MB),搜:
   - `baseURL` / `VUE_APP_INTERFACE_URL` / `VUE_APP_PORTAL_API` / `VUE_APP_BASE_API` / `VUE_APP_REPORT_API`
   - `Authorization` header 拼接逻辑(`token` 来源:URL `serviceTicket` 参数或 localStorage)
   - `/proxy/` 字面量
2. 常见网关名:`/proxy/dataplatform`、`/proxy/portal`、`/proxy/platformexport`、`/proxy/analysis/ds`、`/datashow/decision`
3. 网关响应语义:
   - `401 {"msg":"您未登录或已退出登录，请重新登录后再进行操作"}` = **需要新鲜 ST/token**(过期或缺失都是 401)
   - 带新鲜 ST 后 200 = 网关直通,无 CSRF 阻碍
4. 网关 POST 会由前端自动注入 `appId` 到 body —— 复现时照抄。

## 配套技术:SM2 加密登录(gmssl 坑)

门户类登录常 `userPassword = "04" + SM2_encrypt(hex_md5_wz(pwd))`:
- `hex_md5_wz(s) = MD5(MD5(s).upper()).upper()`(大写双层)
- **gmssl 新版 `CryptSM2.encrypt(data, mode=1)` 会报 `unexpected keyword argument 'mode'`** → 改成属性 `c.mode = 1`(C1C3C2,与前端 sm2.doEncrypt 一致)再 `c.encrypt(data.encode()).hex()`
- 公钥在前端 JS `var p = '04...'` 里直接拿
- 验证加密链正确性:用**已知正确账密**登录,若返回风控拦截而非"用户名或密码错误",说明加密+链路正确(风控在密码校验之后)

## 风控与节奏

- 连续错误密码不锁 IP,但**账号级风控**:多次尝试触发"当前账号因触发安全风控策略,今日已限制所有登录方式" → 锁 24h。目标性弱口令每账号 2-4 个候选、间隔 3-5s,禁止批量。
- 返回"用户名、随机码或密码错误" = 账号存在且未锁,可继续但低频。
- **短信验证码:绝不向不属于用户的手机号发码**(用户明确纠正:收不到就不是你的,别乱发)。

## 参考案例
- `references/95306-console-csrf-case.md` — 国铁采购平台分析台(/system/* 与 /open/* 同应用)CSRF 攻坚实录:错误消息样本、变体矩阵结果、datavis 前端逆向出的 6 个网关、15 组 AppID/AppSecret 明文。


---

## 外部库增量（2026-10-11 分享包）

## 方法绕过:先看请求方法(GET 天然免 CSRF)

- CSRF 的默认 matcher **只匹配 POST / PUT / PATCH / DELETE**。**GET 不受 CSRF 保护** → 对无语义的端点直接用 GET 就能免 CSRF 命中,不必和 token 死磕。
- **但 GET 会改变 principal 语义,容易造出「假预言机」**:Spring Security OAuth2 的 `AbstractTokenGranter.getClientId(principal)` 取的是**已认证主体名**,未登录时是 `anonymousUser`,**不读 `client_id` 等请求参数** → `GET /oauth/token?...&client_id=X` 对任何 X 都返回同一条 `NoSuchClientException`。没识破就会得出「枚举了 N 个全无效」的假结论(实测 68+ 个候选全灭)。
- **铁律:换方法前先确认端点逻辑是否依赖 principal / 认证主体。** 依赖则 GET 只是「到了端点、语义已变」,应换面(枚举 client_id 改用 `/oauth/authorize`,它在鉴权前就查 client)。
