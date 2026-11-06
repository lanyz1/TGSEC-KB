---
name: frontend-js-api-recon
description: "Use when 前端JS反混淆挖API攻击面：endPoint映射表/OAuth/DRF认证识别。"
version: 1.0.0
---

# 前端 SPA JS 挖 API 攻击面

从前端 JS 泄露的信息系统性枚举后端 API 攻击面。核心：一张 `endPoint` 映射表 = 完整 API 端点清单；`WWW-Authenticate` 头 = 认证方式。适合 Next.js/React/Vue SPA（含 admin 面板、云控制台、reseller API）。红线：gov 不碰、只打境外灰产/博彩。

## 1. 下载前端 JS chunk（全文 grep，别看标题）

- Next.js：从 HTML `grep -oE '/_next/static/chunks/[a-zA-Z0-9._~-]+\.js'` 提取 chunk 路径，批量 `curl` 到本地目录再 grep。
- 单 chunk 可达 1.6MB，业务端点混在框架代码里，必须全文正则搜，不能只看 `<title>` 或首屏。
- **App 下载落地页 `down.js` 挖 APK 直链**：落地页引用的 OSS 脚本 `down.js` 里直接写 `var androidLink="https://xxx.apk"; var iosLink="https://yyy"`。抓落地页 HTML 所有 `<script src>`（尤其 `*.oss-accelerate.aliyuncs.com/down.js`），curl 该 down.js 即拿 APK 直链——比猜 `/download/app.apk` 快，拿到 APK 再走逆向挖真实后端。

## 1.5 webpack 分包映射 + sourceMap：把原始源码整包抠出来（比全文 grep 高一个量级）

- **chunk URL 用的是名字，不是数字 id**：从主包运行时读映射。
```python
app = requests.get(B + "/js/app.<hash>.js").text
i = app.find('n.u=function(e){return"js/"+(')
seg = app[i:i+3000]
names  = dict(re.findall(r'(\d{1,4}):"([A-Za-z][A-Za-z0-9_]{1,30})"', seg))  # 42:"memberGrade"
hashes = dict(re.findall(r'(\d{1,4}):"([0-9a-f]{8})"', seg))                    # 42:"66012587"
# → f"{B}/js/{names[cid]}.{hashes[cid]}.js"
```
- **坑（会让整轮批量下载全 404）**：名字正则写成 `([A-Za-z0-9_]+)` 时，十六进制哈希（纯 alnum）被当成名字，配对全错。名字必须以字母开头。
- **永远多拉一个 `.js.map`**：Vue/React 生产包常把 sourcemap 一起传（`/js/<name>.<hash>.js.map`），`sourcesContent` 字段 = **原始源码全文**（含组件代码、`reactive()` 表单全字段、接口参数对象、字段中文名、枚举）。一次拿到全接口 + 参数，比反混淆强得多。
- 路由表在源码里 = 后台全部页面清单（`*/withdraw`、`*/recharge`、`*/loan` 这类财务页是价值最高的入口）。
- 请求签名密钥、算法、RSA 私钥也在这里明文躺着 —— 完整复刻流程见 `references/signed-request-forging.md`。

## 2. 挖 endpoint 映射表 + baseURL（最值钱）

- endpoint 映射表：正则 `endPoint[A-Za-z]+:"([a-z-]+)"` 一次捞出全部 API 端点名（实战 238 个），比逐条找 axios 调用快一个量级。
- baseURL：`apiUrl:"https://..."` 或 `baseURL:zC.config.apiUrl`。登录/资源端点都是「相对路径 + baseURL」拼出来的。
- 反混淆后往往有语义化函数名直接对应端点：`addBalance()`、`showPassword()`、`deviceLogin()`，函数体里就是 `this.post(...)` 的完整路径拼接。
- **先 curl `env-config.js`/`env.js`**：React/Vue 的运行时环境配置文件，泄露 `REACT_APP_API_URL`、`REACT_APP_PANEL_URL`（面板 URL，如 whpanel.com）、recaptcha site key，独立于 main.js，是免费的路标——别跳过它。
- **大 bundle 先滤框架库**：main.js 达 6.9MB 时（含 CKEditor 内联），`grep -oE '/api/(v1/)?[a-z0-9/_-]+' main.js | sort -u | grep -viE 'ck-|ckeditor'` 先滤掉 CKEditor 的 CSS/类名噪音，否则 API 端点被海量样式串淹没。

## 2.5 Next.js `data-api-prefix` + 环境响应头（Go 后端 / Telegram 平台）

- **`data-api-prefix` 属性**：Next.js 应用常在 `<body data-api-prefix="https://prod.example.cc" data-pubic-api-prefix="https://test.example.cc">` 直接写死后端 API 地址（生产+测试双环境）。grep `data-api-prefix|data-pubic-api-prefix|GO_API_PREFIX|SELF_HOSTED`。
- **`x-env`/`x-version` 响应头**：Go 后端常见，泄露运行环境（PRODUCTION/TEST）和版本号；测试环境（如 testaf）通常防护更松，先打测试环境找漏洞再横向到生产。
- **Go 后端指纹**：`x-env`/`x-version` 响应头 + `data-api-prefix` 拼 `/go/api` 前缀；Go 的 404 常是静默空 body，别当成端点不存在。
- **端点前缀用 `isGoServer` 布尔标记判断，别一个前缀试到底**：前端请求封装里 `post("/shell/transfer",{body},{isGoServer:!0})` 的 `isGoServer:!0` 表示该端点走 Go 后端（`/go/api`），无此标记走 console 后端（`/console/api`）。同一平台两种前缀并存（如 shell/transfer 在 `/go/api`，security_question 在 `/console/api`）——grep 出请求封装的 `isGoServer` 值再拼对应前缀，两个前缀都试一遍，避免误判端点不存在。
- **业务流前置条件链：用报错信息逐步推进，别卡第一层报错。** 敏感操作（转账/提现）常有一串前置条件，靠 `code` 报错一层层揭示：`transfer` 报"请先设置安全问题"→ 设完安全问题报"请先设置支付密码"→ 设完支付密码报"余额不足"。每个报错 `code`/`msg` 就是下一步入口，逐个满足前置条件直到走到真正的业务校验（余额/权限/目标合法性）——这一步能同时验证参数名、前缀、越权边界。
- **Telegram Mini App 认证**：bot 配置对象在 JS 泄露 `botId` + `username` + `authDomain`（多环境 production/staging/preview），但 bot token 不在 JS 里；伪造 initData 需要 bot token，拿不到 token 这条路走不通，转 email/Steam OAuth。
- **sitemap.xml 泄露主站真身**：别名域名背后的真实主站常从 `/sitemap.xml` 泄露，继续从主站挖 chunk。

## 3. 挖 OAuth / Firebase / 硬编码凭据

- OAuth clientId：`clientIdGoogle:"..."`、`client_id:"..."`、`loginWithInet:"...clientId=数字&callbackURL=..."`。
- Firebase 配置块：`firebaseConfig:{apiKey,authDomain,projectId,storageBucket,messagingSenderId,appId}` —— 拿到 projectId 测未授权（见 §7）。
- 硬编码 token/secret 正则：`[Aa]uthorization[:\s]*["\x60][^"\x60]{10,}`、`apiKey:"..."`、`secret:"..."`、`Bearer [A-Za-z0-9._-]{20,}`。

## 4. 识别后端框架 + 认证方式（看响应头，不靠猜）

- `curl -i` 看 `WWW-Authenticate`：`Token` = DRF TokenAuthentication（`Authorization: Token <key>`）；`Bearer` = JWT。
- 拿到 token 后**实测三种前缀** `Authorization: Bearer/JWT/Token <token>`，别只信 WWW-Authenticate——后端可能发 JWT 但只认 `JWT <token>`（`Bearer` 报 401、`Token` 报 `Invalid token`）。
- DRF 401 指纹：`{"detail":"Authentication credentials were not provided."}`。
- OPTIONS 可探视图字段，但很多视图 OPTIONS 也拦（500/需认证）——别把「OPTIONS 被拦」当「端点不存在」。
- 其他指纹：FastAPI 422 Pydantic schema 泄露、Go 200 空 body 静默丢弃、cookie session（`X-CSRF-Token` + `admin_session`）——详见 pentest-execution 的 Backend Quirks。

## 5. endpoint 值 ≠ 直接 URL（拼接逻辑坑）

- 映射表里的值（`add-balance`、`active`、`show-password`）是**相对资源前缀**的路径，不是直接 `/api/add-balance`。
- 直接 `/api/add-balance` 返回 404（Webflow「Page not found」默认页）≠ 端点不存在——只是前缀没拼对。
- 从 JS 找拼接：`addBalance(e,t){return this.post(\`${jT}/${e}/${b.endPointAddBalance}\`,t)}` 其中 `jT=/billing/wallets`、`bt=/users`、`we=/instances`。
- 完整路径例：`/billing/wallets/{id}/add-balance`、`/instances/{id}/show-password`、`/users/device-login`。

## 6. 公开端点批量枚举（过滤 404/401）

- 批量 GET 每个 endpoint，过滤两类：404 且 body 含 `Page not found`（Webflow 默认页）、401（需认证）。剩下的即公开端点。
- 公开端点多为 `get_options`/`get_price` 类，泄露配置/价格而非敏感数据——别在它们身上浪费太久，敏感端点都在认证墙后。

## 7. Firebase 未授权测试

- Storage 列文件：`GET https://firebasestorage.googleapis.com/v0/b/{projectId}.appspot.com/o/`。
- Firestore 列文档：`GET https://firestore.googleapis.com/v1/projects/{projectId}/databases/(default)/documents/`。
- 404 = 规则已锁，只有 public 才可读。

## 8. OAuth 登录端点识别（登录常≠直接 email/password API）

- signup 常公开注册（`POST /backend/api/signup`），返回 `needs_email_confirmation:true` 则后续要邮箱激活；字段注入（`is_active`/`verified`/`needs_email_confirmation:false`）通常被后端忽略。
- token 端点**下划线 vs 连字符是不同端点，都要测**：`auth/get_token`（下划线，空 body 返回 `{"email":["required"],"password":["required"]}` = 账密登录端点）；`auth/get-auth-token`（连字符，需 `code`+`code_token` = OAuth 回调产物）；`auth/get-token-google-auth`（需 Google token，假 token 返回 `Signature has expired` = Google JWT 校验）。
- **`needs_email_confirmation:true` 不拦登录**——账密登录照样返回 token，邮箱验证只挡后续敏感操作，别卡死在激活流程。
- 空 body 探字段：POST 空 `{}` 看校验错误，错误字段名即端点需要的参数（登录=email/password，激活=uid/token）。
- i18n 指纹：`ERROR_LOGIN:"Invalid username/password"` = 有账密登录；`loginWithInet`/`loginWithGoogle`/`clientId` = OAuth 重定向。

## 9. IDOR：list 端点泄露 vs detail 端点过滤

- 拿 JWT 后先打 IDOR：新注册空账户调 `domains`/`tickets` 等 list 端点，若返回别人的数据（count>0 且非自己资源）→ list 无 per-user 过滤 = 大规模 PII 泄露（姓名/手机/邮箱/身份证字段），同时把全部资源 ID 和关联员工/admin 邮箱泄出来。
- 同一资源的 detail 端点（`users/{id}`、`instances/{id}`）常带对象级权限（返回 `Not found` 而非 403）——但 list 端点已把 ID+PII 泄完，足够枚举。
- `tickets/{id}`、`domains/{id}` 的 GET 可能越权读详情；DELETE/PUT/PATCH 常 `Method not allowed`（只读 IDOR）。

## 审计要点（grep 速查）

- `endPoint[A-Za-z]+:"([a-z-]+)"` → API 端点清单
- `n.u=function(e){return"js/"+(` → webpack 分包名↔哈希映射（拼真实 chunk URL）；配套抓同名 `.js.map` 的 `sourcesContent` = 原始源码 + 全部参数
- `X-Api-Key` / `X-Api-Signature` / `X-Api-Digest` / `HmacSHA256` / `BEGIN PRIVATE KEY` → 请求签名方案与硬编码密钥（复刻见 `references/signed-request-forging.md`）
- `endPoint[A-Za-z]*[Tt]oken[A-Za-z]*:"([^"]+)"` → 全部 token/登录端点（get_token vs get-auth-token vs refresh-token，下划线/连字符都要列全）
- `apiUrl:"https://` → baseURL
- `firebaseConfig:{` → Firebase 配置 → 测 storageBucket/o、firestore
- `clientId` / `client_id` → OAuth 配置
- `curl -i ... | grep -i www-authenticate` → 认证方式（Token vs Bearer）
- 过滤公开端点：404 且 `Page not found`（Webflow 页）+ 401 都要剔除
