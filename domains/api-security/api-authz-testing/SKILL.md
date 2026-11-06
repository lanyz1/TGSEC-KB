---
name: api-authz-testing
description: "Use when testing API object authz, IDOR, step-up gates."
version: 0.1.0
tags: [api, idor, bola, bfla, stepup, openapi, export, authorization]
---

# API 授权测试（对象级 / 阶梯验证 / 匿名面）

核心纪律：把**认证（你是谁）**、**对象授权（这个对象是不是你的）**、**阶梯验证（第二因子）**当三层分别测。每一层都用外来对象 + 假因子打一发，看错误文案停在哪一层——**文案说「验证码错」而不是「对象不存在/无权」，就是对象授权被跳过的铁证**。

配套：`spa-js-api-mapping`（从 bundle 扒端点与请求形状）；`app-layer-login-ratelimit`（认证层的锁/限速）；`captcha-solving`（挑战墙）。

## 0. 先画端点面（≤10 分钟）

1. **OpenAPI 优先**：`openapi.json` 里全局 `security` + 每个 operation 的 `security`；缺省或 `security: []` = 规范上的匿名。
   - 脚本：`scripts/openapi_anon.py <openapi.json>` 直接列出所有匿名 operation。
2. **无 OpenAPI 就扒 bundle**：grep `/exports/`、`/authorize`、`/reveal`、`/secrets`、`/download`、`verification_method`、`email-verification/send`、`step-up`。
3. **运行时确认比规范可靠**：每个「匿名」端点先发空 body——
   - `422` = 已到 handler/schema（**schema oracle 入口**）；
   - `401` + 全局统一文案 = 被中间件挡；
   - `404` JSON = 路由不存在。
4. **catch-all 401 陷阱（Spring Security 等）**：未知路径也回同一个「认证失败」。先打一条**已知不存在**路径和一条**已知公开**路径对比；两者同文案 = 路径探测无信息量，别据此判断 admin 路由存在。

## 1. 对象级授权（IDOR / BOLA）

对每个收对象 ID 的端点（数字 / UUID / slug / 业务 ID）做三发对照：

| 输入 | 期望 | 含义 |
|---|---|---|
| 自己的 ID | 200 + 数据 | 基线 |
| 随机同格式 ID | 404 / 403 | 有校验 |
| 他人/他租户 ID | 200 + 数据 | **对象授权缺失** |

- **200 但空列表 ≠ 安全**：`user_id/tenant_id/scope` 参数可能被静默忽略。改参数看 `total` 是否变化；不变 = 参数是摆设，数据仍按会话过滤。
- **数字 ID 先测步长**：连建两个对象看 ID 差值；顺序 ID 才能枚举。
- **UUID 不可枚**时，把火力转到**批量接口**：导出/授权/预览这类「一次收一组 ID」的端点，往往直接信客户端给的列表。
- **本租户 0 对象的打法**：自己的列表为空反而最好——导出/授权端点仍接受任意 ID，直接用它测对象授权，不必先造数据。

## 2. 阶梯验证网关（step-up）⭐ 最高性价比

导出明文卡号/CVV、reveal 密钥、改密、删号常用「第二因子」门。典型形状（实测）：

```
POST /xxx/secrets/authorize  {ids:[...], verification_method:"EMAIL|TOTP", verification_code:"6位"}
  -> {authorization_token}
POST /xxx/secrets.csv        {authorization_token}
  -> CSV（完整明文）
POST /xxx/secrets/email-verification/send  -> {expires_in:600, debug_code:null}
```

**胜负手：门可能「替代」对象授权，而不是「附加」在它上面。**

1. 用**外来 ID + 假验证码**打 authorize：
   - `EMAIL_CODE_INVALID` / `CODE_INVALID` / `验证码错误` = **所有权没查**。只要拿到自己账号的合法码，就可能给任意 ID 签发 token。
   - `CARD_NOT_FOUND` / `NOT_FOUND` / `FORBIDDEN` = 该端点查了所有权（换 token 签发端点再测一次，别只测一个）。
2. **同一对象在别的端点做对照臂**：`GET /cards/{id}/verification-code` 对同一批外来 ID 回 `CARD_NOT_FOUND`，而 authorize 回「验证码错」——证明前者查、后者不查，证据链完整。
3. **拿合法因子**：
   - 验证码发到**账号自己的邮箱**——让用户收一下最快（10 分钟 TTL）；
   - 或先走「改邮箱」流程把账号邮箱改成可控地址（若只验新邮箱 + 当前密码）；
   - **不要爆破 6 位码**：常配 10 分钟 TTL + 尝试次数限制，一发就烧窗口。
4. **token 绑定检查**：authorize 返回的 token 可能绑定 ID 列表。解码（JWT 可直接读 payload）；在第二步换 ID、重放、改列表，看是否仍出数据。
5. **debug 字段**：`debug_code` 只会在非生产/白名单客户端出现。实测 `X-Forwarded-For: 127.0.0.1`、`X-Real-IP`、`X-Debug`、body `debug`、`?debug=1` 均**不**填充；不要在这上面耗超过 5 分钟。
6. **发码限速是硬的**：响应 `429 RATE_LIMITED` + `retry_after_seconds`（实测 600s 窗口），每个窗口只有一次机会——先想清楚再发。

## 3. 422 当 schema oracle（FastAPI / Pydantic）

```json
{"detail":[{"loc":["body","card_ids",0],"type":"string_type","msg":"Input should be a valid string"}]}
{"loc":["body","event_type"],"type":"literal_error","ctx":{"expected":"'order.finished'"}}
```

- `loc` = 字段路径；`type` = 期望类型（`string_type` / `dict_type` / `literal_error`）；`ctx.expected` = 枚举字面量。
- 迭代顺序：空 body 拿必填字段 → 错类型拿正确类型 → 枚举值拿全部合法值 → 才进业务层。
- **格式校验先于 DB**：`card_number 格式错误` 会在 SQLi 之前拦下；换**没有格式校验的兄弟字段**（`order_no`、`merchant_order_no`）再试注入，但仍可能撞签名层。
- `tokenjson` 要 dict 不要 string、`card_ids` 要字符串数组不要 int——这类类型坑直接用 422 文案定位，别猜。

## 4. 匿名 ≠ 无鉴权

`security: []` 的端点运行时常见三种额外门：

- **API Key**：缺头 `40106 请求头中缺少 X-API-Key` vs 错 key `40107 API Key 无效或不匹配`——两种码分开，证明守卫存在且可枚举错误面。
- **回调签名**：schema 全合法后回 `40107 回调身份验证失败` = 校验在签名层，不在字段层。
- **订单/卡密凭证**：`{cardKey}`、`{cardNumber,email}` 这类「知道凭证才能查」的端点，本质是预言机，不可枚举，别当 IDOR 打。

判定顺序：空 body（422）→ 合法 body 缺 key（40106）→ 带假 key（40107）→ 才谈绕过。

## 5. 证据与节奏

- 每个探针记录 `(method, path, body, status, body.code)`；**错误文案就是证据**，报告里原样引用。
- 一次只验证一个假设；先对照臂（自己的 ID）再打外来 ID。
- 找到「门跳过授权」后**停下来拿合法因子**，不要在拿到 token 前批量刷 ID（既打草惊蛇又可能触发风控）。
- 报告口径：认证绕过 ≠ 授权绕过。本文这一类的正确写法是「阶梯验证端点未校验对象归属，配合合法第二因子可越权导出」。

## Pitfalls

- **全局 401 catch-all** 让「路径存在性」不可判，先做已知路径对照。
- **空列表 / total:0** 可能是参数被忽略，不是没数据。
- HTTP 200 + body `{"code":500}` 是业务错，不是成功。
- 导出 token 通常**一次性 + 短时效**，拿到就立刻用，别存着。
- 别把「验证码错」误读成「对象不存在」——这正是本文要抓的信号。
- 发码接口的 429 窗口很硬（实测 600s），调试时别把唯一一次机会浪费在错 payload 上。

## 案例与脚本

- `references/stepup-export-gate-case.md` — 白标 VCC 平台卡密导出链：完整端点形状、错误码对照、debug 字段与限速实测（2026-10-21）。
- `scripts/openapi_anon.py` — 从 openapi.json 列 `security: []` 匿名端点。
- `scripts/stepup_authorize_probe.py` — 阶梯授权端点探针：外来 ID + 假码，打印每层错误。
