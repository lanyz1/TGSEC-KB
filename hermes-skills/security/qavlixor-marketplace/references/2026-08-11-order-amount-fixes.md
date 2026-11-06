# 2026-08-11 金额显示类 bug 排查（订单详情三行 + 立即购买四连）

## ★通用排查顺序（金额对不上时先走这三层对照）
1. **服务端计算**（下单/结算 API：subtotal+shipping=total，通常是对的——服务端是真相）
2. **页面展示**（checkout/详情页怎么算的——常错在用错字段）
3. **数据层映射**（orderFromPrisma 等 DB→领域对象映射——**新 DB 字段常忘记补映射，成了 undefined/0**）
对照出"页面显示 ≠ 服务端金额"即定位到展示层 bug。

## 1. 卖家端订单详情金额三行（商品金额/买家运费/预计收入）
- **症状**：商品 19.9 + 运费 5 = 实付 24.9，但显示商品金额 24.9、买家运费 0
- **根因**：① `orderFromPrisma`（lib/order-repository.ts）**没映射 `shippingAmount`**（只有 total）→ undefined；② 详情页运费**写死 `0.00 USDT`**；③ 商品金额直接用 `order.total`（含运费）
- **修复**：映射层补 `shippingAmount: asNumber(row.shippingAmount)`；详情页 商品金额=`(total - shipping).toFixed(2)`、运费=`shipping.toFixed(2)`、预计收入=`total.toFixed(2)`
- **连带收益**：买家端订单详情（用 `money(order.shippingAmount)`）同一数据源，映射补上后一起好
- **验证**：DB 查 `shippingAmount > 0` 的订单核对三行（如 9.99+5=14.99）

## 2. 买家端立即购买四连 bug（多 SKU 商品）
- **症状**：默认款 19.9 ×2 显示商品金额 79.80；切 USDT 通道显示 40.45；返回跳"我的订单"列表；通道"不能切换"
- **根因与修复**：
  - **金额 79.8**：checkout 页 `total = product.price * quantity`，而 `product.price` = **第一个变体价**（product-repository 91 行 `asNumber(firstVariant?.price)`）——用户选的"默认款 19.9"不是首变体（首变体 39.9）→ 39.9×2=79.8。服务端按所选 SKU 算 19.9×2=39.8+运费 0.65=40.45（这才是对的）。
    **修复**：checkout 页按 `params.sku` 在 `entry.operation.skuItems` 里匹配取价（`skuItems.find(i => i.sku === params.sku) ?? skuItems[0]`），total 用 `unitPrice × quantity` 并 toFixed(2)。
  - **40.45 是正常的**（= 39.8 + 首重运费 0.65），收银台按服务端金额——不是 bug
  - **返回跳"我的订单"**：PayCashier.tsx 193 行返回链接**写死** `/account/orders`（kind!=deposit/wallet 时）→ 改为回**该订单详情** ``/account/orders/${view.refs?.[0]?.ref}``（refs 是 intent 的关联单号）
  - **Cancel 按钮 `router.back()`**：历史栈不可控（可能回到订单页）→ 改**明确 Link 回商品页** `/products/${productId}`（记得 import Link）
  - **通道"不能切换"**：checkout 页 radio 本来就能自由点选（提交前）；非 USDT 通道提交先到风控页（payment-restricted），那里有"返回结账 · 切换支付方式"（backHref=原 checkout URL）。提交进收银台后通道锁定是正常设计——先排查再改，别乱加功能
- **验证**：找多 SKU 商品选非首变体 → 立即购买 qty=2 → 金额=所选 SKU 价×qty；提交后收银台金额=同金额+运费

## 3. 商品列表价 vs 详情价不一致（列表 39.9 / 详情 19.9）

- **症状**：商品默认款 19.9，买家主页/商城列表显示 39.9，点进详情又变 19.9
- **根因**：`productFromPrisma`（lib/product-repository.ts）的 `price` 用 `variants[0]`（DB 变体第一条），而详情页 SKU 列表用 `metric.skuItemsJson[0]`（卖家维护的默认款顺序）——卖家调过 SKU 顺序后两个"第一条"不是同一规格
- **修复**：`const metricSkuItems = asSkuItems(metric?.skuItemsJson, undefined);`（**fallback 传 undefined 不传 null**，asSkuItems 的 fallback 参数不接受 null → TS2345）；`const displayPrice = Number(metricSkuItems?.[0]?.price ?? firstVariant?.price ?? 0);` → `price: displayPrice`。一改买家主页/列表/搜索/推荐位全生效（同一 catalog 函数）
- **原则**：详情页默认选中 index 0 = skuItems[0]，**列表价必须与它同源**（skuItemsJson 优先，variants 仅兜底）

## 同类警示
- **多 SKU 商品任何"单价"展示必须按所选 SKU 取价**，`product.price`（首变体）只配当默认值——商品详情/结账/下单/订单详情四处口径要一致
- 收银台/结果页的"返回"链接别写死列表页，能用 refs/orderNo 就带上下文
- 改按钮跳转时 router.back() 是"看起来合理"的坑：历史栈经过支付跳转后不可控，明确 href 永远更稳
