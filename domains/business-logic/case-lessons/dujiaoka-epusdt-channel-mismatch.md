# 案例课：dujiaoka 支付通道错配 → 伪造 epusdt 回调 0 元购

> 来源：报告包 pack-20261022（2026-10）· 域：business-logic

## 一句话

独角数卡 `PayController::loadGateWay` 只按 URL 里的 `payway` 加载通道、**不校验该通道是否属于本单**，于是任意待付单都能借别的通道的 `merchant_id` / `merchant_pem` / `sign`；再用泄露的 sign 反推 md5 拼接规则、伪造 `notify_url` 回调把订单打成已完成，自动发货，卡密到手。

## 链

1. `POST /create-order` 建自己的待付单，拿 `SN`
2. `GET /pay/{yipay|paysapi|vpay}/epusdt/{SN}` — 未授权，各 Pay 控制器把通道凭据拼进跳转 URL / HTML：`pid` / `uid` / `merchant_pem` / `sign`
3. 用泄露 sign 反推拼接规则：`signature = md5("amount=..&order_id=..&trade_id=.." + merchant_id)`
4. `POST /pay/epusdt/notify_url` 伪造回调 → 订单转已完成 → 触发自动发货
5. `GET /detail-order-sn/{SN}` 取卡密
6. 前台零鉴权面（顺手）：
   - `POST /search-order-by-email`（`_token` 从 `/order-search` 公开页取）查任意邮箱历史订单
   - `/detail-order-sn/{SN}`、`/check-order-status/{SN}` 无鉴权且模板无条件渲染 `info`（= 卡密本体）
7. epusdt 当签名预言机：`POST /api/v1/order/create-transaction` 用泄露 `merchant_id` 自建任意金额收款单，回 `token`（收款地址）+ `payment_url`；`/pay/checkout-counter/{trade_id}`、`/pay/check-status/{trade_id}` 同样无鉴权

## 判据

| 现象 | 含义 |
|---|---|
| 换 `payway` 后跳转页里出现该通道的 `pid`/`sign` | 通道归属未校验，实锤 |
| `notify_url` 直接 200 且订单状态变化 | 回调无签名校验或签名可自造 |
| `/detail-order-sn/{SN}` 匿名 200 且模板含卡密 | 前台零鉴权，直接薅 |

## 边界 / 坑

- dcat-admin 后台口令通常破不动（默认 + 品牌口令 3000+、密钥复用 11 变体、XFF/IP 绕过全 302、`.env`/`.git`/备份全 404、`install.lock` 在）→ **别在后台耗时间，走支付面**
- aaPanel 34205 静态文件匿名可读但动态 API 藏在 8 位随机安全入口后，1600+ 入口词零命中
- 888 端口全 403
- 回调伪造要一次性打准：金额/订单号/时间戳任一不符就废，先在本地把 md5 拼法验对

## 检查清单

- [ ] 建单后遍历所有 `payway` × `/pay/<payway>/<channel>/<SN>`
- [ ] 抓跳转页 HTML / URL 里的凭据字段
- [ ] 反推签名拼接规则（先拿已知 sign 做校验，别猜）
- [ ] 伪造 notify，观察订单状态与发货
- [ ] 顺手打 `/detail-order-sn/{SN}` 与 `/search-order-by-email`
- [ ] 用泄露 `merchant_id` 打 epusdt 原生 API 当签名预言机
