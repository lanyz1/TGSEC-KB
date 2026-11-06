## 强制行为

1. 先用 USER Token 打 admin 路径证明越权，再谈劫持。
2. 默认 `probe` **不改** webhook；显式 `--set-webhook --confirm` 才写。
3. 授权测试结束后建议恢复原 webhook。
4. 通知/STATUS 脱敏，不把 bot token 写进可公开文档。
5. 拿到 token 先 `getWebhookInfo` 评估动静，再决定操作深度。
6. 恶意生态情报采集：只读操作（getMe/getUpdates/forwardMessage），不主动 sendMessage 冒充。

