# 变体批量删除事故(2026-08-12) — 证据链 + 最终恢复 + sku 唯一迁移

## 症状
Livvy Home(<EMAIL-REDACTED>)店铺 3D 商品库存全变 0/缺货。用户原话:"库存那会不是都改成999了,怎么现在全是0和缺货什么情况"。

## 排查证据链(按顺序)
1. **先查 DB 变体现状**:`prisma.product.findMany({ where: { storeId, category: { slug: { startsWith: "3d-printer" } } }, include: { variants: true } })` → 47 个商品 44 个 `variants: []`,仅 3 个有变体(= 当日 15:xx 用上品工具 POST 补铺的 PETG Basic/PLA Basic/PLA Matte)。
2. **定位事故时刻**:nginx access.log grep `PATCH /api/seller/products` → 14:23 一串 Chrome 151 `referer=https://qavlixor.com/seller/products`(商品管理列表页批量改库存)→ `metric.updatedAt` 同为 14:23。**批量改库存 = 嫌疑操作**。
3. **恢复源确认**:`ProductOperationMetric.skuItemsJson` **完好**(47 商品全有,含 sku/name/price/stock/barcode 数组)。stock 分布:9999×60 / 999×80 / 499·500×32 / **0×128**。
4. **根因**:`syncProductToPrisma`(lib/product-repository.ts ~370) `deleteMany({ where: { productId, sku: { notIn: skuItems.map(sku) } } })` — 批量 PATCH 的 skuItems 与商品原变体集合不一致时,`notIn` 删光原变体。

## ⚠️ 排查期自踩的坑(重要,别重复)
- **Prisma Json 字段已是对象**:`skuItemsJson` 用 Prisma 客户端读出是**已解析对象/数组**,不是字符串——再 `JSON.parse()` 会抛 `SyntaxError`,被 `try/catch` 吞掉后 `items=[]`,**误判"数据全空"**(第一次检查输出"metric空 47"是错的,实际数据完好)。判断用 `Array.isArray(m.skuItemsJson) && m.skuItemsJson.length`,不要 parse。
- **Product 模型无 inventory 字段**(schema ~323):库存只存在于 `ProductVariant.stockQuantity`;`ProductOperation`/`productFromPrisma` 里的 inventory 是派生(变体求和)。include 时直接 `variants: true` 即可。
- **ProductOperationMetric 无反向 relation**(schema ~794 无 relation 字段)→ 不能 `include: { operationMetric: ... }`(报 Unknown argument),单独 `findMany({ where: { productId: { in: ids } } })` + `Object.fromEntries(metrics.map(m => [m.productId, m]))`。
- **`variants: { none: {} }`** = 查无变体商品的标准 Prisma 写法。
- **groupBy 坑**:`prisma.order.groupBy({ by: ["status"] })` 报 `Invalid value for argument by. Expected OrderScalarFieldEnum` — by 必须用模型真实标量字段。
- **sku 全局 @unique(事故时)** 跨商品同名 sku 会撞唯一约束。
- 服务器 .mjs 脚本:`import { PrismaClient } from "@prisma/client"` 用 `await import()`,`.env.local` 正则逐行注入 env;禁 TS 类型注解。
- **⚠️ bash heredoc + 复杂正则会炸**:服务器验证脚本里写 `/Unique[^\n]*/` 之类,heredoc 经过 shell 转义后 node 报语法错且输出被污染——**node 脚本输出用简单 ASCII 标志(CROSS-OK / DUP-BLOCKED / CLEANED)再 `grep -E "CROSS|DUP|CLEANED"`,别用字符类正则**。
- **⚠️ node --check 本地语法验证**:恢复脚本先 `node --check _q_xxx.mjs` 再上传,修掉多余括号等 SyntaxError(实测 `count({...} });` 多一个 `}`)。

## 最终恢复(已完成,用户拍板 stock 统一 9999)
**用户拍板点(B)**:metric 里 stock=0 的 128 个 SKU **全部恢复为 9999**(不保持 0——铺货偏好库存拉满)。恢复时若用户没拍板,必须问,别自己定。

```js
// ① 清空目标店铺 3D 商品全部变体(防残留/sku 冲突)
const delAll = await prisma.productVariant.deleteMany({ where: { productId: { in: ids } } });
// ② 从 metric.skuItemsJson 逐商品重建(stock 统一 9999)
for (const item of items) {
  let sku = String(item.sku || `${p.id}-SKU`);
  // ⚠️ sku 全局唯一冲突(事故时 schema 还是 @unique): 被其他店铺(如 Nexora 用同模板新铺)占用时
  // findUnique({ where: { sku } }) 查占用者, 非本商品则加后缀区分
  const holder = await prisma.productVariant.findUnique({ where: { sku }, select: { productId: true } });
  if (holder && holder.productId !== p.id) sku = `${sku}-lv`;
  await prisma.productVariant.create({ data: { productId: p.id, sku, optionValues: [String(item.name || "默认款")], price: Number(item.price ?? 0), stockQuantity: 9999 } });
  nextItems.push({ ...item, sku, stock: 9999 });  // 同步 metric,防下次读 metric 显示旧 0
}
// ③ 同步 metric.skuItemsJson 里 stock=9999 + bump CatalogVersion
await prisma.productOperationMetric.update({ where: { productId: p.id }, data: { skuItemsJson: nextItems, updatedLabel: ... } });
await prisma.catalogVersion.upsert({ where: { id: 1 }, update: { version: { increment: 1 } }, create: { id: 1, version: 1 } });
```
**结果**:47 商品 / 300 变体 / 无变体 0 / 0 库存变体 0 / 总库存 2,999,700(=300×9999)。冲突 sku 加 `-lv` 后缀区分(Nexora 新铺商品不受影响)。

## 代码防御(已实施 commit 65d6cdb)
`syncProductToPrisma` 的 deleteMany 改为**只在"现有变体数 > skuItems 数"时才删多余项**:
```ts
const existingVariants = await prisma.productVariant.findMany({ where: { productId: product.id }, select: { sku: true } });
if (skuItems.length > 0 && existingVariants.length > skuItems.length) {
  await prisma.productVariant.deleteMany({ where: { productId: product.id, sku: { notIn: skuItems.map((item) => item.sku) } } }).catch(() => null);
}
// 其余情况靠 upsert(已存在 update / 不存在 create)对齐,绝不删变体
```
**规则**:任何"skuItems 与变体集不一致就 deleteMany"的逻辑都是高危——批量操作传空/兜底 skuItems 会静默删光变体。所有改库存/变体写路径结尾 `await invalidateProductCatalog()`。

## sku 唯一约束迁移:全局 @unique → 商品内 @@unique([productId, sku])(commit 7295798)
**触发**:用户前瞻提问"后面有 100 个店铺全上架这同样的商品,会不会还出现类似情况"——答案是**会且必然**:桌面模板 sku 固定,`sku String @unique` 全库唯一,第 1 店占住 sku,第 2~100 店同模板上架全部 `Unique constraint failed`。本次已实测 Nexora 新铺 PETG Translucent 与 Livvy 冲突。

**迁移四步**:
1. **查脏数据**:`SELECT "productId","sku",COUNT(*) FROM "ProductVariant" GROUP BY "productId","sku" HAVING COUNT(*) > 1` — 0 组才能安全迁移。
2. **schema**:`sku String @unique` → `sku String` + 模型表尾 `@@unique([productId, sku])`。
3. **代码唯一依赖点**:`productVariant.upsert({ where: { sku: item.sku } })` → `where: { productId_sku: { productId: product.id, sku: item.sku } }`(组合唯一自动生成 `productId_sku` 查找键)。**改完必须 `npx prisma generate` 重新生成 client,否则 tsc 报 `'productId_sku' does not exist in type 'ProductVariantWhereUniqueInput'`**。验证:reserve/release 的 `findMany({ where: { productId } })` 内存找 sku 天然限定商品内,兼容。
4. **生产迁移**:**⚠️ deploy.py 的 db push 不带 `--accept-data-loss`——改唯一约束(删旧索引建新索引)Prisma 提示可能丢数据直接失败,但 deploy.py 不检查 db push 结果继续跑完部署(代码已上新、schema 没迁!)** → **必须手动补跑 `npx prisma db push --accept-data-loss`**(已确认无脏数据,实际零丢失)→ `pm2 restart tiktok-marketplace --update-env` 加载新 client。

**验证(生产脚本,ASCII 标志输出)**:跨店铺(Livvy+Nexora)同 sku 各建变体 → 都成功 `CROSS-OK`;同商品重复 sku → 被拦 `DUP-BLOCKED`;测试数据清理 `CLEANED`。

**业务含义**:不同店铺上架同款商品(同 sku)完全正常;同一商品内 sku 重复仍拦截。订单存 `skuSnapshot`(快照不反查)、买家端按 `productId+sku` 组合查找——全部兼容,无破坏。历史 `-lv` 后缀变体建议保留(避免历史订单 sku 对不上)。

## 后续检查清单
- 恢复后卖家端/买家端强刷,确认库存数字与 metric 一致。
- 全库再扫一遍 `variants: { none: {} }` 的无变体商品(可能还有 6 个非 3D 店铺床品历史数据)。
