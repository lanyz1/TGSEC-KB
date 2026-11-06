# 2026-08-11：草稿品牌/运费模板丢失修复（#180）

## 1. 草稿回填品牌名消失——品牌只拼标题不落库

**现象**：发布商品保存草稿后重新进入，品牌输入框空白；运费模板也丢失。

**品牌根因**：`SellerProductForm.submit` 把品牌拼进标题（`composedTitle = brand + title`，slice 60）→ DB 只有标题 → 回填时拆不回品牌 → 输入框空白。

**修复**：Product 表新增 `brand String?`（schema.prisma，deploy.py 的 db push 自动迁移），全链路：
- POST `app/api/seller/products/route.ts`：`brand: typeof body.brand === "string" ? body.brand.trim().slice(0, 40) || undefined : undefined`
- PATCH `app/api/seller/products/[id]/route.ts`：同上但兜底 `product.brand`（保留旧值）
- `lib/product-repository.ts` `syncProductToPrisma` upsert 的 **update 和 create 都带** `brand: product.brand ?? null`；`productFromPrisma` 返回 `brand: row.brand ?? undefined`
- 编辑页 `app/seller/products/[id]/page.tsx` 构建 product 加 `brand: row.brand ?? undefined`
- `SellerProductForm`：`useState(product?.brand ?? "")` 初始化 + payload 带 `brand: brand.trim()`
- Product 类型（`lib/sample-data.ts`）加 `brand?: string`

**★Schema 变更流程（易踩坑）**：改 schema.prisma 后本地 tsc 报 `Property 'brand' does not exist on type ...` —— 本地 Prisma Client 未重新生成。**必须 `pnpm prisma:generate` 后再 tsc**（deploy.py 的 db push 只生成服务器端 client，本地不自动）。

## 2. 发布页看不到已保存的运费模板——下拉硬编码 3 个

**根因**：SellerProductForm 运费模板 AppleSelect options **写死** `["标准模板（首件 5 + 续件 2，满 50 包邮）", "大件模板…", "包邮模板…"]`，从不读卖家在"运费模板"页保存的模板。

**修复**：
- `SellerProductFormProps` 加 `shippingTemplates?: ShippingTemplate[]`
- 新建页 `app/seller/products/new/page.tsx`（改成 async + dynamic）与编辑页：`await listShippingTemplates(scope.storeName)`（`lib/shipping-template-repository.ts`，读 `Store.shippingTemplatesJson`）传 props
- 下拉 options 由模板生成：`pricing === "free"` → `名字（全场包邮…）`，否则 `名字（首件 X + 续件 Y，满 Z 包邮）`；无模板时兜底内联"标准模板"
- **回填**：`/运费模板：(.+)/.exec(product.shippingNote)?.[1]?.trim()` 拆出模板名匹配选中（shippingNote 存的是"运费模板：xxx"文本，submit 里拼装）
- 模板结构：`ShippingTemplate { id, name, scope, pricing: qty|weight|free, firstFee, addFee, freeOver, regions, isDefault, enabled }`

## 3. 坑

- 编辑页追加 import 时注意去重：resolveSellerStore/currentEmail 原本已有 import，patch 追加会 duplicate identifier（tsc 报错），要清理
- 类级模式：**"草稿回填丢 X"一律先查该字段是否独立落库**——只拼进其他字段（标题/备注）的展示值，回填必丢；要么独立字段，要么从持久化文本可逆拆回（运费模板用正则拆）
