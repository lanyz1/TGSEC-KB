# #128 订单联系商家商品卡片缺图（2026-08-10）

## 症状
买家从订单详情点"联系商家"（`/messages/{orderNo}`）→ 对话框商品卡片**不显示图片**（占位 BOX_SVG）；从商品详情点"联系商家"（`/messages/new?product=xxx`）→ 商品卡片**有图**。

## 根因
两个入口的会话创建 cardPayload 数据源不同：
- 商品详情入口（`lib/message-repository.ts` createOrRouteConversation）：`cardPayload: { productId, title, imageUrl: product.images[0]?.url, price }` ✅ 有图
- 订单入口（`ensureBuyerOrderThread`）：`cardPayload: { orderNo, totalAmount, status, itemTitle }` ❌ **无 imageUrl**

底层原因：**OrderItem 快照不存图片**（schema 只有 productTitleSnapshot/skuSnapshot/optionSnapshot，无 image 字段）——订单会话创建时没实时查商品图。

## 修复（两层）
1. **创建时**：`ensureBuyerOrderThread` 在 create 前实时查商品图：
   ```ts
   const firstItem = order.items[0];
   const itemImage = firstItem?.productId
     ? (await prisma.product.findUnique({ where: { id: firstItem.productId }, select: { images: { take: 1, select: { url: true } } } }).catch(() => null))?.images?.[0]?.url ?? null
     : null;
   ```
   cardPayload 加 `imageUrl: itemImage`。
2. **存量会话**：DB 脚本遍历 `conversation.contextType='order'` 的 `message.cardType='order'` system 消息——cardPayload 无 imageUrl 且有 orderNo → 查 Order.items[0].productId → 查 Product.images[0].url → `message.update` 补 `imageUrl`。实测补 4 条（含用户报的会话）。

## 验证
查目标会话的 order 卡片消息：`cardPayload.imageUrl` 应为 cdn.qavlixor.com 商品图 URL。

## 类级教训
**凡是"会话/卡片/快照类"数据缺图**，先查数据源的快照字段有没有 image（OrderItem 这类快照常只存标题不存图），修复路径=创建时实时查 + 存量脚本补。ChatWindow 商品卡片渲染读 `payload.imageUrl`（空则占位 BOX_SVG），键名必须一致。
