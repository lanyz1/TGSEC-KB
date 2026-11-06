# TRON 能量租用 Telegram Mini App（freeEnergyBot 类）

类级：TG WebApp 壳 + 自建 API，卖 Energy/Bandwidth 或 USDT→TRX swap。
**不是**授权盗 U（无钱包 connect/approve）。

## 指纹

| 信号 | 含义 |
|------|------|
| 标题「能量租用」/ package 65k·131k TRX 价 | 业务 |
| `telegram-web-app.js` + `const APP_VERSION` | Mini App |
| `SESSION_TOKEN_KEY = "freeEnergyBot.miniappToken"` | 产品族 |
| `API_BASE_URL = window.MINIAPP_API_BASE_URL \|\| "https://api.<root>/api"` | 后端 |
| 多子域同壳 `bx/m/gx/pao/tron/xm.<root>` | 入口 CDN 静态 |
| 文案 paymentAddressMissing / 后台配置收款 | 地址不在前端 |

## API 面（app.js 还原）

```
GET  /config          # packages, operation.miniappLogoUrl, customerServiceTg, checkin/invite free times
GET  /swap            # depositAddress, trxPerUsdt
POST /session/init    # initData, telegramId, deviceSignals, walletAddress → {token,user}
GET|PATCH /users/me
GET|POST /addresses · POST /addresses/energy-check · /addresses/{id}
POST /orders/energy-rental  # fromAddress, targetAddress, recipientAddress, packageId, useFreeEnergy
GET  /orders?page=&pageSize=
GET  /invites
POST /checkin
POST /logs/copy-result
Authorization: Bearer <token>
```

## 鉴权

- `getTelegramIdentity()`：无 `Telegram.WebApp.initData` → 抛「请在移动端 Telegram 访问」
- 浏览器 curl **不能**自然拿 session；假 initData 视服务端 HMAC（bot token）松紧
- 恢复后优先：未授权 `/config` `/swap` 是否直接吐热钱包

## 攻击顺序

1. 拉 `app.js` 定 API_BASE + 全 path（勿信 SPA 回落 path 扫描）
2. 打 `GET /config` `/swap` — 收款/充值地址 + 客服 TG
3. hostsearch/crt 扫兄弟壳（同 hash 静态）
4. API **CF 522**：源站挂 — 报告环境态；链上暂无地址可跟；**切换目标**或挂起等 API
5. API 活：session 校验、订单/地址 IDOR、`useFreeEnergy` 风控绕过、admin（仅文案提及）
6. 有 deposit/payment 地址 → TronGrid 余额/归集（与 faka 收款溯源同法）

## 与盗 U 对照

- 用户只提供 **公开 TRON 地址**；能量是 `DelegateResource`，不碰用户 USDT allowance
- 付费是 **转 TRX/USDT 到平台地址**，不是 approve MAX
- 风控：「地址活跃度不足」「已被风控封禁，请使用转账租用」

## 锚点（2026-09）

- `https://bx.0trx.top/` · API `https://api.0trx.top/api` · **522 Origin Down**
- 默认档：65k=2.5 TRX，131k=5 TRX
- 工件：`/tmp/bx0trx/`
