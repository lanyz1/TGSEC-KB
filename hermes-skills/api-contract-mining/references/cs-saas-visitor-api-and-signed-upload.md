# 在线客服 SaaS（OCS 式）——访客 API、会话链与签名上传链

来源：weihaicsmc.com 战役 iframe 客服栈（2026-09-25）。后端 Java/Spring Boot + Jakarta Validation，
CF 前置 + 源站 38.47.240.52，SockJS/STOMP，AWS S3 直传。全部结论均为实测。

## 1. 鉴权头与参数的取证顺序（最先做这三件事）

| 证据点 | 读出什么 | 实测值 |
|---|---|---|
| `Access-Control-Allow-Headers` 响应头 | 服务端承认的自定义头清单 | `...,Authorization,x-v-token` ⇒ 真头是 **`x-v-token`** |
| axios 响应拦截器 | 令牌字段名 + 变量 + 拼装方式 | `e.data.data.tk && (U.commonToken = e.data.data.tk, U.cid = e.data.data.cp.id)`；请求侧 `headers:{"x-v-token": K.commonToken}` |
| 调用点形状 | 参数走 query 还是 body | `post(url + formatParams(params), body)` ⇒ **query 与 body 双写** |

用错头的代价：`Authorization: Bearer` / `Token` / `token` / query `t=`/`v=` 全部回同一个
`{"code":401,"msg":"暂未登录或token已经过期"}`，看着像令牌无效，实则头名错。

> 注意：`401` 文案借了若依（RuoYi）的文风，但令牌机制**不是** 若依 JWT（这里是 32 位 hex 会话 token），别按若依的 secret 去伪造。

## 2. 网关白名单按「路径前缀」分桶 —— 枚举前缀，别做路径混淆

- 只放行 `/api/v1/v/*`（访客）与 `/api/v1/t/*`（另一个后端，响应格式不同：`{"code":404,"message":"error 1"}`）
- `/api/v1/u/*`（坐席）→ nginx **return 444**（空响应）；坐席 WS `/api/v1/u/ws` 同策略
- 路径混淆**全败**：`//`、`.`、`..;/`、`%2e`、大小写、`%00`、绝对 URI、HTTP/2、`/API/v1/` —— 前缀规则不吃这套
- **正确做法是枚举 `/api/v1/<X>/` 找被反代的前缀族**（用 POST 一发看是 JSON 还是静态 fallback），而不是试图绕
- 前端资源节点（`IP:3198/3298/3498`）**没有这层路径网关**，`adapt.js` 里 endpoint 是 base64 字符码 + `atob()` → 同源；但该节点只静态服务前端，不反代 API

## 3. 访客生命周期（顺序错了接口全 500）

```
POST /api/v1/v/init  body {cid: <应用key>}        -> tk, vid, cp.id, cst, fs
POST /api/v1/v/bc?cid=<数字>&vid=<vid>             -> agent list (ats)  ← 会话必须由它建立
POST /api/v1/v/message/send?cid=&vid=               -> 发消息（可对坐席社工）
```

- `init` 之后直接读消息 ⇒ `{"code":10005,"msg":"访客不存在"}`：**访客记录在 `bc` 时才落库**
- `bc` 的参数（`dt`=1/2、`br`=短浏览器串）**只放 body 不够**，必须 query + body 双写
- `bc` 返回 `ats[]` 坐席档（`id`、`nn`、`alId` 短码、`ar` 头像 CDN 主机 —— **新主机就是新面**）

## 4. 未授权面清单（该产品族的可复用检查表）

`companySetting/<cid>`（公司配置/多语言文案/skin）、`qn/list`（**快捷回复 = 运营真实联系方式泄漏**：任小聊/蝙蝠/旺旺商聊/55chat/Telegram）、
`message/send`、`oss/sign`、`oss/pro-sn`、`st/pre`、`gen?cid=`+`captcha?cid=`（滑块底图）、`leave/list`、`visitor/form`、`faq/record`。

**参数校验报错会白送后端结构**：故意传空/错参 → Spring `@Valid` 回 `参数检验失败` +
`["field":"cid","objectName":"leaveMessageParam","code":"NotNull"]` ⇒ **逐接口问出必填字段名与类型**（`java.lang.Long` / `java.lang.String`）。

## 5. 签名上传链（两套机制并存）

| 机制 | 端点 | 说明 |
|---|---|---|
| 自家上传签名 | `GET /api/v1/v/oss/sign`、`GET oss/pro-sn` | 回 `sn`/`et`/`ul`（上传域）/`ulw`(备用域) |
| AWS 预签名 PUT | `POST /api/v1/v/st/pre` body `{cid,pfn,cl}` | 回 `preUrl`（`X-Amz-Algorithm=AWS4-HMAC-SHA256`），签 content-length+host |

**上传真实形状（照抄，别猜）**：
- URL `https://<ul>/api/v1/f/wj/pro-tr`（`tr` 回 500，**`pro-tr` 才通**）
- **`sign` / `expTime` 放请求头**，其余进 multipart 表单：`file,cid,og,fn,fg`（+ `dir`，但服务端锁死目录，显式传即 500）
- `fn` 完全可控；黑名单**大小写不敏感**；绕过靠 `X.<黑名单扩展>.<图片扩展>`：`a.php.jpg`/`a.jsp.jpg`/`a.phtml.jpg` 全放行
- 回读 `https://<conf域>/<url>` → **Content-Type 恒 `image/jpeg`，不解析**（只作源码回读/公开可读，不是 RCE）
- `fn` 里的 `../` 是 **S3 字面 key**，不规范化 ⇒ 无穿越；`st/pre` 的 `preUrl` host 实测 PUT 回 404（不可直传）

## 6. SockJS / STOMP 手工驱动（两个必踩坑）

- 端点 = `SockJS(ADOPT.VU + "ws")` = **`/api/v1/v/ws`**；CONNECT 头带 `{x-v-token,cid,vid,aid}`
- **坑1：SockJS 要求 JSON 数组封装** —— `ws.send(json.dumps([stomp_frame]))`。发裸帧服务端回 `c[1007,""]` 直接断开
- **坑2：握手要先收 'o'** —— SockJS 先发 `o`（open），再发 CONNECT 帧，再收 `CONNECTED`；只 recv 一次会误判「没连上」
- **身份伪造**：CONNECT 里的 `vid` 被服务端**原样采纳** —— 回 `user-name:817_2049`（`<cid>_<vid>`）。可自称任意访客/坐席
- 但**坐席推送不经访客通道**（坐席订阅走 `/api/v1/u/ws`，同 444）⇒ 伪造身份能连、收不到坐席消息流；**别把「握住伪造身份」当成已接管**

## 7. 判死项（省弹药）

- 坐席 REST `/api/v1/u/*` 与坐席 WS：前缀级 444，路径混淆全败
- 上传物不解析、无路径穿越、`dir` 锁定
- `st/pre` 的 `preUrl` 不可直传（404）
- 参数强类型（`Long`/`Integer`）⇒ 该族无 SQLi 面

## 8. 复测（reliefs 案 2026-10-10）：粘性 cookie 与全局追加参数 —— `500 操作失败` 的两个真因被分离

同一产品族二次实战，把「500=参数位置错」细化为两级路由问题，修复有严格先后：

1. **粘性会话 cookie（先修这个）**：SockJS `/info` 回 `cookie_needed:true`。裸脚本客户端缺 `JSESSIONID` ⇒ 负载均衡每发请求落到不同后端 ⇒ **所有 REST 恒 500**。给**所有请求**（REST + WS 握手）挂固定 `Cookie: JSESSIONID=dummy` ⇒ 错误立刻变为 `401 暂未登录或token已经过期`（= 路由稳定了、进鉴权层）。
2. **全局追加的 `?cid=<数字公司ID>`**：axios 请求包装器（`formatParams`）给**每一个**请求 URL 追加 `cid`（源码形状 `!e.cid && U.cid && i.push("cid=" + U.cid)`，`U.cid` 来自 init 响应的 `cp.id`；**init 入参那个 32hex 是应用 key，数字 ID 必须回填**）。补上后：`bc` 回业务码 `10003 坐席离线`、`leave/list` / `conversation/history` / `qn/list` 全部 200。
3. **诊断阶梯（先分清再动手）**：`500`（粘性 cookie 缺、路由乱）→ `401 token 过期`（路由对了，查鉴权/参数）→ **业务码/200**（全通）。注意与 §3 的 `10005 访客不存在` 区分：10005 是访客生命周期顺序问题；500/401 是路由与鉴权层问题。
4. **上传签名 Header 复测**：本代上传链 `{ul}/api/v1/f/wj/tr?sign=&expTime=`（≠ §5 的 pro-tr，可能有代际差异）——**sign 放 HEADER**：放 query 回「sign 为空」；链路打通后类型黑名单回「文件黑名单」（txt 被拉黑，换 png/svg）。上传域可能是通配子域（`<随机前缀>.<域名>` 能解析、裸主域 `.in` 反而解不开）⇒ 用签名返回的 `ul` 主机，不要用 `ulw` 备用域。
