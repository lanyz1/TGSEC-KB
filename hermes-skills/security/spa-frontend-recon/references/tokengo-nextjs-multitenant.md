# TokenGo 多租户 Next.js 平台侦察案例(2026-08)

## 目标画像

```
主平台: tokengo.love "TokenGo" — AI 模型 API 网关 + 多租户 SaaS(Cloudflare)
├── wy6688.token6688.com "云映AI" (TencentEdgeOne)
├── pix.token6688.com "PIX" (TencentEdgeOne)
├── admin/app/billing/reseller 子域 (同代码库)
└── api.tokengo.love "TokenGo API Gateway" (124.156.98.229, 腾讯云)

独立站: aitool.globalaiopc.com "全球AI工具平台" (nginx/1.6.2, 阿里云 47.92.73.166 无CDN)
└── :8888 = "短剧工场 AI" (同服务器第二个 Next.js + FastAPI 产品)
```

## 侦察步骤记录

### 1. 三站指纹对比
- 三个目标全是 Next.js(`/_next/static/chunks/`),`X-Powered-By: Next.js`(ai-tool)或 NextAuth cookie(wy6688/pix)
- **wy6688 和 pix 的 main-app chunk 哈希完全一致**(`59757db288e4ffd8`)= 同一代码库多品牌部署
- ai-tool 用不同 chunk(`main-app-027acf4ff61e49a7`)= 独立应用
- 页面是 SPA 骨架,无 `__NEXT_DATA__`,API 全在 JS chunk

### 2. 前端 JS 批量提取
- 下载 index.html 所有 `/_next/static/chunks/*.js`(54 个,2.5MB)
- 主 chunk(main-app-*.js)只是 webpack 引导(466B),业务代码在懒加载 chunk
- 22443.js = API 客户端核心,泄露:
  - 认证: `/api/auth/session` 拿 accessToken, Bearer 认证, cookie `session-token`
  - **impersonation 头**: cookie `impersonate_user_id` → `X-Impersonate-User-ID`;`impersonate_reseller_id` → `X-Impersonate-Reseller-ID`(叠加在 /api/v1/* 请求)
  - 子账户体系: `SUB_ACCOUNT_NO_DELETE` 错误 = 主/子账号权限模型
  - 产品代号 "omniforge"(localStorage key `omniforge.workspace.task-history`)
- 19865.js = 业务调用层,提取 130+ API 端点:
  - `/api/v1/billing/*` 充值/余额/交易/兑换/团队分配
  - `/api/v1/reseller/*` 经销商佣金/提现/客户/下游/加盟(50+ 端点)
  - `/api/v1/promoter/*` 推广者提现
  - `/api/v1/upload/*` presign/commit 上传
  - `/api/v1/admin/*` 配置/签到/经销商管理/自定义域名
  - `/api/v1/model-runtime/invoke` 模型调用
  - `/api/v1/users/me/*` 用户资料/邮箱/手机/密码

### 3. 认证架构(NextAuth)
- `/api/auth/providers` 返回: google(oidc) / github(oauth) / phone-otp(credentials) / credentials
- **signinUrl/callbackUrl 指向 tokengo.love**(主认证域,子站是租户)
- 登录页 RSC payload(i18n 文案)泄露:
  - "手机号首次登录自动创建账号"(phone-otp 自动注册)
  - `signupDisabled: false`(注册开放)
  - "管理后台"/"API 密钥"/"代理商中心" 功能存在
  - 表单字段: email/password(≥8)/confirmPassword/phone(可选)/otpCode(6位可选)
  - 错误文案: emailExists(邮箱枚举)/phoneExists/phoneOtpRateLimited
- `/api/auth/signup` 400,注册走 **Next.js Server Action**(JS 里 `createServerReference("40e019d389ee1fc25690a866ac395eff78a7b7b3e8",...,"signupAction")`)

### 4. Server Action 调用尝试
```
POST /en/signup
Next-Action: 40e019d389ee1fc25690a866ac395eff78a7b7b3e8
Content-Type: text/plain;charset=UTF-8
Accept: text/x-component
Body: JSON 序列化参数
```
- body=`["email","pass"]` → `error: passwordTooShort`(参数结构错)
- body=`{"email":..,"password":..,"confirmPassword":..}` → `error: signupFailed`(参数签名对,进入真实逻辑)
- signupFailed 原因未确认(可能是 React 19 `$K` 引用编码差异,或需要手机 OTP)
- **结论**: 参数签名判定的方法有效(passwordTooShort vs signupFailed),但完整注册优先用真实浏览器填表

### 5. API Gateway(api.tokengo.love)
- 根路径: `{"compatibility":["openai","responses"],"documentation":"/docs","models":"/v1/models","name":"TokenGo API Gateway","object":"api_info","status":"ok"}`
- `/health` → `{"status":"ok","service":"gateway","version":"cc92011fc1"}`(泄露版本)
- `/v1/models`、`/v1/chat/completions`、`/v1/dashboard/billing/subscription`、`/docs` 全需 Bearer key
- 错误区分: `missing_api_key`(无 key) vs `invalid_api_key`(key 格式对但无效)→ 枚举 key 存在性
- OpenAI 兼容 = 标准 API key 体系,可尝试 key 申请/免费额度面

### 6. 源站直连(ai-tool,无 CDN)
- DNS: `aitool.globalaiopc.com → 47.92.73.166`(阿里云,无 CF/EdgeOne)→ 直接全端口扫
- :80 nginx 默认页 / :443 Next.js / **:8888 独立 HTTPS = "短剧工场 AI"**(第二个产品!)
- 8888 的 FastAPI 返回 `{"detail":"Not found"}`(小写 n)= 独立后端(区别于 Next.js HTML 404)
- robots.txt 泄露: `/admin/`、`/login`、`/register`、`/sso-callback`、`/*?conversation=`
- `/login` 200(独立登录页),`/admin` 404(Next.js SPA 回退假象)
- 短剧工场 API: `/api/sso/brand-info`(400 "未找到对应的平台配置",用 `X-Forwarded-Host` 头指定平台标识)、`/api/storyboards/`、`/api/narration/audio/`
- brand-info 枚举平台标识未命中(标识不在域名列表)

## 未完成/待续
- 注册未打通(Server Action 编码差异)→ 需真实浏览器或 Google OAuth 登录
- 登录后测 impersonation 头越权(X-Impersonate-User-ID 叠加 token)
- 登录后测 `/api/v1/admin/config/{key}`(普通前端也能调,疑似配置读取/篡改)
- 登录后测 billing/reseller 资金面

## 可复用工具命令

```bash
# 对比 chunk 哈希判断多租户同库
curl -s <site>/ | grep -oE 'main-app-[a-f0-9]+\.js'

# NextAuth providers(认证架构)
curl -s <site>/api/auth/providers | python3 -m json.tool

# Server Action 调用
curl -s -X POST <site>/en/signup \
  -H "Next-Action: <actionId>" -H "Content-Type: text/plain;charset=UTF-8" \
  -H "Accept: text/x-component" \
  --data '{"email":"a@b.c","password":"pass1234","confirmPassword":"pass1234"}'
```
