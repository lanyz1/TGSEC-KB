# OTC Telegram USDT Trading Platform Fingerprint

目标形态：USDT/KRW OTC Telegram 交易平台（预生产环境实战案例 2026-08）。

## 架构指纹
- 域名含 `otc-preprod` / `otc` / `preprod` 前缀
- 端口：443 (nginx + Node 主站) + 3000 (Teable Airtable 类平台)
- 前端静态页面：index.html (Mini App), admin.html (后台), purchase.html (旧协作台)
- JS 文件：app.js + admin.js + purchase.js + i18n.js（全部公开）
- 认证：`x-api-key` + `x-telegram-init-data` + `x-telegram-login-data` 多头认证

## 资产面
- health 端点: `/api/v1/health` → 未授权泄露 {service, counts: trades/users/auditLogs}
- 数据文件: `/data/*.json` 全部未授权可读
- 源码: `/server/*` `/scripts/*` `/config/*` 全部未授权可读
- Teable: 开放注册 + 创建 PAT 令牌 + CORS 全开

## 业务对象
- users: 用户 + Telegram ID
- trades: 交易状态机 (quote_requested → quoted → quote_confirmed → payment_proof → fiat_confirmed → crypto_proof → completed)
- transferTasks: KRW 转账任务 (requested → finance_submitted → confirmed)
- counterparties: U商（商户）
- otcGroups / otcGroupMembers: 角色控制 (controller / finance / merchant)
- 支付: Woori/Kakao 韩元账户 + TRC20 USDT 地址

## 认证细节
- `requireApiKey`: if (!key || key === "change-me") return true → key 未设置即绕过
- Telegram init data 校验: HMAC-SHA256(WebAppData, botToken) → 需 bot token
- Telegram login data 校验: HMAC-SHA256(sha256(botToken), dataCheckString)
- 测试 token 格式: `123456:test-token`（api-smoke-test.js 中的占位符）

## 高价值数据顺序
1. users.json / tradingUsers.json（账号 + TG ID）
2. trades.json（金额 + TXID 链上可追溯）
3. paymentAccounts.json / counterparties.json（银行账号）
4. transferTasks.json / settlementEvents.json（资金流）
5. auditLogs.json（操作审计）

## 关键防御教训（乙方视角）
- static.js 使用 `path.normalize + path.relative` 防穿越（较难绕过）
- nginx 已拦截 /api/ 等路径但未拦截 /data/ /server/ /scripts/
- 修复清单：阻止源码/数据目录静态访问、关闭 Teable 公开注册、health 去敏感化