# 买家端安全审计缺陷清单（2026-08-07 全量扫描）

范围：app/ 根路径页面（非 /seller /admin）、app/api/ 买家 API（auth/login、products、checkout/orders、orders/*、pay/*、buyer/recharge、buyer/withdrawals、account/*、messages、favorites、aftersales、uploads、contact 等）、components/ 买家组件。审计方法：先读 session/requireRole 层 → 资金路径 → 订单状态机 → 消息 → 最后 grep 危险模式。**未改任何代码**，以下为待修清单。密码均已脱敏。

## 严重

### S1. 买家充值"提交即到账"，可无限增余额并提现套现
- 位置：`app/api/buyer/recharge/route.ts:24-32`；UI `components/buyer/BuyerBalancePanel.tsx`（账户页"充值"按钮直达）
- 问题：不做支付/链上核验，POST 直接 `availableAmount: { increment: amount }` + 建 `BuyerRecharge(status:"approved")`。仅校验 `>0 且 ≤100000`，可无限调用。注释自述"dev 演示链路"，生产未关闭。
- 场景：注册买家 → 循环充值 → 余额百万 → 提现 → 管理端打款（`app/api/admin/buyer-withdrawals/[id]/route.ts:29-35` 只校验 frozen 足够）→ 平台资金流失。
- 修复：接入真实收银台/链上金额指纹核验后到账；生产禁用即时到账分支或改 pending+人工审核。

### S2. 硬编码管理员演示账号生产可登录（默认凭证）
- 位置：`lib/auth-model.ts:22-116`（7 个 admin 明文密码）+ `app/api/auth/login/route.ts:40-49, 69-74`
- 问题：<EMAIL-REDACTED> 等 admin 账号密码写死源码，登录路由无 NODE_ENV/开关禁用；root 权限 "all"（finance/arbitration/改余额全含）。AdminUser 禁用检查只对已建行员工生效，demo 邮箱无行时直接放行。
- 场景：能读到源码/部署包的人用已知密码登录全权限后台。
- 修复：生产移除 demo 分支或随机密码+env 注入；管理员走真实 AdminUser 表。

## 中

### M1. 并发提现竞态：事务内 check-then-decrement 仍可透支负余额
- 位置：`app/api/buyer/withdrawals/route.ts:37-47`
- 问题：事务内 `tx.buyerWallet.upsert` 读余额判断，再无条件下 `decrement`。READ COMMITTED 下两笔并发都过判断 → availableAmount 可为负、frozen 虚增；管理端打款只看 frozen 够就放行。
- 注意：**`$transaction` 本身不够**（pitfalls.md 原建议只说事务原子），必须条件更新。
- 修复：`updateMany({ where: { userId, availableAmount: { gte: amount } }, data: { decrement } })`，count===1 才算成功。

### M2. 多 SKU 商品按首 SKU 价格计价
- 位置：`app/api/checkout/orders/route.ts:104,123`；`lib/product-repository.ts:91`
- 问题：总价与 unitPrice 恒取 `product.price`（= variants[0]），请求 sku 只用于锁库存。sample-data skuItems 价差 = 基础价+4×index；卖家多 SKU 商品同理。高价 SKU 低价卖出 = 平台/卖家损失；反向则买家多付。
- 修复：按所选 sku 查 skuItems/variant price 计价。

### M3. 库存扣减/回补失败静默返回成功
- 位置：`lib/product-repository.ts:385-409`（reserve）、`435-458`（release）
- 问题：Prisma 分支异常 catch 吞掉仍 `return { ok: true }`；`target` 不存在（:389）也返回成功。checkout 据此落单 → 超卖。release 吞错 → 取消/退款订单库存不归还。且两函数同时改 local-db 与 Prisma，Prisma 失败时双库漂移。
- 修复：catch 返回 {ok:false} + 告警；reserve 失败时 checkout 回滚已建订单；release 失败重试。

### M4. 收银台接口无认证，intentNo 即唯一凭证
- 位置：`app/api/pay/[intentNo]/route.ts`（GET :13-19、POST :21-89、renew :29-40）；`app/pay/[intentNo]/page.tsx:7-12`
- 问题：不校验调用者身份/意向归属。intentNo 出现在 checkout 响应、paymentTransaction.metadataJson、通知 metadata、操作日志 → 泄露即可查看订单号金额、提交任意 TXID 刷财务人工队列（chain key 未配时仅提示人工复核）、renew。POST 订单分支（:58-67）不校验 orderStatus，**已关闭订单仍可提交付款凭证**。
- 修复：intent 记 createdByEmail，GET/POST 校验归属；订单分支加 `orderStatus=pending_payment && paymentStatus≠paid` 条件。

### M5. 重复确认收货无限重置 30 天售后期
- 位置：`app/api/orders/[id]/confirm/route.ts:25-39`
- 问题：允许状态含 completed，且读后无条件 update。反复 POST → `afterSalesAvailableUntil = now+30d` 每次重置、completedAt 重置；`refreshSellerWallet`（`lib/funds-repository.ts:97,212`）按窗口冻结卖家可提现余额 → 卖家货款无限期冻结。
- 修复：`updateMany({ where: { orderNo, orderStatus: { in: ["delivered","receipt_confirmed"] } } })`，count!==1 幂等返回。

### M6. 会话不存在时兜底建会话可伪造他人 buyerEmail
- 位置：`app/api/messages/[id]/route.ts:49-63`；`lib/message-repository.ts:376-419`（createOrRouteConversation）
- 问题：兜底路径 `buyerEmail` 直接取 body（:389 `input.buyerEmail || actorEmail`），无归属校验；contextId 可填他人订单号。消息已入库，对卖家/被冒充买家可见（攻击者自己读不回，但消息已发出）。
- 场景：伪造 victim 身份向卖家发消息诱导按其指示发货/退款/转账户；受害买家端出现陌生人会话。
- 修复：actorRole=buyer 时强制 buyerEmail=actorEmail；contextType=order 校验 buyerOwnsOrder。

### M7. 下单无幂等控制
- 位置：`app/api/checkout/orders/route.ts:36-214`
- 问题：无幂等键，双击/重放各生成独立订单并各锁库存、各建 intent。
- 修复：客户端幂等键 + 服务端唯一约束（buyerEmail+idempotencyKey）。

### M8. 已停用账号会话仍可操作全部买家 API（含提现）
- 位置：`lib/api-auth.ts:20-46`
- 问题：requireRole buyer 分支不查 User.status；登录后停用，7 天会话期内提现/下单照常。
- 修复：buyer 分支查 status，deactivated → 401/403（同 admin 分支处理）。

## 低

- **L1 金额精度**：schema BuyerRecharge.amount / BuyerWithdrawal.* 为 Float（Order/钱包为 Decimal）；代码浮点运算（`Number(amount*0.015).toFixed(2)` withdrawals :31-32、checkout :104）。统一 Decimal + 整数最小单位。
- **L2 提现无最低金额/次数限制**：`app/api/buyer/withdrawals/route.ts:19-21,67` 仅 `amount>0`；`amount<0.005` 时事务已提交（冻结+建单）后才返回"提现金额过小"，响应与状态不一致。
- **L3 售后证据可带任意 http(s) 外链**：`app/api/orders/[id]/aftersale/route.ts:39`、`app/api/aftersales/[id]/evidence/route.ts:29-32` 只滤 `/|https?:` 前缀；`app/admin/aftersales/[id]/page.tsx:33`、`app/seller/aftersales/[id]/page.tsx:75` 渲染 `<img src>` → 管理员/卖家 IP+UA 泄露（tracking pixel）。修复：仅允许 /api/upload-files/ 白名单。
- **L4 支付意向金额指纹生成竞态**：`lib/payment-intents.ts:38-51` check-then-insert 非原子，并发同 base 可能同 payAmount → 链上自动匹配错配/跳过。修复：payAmount 唯一索引+冲突重试。
- **L5 无效商品 ID 回退展示第一个商品**：`lib/product-repository.ts:188-192`（`?? catalog.products[0]`），影响 products/[id]、cart、checkout 页。修复：返回 null + 404。
- **L6 session-auth 用户旧密码校验接受公开 demo 密码**：`app/api/account/password/route.ts:28-29`、`deactivate/route.ts:32-33` — checkout 自动建号（passwordHash="session-auth"）的改密/停用旧密码可填 demo 买家公开密码；会话泄露即夺号。
- **L7 local-db 与 Prisma 双写漂移**：`lib/product-repository.ts:359-459`、`app/api/checkout/orders/route.ts:147-161`（先写 local-db 再 sync Prisma，Prisma 失败残留订单行）。生产应确认 LOCAL_DB_MIRROR=0。
- **L8 联系人表单订单号枚举 oracle**：`app/api/contact/route.ts:40-48` 明确区分"不存在"报错。
- **L9 确认收货 source 参数可伪造日志**：`app/api/orders/[id]/confirm/route.ts:14,42` 买家传 source="system" 审计显示"自动确认收货"。

## 干净面（审计确认无问题）
- SQL 注入：全库 0 处 queryRaw/executeRaw，全走 Prisma 参数化。
- XSS：0 处 dangerouslySetInnerHTML；唯一 innerHTML 为卖家端图表自绘数值。
- 水平越权：订单/地址/收藏/售后证据均有 buyerOwnsOrder/userId 归属校验；聊天读写在 findAccessibleConversation 内（除 M6 创建路径）。
- 上传：魔数+类型白名单+路径穿越防护。
- 垂直越权：seller/admin API 均有 requireRole+权限矩阵；cron/mail 有密钥鉴权。
