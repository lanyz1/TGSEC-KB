# 自部署开源应用案例集（2026-10）

四个目标、四条不同结论——展示“先读源码再动手”的产出与止损点。

## 1) cloudflare_temp_email（Dream Hunter）临时邮箱 — 全功能关闭

- 指纹: 页面 title `Temp Email` / `Cloudflare 临时邮件`；前端含 Turnstile + PWA；`GET /open_api/settings` 免登录暴露全部配置。
- 读源码（dreamhunter2333/cloudflare_temp_email, worker/src/）：
  - 地址登录: `POST /api/address_login`（需 ENABLE_ADDRESS_PASSWORD=true）；
  - 地址凭据 = HS256 JWT（`env.JWT_SECRET`）+ 库内校验 `address(id,name)` 存在；
  - admin 面板 = `x-admin-auth` 口令（ADMIN_PASSWORDS env）；TG 迷你应用入口（`/telegram/*`）豁免站点口令，但需 TELEGRAM_BOT_TOKEN 配置。
- 目标部署实测: 建址/注册/改密/TG 集成全关；admin 口令=自定义（模板默认 123/456/admin 全拒）→ 死，记录为“无口”。
- 保留价值: settings 里的收件域列表（他们用了哪些域做注册邮箱）。

## 2) RenewHelper（开源 CF Worker 续费台）— 单口令强

- 指纹: `<title>RenewHelper v3.8.4</title>` + `github.com/ieax/renewhelper` 链接。
- 源码关键（_worker.js 内联了全服务端！）:
  - 登录: `password === (env.AUTH_PASSWORD || "admin")` 严格相等；
  - 限速: 1/s + 100/天（键含 `cf-connecting-ip`）+ **5 错/5分 → 封 15 分**；
  - token: HS256 signed with settings 里自动生成的 jwtSecret；
  - `/api/backup` 支持 `X-Backup-Key` 备用口令（未设则关）。
- 实测: 默认 admin 先被限速吞掉（429≠拒绝，重试一次才真验）；定向词 9 个（含 Tor 换出口）全拒 → 按纪律收束。

## 3) Kite（K8s 控制台 v0.14.1）— 默认 secret 已改

- 源码: pkg/auth/oauth_manager.go —— HS256，claims `{user_id(uint), username, provider}`；middleware 验签后 `GetUserByIDCached(user_id)` **必须存在且 enabled**。
- 伪造测试: 默认 secret `kite-default-jwt-secret-key-change-in-production` + user_id=1 等 → `Invalid or expired token`；对照语义: `{"error":"user not found"}` = secret 对但用户不存在（可用作 secret 对错探针）。
- 其它面: bootstrap `/auth/setup/create_super_user`（启用前可用）、API key `Authorization: kite<key>` 分支、匿名用户开关（AnonymousUserEnabled）。
- 结论: secret 已改 + 限速锁 → 收束记录。

## 4) dev 模板默认值清单（部署者偷懒率很高）

- jeecg-boot: signatureSecret `dd05f1c5…`、密码 AES `1234567890adbcde/hjlkew`、druid stat-view 常见 jeecg/jeecg、ruoyi/123456。
- cloudflare_temp_email: `ADMIN_PASSWORDS=["123","456"]`、`PASSWORDS=["123","456"]` 在 wrangler.toml.template 注释里。
- RenewHelper: `AUTH_PASSWORD || "admin"`。
- Kite: JWT 默认值、bootstrap kubectlEnabled。
- 用法: 每个部署各试 1-3 发即停；不中即自定义，转入逻辑/加密面。
