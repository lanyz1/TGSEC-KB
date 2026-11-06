## SRC 猎手补充手法

### 扫码登录 CSRF → 账户接管
- **认什么**：二维码登录流程回包有 `token`/`qr_key`；登录页吃 `?token=` 参数自动绑定会话；扫码确认接口无 CSRF Token 且 Cookie 是 `SameSite=Lax`
- **打法**：攻击者不登录拿到 qr_key/token → 构造 `https://target.com/login?token=<REDACTED> 发给受害者 → 受害者已登录状态下点击该链接（等于确认扫码）→ 攻击者端 WebSocket/轮询检测到 token 绑定成功，拿到受害者会话
- **算成**：未登录端变成对方账号，能读对方个人信息/操作
- **假点**：token 30 秒过期来不及；点开只出码不绑会话；必须真机扫码 URL 确认无效（要先验证整个流程）

### CSPT2CSRF（客户端路径穿越转 CSRF）
- **认什么**：前端 JS 从 URL/Cookie/存储取值拼成 API 路径（如 `fetch('/api/' + userInput + '/profile')`）；后端有同源敏感写接口（改密/绑定/转账）
- **打法**：构造 `userInput = ../../admin/changePassword` 让前端 fetch 命中敏感写接口。配合 POST body 控制即可跨操作 CSRF。若 Content-Type 需要 JSON，利用 `enctype="text/plain"` + `name={"key":"value","x":"` 构造合法 JSON body
- **算成**：通过路径穿越让正常业务请求变成敏感写操作，绕过 SameSite=Lax（因为是同源请求）
- **假点**：前端做了路径规范化/白名单；穿越后的 URL 404；后端校验了 Referer/Origin

### Multipart CSRF 绕过 JSON Content-Type 校验
- **认什么**：目标 API 要求 `Content-Type: application/json` 但后端框架（Spring/Express/FastAPI）同时接受 multipart 解析；有状态变更接口（改邮箱/绑手机/加管理员）
- **打法**：HTML form 用 `enctype="multipart/form-data"`，`<input name="username" value="attacker">`。如果后端同时解析 multipart 字段为 JSON 对象，则绕过了浏览器对 `application/json` 的 preflight 要求。也可用 `enctype="text/plain"` + `name={"email":"<EMAIL-REDACTED>","x":"` + `value="}` 构造合法 JSON
- **算成**：跨站表单提交成功触发状态变更（无需 CORS preflight）
- **假点**：后端严格只接受 `application/json` 并拒绝 multipart/text-plain；框架开了 CSRF 中间件

