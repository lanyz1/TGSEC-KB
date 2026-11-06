## 攻击面全景

```
                 ┌─────────────────────────────────────────────┐
                 │  目标：一个 TG bot（或运营 bot 的整套业务）   │
                 └─────────────────────────────────────────────┘
                                   │
  ┌──────────────┬────────────────┼───────────────────┬─────────────────┐
  ▼              ▼                ▼                   ▼                 ▼
A. Token 面    B. Webhook/后端面  C. Bot 业务逻辑面   D. 生态/情报面    E. 客户端/源码面
token泄露→接管  伪造update/SSRF   命令注入/IDOR/逻辑  C2拦截/聚类       恶意样本逆向
前端JS/.env     验签缺失          /start payload     stealer家族       PyInstaller/JS
GitHub检索      secret_token      callback data      drainer家族       供应链投毒
```

