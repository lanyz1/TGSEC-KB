# 数字商品商城支付回调:路由发现 / 字段探测 / 签名门判别

场景:数字商品商城(卡密 / 源码 / 账号),目标是「伪造支付成功」不付款拿货。服务端为 Laravel(自研商城脚本)。全部结论来自实测。

## 1. 路由发现 —— 先读 `robots.txt`,别盲猜

**手写 16 个 webhook 候选路径(`/webhook`、`/pix/webhook`、`/notificacao`、`/callback`…)全 404**,而真实端点明文写在 `robots.txt` 里:

```
Disallow: /pixup/callback       ← 支付回调(活)
Disallow: /suitmoney/callback   ← 第二个网关回调(活)
Disallow: /download/            ← 下载路由前缀(存在)
Disallow: /admin  /api/  /livewire/  /redirect/
```

顺序:`GET /robots.txt` + `/sitemap.xml` → 再补 SPA JS chunk / 管理台 / IDOR。

**动词区分**(判「路由是否存在」的可靠信号):
| 观察 | 含义 |
|---|---|
| `GET` 404,`POST` 400 | POST-only 路由**存在** |
| `POST` 405 | 路径存在但 method 不对 → 换 GET |
| 空 POST `{}` → 400 `{"error":"Transaction ID not found in payload."}` | 端点活着,且已在解析参数 |

## 2. 字段名用差分法确认

| 载荷 | 响应 |
|---|---|
| `{"id":"X"}` | `Transaction ID not found in payload.` |
| `{"transaction_id":"X"}` | `Invalid callback data.` ← **变了 = 字段名对了** |

错误信息变化即该字段被服务端取用。这是无副作用、极省时的探测方式。

## 3. 决定性判据:所有组合返回同一个错误 = 签名门,立刻停

把 `status / event / type / event_type / value / amount / valor / paid / pago / signature / hash / token / secret` 以及嵌套 `data.*` / `payment.*` / `pix.*` **全部组合**,分别打两个回调端点 —— **响应一字不变,恒为 `Invalid callback data.`**

→ 这不是缺字段,而是 **HMAC 签名校验**(或等效的服务端验签)。没有网关密钥无法伪造。
→ **到此停止,不要再堆字段、不要试编码变体。**「响应完全相同」就是签名门的确诊证据。

(对照:若某组合让响应变成「订单不存在 / 参数缺失」,那说明签名过了,才值得继续。)

## 4. transaction_id 从支付载荷本身取,不要猜

成功下单后,PIX EMV 载荷直接暴露真实网关与账单 id:

```
00020101021226640014br.gov.bcb.pix2542pix.magenpay.io/cob/Lqs1v6j0Q2a7aM4l_TQIgA
5924NXP GAMING SOLUTION LTDA   6005CUITE   62070503***
```

| EMV 字段 | 含义 | 用途 |
|---|---|---|
| 26 → URL | **真实网关域名** | 本例 `pix.magenpay.io`,而代码里自称 "PixUp" → **网关身份错位,别信代码文案/注释** |
| URL 里的 `/cob/<id>` | 账单对象 id | **transaction_id 首选候选** |
| 59 / 60 | 商户法人名 / 城市 | **可直接查 CNPJ 反查运营方实名与关联站** |
| 62-05-03 | txid | 若为 `***` = 被掩码,仍用上面那个 charge id |

## 5. 拿到有效订单 / transaction_id 之前的现实拦路石

- **网关单笔限额**:`LIMIT_EXCEEDED` + `"details":{"reason":"Valor excede o limite por operação."}`
  = **单笔金额超上限**,**不是**商户额度用尽。→ 换更便宜的商品(本例 R$1500 失败、R$200 成功)。
- **购物车清不掉**:反复加购会累积数量 → 总价超限且删除表单打不动。
  → **注册一个新账号,新账号购物车天然为空**,比跟删除表单较劲快得多。
- **先确认履约方式**:商品页若写「人工 WhatsApp 发货」,即使伪造出 paid 状态也拿不到货。
  → **先看履约环节,再决定投不投入伪造。**
- 部分商品页根本不给购物车(只有「WhatsApp 联系」),这类无端点可打。

## 6. 前置条件:Laravel 整页缓存导致全站 419

CSRF 过不去就碰不到回调。见 `webapp-security-audit` 的
`references/stateful-session-and-framework-triage.md`:`/sanctum/csrf-cookie` + `X-XSRF-TOKEN` 头、
body 不带 `_token`、客户端用 `requests.Session()`。

## 7. 战果判读(避免过度宣称)

- 「端点活着 + 字段名对了 + 下单链跑通」**不等于**「伪造成功」。签名门未破就是未破,如实说。
- 交付时把「已实证」与「未达成」分开写:本类目标常见结果就是**端点确证 + 签名挡住**,
  这本身是有价值的结论(可为后续找密钥 / 换攻击面定向)。
- 顺带产出(真网关身份、商户法人实体、charge id、履约 WhatsApp)往往比原目标更值钱,别漏记。
