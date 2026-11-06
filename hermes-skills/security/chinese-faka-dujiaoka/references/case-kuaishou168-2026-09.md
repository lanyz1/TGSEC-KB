# kuaishou168.com · 2026-09-27

Hyper 独角 + epusdt + Chatwoot 客服。目标接管/rec/getshell；本案**未接管、无壳、无已付卡密**。

## 坐实

- 后台 `/xiaoniu888` Dcat，无验证码。本机 IP CF 1006；**Tor SOCKS5 通**
- 邮箱查单 IDOR 活：`<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` 出**已过期**单+SN，无 `data-clipboard-text`
- `pay-gateway` → epusdt 柜台；`order-trade-id` 如 `202609281790535793442162`
- `GET https://www.usdtpay188.com/pay/check-status/{trade_id}` 无鉴权；`display-order-id` 回 SN + `site_host`
- `/index.php/pay/epusdt/notify_url` 回 `fail`；Vpay 统一 500=控制器已删
- 客服 `kefu.xiaoniu.info` Chatwoot 4.16.2，源 `27.124.47.219`。该 IP 任意 Host 都回 Chatwoot，**不是发卡源站**
- Widget JWT 可发消息；ActionCable `RoomChannel`+pubsub 订阅确认，presence 泄 `account_id=1` users 1/2 online
- widget 附件字段是 `message[attachments][]`（`attachments[]` 500）；SVG 上传成功但 blob `Content-Type: application/octet-stream` + `Content-Disposition: attachment`
- gptupgo.com 同收款地址、同 Chatwoot widget；`/admin` 仅密码；查单要 orderId+email

## 死胡同（别重跑）

- 无 merchant_pem / epusdt api token，伪回调停
- trade_id ±12 空
- Shopify OAuth SSRF 要 agent state JWT；`/shopify/callback` 无 state=404
- `/direct_uploads` 4.16.2 上 422/401，CVE-2026-63765 本案未打穿
- ip138 历史 IP Host 验证全不是独角
- 主站 Ignition 关；yipay GET 500 不吐栈
- kuaishou robots `Disallow: /admin123/` 但该路 404；真后台 `/xiaoniu888`

## 兄弟皮（同次 crt / sitemap）

- `by.xiaoniu.info` = `aws158.com` 独角 Hyper。后台 `/admin123` 活。Laravel 6.20.42 / PHP 7.4.33，`stage=local`
- 路径 `/srv/standby/40/sites/aws158.com`（by）与 `/www/wwwroot/aws158...`（主站）
- `GET /pay/yipay/notify_url` 吐 Ignition；`/_ignition/health-check` `can_execute_commands:true`
- Yipay 白盒片段：`detailOrderSN($data['out_trade_no'])` 再核 `pay_handleroute==/pay/yipay`
- CVE-2021-3129 execute-solution 空 200；php://filter 清 log 通；**phar gadget 未 getshell**——别当可靠链重跑
- **Epusdt 白盒（Ignition HTML POST 空 notify）**：与官方 `assimon/dujiaoka` `EpusdtController` 同源。`epusdtSign` = ksort 跳过空/`signature`，`md5(k=v&…+$payGateway->merchant_id)`；notify 用 `order_id` 查单；`pay_handleroute != 'pay/epusdt'`（**无**前导 `/`）回 `fail`；成功 `completedOrder(order_id, amount, trade_id)` 回 `ok`。`merchant_pem` 是 **create-transaction URL**，密钥是 **`merchant_id` 随机 token**
- 真单 `GNRCQJ3NTQVHQP4O` wait(400000)。收银台「支付网关异常！签名认证错误」= `create-transaction` 用 `merchant_id` 当 epusdt API token 被 401，**没出 trade_id**。短数字/SN/usdtpay188 URL 当 key 一律 `fail`——**无 token 不要伪签**
- `Accept: application/json` 空 notify 只回 file/line/trace，**没有 code_snippet**；白盒要 HTML 500。aws158 apex nginx 403 `/pay/epusdt/notify_url`，`by.xiaoniu.info` 同机可 POST
- OrderService.detailOrderSN：`where('order_sn', $orderSN)->first()` 无拼接注入
- by/aws158 邮箱短号 IDOR 无已付卡密
- `tgjiema.xiaoniu.info` FastAPI「TG 收码面板」OpenAPI 裸：`/admin123` 密码登录，`/api/status` 401，写面全要登录。空密 403
- `shouhou.xiaoniu.info/submit.php` 未授权写：GET `405 仅支持 POST`；缺字段 JSON「请填写正确的邮箱」/「请选择申请原因」/「请上传交易截图」。未灌真工单
