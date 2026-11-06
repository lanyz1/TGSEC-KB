## 十六、修复建议

- **Synchronizer Token（首选）**：每个会话独立随机Token，服务端存储比对，Token一次性（操作成功后失效），Token随机性使用`secrets.token_urlsafe(32)`级熵
- **Token绑定三维度**：绑定Session、绑定User、绑定请求（防方法/路径切换绕过），校验放在业务操作**之前**
- **SameSite严格化**：认证Cookie设置`SameSite=Strict`（或至少`Lax`）+ `Secure` + `HttpOnly`；高价值操作场景可对Cookie使用`__Host-`前缀（禁止Domain，防子域注入）
- **双提交Cookie加固**：必须使用**签名/HMAC双提交**（而非裸比对），签名含密钥+时间戳，校验Cookie名使用`__Host-`前缀防覆盖，避免子域可写
- **Origin/Referer校验（纵深防御）**：状态改变请求校验`Origin`头（严格匹配scheme+host+port，拒绝null/缺失）；缺失时回退Referer；两者均缺失拒绝
- **Fetch Metadata策略**：对非安全方法+`Sec-Fetch-Site: cross-site`一律拒绝（.NET 11/Rails 8.2/Laravel 13原生支持或自研中间件）；注意旧浏览器/WebView无此头时的降级策略（保留Token校验）
- **CORS收敛**：禁止`Access-Control-Allow-Origin: *`+credentials组合、禁止反射任意Origin、白名单精确到子域、`Access-Control-Allow-Headers`最小化、禁止信任`null`
- **写操作禁止GET**：所有状态改变走POST/PUT/PATCH/DELETE，禁止`_method`/`X-HTTP-Method-Override`覆盖（或覆盖后仍强制Token校验）
- **关键操作二次验证**：转账/改密/改邮箱/解绑手机要求重新输入密码/OTP/2FA（防CSRF同时防XSS复用）
- **登录防护**：登录接口加CSRF防护（Login CSRF）、登录后强制轮换Session ID、支持"本设备登录确认"；OAuth严格state（随机+绑定Session+一次性）+PKCE（Proof Key for Code Exchange）
- **OAuth加固**：`redirect_uri`精确匹配注册白名单（禁止前缀/后缀/通配匹配）、code一次性且绑定client_id与PKCE、`state`必须随机且绑定Session并校验、账户绑定操作二次确认
- **WebSocket加固**：握手校验`Origin`头（拒绝跨站）、握手携带一次性Token（而非仅凭Cookie）、业务消息按用户权限校验
- **GraphQL加固**：mutation禁止GET、统一CSRF Token校验（不区分query/mutation）、禁用批量执行敏感mutation、persisted query需鉴权校验
- **Cookie属性基线**：认证Cookie一律`Secure; HttpOnly; SameSite=Strict(Lax)`；涉及第三方嵌入的Cookie单独使用`SameSite=None; Secure; Partitioned`且敏感度最低化
- **XSS根除（前置条件）**：XSS可读取Token/直接同源请求，使全部CSRF防护失效——CSP、输入输出编码、HttpOnly、SRI完整性校验
- **安全响应头**：`X-Frame-Options: DENY`/CSP frame-ancestors（防点击劫持组合）、`Referrer-Policy`、正确配置crossdomain.xml（Flash）
- **纵深防御分级**：高价值操作=Token+SameSite+二次验证；中价值=Token+SameSite；低价值=SameSite——每层独立可审计
- **监控与告警**：记录Origin/Referer异常请求、高频重复状态改变请求、异常跨站模式；将CSRF攻击特征纳入WAF与SIEM

