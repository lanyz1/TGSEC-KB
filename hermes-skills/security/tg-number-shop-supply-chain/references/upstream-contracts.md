# 号源供应链三段契约（实测速查）

> 证据等级：★= 本项目族实测有响应可复现；☆= 推断/待验证。不要把 ☆ 写进交付报告的"已验证"里。

## 一、云控面板（uvicorn / FastAPI 族）

指纹：`GET /` 标题「关键字监听管理后台」；`GET /admin/dashboard` 免鉴权吐 1MB+ Vue3 SPA；
`/openapi.json` 100KB+ / 上百条 path；响应头 `server: uvicorn`。测绘语法（FOFA）：标题 + `"daxi"`/`"号铺"`/`"大喜"` 组合。★

端点族（从 OpenAPI 分类，不是逐个盲扫）：

| 族 | 代表端点 | 备注 |
|---|---|---|
| 账号 | `/api/accounts`、批量上下线/改密/踢会话、`batch-export-tdata`、`{id}/chat/messages`、`{id}/chat/send`、`{id}/pm-logs` | 导出 tdata = 最高价值口（需鉴权） |
| 发码/接码导入 | 接码链接 TXT 导入、`/api/autopm/*` | 与接码服务同生态 |
| 群/派发 | `/api/dispatch/*`（入群队列、群发） | 破坏性动作多，只读优先 |
| 代理池 | `/api/proxies/capacity` | 拿面板后可换出口 |
| 管理员/日志 | `/api/admins`、`operation-logs`、`/api/logs/export` | 日志口常只收 DELETE（维护） |
| 采集 | `/api/oygx/*`（搜刮导出） | 上游供需采集模块 |
| 钱包/提现 | `/api/wallets/*` | **资金面，不碰** |

鉴权与登录：全局 HTTPBearer，受保护口回统一 `{"detail":"Not authenticated"}` ★；
`POST /api/auth/login {username,password}` → 口令正确时 `200 {"status":"require_2fa_code"}`（卡 Google TOTP）★；
`POST /api/auth/bind-2fa`（OpenAPI 标 `security: None`）→ 仍真校验 `totp_code`，假码 400 ★。
`/api/auth/setup` 首装类端点在本族**未注册**（OpenAPI 里也没有）⇒ 首装路不通 ★。

免鉴权口（实测）：`GET /api/orders/debug` → `{"count":N,"rows":[[id,account_id,price,status,plan,start,end],...]}`
= 原始 SQL 行，**直接给表结构与业务字段** ★；`/api/bot-messages/photo/{log_id}`（需有效 id，无 id 回业务错）★；
`/api/autopm/media/{filename}`（穿越变体 `%2f`/`..%5c`/双编码全回「图片不存在」）★。

隐藏维护路由（`Allow` 头 oracle 实测）：`/api/accounts/debug`(DELETE)、`/api/admins/debug`(PUT)、
`/api/accounts/{import,session,tdata,export-tdata}`(DELETE)、`/api/logs/export`(DELETE)、`/api/oygx/export`(GET) ★
—— 均为**破坏面**，只登记不调用。

已排除（别重复烧时间）：JWT 弱密钥表、`alg:none`/空密钥、
`X-Forwarded-For|X-Real-IP: 127.0.0.1`、`X-Original-URL`/`X-Rewrite-URL`、`X-HTTP-Method-Override`、
路径穿越变体、用户名枚举（多实例只存在 `admin`）。★

## 二、号铺分销 API（HMAC 四头）

基址形如 `https://<shop>.amao.pro/api/v1`，`/openapi.json` + `/docs` 公开 ★。

- 鉴权：`X-Api-Key` / `X-Api-Sign` / `X-Api-Timestamp` / `X-Api-Nonce`；
- 分层 oracle：缺头 → `HMAC headers are required`；带假 Sign → `X-Api-Sign format is invalid` ★
  ⇒ 可据此确认路径存在性与鉴权严格性，不必先拿 Key；
- 端点：`/balance`、`/products`、`/products/{id}`、`/products/{id}/stock`、`POST /orders`、`/orders`、
  `/orders/{id}`、`/orders/by-out-order/{outOrderId}`、`/orders/{orderId}/files/{fileId}`（发货文件）★；
- 无自助注册（API 客户由运营总后台人工开通）★。

## 三、接码 / 取号服务 + 运营总后台

- 接码：`/health` → `{"ok":true,"listener_mode":"on_demand","listener_tasks":N,"listener_limit":30}` ★；
  `/accounts/{uuid}` 免鉴权但需**有效卡密 UUID**（示例 UUID → `not_found`）★ ⇒ 卡密即凭据，
  去向是号铺订单/发货文件，不是字典。多个域名（`link.*` / `api.*`）常是**同一服务**（`/health` 响应逐字相同）★；
  `/docs` 可能 308 重定向，跟跳转再读契约。
- 运营总后台：nginx Basic 401，`WWW-Authenticate: Basic realm="<品牌> Operations"` ★ = 品牌/系统名，
  拿去搜源码市场商品页，往往直接给出成品默认口令与源码仓库；该口无 2FA ⇒ 是比面板更短的路径（☆待验证）。
- 兄弟域被 **Cloudflare Access（Zero Trust）** 保护时（302 → `<team>.cloudflareaccess.com`），单独记录，别硬碰 ★。

## 四、从下游反推上游的线索源

下游站的前端 chunk（Vite 产物）里常直接出现上游服务域名与集成名：
`grep -o` 商户域/集成标识（如 `Daxi`、`int<x>.<pub>.com`），再拿它去测绘平台搜同族主机，
能把"号铺 API → 接码 → 云控面板"三段一次串起来 ★。
