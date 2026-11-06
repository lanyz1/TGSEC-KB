# 买家支付链路 & 草稿回填实录（2026-08-11）

## 1. 金额显示链路（多处 bug 同源）

**数据流**：`ProductVariant`（DB）→ `ProductOperationMetric.skuItemsJson`（卖家维护的 SKU 列表）→ catalog（`productFromPrisma` / `operationFromPrisma`）。

- **列表/详情价不一致**（列表 39.9 详情 19.9）：列表价用 `variants[0].price`，详情 SKU 列表优先 `skuItemsJson[0]`（卖家调 SKU 顺序后两个"第一条"不同）。修复：`productFromPrisma` 的 `displayPrice = Number(asSkuItems(metric?.skuItemsJson, undefined)?.[0]?.price ?? firstVariant?.price ?? 0)`。
- **checkout 金额按首变体**（选 19.9 显示 39.9×qty）：checkout 页曾 `total = product.price * quantity`。修复：按 `params.sku` 在 `entry.operation.skuItems` 中匹配取价（fallback 到该商品 skuItems[0]，**不是**别的商品）。
- **支付页恒 39.9**：checkout 无 `product` 参数时 fallback 到 `catalog.products` 第一个有库存商品（水豚 39.9）→ 任何丢参入口显示 39.9×qty。修复：无 product 参数直接渲染"暂无可结算商品，请先选择商品"（`ui.fix.57/58`），删 fallbackProduct 逻辑。

**验证**：详情页读 `.pdp-price-line.main strong`，立即购买 href 读 `a.pdp-buy-now`，checkout 金额读 `Place an order · USDT X` 按钮文本；URL search 必须含 `sku=`（中文 sku 已 encodeURIComponent）。注意 Browserbase 直接导航 checkout URL 可能丢中文参数（浏览器导航规范化）——**验证用真实点击流程**（详情页点 Buy now）。

## 2. 支付死循环（收银台 ↔ 订单列表打转）

**闭环**：checkout 提交（USDT）→ 订单 + intent → 收银台 `/pay/[intentNo]` → 返回（曾写死 `/account/orders` 列表）→ 列表"去支付"（PayNowButton → `POST /api/pay/intents` 固定 USDT 重建 intent）→ 回收银台 → 返回 → …。

**修复三件套**：
1. `PayCashier` footer：返回改 `view.refs?.[0]?.ref` 的订单详情；order kind 且 refs 非空时加"更换支付方式"按钮 → `/account/orders/{ref}?changePay=1`。
2. 订单详情页 `BuyerOrderDetailPage` 接收 `searchParams.changePay`，`PayNowButton channels={changePay}`：channels 模式渲染 7 通道单选（usdt/balance/paypal/wise/card/applepay/googlepay），非 USDT/余额走既有风控页 `/checkout/payment-restricted?method=..&back=..`。
3. 余额补付 API `app/api/orders/[id]/pay-balance`（**参数名必须 [id]，与同目录其他路由一致**）：
   - 校验：buyer 角色 + `buyerOwnsOrder(orderNo, email)` + 订单存在且未付
   - 原子扣减：`prisma.buyerWallet.updateMany({ where: { userId, availableAmount: { gte: total } }, data: { availableAmount: { decrement: total } } })`，count!==1 → 409
   - 订单更新：`paymentStatus: "paid", orderStatus: "awaiting_shipment"`（OrderStatus enum 值，不是中文）
   - `syncPaymentForOrder({ id: orderNo, total, status: "待发货", ... }, { buyerEmail, method: "balance", status: "paid", escrowStatus: "released", providerReference: "balance", metadata: {...} })`（来自 `@/lib/payment-repository`）
   - `incrementProductSold` 按付款口径加销量 + `appendOperationLog/appendBusinessEvent`（来自 `@/lib/local-db`）+ `notifyMany`（order_paid 买/管理端）

**import 真实路径**（易错）：`appendOperationLog`/`appendBusinessEvent` 在 `lib/local-db.ts`；`syncPaymentForOrder` 在 `lib/payment-repository.ts`；`prismaOrderStatus` 在 `lib/order-repository.ts` 内部**未导出**（别 import，直接写 enum 值）。

## 3. Next.js 动态段冲突（全站 500）

- 错误特征：`You cannot use different slug names for the same dynamic path ('id' !== 'orderNo')`，**全站 500 而非单路由 500**。
- 恢复：改名统一段名 → 删服务器残留目录（deploy tar 解压不清理）→ `rm -rf /www/tiktok/.next` 全量重建（增量 build 保留坏 manifest）。
- 新建路由前：`ls app/api/<目录>/` 看同路径段现有参数名，直接复用。

## 4. 草稿回填（品牌/运费模板/参数）

- 品牌：Product.brand 字段全链路（schema + syncProductToPrisma upsert 的 update/create + POST/PATCH 路由 `body.brand` 截断 40 字 + productFromPrisma + 编辑页构建 + 表单 `useState(product?.brand ?? 启发式拆标题首词)`）。
- 运费模板：新建/编辑页 `listShippingTemplates(scope.storeName)` 传 props（SellerProductForm 加 `shippingTemplates?: ShippingTemplate[]`）；下拉 options 由模板构建（free → `名称（全场包邮）`，qty → `名称（首件 X + 续件 Y，满 Z 包邮）`）；**shipFeeMode 从 shippingNote 正则拆回**（`运费模板：`→tpl / `自定义运费`→custom），shipTemplate 拆 `运费模板：(.+)` 且必须存在于 options 才用，否则取第一个。
- 描述参数：`parseDescriptionPairs` pairCount ≥2 启用（原 <3 全降级到卖点）；表单 `filled.length >= 2` 同步（卖点首行像属性名拦截）。
- 提交 payload 加 `brand: brand.trim()`；注意 `composedTitle = 品牌+标题`（DB title 含品牌，回填优先读 brand 字段）。

## 5. 杂项教训

- **不要在 terminal 里直接跑 `ssh user@host` 命令**（会弹系统 SSH 密码框打扰用户）——统一用 execute_code + paramiko（密码在脚本内，不弹窗）。用户问"是不是你弹的框"要如实承认并说明无需输入。
- 浏览器实测卖家端注意**权限隔离**：qa-seller-1 当前会话绑定的店与草稿所属店可能不同（404 正常，先 DB 查 store 归属再断言）。
- paramiko 查 DB：`OrderItem` 无 createdAt（orderBy 用 id）；删 Product 先删 productImage/productVariant/productOperationMetric（外键 23503）。
- 保存草稿"点无反应"：fetch 无超时无 catch 时网络异常 → saving 卡 true → 按钮永久禁用。**所有保存类 fetch 加 `signal: AbortSignal.timeout(30000)` + catch 恢复 saving + 错误提示就近显示（按钮行上方，别只放侧栏）**。
