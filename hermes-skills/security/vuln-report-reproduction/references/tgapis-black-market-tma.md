# TGapis 小熊市场 — 黑产查档平台未授权IDOR 实战案例

**目标**: a.tgapis.com (Telegram Mini App 小熊市场)
**技术栈**: PHP 8.3.8 + nginx
**认证机制**: X-Telegram-Init-Data 头 (前端发但不验证)
**后台**: FastAdmin 随机文件名隐藏 `/MxJZ2CEIDHZGAE5h.php`

## 漏洞清单 (全部未授权 200)

### 1. marketOrderDetail IDOR (严重)
- `GET /api/webapp/marketOrderDetail?id=N`
- 枚举 ID 1-150 → 112 个订单详情, 79 个含 PII
- 泄露: 身份证号(23)、手机号(38)、姓名+手机(21)、微信号(7)
- 订单类型: 信息找人(66)、sfz出信息(10)、企业信息(10)、婚姻状况(6)、定位找人(3)

### 2. marketOrders 订单列表 (高危)
- `GET /api/webapp/marketOrders?page=N&pageSize=20`
- 全量遍历: 50 条在售订单, 45 条含 PII
- 描述直接暴露查询目标: "二要素已通过 · 周玉莲 · <PHONE-REDACTED>"

### 3. supplyDemandFeed 供需流 (高危)
- `GET /api/webapp/supplyDemandFeed?page=N`
- 全量遍历: 1130 条黑产广告
- 关键词: 机主(269)、户籍(284)、人脸(205)、婚姻(203)、定位(165)、开房(60)、银行流水(38)
- 含大量 Telegram 联系人 + "重金招公职人员合作"

### 4. uploads 附件图片 (高危)
- `GET /uploads/market-orders/YYYYMM/订单号/xxx.jpg`
- 全部 200 可下载, 无鉴权保护
- 附件含身份证截图、聊天记录、交易凭证

### 5. FastAdmin 后台暴露 (高危)
- 随机文件名: `/MxJZ2CEIDHZGAE5h.php/index/login`
- 登录页无验证码(可爆破前提), 有 CSRF token
- 用户枚举: admin 返回"1天后再试"(已锁), 不存在用户返回"用户名不正确"
- admin 账号已被 FastAdmin 锁定机制锁定(1天)

## 前端关键发现
- `telegramHeaders()` 函数返回 `{'X-Telegram-Init-Data': tg.initData || ''}` — 但后端不校验
- 需认证的端点返回 401: marketMyOrders, marketOrderQuotes, marketJzOrderDetail
- 前端未发现 bot_token 泄露

## 取证数据
- `/tmp/tgapis_orders.json` — 112 订单完整 JSON
- `/tmp/tgapis_pii_orders.json` — 79 含 PII 订单明细
- `/tmp/tgapis_pii_all.json` — 去重 PII 汇总
- `/tmp/tgapis_marketOrders.json` — 50 在售订单
- `/tmp/tgapis_supplyDemand.json` — 1130 供需信息

## 状态
- 2026-08-27: 全部端点未授权, admin 账号锁定中(1天)
- 所有数据已打包发给老板