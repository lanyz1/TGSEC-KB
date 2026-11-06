# Hyper → epusdt 柜台：无鉴权查单 + PATH_INFO 回调

独角 Hyper 接 `assimon/epusdt` 时，商户签名常拿不到；**柜台查单口常漏签**，与伪回调是两条路。

## 链

```text
POST /create-order → /bill/{SN}
GET  /pay-gateway/%252Fpay%252Fepusdt/epusdt/{SN}
     → 302 /pay/epusdt/epusdt/{SN}
柜台 HTML 扮 id="order-trade-id"（长数字 trade_id）
GET  https://GATEWAY/pay/check-status/{trade_id}        # 常无鉴权
GET  https://GATEWAY/pay/display-order-id/{trade_id}    # 回 SN + site_host
```

GATEWAY 与发卡主域可以不同（例 `www.usdtpay188.com`）。同路走发卡 CF 域可能 1006；直连 GATEWAY 主机。

## 查单响应

- `check-status` 成功：`{"status_code":200,"data":{"trade_id":"...","status":1|3}}`
  - `1` = 待付；`3` = 过期/终态（以实测为准，别当已付）
- 单不存在：`status_code=10008` 「订单不存在」
- `display-order-id` 成功：`display_order_id`（独角 SN）+ `site_host`
- 用 SN 打 `check-status` 会 10008——**只认 trade_id**

## 不要浪费的

- POST/PUT `check-status` 常 405，改不了状态
- `/api/v1/order/create-transaction|query-transaction|notify-url` 无签名统一 `401 签名认证错误`
- trade_id 长且邻近 ±几十 常空，不要当短步长枚举
- 查单 IDOR 是订单存在性/状态预言机，**不是伪回调、不是出卡**。用户口径要库/rec 时别报成接管

## PATH_INFO 回调

nginx 禁 `/pay/epusdt/notify_url`（纯 403）时：

```
GET|POST /index.php/pay/epusdt/notify_url
```

缺签/错签常回纯文本 `fail\n` = PHP 回调活。有 **`merchant_id`（API token，不是 `merchant_pem`）** 再伪签。官方 `EpusdtController`：`merchant_pem` = create-transaction **URL**；`epusdtSign($data, $payGateway->merchant_id)` = ksort 跳过空/`signature` 后 `md5(k=v&…+$signKey)`；notify 字段是 **`order_id`**（独角 SN），成功 `completedOrder` 回 `ok`。`pay_handleroute` 校验串 `pay/epusdt`（无前导 `/`）。

收银台 HTML「支付网关异常！签名认证错误」= **create-transaction 被 epusdt 401**（`merchant_id` 填错/当 URL 用），没有 `order-trade-id`——这时伪 notify 浪费回合。短数字/SN/网关 URL 当 key 一律 `fail`，别喷。

`APP_DEBUG=false` 时 POST 空体 500 只回 Nunito「Server Error」，别等 Ignition 源码。`Accept: application/json` 的 500 **没有 code_snippet**，白盒必须 HTML。apex nginx 403 时换 crt 兄弟 Host 再 POST。
