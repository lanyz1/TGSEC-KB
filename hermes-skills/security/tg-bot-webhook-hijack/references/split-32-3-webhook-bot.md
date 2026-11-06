## 第 3 步: Webhook/后端渗透(bot 服务端)

**伪造 update(最典型):** bot 后端若不校验 `X-Telegram-Bot-Api-Secret-Token` header(secret_token),任何人都能 POST 伪造 update JSON → 伪 from.id 冒充白名单用户执行特权命令(CVE-2026-28454 OpenClaw,CVSS 9.1;zealynx F-2026-0005 用可控 update_id 绕过反重放)。

```json
{"update_id": 999999, "message": {"message_id": 1,
  "from": {"id": 67890, "is_bot": false, "first_name": "Attacker"},
  "chat": {"id": 67890, "type": "private"}, "date": 1700000000,
  "text": "/start VALID_AUTH_CODE_HERE"}}
```
要点:先找到 webhook 端点(Swagger/路径惯例/反代配置);敏感命令只看 from.id 的 bot 必中招。

**业务洞:** SQL 注入(私密消息泄露)、callback_data 篡改、/start payload 注入(64字符,当参数打后端)、payments/Stars 回调伪造白嫖、命令拼接注入。
**管理后台** → 转 `tg-bot-backend-pentest`(测绘找面板+弱口令+路径穿越上传)。

