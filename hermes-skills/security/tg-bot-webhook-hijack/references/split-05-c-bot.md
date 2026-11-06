## C 面：Bot 业务逻辑漏洞

| 漏洞类型 | 原理 | 利用手法 |
|---------|------|---------|
| **身份只信 from.id** | bot 判权只看 `update.message.from.id`，不验 webhook 来源 | 伪造 update（见 B 面）或用他人真实 ID |
| **/start payload 注入** | `t.me/bot?start=<payload>` 64 字符上限 | payload 当参数传给后端：SQLi/命令注入/逻辑参数（如 `start=admin_promo` 白嫖） |
| **callback_data 篡改** | inline button 回调数据客户端可控 | 改 callback_data 触发未授权操作；枚举敏感内容 |
| **Stars 支付伪造** | 不验 `successful_payment` 真伪就发货 | 伪造支付回调白嫖数字商品（校验 `provider_payment_charge_id`） |
| **deep-link token 泄露** | 邀请/验证链接把用户标识放 start 参数 | 截获 start payload 撞出未授权态 |
| **命令/文件路径注入** | bot 后端 shell 拼接用户输入 | echo bot 模板即典型：用户文本直接插 shell → 命令注入 |
| **LLM bot prompt injection** | AI bot 把聊天内容当指令 | 泄露 system prompt/flag/密钥 |
| **SQL 注入** | bot 后端拼接查询 | 私密消息全暴露 |

```bash
# 功能枚举
# 对目标 bot 发：/start /help /admin /debug /status /config /settings
# 抓 inline query、callback、web app 按钮、Deep link 参数
# 从 bot 回包找后端 API 域名 → 转 WebApp/后台打法

# /start payload 注入测试
# t.me/target_bot?start=admin_promo
# t.me/target_bot?start='OR+1=1--
# t.me/target_bot?start=;id;

# callback_data 篡改（需抓包改 callback_query.data）
# 原始：callback_data="buy_item_123"
# 篡改：callback_data="buy_item_0" 或 "admin_panel"
```

---

