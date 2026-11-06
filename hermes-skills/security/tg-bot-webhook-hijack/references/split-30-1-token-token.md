## 第 1 步: Token 挖掘(拿到 token = 拿到一切)

**格式与验证:**
```bash
# 正则: [0-9]{10}:[A-Za-z0-9_-]{35}
curl -s https://api.telegram.org/bot<TOKEN>/getMe    # 验证有效
```

**挖掘途径(按性价比):**
1. 目标站前端 JS:`curl -s https://target/_nuxt/*.js | grep -oE "[0-9]{10}:[A-Za-z0-9_-]{35}"`
2. 请求抓包:Contact/表单提交等请求里可能直接带 bot token(真实案例:公司客服 bot 被这样接管)
3. GitHub 仓库与 git history(gitleaks/trufflehog + 上述正则规则)
4. .env / docker-compose / 配置泄露:`BOT_TOKEN=`
5. 测绘引擎 body 搜索:Netlas `http.body="api.telegram.org"`;ZoomEye/Fofa `body="bot_token"` / `body="api.telegram.org"`
6. 恶意样本:VirusTotal 搜与 api.telegram.org 通信的样本,contacted URL 里 token 原文;MalwareBazaar `telegram_bot_api` YARA
7. APK:`jadx` 解包 grep token;PyInstaller bot 用 pyinstxtractor 解包后反编译 .pyc

