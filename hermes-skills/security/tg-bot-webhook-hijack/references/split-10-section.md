## 实战流程（浓缩）

```
① 目标确认：bot @username → /start /help 摸功能 → 抓转发链路里的后端域名
② Token 挖掘：JS/.env/GitHub/git history/测绘 body 搜/恶意样本
   → getMe 验证 → getWebhookInfo 评估动静 → 最小化利用
③ 后端渗透：webhook 伪造（无 secret_token）→ 业务洞（SQLi/IDOR/payload）
   → 管理后台走 tg-bot-nextauth-takeover / tg-bot-pool-panel-pentest
④ 逆向深化（黑产 bot）：PyInstaller/JS 反混淆/APK → token+chat_id+后端 API
   → 情报采集+聚类
⑤ 交付：复现步骤 + 利用链 + 修复建议
```

