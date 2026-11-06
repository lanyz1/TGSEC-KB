# 支付平台后台渗透 (merchant/agent portal pentest)

Fortis-Pay / qixinpay(启新支付) 类支付聚合平台：商户后台 + 网关 API + 超管后台，目标从商户权限越权到 admin。区别于上游网关凭据验证（PayPal/Epay），这里是打平台自身的基础设施。

## 架构（四子域一台机器）
- `user.<domain>` — 商户/代理 Vue SPA 前端
- `u.<domain>` — 后端 API（真正 JSON 接口所在，**不是前端 host**）
- `api.<domain>` — 网关 API（MD5 签名）
- `admin.<domain>` — 超管后台

## Step 1 — 从 SPA bundle 读后端 baseURL（最高价值第一步，别瞎猜）

前端 bundle 硬编码了一个从 `window.location.hostname` 推导 API host 的函数：
```js
if (e.startsWith("user."))  return "https://u." + e.substring(5) + port;   // user.X → u.X
if (e.startsWith("admin.")) return "https://u." + e.substring(6) + port;   // admin.X → u.X
return "https://api.jingyupay.cc";  // 硬编码 fallback = 另一个兄弟平台的 API
```
grep bundle 的 `baseURL`、`startsWith("user.")`、`startsWith("admin.")`、以及字面量 fallback URL。这一个函数同时暴露：真实后端 host（`u.<domain>`）、确认存在 `admin.` 子域、泄露一个 fallback 域名（常是兄弟平台 → 可作横向 pivot）。

**陷阱：** 在前端 host 上扫 `/view/*.json` 或后端路径只会得到 `200 + index.html`（SPA fallback），永远到不了真 JSON。只有先发现 `u.<domain>` 才能打真接口。

## Step 2 — OAuth2 password-grant 登录（client_id/secret 是公开的）

- GET `/getClientInfo`（无鉴权）→ `{client_id, client_secret, web_title}`。这对值随 SPA 下发，是登录 grant 的必填参数，无需猜测。
- GET `/loginCaptcha` → `{token, image:"data:image/png;base64,..."}`。
- POST `/login` `{username, password, code, captcha_token, captcha_code, client_id, client_secret, grant_type:"password"}` → `{access_token, refresh_token, type}`（type 区分商户/admin）。

登录参数里 `code` 与 `captcha_code` 并存——两个字段名不同，从登录 JS 的 `JSON.stringify({...})` 读准（见 captcha-bypass-automation.md 的字段名陷阱）。

**验证码 OCR（带灰色干扰线的图）：** 全局阈值 `x<128→黑` 会把灰色干扰线（灰度 112-175）和深色字符（<100）混在一起，tesseract 整图 `--psm 7` 返回垃圾（"UST"/"ue"）。改用：先看灰度直方图分桶 → 只按字符带二值化（`x<100→黑`，其余白）→ 垂直投影按零游程切字符（丢弃 <4px 噪声）→ 逐字符 `--psm 10` + 6× 放大 + 白边 + 白名单 `0-9a-zA-Z`。整图 `--psm 7` 失败的同张图，逐字符分割后首试即登录成功。

## Step 3 — getUserInfo 明文泄露整个权限模型（这就是提权地图）

鉴权后 `GET /getUserInfo` 返回：`role_id`（商户=8，admin=1/0）、`payout_enabled`、`collect_enabled`、`is_drawing`、`token`（= 商户的 MD5 网关签名密钥，**明文返回**）、`safetycode`、`df_balance`。

- `role_id` → 垂直提权目标（任何 profile-update / 角色接口的 IDOR 或参数篡改）。
- `collect_enabled=0` → 解释了网关每个 method 都报 `该商户代收功能已关闭`：签名是有效的，但能力开关在业务逻辑之前就把所有调用挡了。别在签名上死磕，先看开关。
- `token` 明文 = 直接拿到的签名密钥，可用于伪造该商户的网关请求。

## Step 4 — 网关 API（与 XxPay 相同的 MD5 签名）

`api.<domain>/api/gateway`，method 有 `topay`/`orderQuery`/`balanceQuery`/`rateQuery`，`return_type=json`。签名 = `strtoupper(md5(ksort(k=v&k=v&) + "key=KEY"))`，只对文档标「参与签名」的字段（`user_id`/`order_id`/`order_amount`/`pay_type`/`return_url`/`notify_url`；`method`/`sign_type`/`return_type` 不参与）。

先验证签名被接受（返回「签名失败」才是签名错），再判断错误是否来自能力开关。

## 提权路径（已验证前置，未走到终点时按此续）

1. 枚举后端完整 API（`/index/statis`、`/bankcard/list` 等已确认存在——路径存在但需鉴权/数据的接口会返回业务错误而非 40001）。
2. 打 `role_id` 越权：找任何能改自身 profile / 角色的接口，尝试把 role_id 从 8 改 1。
3. IDOR：改 `id`/`user_id` 参数看他人商户数据。
4. 探测 `admin.<domain>` 超管后台登录 + 未授权接口。

## Spring Boot 商户后台变体（sompay.co 模式）

Cloudflare + Vue.js SPA + Spring Boot（Java）+ Druid，多品牌支付商户后台（sompay/betixpay/f2pay/raajapay）。区别于 Fortis-Pay 的 OAuth2/nginx——这里后端是 Spring Boot，登录字段结构按角色不同。

### 侦察链（同 Fortis-Pay 第 1 步，但字段不同）
- 主 bundle `baseURL=/dev-api`，登录 `POST /dev-api/api/anon/auth/validate`。
- **登录字段按角色不同**：商户后台 `{merchantId, account, password, googleCode}`；admin/agent 后台 `{account, password, googleCode}`（无 merchantId）。各子域自己的 bundle 是另一份，分别读准（admin-dev/agent-dev 的登录 JS 字段与商户不同）。
- **password 是 base64**（前端 `btoa(password)`，后端 decode 后校验）；googleCode 是 Google Authenticator 6 位 TOTP。响应 `{code,msg,sign,traceId}` 里 `sign` 暗示网关层有签名，但商户登录本身不验签。

### crt.sh 子域枚举 → dev/QA 是软肋
`crt.sh/?q=<domain>&output=json` 反查泄露 `api.` / `admin-dev.` / `admin-qaqez.` / `agent-dev.` / `job-dev.` / `merchant-dev.` / `dev.` / `web.` 全套子域。admin-dev 的 bundle 泄露完整管理端 `/api/operate/*`（货币/商户/客服/支付通道/交易查询），虽需 admin token，但端点清单即越权地图。dev/QA 子域防护常比生产松，优先打。

### 后端指纹
- `api.<domain>` 根路径返 Spring Boot 默认 404 JSON `{timestamp,status,error,path}` → 确认 Java。
- 429 错误页泄露反代 `nginx/1.18.0 (Ubuntu)` 版本。
- 登录空字段报错泄露 Bean 字段路径（`{merchant.user.password_require}` 等，见 web-error-oracles）。

### 登录后端点（chunk 分析）
主 bundle 里 `import("./xxx.js")` 列出登录后懒加载 chunk（TradePanel/pay-two/createLink/usdtDeposit/withdrawForm/addMember/modifPassword/upi/bankTransfer...）。下载这些 chunk 提取登录后 API：**`/dev-api/comm/upload`（文件上传=RCE 正主）**、`/api/merchant/settlement/topUp/{create,open,submit}`（充值=印钞测试点）、`/api/merchant/settlement/withdraw/{create,open,submit}`（提现）——全部 401 需 token，但端点清单定了登录后主攻面。

### 硬阻塞（别浪费精力）
- validate 统一返 `"Please check"` 防枚举 + Cloudflare Error 1015 限流封 IP，爆破不可行；账号密码未知时唯一支点是社工/泄露库/默认字典。
- 反序列化（`$type`）、Spring4Shell、Gateway SpEL、actuator/druid 全被 WAF/401/类型安全挡死；Nacos 部署内网无公网暴露面，劫持需先拿内网 shell/SSRF——都卡在登录这道门后。
