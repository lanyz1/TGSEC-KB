# Dujiao-Next 管理台 & 旧构建攻击面 (v1.2.1 实测 2026-10)

> 场景: admin.<域> 管理台 + api.<域> 前台同产品。前台 config `app_version` 字段可读 → 直接定版本。
> v1.2.1 = 2026-05-27 构建(4个月旧); 后续到 v1.4.9 修了大量安全项(typ混淆/限速/订单履约)。

## 版本指纹

- `GET /api/v1/public/config` → `app_version` 字段 = 准确构建版本(实测直出 "v1.2.1")
- 同响应还带: 注册开关/邮件验证开关/captcha scenes/payment_channels/telegram_auth
- admin SPA = `/dj.svg` + `/assets/index-*.js`

## ★ 管理台登录限速绕过 (X-Forwarded-For)

- `POST /api/v1/admin/login`  {"username":"..","password":".."}
- 默认 3 次错误 → `登录尝试过多，请在 900 秒后重试` (429)
- **绕过: 加 `X-Forwarded-For: <随机IP>` → 429 变 401** — 限速 key 用伪造 IP。
  原理: 部署 nginx 透传客户端 XFF; Go 端 trusted_proxies=127.0.0.1(同机 nginx) → 信任第一个值=伪造值。
  每次请求换 IP = 无限尝试。(v1.2.1 无防御; 新版对 key 爆炸有 10000 上限防御)
- 用户枚举: 无 oracle (用户名/密码错同一文案)。

## 已验证的"没有洞"清单 (v1.2.1 源码审计)

- 管理路由全量: login/verify-2fa 公开(限速), 其余全部挂 JWT+RBAC, 无漏挂
- 用户票(user_jwt HS256)打管理 API = 401 (两密钥分离, 无串用)
- channel API = HMAC(时间戳+签名), 需要 channel_client key; 无弱化
- guest 订单 = 必须 email+order_password 双因子 (by-order-no 单参数不泄漏)
- 管理 JWT: HS256 only + AdminID≠0 + typ=access + token_version 撤销 + token_invalid_before

## 常规面

- 注册常全开: captcha=none + email_verification=false → email+password+`agreement_accepted:true` 直接注册
- 登录: POST /api/v1/auth/login → data.token (HS256, claims: user_id/email/token_version/typ)
- 前台宝塔 nginx 1.18 Ubuntu + 后台同机 or 独立

## 工件

- 源码: github.com/dujiao-next/dujiao-next (v1.2.1 worktree + HEAD 全史对比)
- 管理前端 API 面: /api/v1/admin/{login,card-secrets,orders,payments,gift-cards/generate,api-credentials,authz/*,compliance/*,2fa/*}
