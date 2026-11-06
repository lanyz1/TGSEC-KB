# 反爬挑战逆向与页内 RPC（betmaster/VND-bmt 案例，2026-10）

主站 API 对敏感调用（注册/登录/投注/联系人确认）叠加自研反爬：机器人评分（TLS 指纹级）+ 工作量证明挑战（X-Verify 三头协议）。本文为完整逆向记录与复用要点。

## 1. 机器人评分：非浏览器客户端吃「假响应」

现象：python requests / curl 对 `POST /api/auth/email/register/v2` 恒回
`404 {"code":400,"reason":"invalid login/password"}`（格式完美的假错误，换任意邮箱/密码/字段都不变）；
同一请求从真浏览器页内 fetch 发出 → 真实校验错误（`marketing: Invalid format` → 之后才是 `418 region`）。

判定法：
- 同一请求两条链路各打一发对照：requests 直发 vs Playwright `page.evaluate` 页内 fetch。
- 响应「太合理」且不随输入变化 → 高疑假错误。
- 触发因素含 TLS 指纹（JA3）与浏览器头；补请求头在部分站点够用，不够就上页内 RPC。

## 2. X-Verify PoW 协议（三头重放）

- 首次 POST → 200 挑战体 `{"func":"zeros","params":{"a":4,"b":"<32hex>"}}`；响应头含 `x-verify: required` + `x-verify-data` + `x-verify-sign`。
- 求解后**重放同一请求**（同 method/body），带三头：`X-Verify-data`/`X-Verify-sign` 原样回传 + `X-Verify-result` = 答案。
- 挑战可多轮（客户端节流 `newThrottle = r===0?1000:r*2`，即 1s→2s→4s…），循环到非挑战响应。
- 服务端另按 IP 限速：`429 {"reason":"requests limit"}`——注册端点窗口很紧，同 IP 短时间内超过约 2 个完整循环即 429，退避分钟级。

### 求解语义（照抄压缩 JS 的 `EBe`/`TBe`/`SD`）

- `zeros(a, b)`：找最小 i≥0 使 `SHA256(Utf8(b) ‖ uint32BE(2^31+i))` 的**前 a 个半字节**（nibble）为 0；答案 = `btoa`(4字节BE(2^31+i)) = 标准 base64 **带 `=` 填充**。
- `sha256(a, b)`：`hex(SHA256(b 重复 ceil(a) 次))`。
- **两个自造坑（都踩过）**：
  1. `b` 是 hex 字符串，但 JS `TextEncoder.encode(b)` 编码的是**字符串本身**（32 字节 ASCII），不是 hex 解码（16 字节）——按 bytes.fromhex 求解全错。
  2. 答案用 `btoa`：标准 base64、**带填充**；`urlsafe_b64encode().rstrip('=')` 是错的。
- 验证法：把原版 minified 求解器片段贴进 node 跑一遍，与 Python 实现逐字节对比（本案例 4 处挑战全一致）。
- 独立端到端验证：对同样受保护的数据端点（feed）求解后重放，拿到业务层响应（如「缺参数」= PoW 已过）。

## 3. 字段 schema 逼取（空载/畸形载）

- `{}` → `{"currency":"Field required"}`（字段清单直接吐出来）。
- `marketing` 传 false/字符串 → `"Invalid format"`；真实客户端在 injectedProps 为空时**直接省略该键**（照抄客户端行为，无效键别乱塞）。
- `{"personal_data":{}}` → `value_error.discriminated_union.missing_discriminator` → 判别字段名 = `shape_id`（值如 `betmaster_mx`），补上即 201 通过。

## 4. 认证通道枚举（同平台不同门）

JS 路由表里的通道：email / phone / whatsapp / estonian-id / account_id / oauth。实测差异（MX 市场）：
- email/phone 注册：地区门 `418 "service is not available for your region"`（非目标地区 IP 全拒；**同地区 Tor 出口也被拒——含反匿名评分**）。
- **account_id 通道**：`POST /api/auth/account_id/register/v2 {"language","currency"}` → 200 直接发号：`user.login`（数字账号ID）+ 响应 `credentials.password`（生成密码）+ `api_auth_token` 双 JWT（普通 + promo_action）。无短信/邮箱/证件/地区任何检查（合规洞）。
- 后续登录：`POST /api/auth/account_id/signin {"password","account_id"}` → 会话就绪（`is_confirmed` 转正）。

### 4b. 挑战确认链（OTP 回填，2026-10 半程验证）

- 触发（加邮箱联系人）：`POST /auth/contacts {type:email, contact}` → 200，响应带 `challenges_requested: {token, challenges:[{id: UUID, type:"OTP", target, target_type:"EMAIL"}]}`；同刻发出 6 位码确认邮件（SendGrid）。
- 回填 = **重放原请求**（`POST /auth/contacts/{cid}/confirm`），两头：`VND-bmt-challenges-auth-token`=token、`VND-bmt-challenges-answers`=**base64(JSON {"<challenge_id>":"<code>"})**（客户端语义 `btoa(JSON.stringify({challenge.id: 输入}))`，见 JS 里 `od`/`sd` 常量）。
- 重发码：`POST /challenges/challenges/{challenge_id}/resend`（头 sd=token）；码有 TTL（分钟级）。
- 状态码语义：`4001` 还差挑战 / `4002` "incorrect challenges answers"（**格式被受理的信号**——用过期码即得此码，格式验证通过 ≠ 成链）/ `4003` 挑战过期需重发。反复重试后端点转 500/429——本战役止步 4002；重试要单发 + 重取新挑战，别连打。

## 5. 页内 RPC 通用模式（Playwright）

1. venv 装 playwright；本机已有 ms-playwright 缓存时直接 `launch(executable_path="~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")`，无需再下载浏览器。
2. `page.goto(首页)` 等 cookie 就绪（csrftoken / `window.__ENV`）。
3. `page.evaluate(JS, payload)`：JS 内 fetch + PoW 求解 + 重试循环，返回 `{status, body, cycles}`。
4. 鉴权接口把 token 放自定义头；**头名大小写敏感**（本案例 `Auth-Token` 对、小写变体触发服务端 500）。
5. `reason_data` 是金矿（字段校验细节）；`x-verify-*` 头只在挑战响应上出现。
6. 协议未知时先**跑真实流程抓包**（点击真实 UI），拿到市场专属版本头/平台值/请求体真值，再页内复刻。

## 6. 端点清单抓取

对全部 bundle 用正则 `(get|post|put|patch|delete)\s+/[a-zA-Z0-9_/{}$.:-]+` 直扫包装函数（`kA(\`post /x\`)`、`lN(...)`、`cr(...)`），一次拿全（本案例 171 条，含 `{user_id}`/`{transaction_id}` 占位 = IDOR 清单）。

## 7. 箴言

- 需要对「认证/注册语义」下结论前，**必须**有浏览器上下文对照臂；否则一切「无效凭据/无此路由」都可能是假响应。
- 挑战系统变体：单头、三头重放（本例）、cookie 门（Beget `beget=begetok` 型）——共同点：**读客户端 JS 实现，照抄语义再谈攻击**。
