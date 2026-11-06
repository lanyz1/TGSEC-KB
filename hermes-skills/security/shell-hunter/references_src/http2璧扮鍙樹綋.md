# HTTP/2 走私变体与高级 Desync（H2.CL / H2.TE / CL.0 / CSD）

> 请求走私高级篇：HTTP/2 降级面（前端 H2 ↔ 后端 H1 的解析差异）与连接关闭类 desync。基础 CL.TE/TE.CL 见 `http-smuggling-test.md`。

## 1. H2.CL — HTTP/2 Content-Length Desync

前端与客户端讲 H2，向后端降级为 H1.1。H2 帧自带长度（frame length），但代理可能同时向后端转发 `content-length` 头。两者不一致时：**后端信 CL，前端信 H2 帧界**。

```
客户端 ──H2──> 前端代理 ──H1.1──> 后端

1. 客户端发 H2 POST：
   - H2 DATA frame 内容: "0\r\n\r\nGET /admin HTTP/1.1\r\nHost: target\r\n\r\n"
   - content-length 头: 0
2. 前端按 H2 帧读取整个 DATA 为第一个请求 body → 降级转发为 H1 POST
3. 后端看到 content-length: 0 → 认为没 body → 下一字节 "GET /admin..." 成为第二个请求
```

**测试**：POST 一个 body 为 `0\r\n\r\nGET /canary HTTP/1.1\r\nHost: target\r\nX: ` 且 CL=0，看第二个响应是否 /canary。

## 2. H2.TE — HTTP/2 Transfer-Encoding Desync

前端剥离 H2 帧语义但保留 `transfer-encoding` 头给后端，后端（H1）处理 TE 分块 → 分块长度字段可插入第二个请求。原理同 TE.CL，但触发面在 H2 明文头里塞 `transfer-encoding: chunked`。

## 3. CL.0 — 连接关闭 Desync（无头也通）

**核心**：找"不消费 body 的端点"——POST 到一个不读 body 的端点，CL 大于实际 body，剩余字节留在连接里作为下一个请求前缀。

```
Step 1: 找不消费 body 的端点（302 重定向、204、静态页应答 POST）
Step 2: 发 POST，Content-Length 大于真实 body
Step 3: 同连接发第二个请求（/canary）
Step 4: 响应是 /canary 的内容而非预期页面 → CL.0 成立
```

**候选端点**：`/redirect`（302）、`/static/*`（静态页接受 POST）、204 端点、错误处理不读 body 的页面。

## 4. Fat GET 走私

GET 带一个"假 body"（Content-Length 声明大于实际），配合不消费 body 的端点 → 下一个请求前缀。打**前向代理/未打补丁的缓存**常用。

## 5. 走私 → 缓存投毒链

```
1. CL.0/CL.TE 走私确认（canary）
2. 把走私的第二请求变成对目标页 URL 的请求 + 投毒头（X-Forwarded-Host / 恶意 body）
3. 目标页被缓存成毒化版本（带执行的脚本/带凭证窃取 JS）
4. 受害者访问毒化缓存页 → XSS/凭证窃取
```

判定：走私进缓存 = **影响所有访客的高危链**（区别于单请求走私只打自己）。

## 6. 客户端侧 Desync（CSD — Client-Side Desync）

**浏览器 → 恶意页 → 受害者浏览器行为**，浏览器作为走私发起端：
1. 恶意页让受害者浏览器对目标服务器发一个"语义不同"的请求（浏览器与服务器对 body 边界理解不一致）
2. 常见触发：`<form>` 带异常 Content-Length、fetch + 手动 CRLF、畸形 multipart
3. 服务器认为 body 没完 → 受害者后续请求成为走私前缀
4. 效果：跨站请求伪造升级（CSRF→走私）、缓存投毒、账户操作接管

**需浏览器侧可控**（XSS/已控域名/交互端点），测试面窄但影响大。

## 7. CDN/反向代理行为矩阵（选目标先对表）

| 组合 | 走私面 | 注意 |
|------|--------|------|
| Cloudflare → 源站 NGINX | H2.TE 常见（CF 剥离 H2 帧、源站信 TE） | CF 部分配置已修，先验证 |
| AWS ALB → EC2 | CL.0 常见（ALB 关闭连接语义） | ALB 对畸形 CL 有过修复历史 |
| NGINX → Tomcat/Java | TE/CL 差异 | Java 容器解析差异是经典面 |
| Varnish → 后端 | 走私→缓存投毒高价值 | Varnish 缓存键语义 |
| 自建代理链 | 每层一个解析器，差异面最大 | 逐层测 |

## 8. 测试方法论（快速验证流程）

```
1. 探测：接多个端点测 desync 信号（同一连接发两条请求，第二个响应是否异常）
   - 工具：Burp 扩展 HTTP Request Smuggler / smuggler.py
   - 手工：curl 单连接发双请求对比
2. 确认：canary 请求走私成立（第二响应 = canary）
3. 升级：走私第二请求查同队请求前缀（认证 Cookie 落入走私请求 → 越权读）
4. 缓存链：投毒目标页面（高危升级）
5. 报告：链明确（入口 → desync 类型 → 影响面）
```

**红线**：走私测试用 canary 无副作用；投毒链在授权范围内做、测完清缓存；不实际窃取/未授权访问。