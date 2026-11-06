# 定制数字商品商城（/api/v2.php）

非独角模板：首页「软件商城/协议号」+ `/assets/store.js`。

## API

```
GET  /api/v2.php?action=catalog&type=BUSINESS|PERSONAL|RING|OLD&page=&size=
POST /api/v2.php?action=create_order  {product_id,quantity,buyer_tg,query_password}
POST /api/v2.php?action=check         {order_id}     # 常无密码 → CRITICAL
POST /api/v2.php?action=lookup        {buyer_tg,query_password}
POST /api/v2.php?action=claim_txid    {order_id,buyer_tg,query_password,tx_id}
POST download | machine_code | bind | resume
```

## CRITICAL：check 未授权

只传 `order_id` 若返回 ok，会泄露：

- buyer_tg
- query_password_hash（bcrypt `$2y$10$...`）
- amount / pay_address / status / claim 字段
- download_url（常 Google Drive）
- machine_code_guide（解压密码、exe 名、图文教程）

SN 格式例：`ORD` + yymmddHHMMSS + 8hex。

## 支付

- 固定 TRC20；金额带小数防尘
- body 改 amount 无效时服务端重算；qty≤0 可能夹 min
- claim_txid：64hex 可写入 claim，**不等于 PAID/发货**

## 锚点 2026-09-10 exeprog

- order.exeprog.com · 150.109.20.25
- 收款 `TKSjmC4WhMJESoDVoTnHggKL76DJtbE5sa`（与 appfilter 充值同址）
- 样例 ORD2609100823344C70ABDA；软件教程解压码 `123`；Filter_v5.6.1.exe
- 协议号最便宜档可 ~0.95U×min_qty

## 坑

- 随意 `/api/foo` 可能 SPA/HTML 回落；以 store.js 为准
- `/api/` 目录 403 正常；接口在 v2.php
