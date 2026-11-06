# 2026-08-11 订单单价映射缺失 + 审核页图片 tab + 生产脚本模型名坑

## #177 卖家端订单详情单价恒 39.9（映射缺失类，与 #174 shippingAmount 同型）

**现象**：买家买任意价商品，卖家端订单详情"商品明细"单价都显示 39.9。

**排查路径（类级教训）**：
1. **先验 DB 再查映射层**——`p.orderItem`（client 属性 `orderItem`，模型 `OrderItem`）查 unitPrice 实际多样（39.9 / 69.9 / 9.99 各不相同）→ **数据层正确，问题在读取层**。
2. 读取层：`lib/order-repository.ts` 的 `fulfillmentFromPrisma` 里 `row.items.map(...)` **只映射了 productId/sku/quantity/title，漏掉 unitPrice/totalPrice** → 详情页 `unit = item.unitPrice ?? product?.price ?? 0` 回落商品目录价 → 显示 39.9（那个商品的默认价）。
3. 修复：映射时补 `unitPrice: item.unitPrice != null ? Number(item.unitPrice) : undefined`（totalPrice 同）。

**类级规则**：order-repository 的映射函数（orderFromPrisma / fulfillmentFromPrisma）改动字段前先核对映射完整性；"显示值异常"的排查顺序 = DB 数据 → 映射层 → 展示层回落逻辑。

## #178 管理端商品审核页图片 tab 点不动 + 只看得到主图

**根因**：`app/admin/products/[id]/page.tsx` 的 `product-thumb-row` 里 4 个 tab 是**静态 `<span>` 标签**（无任何 onClick），且页面只 `images.sort(sortOrder)[0]` 显示主图一张。

**修复**：
- 新建 `components/admin/AdminProductGallery.tsx`（client 组件）：按 sortOrder 分组 tab——**0=主图 / 1-19=详情图 / 20-39=包装图 / 40+=资质图**；每个 tab 带数量（如"详情图（5）"）；点击切换大图；**空分组自动隐藏**；选中 tab `.on` 蓝色高亮。
- 页面接入：`<AdminProductGallery images={product.images.map(img => ({url, sortOrder}))} alt={title} />`，删除原静态 thumb-row 和 image 变量。
- CSS：`.product-thumb-row span, .product-thumb-row button { ... cursor: pointer; }` + `.product-thumb-row button.on { border-color:#0071e3; color:#0071e3; background:#f0f7ff; }`。

**分组依据验证**：DB `productImage.sortOrder` 分布 = 0:7001 / 1-19:35807 / 20-39:53 / 40+:0 → 分组合理（主流商品 0 + 1-19 详情图）。

**通用模式**：用户报"画圈的地方点不动"——先查元素是 `<button>` 还是静态 `<span>`（占位标签伪装可交互控件是常见坑）。

## 生产脚本 Prisma 模型名/字段名坑（SSH 脚本查 DB 用）

- **模型名**：schema 的 `model OrderItem` → client 属性 `p.orderItem`；`ProductOperationMetric`（不是 `ProductOperation`）；`NotificationMessage` → `p.notificationMessage`。**查 schema 确认后再写脚本**（`p.productOperation.findMany` 报 `Cannot read properties of undefined`）。
- **字段名**：`OrderItem` **没有 createdAt**（orderBy createdAt 直接抛错）→ 用 `orderBy: { id: 'desc' }`。
- 报错堆栈是 Prisma runtime 压缩代码时，看不到具体错误——先检查模型名/字段名（90% 是这两个）。
