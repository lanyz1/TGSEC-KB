# 2026-08-11 提交审核慢 + 单价漏映射 + 审核图片 tab

## 1. ★卖家端"提交审核"慢到极致（20-60s 挂起）——写路径禁同步 LLM 翻译

- **症状**：商品管理编辑页点"提交审核"，按钮长时间转圈，慢到极致
- **根因**：`app/api/seller/products/[id]/route.ts`（PATCH）里：
  ```ts
  const i18n = contentChanged
    ? (await buildProductI18n({ title: nextTitle, detail: nextDetail, skuItems }).catch(...)) ?? product.i18n
    : product.i18n;
  ```
  只要内容有变化（标题/详情/规格名——提交审核前基本都改过），就**同步调用 SiliconFlow LLM 翻译整品 7 语言**（单条 11.7s，整品 20-60s），整个请求挂起。
- **修复**：`const i18n = product.i18n;`（完全异步化）——翻译由后台 `scripts/sync-content-i18n.mjs` cron（2 分钟）补译，与新建商品 POST 已异步化（138-140 行注释）同策略，**秒回**
- **类级原则（Qavlixor 翻译铁律之一）**：**所有写路径（POST/PATCH）禁同步 LLM 翻译**。发现新商品/新页面"保存卡灰"先查 `buildProductI18n` / `translate` / SiliconFlow 调用是否在请求主链路上
- 注意：`buildProductI18n` import 可以留着（tsc 不报未用；noUnusedLocals 未开）

## 2. 卖家端订单详情"单价全 39.9"——fulfillment 映射漏 unitPrice

- **症状**：不管买什么商品，订单详情"商品明细"表单价都显示同一个数（如 39.9）
- **排查顺序**（先验证 DB 再怀疑显示层）：`prisma.orderItem.findMany` 查 `unitPrice`——**DB 数据是对的**（39.9/69.9/9.99 各不同），说明问题在读取层
- **根因**：`lib/order-repository.ts` 的 `fulfillmentFromPrisma`（约 144 行）构建 items 时**只映射了 productId/sku/quantity/title，漏了 unitPrice/totalPrice** → 详情页 `const unit = item.unitPrice ?? product?.price ?? 0` 回落 catalog 价
- **修复**：映射补上 `unitPrice: item.unitPrice !== null && item.unitPrice !== undefined ? Number(item.unitPrice) : undefined`（totalPrice 同补）
- **模式**：**"新 DB 字段忘补映射"是本项目金额/显示 bug 第一来源**（shippingAmount/unitPrice 都是这个模式）——显示异常先查 `*FromPrisma` 映射是否带全字段

## 3. 商品审核页图片 tab 点不动——静态 span 假 tab

- **症状**：管理端商品审核页"主图/详情图/包装图/资质图"一排点不动，且只显示第一张主图
- **根因**：`app/admin/products/[id]/page.tsx` 里那排是**四个静态 `<span>` 文字**（`<div className="product-thumb-row"><span>主图</span>...`），无任何点击逻辑；大图只取 `images.sort(sortOrder)[0]`
- **修复**：新建 `components/admin/AdminProductGallery.tsx`（client 组件）：
  - 按 sortOrder 分组：`0=主图 / 1-19=详情图 / 20-39=包装图 / 40+=资质图`（DB 实测分布：0→7001 张、1-19→35807、20-39→53，分组合理）
  - tab 按钮带数量（`详情图（5）`）、点击切换、选中 `.on` 蓝色高亮、**空分组自动隐藏**
  - 审核页改为 `<AdminProductGallery images={...} alt={...} />`，删掉 `const image = ...` 未用变量
- **模式**：**管理端/买家端"一排 tab 点不动"先看是不是静态 span 假 tab**（无 onClick/无 state）——真 tab 必须是 button + 受控切换

## 附：验证技巧
- 生产 Prisma 脚本动态 import：**OrderItem 模型没有 createdAt 字段**（orderBy: {createdAt} 会报错，用 id 排序）
- 图片/金额类 DB 验证：先 `findMany take N` 看分布再下结论，别只看一条
