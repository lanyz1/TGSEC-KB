# 万邦 onebound（直营店自动铺货数据源）

> 2026-08-11 用户问"还记得万邦那个自动上货调的 API 吗"——代码库/文档实锤：**直营店的货 = 万邦 onebound 采集器铺的**（1688 / 速卖通 / 淘宝）。

## 接入位置

| 组件 | 说明 |
|---|---|
| `lib/importers/onebound.ts` | 万邦采集适配器：调 `item_get`（1688/淘宝共用，返回结构一致）→ 映射 `NormalizedImportProduct` → 交给 `lib/product-import` 通用管线建品。采集层只在这里，管线不感知平台 |
| API 地址 | `https://api-gw.onebound.cn`（文档站 open.onebound.cn/help/api/1688.item_get.html）|
| 配置 | `OneboundConfig`：platform（"1688" \| "taobao"）、key、secret、base、agent（1688 取分销代发价）、lang |
| 入口一（私密） | `/ops-direct`（admin 登录可见，非 admin 404）：输关键词+类目+数量 → 自动采集建店铺货 |
| 入口二（脚本） | `scratchpad/fill-aliexpress.mjs`（**速卖通=主力货源**，中文率仅 ~6% 首选）/ `fill-catalog.mjs`（1688，中文率 ~80% 需大量去图）|
| 文档 | `docs/直营店说明.md`（规模/店名池/登录信息/坑）|

## item_get 映射要点（onebound.ts 内）

- **跨境去中文**：只取 `item_imgs`（干净主图），**明确丢弃 desc_img（中文详情长图）与非图片 URL（埋点像素）**；详情正文由 props（属性 name/value）拼成交替行走既有 7 语言翻译。
- SKU：`skus.sku` 数组 → `parseSkuName`（properties_name 取"第 3+ 项"值段，多维用 " / " 连）；1688 供应商天量库存**封顶 STOCK_CAP=9999**。
- 参数表过滤 `SKIP_PROP_NAMES`：颜色分类/颜色/尺码/尺寸/规格/版本/吊牌价（变体维度/噪音不进详情参数）。
- 调用参数：`CALL_TIMEOUT=15000`（15s 早失败早让位，原 30s 会拖垮整批）、`GET_CONCURRENCY=4`（按次计费不按并发限流）。
- 图片下限 `minImages=5`，不足 5 张干净图不上架。

## 铺货管线

```
采集(onebound item_get) → 去中文图(GPT-5.5 视觉判断) → ×2 定价(下限 $2.99)
→ 按品类哈希分店(14 类 × 4-6 家直营店池, lib/direct-stores.ts CATEGORY_STORE_POOLS)
→ 建 Product+变体+图 → 翻译回填 cron 补 7 语译文
```

- 直营店规模（2026-07-30 实测）：**70 家店 / 6995 个商品**（占全站绝大多数）。
- `Store.storeKind` 三值：normal(真实卖家) / **self_operated(官方直营)** / test。买家端完全按普通店铺显示不露自营字样。
- 直营店保证金 gap 恒=0 是代码自动覆盖（`lib/deposit-rules.ts::isPlatformOperatedStore`），**不是真缴了钱**，别去后台手动充。
- 登录：统一密码 `Qav@Direct2026`，邮箱 = slug + @qavlixor.com（早期 4 家简写：vellora@/voltedge@/copperclay@/summittrail@）。

## 坑

- **铺货/翻译后台任务运行期间严禁 `pnpm build` / `pm2 restart`**（掐断 node 实例整批失败）。
- 铺货传中文品类名时 ssh curl 会 GBK 乱码归错店 → 用 node fetch。
- `ensureCategory` 把中文品类映射到分类树叶子（"厨房餐厨"→"切配工具刀具"），要精准子类得传具体叶子名。
