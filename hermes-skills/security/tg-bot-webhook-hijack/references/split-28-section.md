## 关联
- `tg-bot-pentest-reverse`: 攻击面理论 + 全网资料汇编
- `tg-bot-backend-pentest`: 打 bot 的 Web 管理后台(测绘/弱口令)
- `telegram-webapp-api-pentest` / `tg-webapp-pentest`: MiniApp initData 认证
- 实战案例细节: references/okpay-case-2026-09.md

---

<!-- 补充视角: tg-bot-pentest-reverse (兄弟技能库 2026-09-12) -->

---
name: tg-bot-pentest-reverse
description: "TG bot本体渗透逆向: token接管、webhook伪造、消息拦截、客户端逆向。触发: bot渗透。"
---

# TG Bot 本体渗透与逆向(Token 接管 / Webhook 伪造 / 拦截 / 逆向)

针对 **Telegram Bot 本身**(而非 bot 的 Web 管理后台——那是 `tg-bot-backend-pentest`)的渗透逆向打法。核心事实:**token 即全部权限**,无密码无 2FA;恶意 bot 常把 token+chat_id 硬编码在产物里。

