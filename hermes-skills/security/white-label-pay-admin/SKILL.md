---
name: white-label-pay-admin
description: "Use when white-label pay backends (worldpaypp/yudao/CF)."
version: 1.0.0
metadata:
  hermes:
    tags: [worldpaypp, yudao, white-label, payment, cloudflare, alb, tenant, origin-ip]
    related_skills: [cdn-origin-tracing, crypto-web-campaign-patterns, card-merchant-platform-pentest]
tags: [wss, 订阅, 支付网关, 盘口后台, 后台进不去, 白标支付, 跑分]
---

# 白标跑分/支付后台（worldpaypp + 芋道同机）

CF 罩住的多租户收银台 + 兄弟品牌管理端（常是芋道 yudao）同生态。源站 Host 指纹打空后，**优先兄弟品牌 admin/ALB**，不要无脑继续 CIDR。

**期望管理（写给人看的）**：CF 配得干净的站点，**网络层**源站 IP 可能整日拿不到（CIDR/证书/DNS 全 0 = 只放行 CF 回源）。业务 API 穿 CF 全通，**先打业务面**——早点向用户交底，别把一天全押在 masscan 上。**本家族已实测**：管理号可撞开（用户名=密码）并拖出全量业务数据；拿到管理 JWT 后，用 `ShopInformUrl`+`informOrders` 让服务器主动回调 → **出站 IP = 源站**（已验证，见 `references/shopinformurl-origin-capture.md`）。交底按「业务面产出 + 回调抓源站」计，别在百万级 CIDR 上死磕。

## When to load

- `webpackChunkworldpaypp` / `PlatformName` / `GBKPay`/`9MPay`/`StarPay`/`TAKAPay`
- 收银未鉴权：`/api/getSetting`、`/api/getOrder?trackingNumber=`、`/api/createOrder`（缺 `ShopUserLongId`）
- 免鉴权用户枚举：`/api/getTwoFactorAuthEnabled?userName=`（回 `UserTypeId` + 2FA 开关）；`POST /api/login` 本身就是一个 oracle —— `NoUser` / `PasswordError` / `TwoFactorAuthCodeError` / `WaitingEnable` 各有独立语义（全表见 `references/worldpaypp-login-oracle-and-cf-throttle.md`）
- 撞密撞到 `["AccessFailedCountLimit"]`（按账号锁）或 CF 边缘 `TryAgainLater` / `429 Just a moment`
- 后台 SPA：`/login/manager|shop|shopAgent`、`WAuth: Bearer`、`/api/admin/*`
- 兄弟域 cert SAN / 前端 `lucky1pay` 映射 → Aliyun ALB / 芋道 `/admin-api/`
- 响应头 `encrypt-key` + body Base64（芋道 ApiEncrypt）

## 攻击面顺序

1. **钉产品**：footer/`getSetting` 的 `PlatformName`；JS `webpackChunk*`；后台路由图。
2. **CF 侧未鉴权**：`getSetting`、收银 `getOrder`/`setOrder*`/`createOrder`（字段齐后卡真实 `ShopUserLongId`）。
3. **源站 Host 指纹**：masscan 候选 + `Host: <tenant>.root` + 指纹；**丢弃带 `CF-RAY`/`server: cloudflare` 的命中**（ISP 透明缓存假阳性）。
4. **CIDR 打空 → 兄弟白标**：cert SAN、前端 Host 特判（`lucky1pay.com`→`admin.lucky1pay.com`）、历史 DNS；解析 admin/panel → ALB/ECS。
5. **芋道管理端**：解 `encrypt-key`（前端 RSA 私钥）+ AES-ECB；`get-id-by-name` 枚租户；登录后读 `/system/tenant/white-ips`（可能直接出源站/运营出口）。
6. **登录撞开管理号后抓源站（首选，已验证）**：CIDR/证书全 0 就停扫。用管理 JWT：`getTwoFactorAuthData`→自开 2FA→`createOrder`(ShopInformUrl=接收器)→`informOrders`→读回调源 IP→`--resolve`+证书 SAN 双验。完整剧本见 `references/shopinformurl-origin-capture.md`。`admin/getProxySetting` 只在独立管理端子域存在，租户面 404，别死等。
7. **登录分流**：
   - `Content-Type: text/plain` + AES body → 常 `500 系统异常`
   - `application/json` + 明文短密码 → 常 `403 没有访问权限` = **IP 白名单**（XFF 伪造通常无效；需干净出口）
   - 密码另有 512-bit RSA（LoginForm 本地存盘用），与传输 `encrypt-key` 不是同一把。

## Pitfalls

- Host 200 + 业务指纹但仍有 `CF-RAY` ≠ 源站。
- Tor/脏出口打芋道登录必 403；别把 403 当密码错误。**但要分清两类闸**：目标**自己按 IP 做白名单**（芋道回 `403 请加白名单`）时 Tor 有害；CF **按出口 IP 计数**的登录限速（`TryAgainLater` / `429 Just a moment`）时 Tor 就是解药 —— `--socks5-hostname 127.0.0.1:9050 --proxy-user "$RANDOM:$RANDOM"` 每请求独立出口（`IsolateSOCKSAuth`），限速全失效。并发 >~15 会大量 `000`，逐请求重试。
- 区域 masscan 全 0 后继续扫 = 浪费；转兄弟 admin/ALB。
- **扫段止损阀值（百万级实测）**：云/区域 + 多国 ISP ASN 指纹累计到**百万级 IP** 仍 0，且数千词 DNS 暴力显示**全部记录在 CF 后面、无任何 DNS-only 记录** ⇒ 判定源站只放行 CF 回源，**立即停扫**，转业务/后台面。
- **大字典 Host 指纹只能用产品字节串，不能用品牌词**：宽松词（品牌名 / `PlatformName`）会被同族白标与共享主机刷成假阳性；命中带 `CF-RAY`/`server: cloudflare` 的一律是边缘。ISP 透明缓存对**任意** Host 都可能回 200。
- **探针实现：asyncio 扫大批量时会静默停滞**（0% CPU、socket 全 ESTABLISHED、进度不涨）→ 换线程池（`concurrent.futures`）版本，同一输入就能推进；长批次一律 `python3 -u` + 周期进度行。
- `get-by-website` 常 null；`get-id-by-name` 更香（大小写变体都试）。
- 同 IP 上 worldpaypp `getSetting` 与芋道 `/admin-api` 可共存（Host/路径分流）。
- **`AccessFailedCountLimit` 是按账号锁**；锁定时长 >1h。**绝不轮询“解锁”接口**——多打一发就重置计数并**续锁**（实测：号刚解锁，一发多余尝试立刻锁死）。撞密预算里，没命中就当该号已烧掉。
- **字段校验顺序 = 假阴性**：`createOrder`/LongId 探测时服务端先校 `PaymentChannelId`/`CurrencyId`，后校 `ShopUserLongId`。字段不齐直接回 `NoPaymentChannelId`，用户校验根本没跑 → “全 NoUser”不能证明 ID 不存在。
- **校验器抢跑 ≠ 突破**：芋道 `密码长度为 4-16 位` 是校验器早于白名单执行；不要误读为过了白名单。
- 芋道加密路（`text/plain`+AES）虽回 `500`，但真消息 `IP x 请加白名单` **只能从加密路拿到** → 用它确认白名单墙仍在、看自己出口 IP。
- 多租户子域共用同一 API，账号很可能全局同库 → **默认锁也是全局的**；多子域分开喷不会解锁。

## References

- `references/yudao-encrypt-tenant-whitelist.md` — 加密链、租户枚举、白名单登录、white-ips
- `references/worldpaypp-login-oracle-and-cf-throttle.md` — 登录响应 oracle 全表（含「2FA 校验先于密码」）、Tor 每请求换出口绕 CF 限速、弱口令模式（用户名=密码 / 默认 `123456`）、管理 JWT 后的拖库接口面、源站 CF-only 否定结论 + **ShopInformUrl 抓源站摘要**
- `references/shopinformurl-origin-capture.md` — **已验证**：ShopInformUrl+informOrders 回调抓出站 IP 的完整剧本、字段矩阵、错误语义、验证清单
- `references/white-label-sibling-origin-pivot.md` — CF 源站打空后的兄弟品牌枢轴
- `references/worldpay-panel-api-and-lockout.md` — 免鉴权接口/枚举原语、锁定与限速纪律、字段校验顺序假阴性

## 支付网关 WS 无认证订阅（2026-10 SKYSCRM）
- 网关入口页 JS 里直接搜 `wss://`，连上后**不鉴权**就能收到全平台订单推送（含 user_id/金额/订单号）
- 配合 `paymentGetState` 只凭订单号查询 → 订单号即凭证，无需 token；订单号递增/可预测时全量读取
- 判据：WS 握手 101 且首帧即为业务 JSON = 无鉴权；先收 30s 再判空
