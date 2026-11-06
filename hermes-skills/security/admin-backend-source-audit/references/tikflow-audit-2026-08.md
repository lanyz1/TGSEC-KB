# TikFlow 投流 SaaS 全量审计(2026-08)

项目:`C:\Users\Administrator\Desktop\touliu`(TikFlow — TikTok 海外投流 SaaS;Next.js 14 + Prisma SQLite + 自研 bcrypt/JWT 认证;注意 D:\Codex\touliu 是旧副本)
范围:16 个 API 路由 + lib(auth/wallet/campaign/payments/engine/admin/tiktok) + schema + middleware + cron;vitest 82/82 通过,未改代码。

## 严重
- **S1 支付 webhook 沙箱分支无鉴权 → 白嫖充值**:`src/app/api/payments/webhook/[provider]/route.ts:78-87`
  - `paypalConfigured()`/`stripeConfigured()` 为 false 时落入沙箱分支,仅凭 body `{externalRef}` 直接 `settleRecharge`,无需登录/验签。
  - 攻击链:免费注册 → `POST /api/wallet/recharge` 拿 externalRef → 不付款直接 `POST webhook` → 余额到账 → 提现。
  - 生产 `PAYMENT_SANDBOX=true`(未配凭证)时同样生效。
  - 修复:沙箱分支要求登录+订单归属校验;`NODE_ENV=production` 禁沙箱分支;`settleRecharge` 校验 `type==="RECHARGE"`(wallet.ts:81-96 目前无类型校验)。
- **S2 生产超管弱口令**:部署文档种子账号 `<EMAIL-REDACTED> / admin12345`(DEPLOY.md + W15 部署记录),知道项目即可登超管台审提现。
- **S3 禁用用户会话失效**:`src/lib/auth/session.ts:28-31` `getSession()` 只验 JWT 不查 status(34-41 的 `getCurrentUser` 才查);全部 API 路由用 `getSession()` → 管理员禁用后 JWT 7 天内仍可充值/提现/建计划。

## 中
- **M1 cron/tick 无鉴权**:`src/app/api/cron/tick/route.ts:5`(TODO 注释自认);usdt-scan / tiktok-refresh 仅在 `CRON_SECRET` 已设置时才拦(route.ts:8-11 `secret` 为空则完全公开)。
- **M2 改密后旧 JWT 仍有效 7 天**:`api/auth/change-password/route.ts:25-28` 只更新 hash,无 tokenVersion 机制。
- **M3 登录无限流/无失败锁定**:`api/auth/login/route.ts`;配合 S2 弱口令风险放大。
- **M4 注册 409 泄露账号存在性**:`api/auth/register/route.ts:24-25`(登录统一报错,注册区分,可枚举邮箱/手机号)。

## 低
- **L1** 充值订单无过期机制,PENDING 永久累积 + USDT expectedAmount 尾数永久占用(`src/lib/wallet.ts:42-56`)。
- **L2** `externalRef = CR-{ms}-{6位随机}` 同毫秒并发可碰撞(`wallet.ts:7-9`)→ 建单偶发 500。
- **L3** `api/user/profile/route.ts:20-28` 改 phone 无占用检查(@unique 冲突抛 500;恶意抢注他人手机号可阻其注册)。
- **L4** USDT 链上到账仅按金额尾数匹配、无来源地址校验(`lib/payments/tron.ts:31-58`),金额撞车会误入账到旧 PENDING 订单。
- **L5** `videoUrl` 直接进 `href`(tiktok/campaigns 页面),第三方数据源若返回 `javascript:` 链接,管理员点击可执行(无 dangerouslySetInnerHTML,低危)。

## 无问题确认项(复扫跳过)
- JWT HS256 + 强密钥门控(<16 字符拒绝启动)+ 算法白名单;IDOR 全带 userId 过滤(campaigns pause/resume/cancel、tiktok unbind、详情页);createCampaign 校验作品归属。
- 管理员 API(users/withdrawals/export)三处均校验 `session.role !== "ADMIN"` → 403;admin 页面 layout 双重校验。
- 提现状态机 approve/reject 限 REVIEWING、幂等正确;驳回必填理由;驳回退回余额同一事务原子。
- 余额 Decimal 运算 + 负数拦截;充值 settleRecharge 按 externalRef 幂等、USDT 按 chainTxHash 幂等 + 唯一约束。
- OAuth state cookie httpOnly + 回调比对(防 CSRF);无 dangerouslySetInnerHTML;_blank 均带 rel="noopener noreferrer";bcrypt cost 10;注册硬编码 role USER 无提权路径。
