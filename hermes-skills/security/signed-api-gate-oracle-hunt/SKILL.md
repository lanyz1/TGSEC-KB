---
name: signed-api-gate-oracle-hunt
description: Use when API gated by sign/nonce/HMAC you cannot forge. 含聚合支付/易支付网关契约逆推与配置载体定位。
---

# 签名闸 / 参数闸 API:预言机优先法

适用:目标 API 强制携带你算不出的 `sign` / `signature` / `nonce` / `timestamp`(密钥在 native/加固包、服务端 HMAC、或根本不下发)。目标是**拿会话/实例数据**,不是还原算法本身。

<!-- split-index -->

## Section index

- [§0 预检:先校服务端时钟(★在判「签名失效/nonce 已消费/TTL 过期」之前)](references/split-01-0-nonce-ttl.md)
- [决策顺序(严格按序,别跳步)](references/split-02-section.md)
- [1. 先判闸类型(一次请求定路线)](references/split-03-1.md)
- [2. 逐参喂参配方(报错即下一个参数名)](references/split-04-2.md)
- [3. 找签名预言机(★ 最高杠杆)](references/split-05-3.md)
- [4. 兄弟前端改判(签名打不动时的战略转向)](references/split-06-4.md)
- [5. 缺口收敛:同一句鉴权错 = 只剩一个实例 ID](references/split-07-5-id.md)
- [6. 挑战值/随机数往往在 cookie,不在响应体](references/split-08-6-cookie.md)
- [7. 客户端签名还原(App/native 侧)—— 静态优先](references/split-09-7-app-native.md)
- [8. Web/H5 前端签名还原 —— 密钥通常是**明牌**,先找再算](references/split-10-8-web-h5.md)
- [信封闸(请求体加密):三档错误码判据 + 自实现坑](references/split-11-section.md)
- [Pitfalls](references/split-12-pitfalls.md)
