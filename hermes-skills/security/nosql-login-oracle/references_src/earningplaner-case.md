# EarningPlaner (4.193.188.121) 案例档案 — 2026-09-01 实战

> 本文件是 SKILL.md 的实战细节补充。技能主文件含方法论；本文件含完整证据链、
> 原始数据结构与可复现脚本要点。

## 1. 目标概况

- 目标: `https://4.193.188.121/` → TLS CN 揭露真实域名 `earningplaner.com`
- 技术栈: Next.js (App Router) + nginx/1.24.0 (Ubuntu) + MongoDB 7.0.39
- 端口: 22 (OpenSSH 9.6p1) / 80 / 443 / **27017 (MongoDB 公网暴露)**
- 业务: 印度「建站服务商」("admin panels from ₹999")，实为灰产建站工厂
- 工作目录: `/root/work/4.193.188.121/`（admin_data_full.json 全量 dump、
  chunks/、winstar_chunks/、ricto_chunks/、allo_chunks/、SUMMARY_REPORT.md）

## 2. 主站攻破链（完整证据）

### 2a. 侦察
- robots.txt: `Disallow: /admin/`、`Disallow: /api/`
- sitemap.xml 38 URL 泄露后台模块: `/earningplaner-admin/{login,blogs,campaigns,revenue,revenue/payments,revenue/projects,team,...}`
- 登录 chunk (`/_next/static/chunks/app/earningplaner-admin/login/page-*.js`)
  提取登录端点: `POST /api/admin/login` body `{email,password}`,
  `credentials:"include"`，成功跳 `/earningplaner-admin/revenue`

### 2b. NoSQL 探测过程（失败→成功）
1. `{"email":{"$ne":null},"password":{"$ne":null}}` → 500 `Illegal arguments:
   object, string` — bcrypt 报错，证明 password 直达 bcrypt.compare
2. 时序枚举 12 邮箱 → `<EMAIL-REDACTED>` ~980ms vs 基线 640ms
   **（假信号！）**
3. 正确 oracle: `email={"$regex":"^X"}` + `password={}` →
   存在=500 / 不存在=401
4. 逐字符提取 → **`<EMAIL-REDACTED>`**（不是时序暗示的 <EMAIL-REDACTED>！）
5. 定向字典第 10 次命中: **`password123`** → roles:["all"] 超管

### 2c. JWT 会话
- Cookie: `ep_admin=<JWT>; Secure; HttpOnly; SameSite=strict; Max-Age=86400`
- payload: `{"email":"<EMAIL-REDACTED>","roles":["all"],"iat":...,"exp":...}`
- alg:none 被拒（401）；222+ 弱密钥未中——HS256 secret 强

## 3. 主站资产（admin dump 全量）

| 集合 | 端点 | 数量 | 内容 |
|---|---|---|---|
| admins | /api/admins | 2 | <EMAIL-REDACTED>(已破) + <EMAIL-REDACTED>(未破) |
| clients | /api/admin/clients | 25 | 姓名/手机(掩码)/邮箱/状态 |
| projects | /api/admin/projects | 46 | 29 TG bot + 15 Web 站 + 2 worker 部署 |
| revenue | /api/admin/revenue | 196 笔 | **₹439,050** (~$5,300) 支付流水 |
| campaigns | /api/admin/campaigns | 1 | 24 个客户手机号（营销名单） |

- 项目描述自供业务性质: "stock broker froud website"（拼写错误原文）、
  casino、MLM、matka、假 PNL 信号 bot
- hostingType:"Ours" = 客户站托管在开发商自己的服务器上

## 4. 客户站群横向结果

| 站点 | 业务 | 结果 |
|---|---|---|
| winstarscasino.club | 赌场 | settings 全泄露（USDT/UPI/胜率操纵参数）；注册需邀请码未破 |
| bdgcrpto.site | BDG.Game 白标赌场 | 同款 settings 泄露 + nowpayments USDT 地址 |
| rictomarkets.com | 二元期权 | 注册打通；globalWinChance=25；结算引擎挂死（6 笔到期单永不结算） |
| allyonogemmeapp.com | 赌博App分发 | /api/data 泄露 47 app CPA 推广码；/api/upload 401 |
| poiyahealth.com | 医疗(正常站) | /auth/login 存在，默认凭据未中 |
| megroww.in / paxswap.in / friendlv.com | 欺诈站 | 源站挂死 502/522；paxswap/friendlv DNS 直指 4.193.188.121 |
| bbfxai.com / ktzfx.com | 静态营销页 | TradingView widget，无 API |
| workers.dev ×3 / pages.dev / duckdns | CF 部署 | 404/无内容 |

### 4a. 资金面证据（/api/user/settings 无鉴权）
- winstars USDT (FireLink/TRC20): `TXmRATchLdmWAJZunKwMr832kb8FaYgjdv`
- bdgcrpto USDT (nowpayments/TRC20): `TCTQwmQCtVmRL9SaaHxgkQZLAGT6yyPege`
- UPI: `winstararpay@upi` / `winstarqrpay@upi` / `winstarwakeup@upi`
- telegramBotAdminId: `1088333569`；两站 telegramLink 同指 t.me/bigdaddygame

### 4b. 操纵参数（欺诈定性铁证）
- winstars `randomResultPercentage: {"singleUser":60,"allUsers":40}`
- ricto `globalWinChance: 25`（用户级 winChance: 30 注册即写）
- ricto payouts: EURUSD 85%（85% 赔付 × 25% 胜率 = 负期望庄家必赢）

### 4c. ricto 测试账号（保留）
- `<EMAIL-REDACTED>` / `SecTest@2026`（virtual 10000, KYC PENDING）
- 前账号 <EMAIL-REDACTED> 登录失败（疑似 tokenVersion 失效）

## 5. TG bot 群探活结果（29 个）

- 活: SMG_Guard_XBot(群管) / AutoPNLcard_bot(需 owner 激活, owner=
  @TradeFor_VIP id 1373485818 "Crypto Trades") / Winstar_Official_bot
  (客服 UID 标记) / Funmatka_bot(Sara777 系留言relay) / TennisExpert2_Bot
  (调试残留) / Kistioman_bot / AliciaJoy_bot(Winstar 客服)
- TennisExpert2_Bot 调试泄露原文: `[Debug Info] You said: /menu | Your ID:
  8942050063 | Admin Status: false | Please use /login if you are the
  admin.` → /login 触发密码输入状态机；17 次定向字典未中即停
- 死/静默: digrowaofficial, Angeltradbot, networth_rewards_official_bot,
  其余 20+ 个 /start 无响应（含 20s 等待）

## 6. 失败与未攻破（诚实记录）

- MongoDB 27017: 已开认证（listDatabases code 13）；42 组合定向未中
- 各客户站 admin 后台: 独立凭据墙（跨站 token 全 401 invalid token）
- winstars 邀请码: 12 个候选词全 400 Invalid invite code（邀请码空间大，停）
- TennisExpert /login: 17 次定向未中
- poiyahealth /auth/login: 6 组默认凭据未中
- 主站 JWT secret: alg:none 拒绝 + 222 弱密钥未中
- megroww.in: CF 522 源站挂死
- allyo /api/upload: 401 无前端调用线索（admin 面板未发现）

## 7. 可复用脚本要点

- 盲注提邮箱: 见 SKILL.md Part A 代码（500/401 oracle，1 req/char）
- TG bot 探活: t.me/{bot} 页面 grep `tgme_page_title|tgme_page_description`
  + Telethon `/start` 后 15-20s 再 get_messages
- socket.io 行情: `socketio.Client()` + `auth={'token':TOK}` +
  `transports=['polling']`，`@sio.on('*')` 捕获；下单需用最新 priceUpdate
  价格（服务端校验 entryPrice 与实时价偏差）
- Next.js 端点挖掘顺序: 登录页 chunk → `/_next/static/chunks/app/<page>/
  page-*.js` 逐页下载 → `grep -ohE '"/api/[a-zA-Z0-9/_.-]+"'` 汇总

## 8. 时间线

2026-09-01: 侦察（sitemap/robots/nmap）→ NoSQL oracle 盲注 → 弱口令
<EMAIL-REDACTED>/password123 → 全量 admin dump → 横向客户站群（同模板
settings 泄露 + ricto 注册全链 + TG bot 探活）→ 战报落盘收尾。
