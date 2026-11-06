---
name: oauth2-authorization-server-attack
description: "OAuth2 auth-server attacks - client_id oracle, token."
---

# OAuth2 / OIDC 授权服务器攻击

**触发词**:`oauth2`、`/oauth/token`、`/oauth/authorize`、`/oauth/token_key`、`client_id`、`NoSuchClientException`、`Invalid access token`、`Full authentication is required`、`授权服务器`、`RemoteTokenServices`、网关代理前缀带 `oauth/token/uaa/auth/as`。

**目标**:用**一个合法 client(或 token)**打开被 RemoteTokenServices 保护的资源服务器。

> 深度细节(语义矩阵 / 凭据来源 / 假阳性判定)见 `references/spring-oauth2-authserver.md`。
> 若卡在纯 CSRF 面(403 + session 型 token),配 `spring-security-csrf-bypass`;登录跳 `/oauth/authorize` 的授权码劫持走 `oauth-oidc-flow`。

## 顺序(按此推进,别跳步)

1. **定位授权服务器**:网关/微服务代理前缀里找 `oauth`/`token`/`uaa`/`auth`/`as`;子域枚举后逐个试 `GET /oauth/token`。
   - 错误体 `path` 字段 = 服务 `server.servlet.context-path` + 请求路径 → **直接读出服务名/模块名**,据命名族横向枚举同族服务。
   - 未认证 `GET /oauth/token` → 302 到 `http://<内网IP>:<port>/login` = 授权服务器,同时**泄露内网地址**(记下来供 SSRF/内网复用)。
2. **先分清 prod / preprod 的 nginx 面**:prod 可能只开前缀 location `/oauth/token*`(`/oauth/authorize` → 404 nginx),staging/preprod 常额外放出 `/oauth/authorize`、`/login`。**横向比完环境再选打法。**
   - 区分 nginx 404(HTML 带 `<center>nginx</center>`)与应用 404(JSON):被 nginx 挡 ≠ 端点不存在。
3. **★ 枚举 client_id —— 只用 `/oauth/authorize`,绝不用 `/oauth/token`**:
   ```
   GET /oauth/authorize?response_type=code&client_id=<X>&redirect_uri=/
     不存在 → 500 NoSuchClientException("OAuth2 client not found")
     存在   → 其它响应(302 → /login,或 redirect_uri 校验错)= 命中
   ```
   成因:authorize 分支在**鉴权之前**就 `loadClientByClientId()` → 无凭据即可无限枚举。
4. **拿 secret**:命中 client_id 后 ① public client(空 secret / NoOp PasswordEncoder)→ 直接走 `authorization_code` 换 token;② 否则 `/oauth/token` + HTTP Basic 爆破,成功判据 = **响应不再是 `Bad credentials`**。
5. **打资源服务器**:无 token → `Full authentication is required ...`;带假 token → `Invalid access token: <REDACTED> 被解析并送远端校验)= 该资源服务器信任这个授权服务器。
   - **先确认资源服务器与授权服务器同环境** —— prod 签发的 token 通常不被 preprod 资源服务器接受,跨环境投入必白费。
6. **落点**:任何编排/引擎/任务类后端(如 Netflix Conductor 的 INLINE 任务、脚本任务、模板渲染、动态编译)拿到合法 token 即等于代码执行。

## 铁律 / 坑(每条都是实测踩出来的)

- **GET 不受 CSRF 保护,但 GET 会改变 principal 语义** → `GET /oauth/token?...&client_id=X` 对任何 X 都返回同一条 `NoSuchClientException`:`AbstractTokenGranter.getClientId(principal)` 取的是**已认证主体名**(未登录 = `anonymousUser`),**根本不读 `client_id` 请求参数**。**这是假预言机** —— 不读异常类型就下结论会得出「枚举 N 个全无效」。**换请求方法前,先确认端点逻辑是否依赖 principal/认证主体。**
- **`/oauth/token` 的 Basic 认证不是预言机**:不存在的 client 与「存在但 secret 错」都返回 `Bad credentials`,不可区分(Spring Security OAuth2 默认行为)。别在它上面做字典。
- **500 ≠ 绕过**:畸形路径(`;`、`//`、`%252e%252e`、`;jsessionid=`)→ 500 `org.springframework.security.web.firewall.RequestRejectedException` = **StrictHttpFirewall 拒绝,不是绕过**。**必须读 500 响应体的异常类型再下结论。**
- **nginx 前缀 location 穿越两头夹死**:单编码(`..%2f`、`%2e%2e`)被 **nginx 归一化**掉出前缀 → nginx 404;双编码(`%252e%252e`)能活到 Spring 却被防火墙拒。判定此路不通后**别反复变形重试**,换面。
- **不要在前端 bundle 上找 client 凭据**:登录走后端代理(如 `/api/oauth/login`)时凭据由服务端持有,前端翻到底也没有。先判断凭据持有方,再决定去哪挖。
- **APK/IPA 是最确定的凭据来源**:先找版本/升级接口(`/api/app/version`、`/api/v1/app/version`、`/api/app/upgrade`)拿下载 URL 或 OSS key 再去下包;OSS 桶「列出 403 AccessDenied 但按键可读 404 NoSuchKey」= 只要 key 就能下。
- **`oauth_client_details` 表**(Spring `JdbcClientDetailsService`):数据库一旦可达(如 Druid 控制台泄露的连接串/账号)→ 一把读走全部 client + secret,胜过任何爆破。
- **`/oauth/token_key` 若可绕鉴权读到**:对称签名时返回的就是**共享密钥** → 直接伪造 token。
- **假阳性判定**:SPA/网关前置站常把未知路径一律回落 `index.html` → `/actuator/*`、`/v2/api-docs`、`/swagger-ui.html` 全返回 **200 且 body 字节数完全相同**。**比响应体大小/内容,不看状态码。**
- **低速单发**:授权服务器是登录命脉,高频枚举会被限速(表现为连接级失败 / 状态 0,**别误判为端点挂掉**),加 `sleep 0.2-0.5` 重试并复核一次存活。
