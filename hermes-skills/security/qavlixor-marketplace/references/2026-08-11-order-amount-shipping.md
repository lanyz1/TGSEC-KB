# 订单详情金额修复（2026-08-11）

## 症状
卖家端订单详情：商品 19.9，买家实付 24.9（含运费 5），但显示"买家运费 0.00、商品金额 24.9"。

## 根因（两个叠加）
1. **数据层映射缺失**：`lib/order-repository.ts` 的 `orderFromPrisma()` 只映射 `total`，**没映射 `shippingAmount`** → `order.shippingAmount` 恒为 undefined。Schema 字段存在（`Order.shippingAmount Decimal @default(0)`），纯属映射漏掉。
2. **前端写死 + 口径错**：`app/seller/orders/[id]/page.tsx` 金额区——买家运费**写死 `0.00 USDT`**；商品金额直接 `order.total`（实付=小计+运费），应显示小计。

## 修复
- `orderFromPrisma` 补 `shippingAmount: asNumber(row.shippingAmount)`（Order 类型 sample-data 已有 `shippingAmount?: number`）
- 详情页金额区：
  - 商品金额 = `(total - shippingAmount).toFixed(2)`
  - 买家运费 = `shippingAmount.toFixed(2)`
  - 预计收入 = `total.toFixed(2)`（实付）
- **买家端同步受益**：`app/account/orders/[id]/page.tsx:163` 本就渲染 `money(order.shippingAmount)`——同一数据源，映射修复后买家端"免运费"误显也一起好了（无需单独改买家端）。

## 验证
生产库 `order` 表 `shippingAmount > 0` 查证：subtotal 9.99 / shipping 5 / total 14.99 ✅（9.99+5=14.99 对账）

## 通用教训
前端"**恒 0 / 恒空 / 恒默认值**"显示（尤其金额/时间/枚举类字段）→ 排查顺序：
1. 先查**数据层映射**（repository 的 row→domain 映射是否漏字段）——本次就是这层，DB 数据一直是对的
2. 再查前端是否**写死占位值**（`0.00 USDT` 这种字面量是危险信号）
3. 最后查口径（total vs subtotal vs shippingAmount 各自含义：subtotal=商品小计 / shippingAmount=运费 / totalAmount=实付）
4. 同一 repository 被多端消费时，修复一处多处受益——修完检查所有消费方（grep `order.shippingAmount` 全仓）
