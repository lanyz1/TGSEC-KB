## 成功口径

| 级别 | BOLA 路径 | Token 泄露链 | Webhook 伪造链 | 业务逻辑链 |
|------|----------|-------------|---------------|-----------|
| L1 | USER 可写配置 | `getMe` 有效 | secret_token 缺失确认 | /start payload 注入 |
| L2 | 自控 URL 收到 Update | `getUpdates` 读到历史 | 伪造 update 执行命令 | callback_data 越权 |
| L3 | — | webhook 无签名可伪造 | 伪造 admin from.id 提权 | Stars 支付伪造白嫖 |
| L4 | — | 伪造 callback 触发业务 | 绑定钱包/截获清算 | — |

---

