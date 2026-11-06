# 万邦 onebound 铺货（直营店货源）— 2026-08-11 拓竹案例整理

## 平台与凭证
- 万邦 onebound 开放平台：https://open.onebound.cn（帮助文档：`/help/api/{platform}.item_get.html`）
- API 网关：`https://api-gw.onebound.cn`（`lib/importers/onebound.ts` 的 DEFAULT_BASE）
- 凭证：服务器 `.env.local` 的 `ONEBOUND_KEY` / `ONEBOUND_SECRET`（已配）
- 平台值：`1688` / `taobao` / `aliexpress`（item_get/item_search 返回结构各平台一致，适配器共用）

## 核心模块
- `lib/importers/onebound.ts`：`mapOneboundItem`（纯映射）/ `fetchOneboundItem`（item_get，15s 超时）/ `searchOnebound`（item_search）/ `importFromOnebound`（numIids 批量）/ `importByKeyword`（关键词）
- `lib/product-import.ts`：`importProducts`（通用建品管线：markup 定价/defaultStock/cleanImages 去中文图/minImages/priceMin/**storeName 强制挂靠**/deadline 时间预算）
- `lib/direct-stores.ts`：`ensureDirectStore(name)`（幂等建 self_operated 店：User+SellerAccount+Store，统一密码 DIRECT_STORE_PASSWORD）
- `lib/product-repository.ts`：`ensureCategory(name, {parentSlug, autoActive, committed})`（直营店自定义类目免审 active）

## 铺货入口
1. 私密管理页 `/ops-direct`（仅 admin，表单走 POST `/api/admin/products/import-source`）
2. 后台脚本（服务器 `/www/tiktok` 下 `node scripts/fill-*.mjs`）→ 同样调 import-source API

## import-source API（POST /api/admin/products/import-source）
参数：`platform` / `keyword` 或 `numIids` / `category` / `maxItems` / `markup` / `minImages` / `cleanImages` / `priceMin` / `storeName`（2026-08-11 新增）/ `budgetMs`（时间预算，默认 100s 上限 240s）
- **storeName 传了会自动 ensureDirectStore 建店 + 全部商品强制挂靠该店**（不传则按类目池哈希分店）
- 返回 `{ok, fetched, mapped, report:{created,updated,skipped,failed}, errors, elapsedMs}`；skipped 原因见 report.items warnings（图片不足/清洗后不足/价格低于 priceMin）

## ★脚本认证模式（重要）
- **旧 cookie 格式 `gm_role=admin; gm_email=...` 已失效**（fill-leaves.mjs 里的已不能用）
- 正确：脚本先 POST `/api/auth/login`（role=admin）→ 从 Set-Cookie 提取 `gm_session=`（httpOnly 签名 cookie）→ 铺货请求带 `Cookie: gm_session=...`
- 注意：`.mjs` 里不能写 TS 类型标注（`as string[]` 会 SyntaxError）
- admin 文档密码可能失效（DB `AdminUser.passwordHash` 被改）→ 用 `lib/password.ts` 的 hashPassword（`sha256:salt:hash`）重置回文档密码

## ★平台选择：速卖通首选，不要 1688
- 项目文档结论（fill-leaves.mjs 头部注释）：1688 主图普遍带中文，图片清洗 fail-closed（宁可图不足不上架也不放中文图）→ 采回货绝大多数被过滤，产出极低
- 速卖通（aliexpress）：英文图干净（~6% 中文率）、美元价直接定价；拓竹官方店全系在售
- **cleanImages=true 会误删速卖通图导致跳过**（实测）→ 速卖通铺货用 `cleanImages: false`

## ★搜索结果要品牌过滤
item_search 按关键词返回会混入兼容配件/竞品（BIGTREETECH/Creality/SUNLU/Anycubic 等）：
- 脚本先本地调 item_search → 过滤（如 isBambu: title 含 "bambu"/"拓竹"）→ 传 numIids 数组给 import-source
- 已入库的杂牌要清理：按 storeId 查商品 → title 不匹配品牌的删（先删 productImage/productVariant 子表）

## 拓竹案例（2026-08-11 已落地）
- 店铺：**Nova Print Studio**（nova-print-studio，self_operated，登录邮箱 <EMAIL-REDACTED> + 统一密码）
- 分类：新增"3D打印机"（父类 active；可再挂"整机/耗材"子类 parentSlug）
- 关键词：bambu lab 3d printer / filament / ams / p1s / a1 / x1c / a1 mini / pla / petg / abs
- 定价：速卖通美元价 ×1.5（markup=1.5，minImages=4）
- 结果：31 商品 published（打印机 P1S/P1S Combo/X2D/A1 mini/P2S + 耗材 PLA/PETG/PC/PA6-GF/TPU + AMS 配件）
- 脚本：`scripts/fill-bambu.mjs`（改 KEYWORDS 数组可扩品，重复跑 upsert 不重复建）

## 部署警告
- 铺货/翻译后台任务运行期间**严禁 `pnpm build` / `pm2 restart`**（会掐断 node 实例导致整批失败）
- 铺货跑完才部署
