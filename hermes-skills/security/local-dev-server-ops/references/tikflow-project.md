# TikFlow — TikTok 海外投流 SaaS 平台 (tk投流项目)

## 位置与副本
- **ACTIVE**: `C:\Users\Administrator\Desktop\touliu` (git W1–W15, 最近改动 2026-07-31)
- **STALE 副本**: `D:\Codex\touliu` (2026-06-29 旧快照, 勿改勿部署)
- 需求/运营资料: `C:\Users\Administrator\Desktop\出海\` — `touliu.txt`=需求(5条), `tk账号.txt`=养号清单, `tk一些网站.txt`=资源(白号/ID/VPN路由), 海报/素材/外链素材
- ⚠️ `D:\Codex\tiktok` 实为 Qavlixor 商城代码, 与 TikFlow 无关 (文件夹名误导)

## 技术栈
Next.js 14 (App Router) · TS · Prisma 5.22 (dev=SQLite / prod=PostgreSQL) · Tailwind+shadcn 风格 · next-intl (zh-CN/en-US 默认重定向 /zh-CN) · ECharts · exceljs · bcrypt+jose JWT · zod · react-query · vitest

## 命令 (在 Desktop\touliu)
- dev: `PORT=3001 npx next dev -p 3001` (3000 常被 Qavlixor 占用; 日志在 .claude/devserver.log)
- `npm run db:push` / `db:seed` / `npm test` (vitest) / `build` / `start`
- 种子账号: 超管 <EMAIL-REDACTED> / admin12345 · 用户 <EMAIL-REDACTED> / demo12345

## 功能
自助注册+多语言 · TikTok 账号绑定监控(粉丝/播放/点赞/评论/收藏) · 对标 dou+ 5步投流向导(目标/受众/预算/版位/确认) · 模拟投放引擎(cpmFactor, instrumentation 定时 tick) · 钱包(PayPal/USDT TRC20/Stripe Visa 真实网关, env 门控, PAYMENT_SANDBOX) · 超管控制台(用户/计划/提现管理+Excel 导出代投) · 提现人工审核(冻结→驳回退款)

## 生产 (2026-08-08 状态)
- 服务器 137.220.199.164 (Debian 12, SSH 端口 22860; 与既有站 globalcross-bordershop.com 外科式共存)
- 域名 tikforads.com + www → Let's Encrypt 证书 (到期 2026-09-08, certbot 自动续期 + nginx reload hook)
- pm2 进程 `tikflow` (PORT=3000, next start) · 运行目录 /www/wwwroot/tikflow · nginx vhost tikflow.conf (80域名→301 HTTPS, 80裸IP→反代, 443→反代)
- 更新代码: 本机 `git archive` → SFTP → 解压 → `npm ci` → `npm run build` → `pm2 restart tikflow`
- **🔴 2026-08-08 检测: 80/22/22860 TCP 通, 但 HTTP 空响应 (curl exit 52) → nginx 或 pm2 疑似挂, 需 SSH 排查; 本地 DNS 解析不到 tikforads.com (fake-ip, 非公网 DNS)**

## 待办 / 安全 (2026-08-08)
- 🔴 W15 记录 root 密码曾明文传递 → 应立即改密 / 换 SSH key 禁用密码登录
- W11–W15 改动未 commit: messages/*.json, prisma/schema.prisma, prisma/seed.ts, src/lib/engine.ts, payments 相关, DEPLOY.md (未跟踪)
- 支付仍为沙箱 (未配真实 PayPal/Stripe/USDT 凭证); ENSEMBLE_API_KEY 未填 (TikTok 真实数据回退本地 mock)
- 上线前自检清单见 DEPLOY.md (JWT_SECRET/CRON_SECRET 强随机、PG 迁移、PAYMENT_SANDBOX=false、合规页法务核订)

## 已完成的里程碑 (git log)
W1 脚手架 · W2 认证 · W3 TikTok 模块 · W4 钱包支付 · W5 投流向导+引擎 · W6 管理后台 · W6b 独立控制台 · W6c 向导对标 TikTok · W7 收尾 · W8 计划丰富(详情页+ECharts+筛选+定向) · W9 设计系统升级 · W10 全站重做 · W11 下拉框+全球地区 · W12 PayPal 真实网关 · W13 USDT TRC20 链上监听 · W14 Stripe Visa · W15 部署上线+HTTPS
