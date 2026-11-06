---
name: bot-panel-spacemapping
description: "空间测绘找TG bot/管理面板+测绘引擎登录态恢复+平台API头逆向。"
---

# Bot 面板空间测绘与平台侦察

通过空间测绘(Censys/Shodan/Fofa)批量找 TG bot 面板/管理后台,并逆向 bot 背后的博彩/支付平台 API。2026-08 实战沉淀(周氏PG电子 @zhoushipgbot → c7/AYX 平台)。

## 何时使用

- 拿到 TG bot(t.me/xxxbot)但无 token,无法直接管理
- 需要批量找 bot 管理面板(空间测绘)
- bot 背后是博彩/支付平台,需逆向其 API
- 用户提到「扫 bot 面板」「bot_token」「测绘 bot 后台」

## 第 1 步: 先扫 BOT 本体,再追背后平台(2026-08 用户纠正)

拿到 bot 后**不要直接顺着品牌/描述跳去追背后平台**(实战差点漏掉 bot 本体)。顺序:

```
1. t.me/xxxbot 页面: OG title/desc、菜单命令、外链
2. GitHub 搜 bot 用户名/token(zhoushipgbot / 品牌 + "bot")
3. 关联面板域名探测: 品牌变体 .com/.vip/.top 解析测试
4. Telegram API 无效 token 401 确认
5. 全部无果 → 才追背后平台(落地页 JS 挖平台矩阵)
```

**Bot 管理面板的真相**: TG bot 的管理接口藏在 Bot API 后面(getUpdates/getWebhookInfo),需 Bot Token 才能访问。无 token 时互联网上扫不到该 bot 的面板。所以"扫 bot 面板" = ①找 token 泄露点 ②或空间测绘找**同类** bot 面板。

## 第 2 步: Censys 空间测绘(2026-08 平台迁移)

search.censys.io 已迁移到 platform.censys.io,**legacy 语法已禁用**,必须用新平台语法:

```
# 新平台语法(实测有效):
host.services.endpoints.http.html_title:"bot" and host.services.endpoints.http.html_title:"panel"
host.services.endpoints.http.body:"bot_token"
host.services.endpoints.http.body:"telegram_bot" and host.services.endpoints.http.body:"login"
# Web Properties 版: web.endpoints.http.body:"..." ; 双查: (host...) or (web...)
# 实测: "bot"+"panel" 标题 → 853 主机 → 提取 99 IP → 6 个真 bot 面板
```

Shodan/Fofa 语法(未迁移,照旧):
```
http.title:"bot" port:443 / http.html:"bot_token"
title="Bot" && body="telegram" / body="bot_token" && port="443"
```

**Censys 登录态恢复(无需账号密码)**: 本机 `C:\Users\Administrator\chrome_censys` profile 存有效 cookies(auth_v1/search.censys.io.session.id/cf_clearance,expires 到 2090)。CDP 加载该 profile 即自动登录:
```
chrome.exe --remote-debugging-port=9227 --user-data-dir="C:\Users\Administrator\chrome_censys"
```
- cookies 在 `Default/Network/Cookies`(sqlite)。Chrome 锁定时直接复制会 WinError 32(文件被占用),别硬读——直接用 CDP 加载 profile。
- 结果页提取 IP: CDP 多次 `window.scrollBy(0,1500)` + `document.body.innerText` + 正则抓 IP(一次拿 99 候选)。

## 第 3 步: 批量验证面板 + 弱口令

批量 HTTP 探测候选 IP(80/443/8080),按标题/登录特征筛真面板:
- 标题含 bot/panel/telegram + body 含 password/login/username = 高价值
- 登录失败统一 303 跳回 / 时,**无法从状态码区分成功失败** → 需带 cookie 跟随重定向看是否进 dashboard

手动弱口令(间隔 2-3 秒): admin/admin admin/123456 admin/password root/root test/test 等;俄语站长面板改用 admin/qwerty123 等。

## 第 4 步: 平台 API 逆向(以 AYX/c7 为例, 详见 references)

```
1. 落地页 JS(xklink.js)挖平台矩阵: 8 平台 × 6 入口 = 50+ 随机 .vip 域名
2. API base 确认: 同域 /api/* (H5) 或独立端口
3. 请求头体系(缺头报"平台类型错误"而非 401 → 头是硬门槛):
   X-API-CLIENT: web | X-API-VERSION: 2.0.0 | X-API-SITE: 1001
   X-API-UUID: uuid-v4 | X-API-XXX: WASM签名 | X-API-TOKEN: 登录后
4. sec 端点返回 AES 密钥对(静态密钥, 可复刻)
5. 注册链: defaultKaptcha(验证码) → validateGeeCheckV2(极验) → register
6. 登录密码 = MD5 明文
```

**平台类型/站点 ID 是常见坑**: preInfo 等接口报"平台类型错误"时,先查 JS 默认值(platformType 默认 6)和请求头里的 X-API-SITE(站点 ID 1001),不是穷举 body 参数。

## 关联

- `references/censys-bot-panel-scan.md` — Censys 平台迁移/登录态恢复/扫描实测
- `references/ayx-c7-platform-recon.md` — AYX/c7 平台 API 头逆向细节
- 相关技能: tg-bot-backend-pentest(user-owned,含 TGSEC 弱口令/路径穿越)、white-label-casino-pentest、wasm-ws-protocol-crack
