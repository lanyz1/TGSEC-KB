---
name: tg-bot-webhook-hijack
description: >-
 TG Bot 渗透逆向全链（5 面攻击面）：
 A 面 Token 泄露→全接管（JS 硬编码/GitHub/.env/恶意样本/测绘 body 搜）；
 B 面 Webhook 伪造（secret_token 校验缺失/CVE-2026-28454/框架差异矩阵）；
 C 面 Bot 业务逻辑（/start payload 注入/callback_data 篡改/Stars 支付伪造/IDOR）；
 D 面 恶意生态情报（C2 拦截/Stealer 逆向/Drainer 家族/聚类运营者）；
 E 面 客户端源码供应链（框架 CVE 审计/供应链投毒检测/MTProto 协议攻击）。
 含 BOLA 越权写 /admin/telegram/bot 配置、Webhook 劫持、
 Bot Token 泄露 getMe/getUpdates/setWebhook/sendMessage 接管、
 伪造 Update JSON、callback_query 伪造、Fatal Error 行号溯源、
 ANY.RUN 拦截方法论、PyInstaller 解包、JS 反混淆、供应链投毒、
 matkap 猎杀面板、Netlas/FOFA body 搜 token。
 用户提到：TG bot 越权/渗透/逆向、admin/telegram/bot、webhook 劫持、
 Bot Token 泄露、JS 硬编码 bot token、getMe 验证、getUpdates 读消息、
 setWebhook 覆盖、无签名校验伪造 Update、callback_query 伪造、
 token 接管、bot 拦截、stealer bot、drainer bot、供应链投毒 bot、
 matkap、pyronut、CVE-2026-28454、Bot API、Telegram Bot 渗透时使用。
 Mini App/initData 走 telegram-webapp-api-pentest；
 管理后台 NEXTAUTH 走 tg-bot-nextauth-takeover；
 Bot 池/群发面板走 tg-bot-pool-panel-pentest。
version: 3.1.0

---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='tg-bot-webhook-hijack', file_path='references/full.md')`

# TG Bot 渗透逆向全链（5 面攻击面）

**前提**：目标在 `config/scope*.json`。`--set-webhook --confirm` 会中断原通知流 → **先问**或用测试 bot。

<!-- split-index -->

## Section index

- [攻击面全景](references/split-01-section.md)
- [成功口径](references/split-02-section.md)
- [A 面：Token 泄露 → 全接管（最高频入口）](references/split-03-a-token.md)
- [B 面：Webhook/后端攻击](references/split-04-b-webhook.md)
- [C 面：Bot 业务逻辑漏洞](references/split-05-c-bot.md)
- [D 面：恶意生态情报利用（C2/Stealer/Drainer）](references/split-06-d-c2-stealer-drainer.md)
- [E 面：客户端/源码/供应链](references/split-07-e.md)
- [工具链速查](references/split-08-section.md)
- [强制行为](references/split-09-section.md)
- [实战流程（浓缩）](references/split-10-section.md)
- [关联技能](references/split-11-section.md)
- [真源](references/split-12-section.md)
- [何时使用](references/split-13-section.md)
- [第 1 步: 空间测绘语法找 Bot 后台(搜代替扫)](references/split-14-1-bot.md)
- [第 2 步: 手动弱口令(先手动后字典)](references/split-15-2.md)
- [第 3 步: Bot Token 接管(拿到 token = 全接管)](references/split-16-3-bot-token-token.md)
- [第 4 步: 路径穿越 + Vue 头像上传 getshell](references/split-17-4-vue-getshell.md)
- [第 5 步: 渗透思维链(比 Payload 重要)](references/split-18-5-payload.md)
- [关联](references/split-19-section.md)
- [触发](references/split-20-section.md)
- [第 1 步: 摸清目标家族(静态侦察)](references/split-21-1.md)
- [第 2 步: 接管 TG 会话(指纹浏览器 CDP 最快)](references/split-22-2-tg-cdp.md)
- [第 3 步: TG Web K 版驱动要点(大量实测坑)](references/split-23-3-tg-web-k.md)
- [第 4 步: bot 消息层情报收割](references/split-24-4-bot.md)
- [第 5 步: 商户 API 网关测试(HMAC-SHA256)](references/split-25-5-api-hmac-sha256.md)
- [第 6 步: 安全面测试 + 风控识别](references/split-26-6.md)
- [Pitfalls](references/split-27-pitfalls.md)
- [关联](references/split-28-section.md)
- [何时使用](references/split-29-section.md)
- [第 1 步: Token 挖掘(拿到 token = 拿到一切)](references/split-30-1-token-token.md)
- [第 2 步: Token 接管链(控制权)](references/split-31-2-token.md)
- [第 3 步: Webhook/后端渗透(bot 服务端)](references/split-32-3-webhook-bot.md)
- [第 4 步: 客户端/恶意样本逆向](references/split-33-4.md)
- [第 5 步: 情报聚类与归属(恶意 bot)](references/split-34-5-bot.md)
- [关联](references/split-35-section.md)
- [When to Use](references/split-36-when-to-use.md)
- [A 面: Token 泄露 → 全接管(最高频)](references/split-37-a-token.md)
- [B 面: Webhook 后端攻击](references/split-38-b-webhook.md)
- [C 面: 云控面板认族(四族,禁止混打)](references/split-39-c.md)
- [云控平台(系统选择双应用)](references/split-40-section.md)
- [下游衔接](references/split-41-section.md)
- [完整情报](references/split-42-section.md)
