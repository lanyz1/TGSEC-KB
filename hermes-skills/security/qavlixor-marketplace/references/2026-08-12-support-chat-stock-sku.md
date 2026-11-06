# #203 客服系统独立 + 库存/SKU/钱包修复 + 翻译陷阱(2026-08-12 晚 ~ 08-13)

## ★LanguageSync dynamic 覆盖陷阱(高优先, "主体类型"又变回去根因)
- **症状**:改翻译键值后页面仍显示旧文案,或改完又变回去。
- **根因链**:①组件 JSX fallback 文本没改(如 `<label data-i18n="seller.account.entityTypeLabel">主体类型</label>` 只改 translations.ts 键值);②LanguageSync 把页面上 fallback 文本当"未翻译原文"上报机翻,生成 **UiTranslation 表 dynamic 覆盖记录**(source=中文原文,scope=dynamic);③**dynamic 覆盖优先级高于代码翻译键** → 页面显示旧值。
- **修法(双保险)**:①JSX fallback 文本与翻译键值保持一致;②删生产 UiTranslation 里 `source=<旧文案>` 的 dynamic 记录(`prisma.uiTranslation.findMany({ where: { source: { contains: "旧文案" } } })` 后 delete,source 是唯一键)。
- **规则**:任何改文案任务 = 翻译键值 + JSX fallback 文本**同步改**,否则 LanguageSync 会"自动还原"。
- UiTranslation 模型字段:source(唯一,存 key 或中文原文)+ i18nJson(各语言值 JSON);生产校验覆盖:`findMany({ where: { source: { contains: key } } })` 命中 0 才安全。

## ★翻译键批量插入脚本陷阱(fr/en 同值重复插入)
- **症状**:python 脚本按"语言值"做锚点(`"chat.tab.support": "Support"`)在 6 语言区块插新键 → fr 和 en 的值相同(都 "Support")→ 英文块插进 fr 区,键重复 → tsc TS1117 "object literal cannot have multiple properties"。
- **正确做法**:插前先 `grep -n '"键名"' lib/translations.ts` 看各语言**实际值**(可能被 LanguageSync 机翻改过,与源码不一致!);锚点值必须**该语言唯一**;插入后验证 `src.count('"新键"')` = 6 且 tsc 通过。误插入的修复:删重复块(按语言上下文定位,不要按值)。

## 库存乱跳(CatalogVersion 广播完整性)
- `reserveProductStock`(下单扣库存)/ `releaseProductStock`(取消回补)**漏调 `invalidateProductCatalog()`** → 4 实例缓存各执一词,刷新来回跳。
- **规则**:所有改库存/改价/销量写路径必须广播 CatalogVersion(卖家 PATCH、扣/还库存、增/减销量)。全库排查:`grep "stockQuantity: { decrement|increment" app/ lib/`。

## ★批量改库存删光变体(deleteMany(notIn) 误删)
- **症状**:商品管理页批量改库存后,商品变体全被删 → 页面显示"缺货/库存 0"(ProductVariant 空,但 metric.skuItemsJson 还在)。
- **根因**:`syncProductToPrisma` 里 `deleteMany({ productId, sku: { notIn: skuItems.map(sku) } })` —— skuItems 与现有变体不一致时(哪怕顺序/个别缺失)**无脑删掉所有不在 skuItems 里的变体**。
- **修复**:只在"现有变体数 > skuItems 数"时才 deleteMany 多余项;否则保留 upsert 已有变体。
- **数据恢复**:从 `ProductOperationMetric.skuItemsJson` 重建 ProductVariant(Json 字段 Prisma 返回已是对象,**不要 JSON.parse 字符串**);同 sku 跨店铺冲突(另一店用同模板铺了同款)→ 加 `-lv` 后缀;重建后 bump CatalogVersion。

## ★sku 全局唯一 → 商品内唯一(多店铺同模板上架)
- 平台原 `sku String @unique`(全局):100 个店用同一模板铺同款,第 2 个店起全部 `Unique constraint failed`。
- **修复**:schema 改 `@@unique([productId, sku])`(组合唯一);upsert 查找键 `where: { sku }` → `where: { productId_sku: { productId, sku } }`(需 `prisma generate` 后才有该查找键)。
- 迁移前**必须查同 productId 重复 sku 脏数据**(`GROUP BY productId, sku HAVING COUNT(*)>1`),有则先清。
- **deploy.py 的 db push 不带 `--accept-data-loss`** → 改唯一约束等"可能丢数据"的迁移会静默失败但部署继续跑完(h1/h2 200 假象)!需手动补:`cd /www/tiktok && npx prisma db push --accept-data-loss`(生产目录 /www/tiktok,`unset PYTHONPATH`)。

## 钱包口径(用户拍板: 校验单走正规流程计入资金)
- 校验订单(validation)生成即付(paymentStatus=paid),**用户明确拍板计入结算/可提现**,撤销 2026-08-07 安全扫描 S2 的"validation 不计入"排除。
- 两处口径必须一致:`prismaSnapshot`(资金页)+ `refreshSellerWallet`(钱包表/工作台 KPI),都含校验单。改一处必须改另一处,否则工作台余额与资金页对不上。
- 校验单生成后必须调 `refreshSellerWallet`(generateValidationOrders 落库后),否则新订单余额长时间不同步。
- **保留的正确排除**:校验单不扣库存 → 取消/退款/超时关单**不回补库存**(3 处 validation 判断是库存逻辑,勿动)。
- 全库重算脚本可复刻 refreshSellerWallet 计算(paidOrders → pending/available/frozen),遍历 `order.groupBy({ by: ["storeId"] })` 的店铺。

## 批量订单生成(管理端 test-orders)
- **时间参数 {raw, offset} 契约**:前端把 `datetime-local` 输入 `JSON.stringify({ raw: "YYYY-MM-DDTHH:mm", offset: 浏览器时区偏移 })` 传后端。**后端 parseTime 必须兼容字符串 JSON**(value.startsWith("{") 先 JSON.parse 再按对象走),否则 `new Date(str)` → Invalid Date → "开始时间格式无效"。
- 数量上限已删(用户拍板):后端兜底 `Math.max(1, Math.min(count, 100000))`,前端 max 移除;`test-order-generator.ts` 里的 20 上限同步删(立即生成/定时 cron 共用)。
- 定时模式:startTime+endTime 都填 → 登记 ScheduledOrderJob + 逐单 ScheduledOrderItem,`app/api/cron/scheduled-orders` 每 30s 扫描到点落库。

## 工作台 KPI 日期筛选(今日/7/14/30)
- 服务端只查**一次近 60 天已付款订单明细**(含 buyerUserId/guestEmail/createdAt/totalAmount),序列化 `{t,c,u,g}` 传客户端组件,本地聚合切换零刷新。
- 结构:客户端 `DashboardRangeHost`(管 range state)+ `DashboardKpis`(KPI 卡+筛选胶囊)+ `SalesLineChart`(改为受控组件,range 由父级传)。环比:今日↔昨日,N天↔前N天。
- 样式复用 `.sap .seg` 胶囊;新增 `.kpi-range` 同款。

## 客服系统架构(2026-08-12 拍板: 客服与消息中心分离)
- **独立客服页**:买家 `/account/support`(+`[id]`)、卖家 `/seller/support`(+`[id]`)、**客服工作台 `/agent`**(admin 登录,全屏独立页)。
- ChatWorkspace/ChatList 加 `supportOnly` prop:无搜索/无 tab,顶部客服类型发起列表(图标+描述+箭头,借鉴电商客服),下方客服会话列表;`role==="support"` 时不显示发起网格(客服只回复)。
- supportOnly 布局:`.chat-grid.support-only{grid-template-columns:300px minmax(0,1fr)}` 两栏(去 ctx-panel 300px,聊天区拉满);顶部条 `.chat-support-topbar`(标题+在线时间+红色"退出聊天")。
- **消息中心(ChatList 普通模式)去掉 support tab**,只剩 All/Unread(客服不再混入)。
- **客服身份**:AdminUser 加 `supportNickname`;`/agent` 顶部"当前客服:昵称";`/api/messages/[id]` admin 发消息带 `senderName=昵称`(对方看到"客服-昵称");管理端 `/admin/roles`(AdminPermissionsManager)每行可编辑客服昵称。
- 退出聊天 href:`role==="support" ? "/admin" : baseHref.replace(/\/support(?:\/.*)?$/, "")`(客服端 baseHref=/agent 无 /support 后缀,直接用 /admin)。

## 卖家端会话管理(置顶/标未读/删除)
- schema:Conversation 加 `pinned Boolean @default(false)` + `sellerDeletedAt DateTime?`(卖家视角软删除,买家/客服不受影响)。
- API:`POST /api/chat/conversations/[id]/pin`、`/unread`、`DELETE /[id]/hide`;列表排序 `[{pinned:"desc"},{lastMessageAt:"desc"}]`;visibleWhere 卖家分支加 `sellerDeletedAt: null`。
- 标未读 = 清空该会话"对方发来的已读消息" readAt(`updateMany({ senderRole: { not: viewer }, readAt: { not: null } }, data: { readAt: null })`)。
- 前端:会话项 ⋯ 菜单(置顶/取消置顶/标为未读/删除),ChatList 加 `onUpdate` 回调 → ChatWorkspace 本地更新+重排。

## 买家个人中心调整(用户拍板)
- 主页删"资金记录"卡(流水统一在 `/account/funds`,记录列表抽到独立页保留);BuyerBalancePanel 只留余额卡+充值提现弹窗。
- 右下角固定客服悬浮按钮(黑色胶囊)→ /account/support。

## 商品详情 SKU 下方主副图
- `app/products/[id]/page.tsx` pdp-spec 区 SKU 表后加 `.pdp-sku-images`:galleryImages(主图+副图,排除 role=detail 详情大图,与左栏轮播同口径)按 sortOrder 顺序;样式 grid auto-fill minmax(160px,1fr)。

## 验证工具链复用
- 无头验证:cdp 驱动 puppeteer-core@23 + 系统 Chrome;登录先 `fetch /api/auth/login` 拿 cookie 再 goto;React 受控输入用原生 setter + input 事件(js 直接赋 value 不触发)。
- 生产数据脚本:`cd /www/tiktok && node xxx.mjs`(.env.local 手动 parse);Json 字段 Prisma 返回对象;db push 手动补跑;4 实例 restart 用 pm2。
- 测试残留务必清理(测试会话/商品/置顶/软删除都要还原)。
