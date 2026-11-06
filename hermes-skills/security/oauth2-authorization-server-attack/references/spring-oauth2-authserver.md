# Spring Security OAuth2 授权服务器 —— 深度细节

配套 `SKILL.md`。目标:`@EnableAuthorizationServer` 的 `/oauth/token`、`/oauth/authorize`、`/oauth/token_key`,以及挡在前面的 nginx / CSRF / StrictHttpFirewall。

## 1. 定位与指纹(不用猜)

- 错误体里的 `path` = 服务 `server.servlet.context-path` + 请求路径 → **直接得到服务名/模块名**(如 `/poseidon/customer/oauth/token` → 后端起名 poseidon、模块 customer),据此反推微服务命名族再横向枚举。
- **未认证访问 `/oauth/token` → 302 `Location: http://<内网IP>:<port>/login`** → 一次拿两条情报:内网地址 + 该服务用表单登录(非纯 API)。
- `GET /oauth/token_key` 存在(401)= JWT token store。**若最终能绕鉴权读到:对称签名返回共享密钥 → 可伪造 token**;非对称只给公钥。
- nginx 常只开**前缀 location**:`location /oauth/token` 会把 `/oauth/token*` 全代理(所以 `/oauth/token_key` 也活),而 `/oauth/authorize`、`/oauth/check_token`、`/oauth/confirm_access` **404 nginx** = 未开。
- **preprod/staging 常比 prod 暴露更多**(authorize、`/login` 可达)→ 先横向比一遍环境的 nginx 面,再决定打哪个环境。

## 2. ★ 未认证 client_id 预言机(首选手法)

```
GET /oauth/authorize?response_type=code&client_id=<X>&redirect_uri=/
  不存在 → 500 NoSuchClientException("OAuth2 client not found")
  存在   → 其它响应(302 → /login,或 redirect_uri 未注册的校验错)
```

- 成因:`AuthorizationEndpoint.authorize()` 第一步就 `clientDetailsService.loadClientByClientId(clientId)`,**在鉴权之前** → 无凭据即可调用。
- 判据:响应体含 `NoSuchClientException` = 无效;否则 = **命中**。
- 命中后:① public client → `authorization_code` 直接换 token;② 否则 `/oauth/token` + Basic 爆破 secret,成功判据 = **响应不再出现 `Bad credentials`**。
- 候选铺法顺序:业务名 → 微服务名 → 厂商/平台代号(从报错泄露的 `XXX_APP_TITLE`、包名 `com.<vendor>.*` 反推)→ 环境名 → 移动端标识;全灭说明 id 是 UUID/内部编号,转 §6 去挖真值,别硬爆。

## 3. `/oauth/token` 语义矩阵(别把无效路径当有效)

| 请求 | 典型结果 | 能否枚举 client_id |
|---|---|---|
| `GET /oauth/token?...&client_id=X` | 500 `NoSuchClientException` | ❌ **假预言机**:`AbstractTokenGranter.getClientId(principal)` 取**已认证主体名**(未登录 = `anonymousUser`),**不读 client_id 参数** → 任何 X 都一样 |
| `POST /oauth/token` + `client_id`/`client_secret` 表单参数 | 401 `Full authentication is required` | ❌ 该部署只认 HTTP Basic(`ClientCredentialsTokenEndpointFilter` 未生效) |
| `POST /oauth/token` + `Authorization: Basic X:Y` | 401 `Bad credentials` | ❌ 不存在 client 与 secret 错**返回同一错误**,不可区分 |
| `POST /oauth/token`(CSRF 开启) | 403 CSRF 先拦 | ❌ |

**结论:`/oauth/token` 预言机价值≈0,client_id 枚举一律走 `/oauth/authorize`。**

## 4. CSRF 与方法

- CSRF 只保护 **POST/PUT/PATCH/DELETE**(实测全 403);**GET 不受保护** → 是唯一「免 CSRF 到达端点」的手段,但受 §3 的 principal 陷阱限制:**端点逻辑依赖 principal 时,GET 绕过去也没有意义**。
- `HttpSessionCsrfTokenRepository` 时响应只 `Set-Cookie: JSESSIONID=...`,**没有** `XSRF-TOKEN` 之类可读 cookie → token 只在服务端 session,`X-CSRF-TOKEN`/`X-XSRF-TOKEN`/`_csrf`/`RequestVerificationToken` 变体全 403,不可绕。
- 要拿 token 必须让登录页渲染出 `<meta name="_csrf">` 或表单隐藏字段;若登录页 500(模板表达式报错,常见 `session.xxx` 取不到)→ **先去走会填充 session 的入口(SSO redirect / authorize 流程)再回头取**,而不是原地重试。

## 5. 穿越(区分拒绝 vs 绕过)

- 畸形路径 → 500 `RequestRejectedException` = **StrictHttpFirewall 拒绝,不是绕过**。**读 500 响应体的异常类型再下结论。**
- 经 nginx 前缀 location 穿越到 `/actuator`:**单编码被 nginx 归一化**掉出前缀 → nginx 404;**双编码**活到 Spring 但被防火墙拒。**两头夹死 = 此路不通,别反复变形重试。**

## 6. 合法 client 的来源(拿不到就换路)

1. **移动端 APK/IPA** — 硬编码 `client_id`/`client_secret`,最确定。先找**版本/升级接口**(`/api/app/version`、`/api/v1/app/version`、`/api/app/upgrade`)返回下载 URL/OSS key,再下包;或从前端/落地页反查完整下载 URL。拿到包后 `jadx`/`unzip` 全局搜 `client_id`、`client_secret`、`oauth/token`、`Basic `。
2. **OSS/S3 桶**:对象**列出被拒(403 AccessDenied)但按键可读(404 NoSuchKey)** → 拿到 key 就能下;key 来自版本接口或前端拼接。
3. **`oauth_client_details` 表**(`JdbcClientDetailsService`)— 数据库可达(如 Druid 控制台泄露的连接串/账号)→ 一把读走全部 client+secret。
4. **资源服务器自身配置** — 用 RemoteTokenServices 的网关/资源服务必须持有 client-id/secret → 它的 `/actuator/env`、`/actuator/configprops`、heapdump 就是凭据来源(**前提:actuator 真开着,见 §7**)。
5. **前端 JS 通常不含凭据**(登录走后端代理)→ **别在前端 bundle 上耗时间**。

## 7. 假阳性判定(API 面测绘通用)

SPA/网关前置站常把**任意未知路径回落 `index.html`** → `/actuator/env`、`/actuator/heapdump`、`/v2/api-docs`、`/swagger-ui.html` 全返回 **200**,但 body 是同一份首页。

**判定:比响应体大小与内容,不看状态码** —— 同字节数 + `<!doctype html>` = 回落假阳性;真 actuator 是 JSON,真 swagger 是 `{"swagger":"2.0"...}`。仅当**所有路径返回同一大小**时才可判为 catch-all。

## 8. 拿到 token 之后

- 打同环境用 **RemoteTokenServices** 的资源服务器。语义判据:无 token → `Full authentication is required to access this resource`;带假 token → **`Invalid access token: x`** = 信任该授权服务器。
- **先确认授权服务器与资源服务器同环境**(跨环境 token 不通用),再投入攻 token。
- 高价值落点:任何「引擎/编排/任务」类后端(Conductor INLINE 任务、脚本任务、模板渲染、动态编译)——拿到合法 token 即等于代码执行。
