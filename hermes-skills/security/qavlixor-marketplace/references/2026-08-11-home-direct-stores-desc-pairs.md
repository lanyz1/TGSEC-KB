# 2026-08-11：草稿参数回填 + 主页直营店轮换（#178/#179）

## 1. 草稿回填"产品参数跑到卖点文字"（#178）

**现象**：卖家端发布商品保存草稿后重新进入，产品参数内容全部显示在"卖点文字"框里。

**根因**：`lib/description-pairs.ts` 的 `parseDescriptionPairs` 要求**参数对 ≥3 对**才识别为产品参数表（`pairCount < 3 → 整体降级为 rest`），否则全部进 `rest`（卖点文字）。商家填 1-2 对参数 → 保存 → 回填时全跑进卖点框。`SellerProductForm.buildDetail` 的拦截校验同样是 `filled.length >= 3`（两边口径不一致会互相打脸）。

**修复**（两侧同步放宽为 ≥2 对）：
- `description-pairs.ts`：`if (pairCount < 2)` 才降级
- `SellerProductForm.tsx` buildDetail：`if (filled.length >= 2 && ...)` 卖点首行像属性名的拦截
- 影响面：买家端详情页参数表解析共用同一函数，≥2 对描述会显示参数表（更合理，防误判叙述文本仍靠 ≥2 门槛）

**未放宽**：`isLabelLine` 字符集（汉字/字母开头 ≤16 字符无句读）。若复现"首行参数名含冒号/括号导致全进卖点"，需放宽 LABEL_PATTERN 字符集（会影响买家端解析，谨慎）。

## 2. 买家主页"全部商品"只轮换直营店商品（#179）

**需求**：买家主页（`https://qavlixor.com/`）所有商品轮换区（今日热卖/新品首发/精选/每日推荐）只显示官方直营店商品；普通商家新增商品不上主页（仍正常出现在 /products 列表、搜索、店铺页）。

**实施**：
- 直营店识别：`Store.storeKind === "self_operated"`（schema enum，`lib/direct-stores.ts` 管理）
- `lib/product-repository.ts`：
  - `PrismaProductRow.store` 类型加 `storeKind?: string | null`
  - `prismaCatalog()` include 的 store select 加 `storeKind: true`
  - `productFromPrisma` 返回加 `storeKind: row.store?.storeKind ?? undefined`
- `lib/sample-data.ts` Product 类型加 `storeKind?: string`
- `app/page.tsx`：`liveProducts = catalog.products.filter(p => p.status === "已上架" && p.storeKind === "self_operated")`（所有轮换区切片基于此）
- HomeProductTabs 是纯 UI（数据全由 page.tsx 传入），无需改

**规模确认**：直营店 13+ 家（Nestwell Home 97、Vellora Studio 155、Marlowe & Co 176、Copper & Clay 80…每家 52-176 个已上架商品），轮换池充足。

**验证脚本**（服务器 npx tsx）：
```js
// 直营店商品量
const stores = await p.store.findMany({ where: { storeKind: 'self_operated' }, select: { name: true } });
for (const s of stores) {
  const c = await p.product.count({ where: { store: { name: s.name }, status: 'published' } });
}
```
