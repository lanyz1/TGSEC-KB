# 2026-08-11 支付页金额恒 39.9 + 金额类 bug 汇总（买/卖端）

## 症状与根因（最终一个）

**症状**：买家不管买什么商品、数量多少，支付页金额都是 39.9×数量。
**根因**：`app/checkout/page.tsx` 有"兜底商品"逻辑——URL 缺 `product` 参数时
`fallbackProduct = 第一个已上架且有库存的商品`（正好是水豚 39.9），任何不带参数
进结算页的入口（分享链接/参数丢失/直接访问）都显示 39.9×qty。
**修复**：移除兜底——无 `product` 参数直接渲染"暂无可结算商品，请先选择商品"
（同时删掉不再使用的 `getProductCatalog()` import/变量）。

## 同日金额类修复全清单（买/卖端，模式相同：显示层从"下单真实数据"取，不从 catalog 回落）

1. **卖家订单详情运费恒 0 / 商品金额含运费**：`orderFromPrisma` 漏映射
   `shippingAmount` → 详情页写死 0 + 商品金额=total。修复：映射 shippingAmount，
   商品金额 = total - shipping，运费 = shippingAmount。（买家端详情同一数据源，一起好）
2. **卖家订单详情单价恒 39.9**：`fulfillmentFromPrisma` 构建 items 时漏映射
   `unitPrice/totalPrice` → 详情页回落 `product?.price`。修复：补映射
   （有值用真实下单单价，无值才回落）。DB 实测 unitPrice 数据本身是对的（39.9/69.9/9.99 多样）。
3. **列表价 vs 详情价不一致（列表 39.9 详情 19.9）**：列表 `product.price` 用
   `variants[0]`（DB 变体第一条），详情页 SKU 列表用 `operation.skuItemsJson[0]`
   （卖家维护的默认款顺序）——SKU 顺序调整后两个"第一条"不是同一规格。
   修复：`productFromPrisma` 的 price 优先 `skuItemsJson[0].price`（fallback variants[0]）。
4. **立即购买金额翻倍（79.8=39.9×2）**：checkout 用 `product.price`（首变体）而非
   所选 SKU 价。修复：按 `params.sku` 在 operation.skuItems 中匹配取价，
   匹配不到才回落本商品 skuItems[0]（**绝不能跨商品回落**）。
5. **收银台"返回"跳我的订单列表**：`PayCashier` footer 写死 `/account/orders`。
   修复：订单 kind 返回 `/account/orders/{view.refs[0].ref}`（订单详情）；checkout 的
   Cancel 从 `router.back()` 改明确 Link 回商品页（历史栈不可控）。

## 测试方法教训（重要）

- **金额类 bug 必须用"真实点击流程"验证**（详情页选 SKU → 点 Buy now → 看 checkout URL+金额），
  不能只靠直接导航 URL：Browserbase/部分浏览器整页导航会**丢中文 URL 参数**
  （如 sku=8寸），导致误判为 bug 已复现/未复现。真实用户点 Link（Next 客户端路由）
  参数完整。实测：未登录 → Buy now → 登录跳回 → sku 参数保留、金额正确。
- 验证要覆盖：多 SKU 商品选非默认规格（关键）、登录跳回、数量变化。
- 生产 DB 验证用 paramiko 脚本（动态 import prisma）；删商品测试数据要**先删子表**
  （ProductImage/ProductVariant/ProductOperationMetric）再删 Product，否则外键 23503。
- **schema.prisma 加字段后本地必须 `pnpm prisma:generate` 再 tsc**（deploy.py 会自动
  在服务器端 generate，本地不会）。

## 关联

- checkout 页此前 #174 修过"按 SKU 取价"（79.8 问题），本次是兜底商品残留。
- 卖家端金额显示通则：详情/列表任何金额都优先"下单快照/所选 SKU"数据源。
