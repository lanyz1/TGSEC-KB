---
name: telegram-bot-attack-surface
description: "Use when mapping/attacking Telegram bot ecosystems."
version: 1.0.0
tags: [telegram, bot-api, osint, webhook, tg-platform]
---

# Telegram Bot API as recon & attack surface

Using (owned) bot tokens to map an org's TG estate, and probing Chinese TG-platform webhook layers. Verified on youyoulai/folktec ecosystem 2026-10.

## 1. `getChat` resolves ANY public identifier — with one working bot token

- `GET https://api.telegram.org/bot{T}/getChat?chat_id=@username` works for **any public** user/bot/channel — returns numeric `id`, name, `type`, `description`, and for channels `pinned_message` **including `caption_entities`/`entities` — `text_link` URLs often reveal support-bot links** (e.g. `t.me/uulkf1`) and official sites.
- Enumerate candidate usernames in bulk (brand + suffix patterns: `<brand>_bot`, `<brand>888_bot`, `uukf_bot`, …); misses just return `chat not found`. Maps an org's whole bot family cheaply.
- Bot `first_name`s reveal platform roles inside a family: "YouYouLai 客服（双向）" = bidirectional-bot platform's support bot; "星钥【钱包监听/USDT实时汇率…】" = wallet bot; "悠悠全球TG号铺" = TG account shop bot; channel titles like "TG云控·VB云控·数据筛选（全网招代理）" name product lines.
- Cross-link discoveries: a frontend's public config leak (`{"bidiKefu":"https://t.me/xxx_bot","channel":"https://t.me/yyy"}`) seeds the next getChat round; each round yields more links (客服1/客服2, other product channels).
- **无 token OSINT**: `t.me/s/<channel>` 直接 HTTP 抓公开帖子预览（曾从"官方机器人大全"置顶帖拿到完整 bot 花名册与新域名）；tgregister.com / tgstat 补频道元数据与成员数时间线。

## 2. Owned-token capabilities

- `getMe` — validate before claiming a token works.
- `getWebhookInfo` — reveals the **registered webhook URL** (path patterns, internal hostnames, API host). `getUpdates` empty = webhook mode (normal, not a dead bot); if non-empty it can leak queued user messages. `getUpdates` 报 `Conflict: can't use getUpdates method while webhook is active` = webhook 模式下的正常表现；**生产 bot 绝不 deleteWebhook**（会中断对方业务处理）。只读替代: getMe / getChat / getMyCommands / **getMyDescription（常泄整条服务矩阵：其它 bot、频道、客服号）**。
- **`getWebhookInfo` never returns the webhook secret** (`secret_token` is write-only on TG's side) — an unknown platform-side webhook secret is NOT recoverable from Telegram; only platform-side storage (DB/panel/logs) holds it. Don't grind the secret.
- Token regex for loot mining: `\d{8,12}:[A-Za-z0-9_-]{30,}` (46-char tokens common). Re-extract carefully — one missing character = 401. **误报「token 已被轮换」的头号来源是手敲 token**——从落盘文件程序化读取，别凭记忆重打（曾把有效 token 打成 401 误判 revoked）。

## 3. Webhook probing semantics (Chinese in-house platforms)

- Common public route: `POST {base}/api/v1/telegram/webhook/{bot_id}`; **bot_id is frequently the TG numeric bot id** (matches `telegram_bot_config.id` PK convention seen in multiple platforms).
- **Oracle:** existing bot with secret → `403 {"msg":"Webhook密钥无效"}`; non-existing → `404 {"msg":"Telegram Bot不存在"}` → sweep candidate numeric IDs gathered from getChat to find which bots live on which platform.
- Header `X-Telegram-Bot-Api-Secret-Token`; the check is strict — empty string, spaces, query params, body fields all fail. Secret ≥16 chars, configured per-bot in the panel (`webhook_secret`); a custom `webhook_path` may replace the default route (default-path sweeps then find nothing).
- If a bot's webhook has **no** secret configured, forged updates can impersonate arbitrary users to the bot. Do NOT fire forged updates at real group chat ids — the bot may reply visibly in production groups. Private fake chat ids only.
- **验证过的伪造成功判据（jeecg 家族，2026-10）**: 路线 `POST {base}/jeecg-boot/telegram/{bot_id}/webhook` + header `X-Telegram-Bot-Api-Secret-Token` → 正确 secret = **200（按真实 TG 更新处理）**，无 secret = 401。零影响复验: 伪造 update 的 chat_id 用**不存在的值**（如 -9999999999999）→ 后端绑定表查无 = 无副作用；真实群 id 绝不用。

## 4. Token/secret sources that worked

- Platform DBs read via SQLi: `telegram_bot_config` columns `token`, `secret_token`, `webhook_url`, `proxy_host/port/username/password` — secret_token + webhook_url = replay-capable forged updates for that platform's bots.
- Panel JS bundles / public config endpoints; ops-tool configs (e.g. RenewHelper notification channels hold bot tokens).
- 群管理基建表族（jeecg 实例）: `telegram_bot_bind_group(+_admin/_captcha/_keyword/_log_channel)`, `telegram_ad*`, `telegram_user*` — bind_group = 群矩阵与成员数（本例 30 群≈12 万人）、_admin = 管理员真人 ID 名册、_captcha/_keyword = 入群验证与关键词处罚风控配置。

## 5. 用户侧进攻面：TWA / Mini App initData 抓取（Web K 配方）

Bot 菜单的「网页版控制台」按钮 = `webview` 类型（Web K DOM class `reply-markup-button is-web-view`）。此类 TWA 后端以 **Telegram initData 签名**认证（`X-Telegram-Init-Data` 头；或 `POST /api/session {"initData": ...}` → Bearer）。有任意真实 TG 账号（客户小号/自有）即可自抓：

1. 无头 chromium `--headless=new --remote-debugging-port=9222`；playwright `connect_over_cdp` 接入（不用 playwright 自带浏览器）。
2. 登录 `web.telegram.org/k`：手机号（`.input-field-input` **contenteditable**）→ 验证码**从 Telethon 读 777000**（历史多条混杂，按消息时间戳挑最新）→ 2FA 密码（`input.stealthy` 是诱饵框，用 `input.input-field-input`）。
3. 打开目标 bot 会话（搜索框 `input.input-search-input`）→ 点 webview 按钮 → 过 `LAUNCH` 确认弹窗。
4. **抓 initData：playwright `page.frames` 看不到跨进程 OOPIF 的 mini-app iframe——必须原生 CDP `Target.getTargets`**：取 `type=iframe` 且 URL 含 `tgwebappdata` 的 target，解析 URL fragment 的 `tgWebAppData`。
5. 直调后端验证身份（QQ/qf 控制台、FastAPI 均实测通过）。

全细节/选择器/踩坑（asyncio 冲突、5位自动提交、时效窗口）→ `references/twa-initdata-capture-webk.md`。
**initData 只解决身份、不解决 admin**——管理端仍按服务端 role 表 403/静默丢弃。副产物：webview URL 常暴露**未入 CT 日志的新子域/新构建**（实例 `wuzi-20261006.pc28gj.cc`）。

## 6. web-bind 流：无 initData 让桌面浏览器登入 TWA 应用

`POST /web/session` → `link_code`（15位 base32，600s，可复取）+ `t.me/<Bot>?start=web_<CODE>` → **真实 TG 账号给 bot 发 `/start web_CODE`**（Telethon 一句 `send_message`）→ 浏览器 cookie 变 `linked:true`（常见 30 天），此后普通 HTTP 即可以该 TG 身份调业务 API（部分平台写接口只查绑定、不再要 initData）。反向理解即钓鱼面：**发码诱受害者点击 = 把受害者 TG 身份绑到攻击者的浏览器会话**。

## 7. Telethon 当“用户”驱动 bot 菜单（评测 TG 服务的标准动作）

- `message.click(i, j)` 点 inline callback，随后 `get_messages(limit=1)` 读**编辑后**新屏；这类 bot 多为单屏编辑式 UI（旧按钮消失）——找不到按钮时先点「返回」回主菜单再进。
- 服务菜单 = 攻击面地图：号铺分类直接泄露各分类库存量；每层文案注明文件格式与限制（S+J ZIP、≤5000 个/批 等）。
- **TG 支付机器人链**：下单深链 `t.me/OkayPayBot?start=shop_deposit--<hash>`、`t.me/kkpay?start=merchant_deposit--<hash>`（金额/商户/订单号在 bot 屏回显）；USDT 充值常配 TronScan 链上核对（「我已转账」→ 服务端查链；集成故障会回显 `TronScan HTTP 401` 之类原始错误）；最终闸门 = 支付 bot 内余额 + 转账 PIN。
- **钱包 bot 本体（OkPay/KkPay 双胞胎系）**：菜单=充值/提币/转账/收钱/红包/闪兑/余额宝/话费·星星·会员/商户/游戏中心（KkPay 另有匿名信用卡、OTC 承兑群）；实测**零余额支付=`操作失败，余额不足`（校验真实）**、USDT 充值=共享 TRC20 地址可重复充值（靠发送方地址归账）、商户创建入口被 4 位支付 PIN 拦截。细节/未测余项 → `references/pc28gj-ecosystem.md`。

## Pitfalls

- **越权结论先受控对测再定性**：这类 TWA/控制台后端上「跨用户删除/写」的可疑端点，单次 `{"ok":true}` 可能只是幂等 no-op——注册 A/B 两枚自有账号互测（A 会话打 B 的资源 id，再打一个不存在的深 id）确认作用域后才写高危（pro.pc28gj.cc 的 DELETE 实测如此从“疑似高危”修正为无洞）；测试从不存在的 id 起步，未定性前不碰真实低 id 资源。
- Do not expect user account **sessions** from Bot-API platforms — they hold bot tokens + user PII only; sessions live where tdata/Telethon `.session` land (collector accounts, S3, runtime disks).
- Channel post history is NOT readable via getChat/getUpdates unless the bot is a member — pinned message + description are the reliable free reads.
- "Bot不存在" on one platform doesn't mean the bot is unused — it may live on a sibling platform with custom webhook paths; keep the numeric-id map and test across all known endpoints.
- **借号操作纪律（客户/第三方提供的 TG session）**：先 `get_me` 验活再用。账号是「借来的真人身份」，不是弹药：不要把它上传进目标平台会**入库 session 的功能**（如群发控制台的「添加账号/健康监测/交付安全化」、挂机平台「绑定账户」）——等于把号送进对方仓库；不要启动带真实资金的引擎；不要爆破支付/转账 PIN（4 位也勿试）；Web K 登录会在对方 Devices 里留痕（可事毕清理）。支付/订单等写操作前先问自己：这一步会不会动到真钱或给对方留下可用凭据。

## Related

- FastAPI platforms that host such bots → `fastapiadmin-pentest`.
- TG session export chains → user-owned `pentest-execution` refs / `fastapi-tg-script-admin-pentest`.
- TWA initData 抓取配方（Web K + CDP）→ `references/twa-initdata-capture-webk.md`
- 「花」系 / pc28gj.cc 完整生态档案（挂机+群发控制台+号铺+支付链）→ `references/pc28gj-ecosystem.md`
- 现成脚本：`scripts/grab_twa_initdata.py`（CDP 原生扫 OOPIF 取 initData）· `scripts/tg_bot_click.py`（Telethon 按文字点 bot inline 按钮并读编辑后新屏）
