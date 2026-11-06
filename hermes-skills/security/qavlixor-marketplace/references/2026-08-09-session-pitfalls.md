# 2026-08-09 会话新坑速查（定时创建/时区/actor/部署/切语言）

本文件记录 2026-08-09 一次大型维护会话踩过的坑与修复，按类目归档。

## 1. 切语言不生效（getTranslation SSR 固化）—— 全站通用
- **根因**：服务端组件的 `getTranslation()` 是 SSR 固化的（页面加载时算好语言写进 HTML）。切换语言后客户端 LanguageSync 只更新带 `data-i18n` 标记的元素，SSR 固化文本更新不到 → 必须手动刷新才变。
- **修复三层**：
  1. 服务端组件文本尽量用 `data-i18n="key"`（客户端实时翻译，切语言即时生效）
  2. 客户端组件用 getTranslation（如按钮）需监听 `qavlixor-language-change` 事件强制重渲染（`useState` tick）
  3. **全局兜底**：LanguageSync 的 `handleLanguageChange` / `handleStorage` 在 `scheduleApply()` 后加 `router.refresh()`（防抖 400ms，`window.clearTimeout` + 模块级 timer）—— 全站切语言一步到位，无需手动刷新。LanguageSync 挂根布局 `app/layout.tsx`，全站生效。
- 用户原话："切换语言老是点击之后不能一步到位，需要自己手动刷新才能生效" —— 此机制上线后闭环。

## 2. 时区偏移 bug（前端 toISOString 依赖浏览器时区）
- **症状**：管理端选开始时间 23:15-23:20，订单 createdAt 却是 06:15 UTC（=14:15 本地，早 9 小时）。
- **根因**：前端 `new Date("2026-08-09T23:15").toISOString()` 按浏览器时区转 UTC；服务器 UTC 环境对无时区字符串解析不同，前后不一致。
- **修复一（时间戳）**：前端改传 **Unix 毫秒时间戳**（`String(new Date(x).getTime())`，时区无关）；服务器 `parseTime` 兼容解析（number / 纯数字串 / ISO 字符串）。
- **修复二（最终方案，时间戳仍偏移时）**：用户实测传时间戳后仍偏移 +4h（选 12:57 存 16:57Z）——因为 `new Date("2026-08-09T12:57")` 解析本身依赖浏览器时区设置。**最终方案：前端传 `{raw: "2026-08-09T12:57", offset: new Date(raw).getTimezoneOffset()}`**（raw=用户填的本地墙钟原样，offset=浏览器报告的分偏移），服务器：
  ```ts
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  const asUtc = Date.UTC(y, mo-1, d, h, mi) + Number(offset) * 60_000;  // 注意是 + 不是 -
  ```
  `getTimezoneOffset()` 定义 = UTC−本地（分钟），UTC+8 为 −480 → `Date.UTC(raw) + (−480min)` = 04:57Z ✅。本地验证：UTC+8 填 12:57 → 04:57Z → 服务器 toLocaleString 显示 12:57。
- **教训**：① 公式方向第一版写反（− offset）→ UTC+8 得到 20:57Z，先用 node 本地跑一遍再部署；② 时间传递链路不要依赖任何一端时区解析的一致性，显式传墙钟+偏移最稳；③ 用户报"时间还是不对"优先怀疑浏览器旧 JS 缓存（getTime/toISOString 旧版本未生效），让用户强刷再复测。

## 3. 售后列表 actor 判定 —— parseHistoryEntry 返回中文标签
- `lib/aftersale-reason.ts` 的 `parseHistoryEntry` 解析出的 `actor` 是**中文标签**（"商家"/"平台"/"买家"），不是英文码。
- 判定必须写 `h.actor === "买家"`。本会话 bug：写成 `h.actor === "buyer"` 永不匹配 → "买家补充材料"徽标/文案永远不显示，用户反馈"没改动"。
- 详情页时间线 `actorKeys[entry.actor]` 同理走中文。

## 4. 售后证据 CDN 白名单
- 生产上传走对象存储（`https://cdn.qavlixor.com/...`），但证据白名单（2026-08-07 安全扫描 L3 加）只认 `/api/upload-files/` 和 `/uploads/` → CDN URL 全被过滤，`evidenceJson` 存空，卖家端看不到证据。
- 修复：白名单正则加 `^https:\/\/cdn\.qavlixor\.com\/`（自有域名安全，外链追踪像素仍拒）。
- 涉及两处：`app/api/orders/[id]/aftersale/route.ts`（申请）+ `app/api/aftersales/[id]/evidence/route.ts`（补充证据）。
- 排查经验：全库 evidenceJson 几乎全空是"证据根本没存进去"的信号，先查写入端白名单，别先怀疑渲染。

## 5. 部署包自我包含事故（tar.gz EOF）
- **症状**：部署连续失败，`gzip: stdin: unexpected end of file`；本地 `gzip -t` 却 OK，文件大小一致。
- **根因**：`qav-deploy.tar.gz` 被 git 跟踪了 → `git archive` 把它打包装进 tar 里 → 服务器解压时 tar 把包里的 gz 解压**覆盖正在读取的 gz 文件** → EOF。
- **修复**：`git rm --cached qav-deploy.tar qav-deploy.tar.gz` + `.gitignore` 排除；包从 25MB 缩到 ~3.6MB。
- **通用教训**：部署包（tar/tgz）绝不能被 git 跟踪。

## 6. 校验订单定时创建（ScheduledOrderJob 模式）
- **需求**：管理端选时间范围（如 23:15-23:20）生成校验订单 → 订单**到点才落库出现**（卖家端到点才看到），不是立即生成。
- **架构**：
  - 新表 `ScheduledOrderJob`（jobNo/adminEmail/storeIds/count/statusMode/startTime/endTime/status）+ `ScheduledOrderItem`（jobId/storeId/plannedAt/status/orderNo）
  - `/api/test-orders`：startTime+endTime 都填 → **登记计划**（每单计划时间=区间内随机升序，store 轮流分配）；不带时间 → 立即生成
  - `/api/cron/scheduled-orders`（POST，CRON_SECRET 鉴权）：扫描 `plannedAt <= now` 的 pending 条目 → 按 job 分组 → **按 storeId 再分组**调用 `generateValidationOrders` → 标记 done + 回填 orderNo
  - `scripts/process-scheduled-orders.mjs`：fetch 内部 API；crontab 每分钟 + `flock -n` 防重入
  - 管理端 UI：生成后提示"已登记定时生成" + 计划列表（15s 轮询，进度条）
  - 生成核心提取到 `lib/test-order-generator.ts`（立即/定时共用，`plannedTimes?: Date[]` 参数）
- **坑**：
  - crontab 行必须**内联环境变量**（`CRON_SECRET=xxx node scripts/...`），否则脚本读不到 env → API 401；服务器 `.env.local` 也要有 CRON_SECRET（API 端 `!process.env.CRON_SECRET` 直接拒）
  - 同店多条计划 → 总数算错（count=1 + storeIds 去重）→ **按 storeId 分组调用**（count=该店条数）
  - `db push --skip-generate` 后 build 类型检查失败（新模型不在 Prisma Client）→ 必须再 `prisma generate`
  - `.mjs` 脚本禁 TS 类型标注（`const keep: string[] = []` 是 SyntaxError）；`node --check` 先验语法
  - 服务器时区是 UTC；订单号 `generateOrderNo` 里的时间戳是 UTC 时刻

## 7. SKU 上限 20 + 存量收敛
- 用户拍板：SKU 上限 10 → **20**，存量商品只留 20 个。
- 发品/编辑 API（`app/api/seller/products/route.ts` + `[id]/route.ts`）硬校验 `skuItems.length > 20` → 400"每个商品最多 20 个 SKU"。
- 表单（`components/SellerProductForm.tsx`）：`addSku()` 超限不添加；"添加规格"按钮**始终保留可点**（第 21 次点击时表单内 notice 提示上限，7 语言键 `seller.productForm.skuLimit`）。
- **交互教训**：最初做的是"20 个时按钮隐藏"，用户反馈"超过20个直接就不能新增了"（体验差）→ 改为按钮保留可点 + 点击提示。**上限类输入别藏入口，点不动时给提示**。
- 存量收敛脚本 `scripts/trim-over-sku.mjs`（`--dry-run` 预演）：
  - 保留策略：①订单引用优先（`OrderItem.variantId` + `OrderItem.skuSnapshot` 都查）②其余按 `sku` 升序补足 20
  - 生产实测：超 20 商品 784 个，删 32,171 SKU，保护 15,680（ProductVariant 74,305 → 42,135）
- **坑**：`ProductVariant` 没有 `createdAt` 字段（用 `orderBy: { sku: "asc" }`）；`.mjs` 不能写 TS 类型标注。
- 注意：删除后 `OrderItem.skuSnapshot` 孤儿主要是历史规格名（"普通版"x280、"旋钮版"x120，早期订单存规格名非编码），与删除无关，订单展示走快照文本不受影响。

## 8. 物流 lastEvent 乱码（17TRACK JSON 兜底）
- `lib/logistics-provider.ts` parse 17TRACK 响应时，rejected（无跟踪信息）分支 `readNestedText(rejected)` 读不到 `error.message` → 兜底 `JSON.stringify(payload).slice(0, 260)` 把整个响应塞进 lastEvent → 总后台显示 JSON"乱码"。
- 修复：rejected 时读 `error.message` 作可读文案，不再拼 JSON；存量含 JSON 的 lastEvent 已清洗。
- 商家端/总后台差异原因：商家端显示发货时表单快照（干净），总后台读最新查询结果（脏）。

## 9. 用户布局意图教训
- 用户说"这两个有点太靠两侧了"（订单详情页顶栏）→ 以为是布局方式问题改成 center，用户不满意（"靠左靠右但不贴边+上下居中"）。
- **教训**：用户说"太靠两侧"通常指**贴边问题**（要留 padding），不是要改 space-between 布局；订单号靠左、返回按钮靠右是期望默认，`justify-content: space-between` + `align-items: center` + 适量 padding 即可。

## 10. translations.ts 插键语言区错位（checkout 补键实战，高频坑）
- **语言区顺序不固定（别依赖）**：早期观察是 `zh → en → es → fr → pt → ru → ar`，但本会话后段实测 `account.rma.actor.seller` 是 `es → fr → pt → ru → ar → zh → en`（75/2105/4136/6168/8200/11840/14791 行）——不同键组因增量插入历史顺序不同。**正确姿势：永远按各语言区锚点值定位**（`grep -n '"键名"'` 看分布确认各区实际位置），不要假设固定顺序。
- **插键锚点必须用语言特定值**：如 `"ui.cn.94": "Receipt Confirmed"` 只匹配 en 区、`"Recibo confirmado"` 只匹配 es 区、`"已确认收货"` 只匹配 zh 区。用裸键名（`"ui.cn.95":`）做 replace 锚点会匹配**文件里第一个出现处**（常是 zh 区），把其他语言值插错区 → TS1117 重复键。
- **插键前先查键号占用**：`grep '"ui.sel.321"'`——本会话 ui.sel.321 已被"取消失败"占用，误插后 JS 对象重复键被后者覆盖（值悄悄变错，运行时才暴露）。
- **插入后验证**：`grep '"ui.cn.97"'` 应为 **7 处**，且每处值与其所在语言区匹配（按行号 + 值语言判断）；`npx tsc` 0 错才算过。
- SiliconFlow 翻译偶发超时（60s）→ 短文案**手工直译兜底**（6 语言人工写），别死等重试。
- 误插修复法：① 删重复块（按值内容定位）② 按各语言 `ui.cn.94` 值锚点重插 ③ tsc 验证。

## 11. data-i18n-raw = 跳过翻译（动态中文值不翻的根因）
- LanguageSync（components/LanguageSync.tsx ~354 行）：`parent.closest("[data-i18n-raw]")` → return false（**明确不翻译**）。任何动态中文值（订单/资金状态、后端返回文本）若被 `data-i18n-raw` 包裹，切语言永远不翻。
- 修复：动态中文值改 `<DynamicText kind="status">`（走词典翻译）；`data-i18n` 仅用于静态键文本。
- 实战：买家中心资金记录状态（"已到账/处理中/已打款/已驳回/已支付"）原带 `data-i18n-raw` → 用户报"我的账户页中文翻译英文转化不了"（/account 页面，而 /account/orders 正常）→ 去 raw 改 DynamicText 闭环。
- 同文件连带坑：fallback 文案用错键号（"提现"误用 `ui.sel.155`=上传主图，正确键 `ui.sel.303`）；无标记文案（"暂无记录"）要补键（`account.dash.noRecords`）。
- **排查步骤**：页面"切语言不翻"先扫 `data-i18n-raw` 和硬编码中文（`grep -n '>[^<{]*[\u4e00-\u9fff][^<{]*<'` 排除已标记行），别直接怀疑 LanguageSync。

## 12. 按钮/链接漏 data-i18n 标记（checkout 实战）
- `app/checkout/page.tsx:103` "返回购物车" `<Link>` 无 data-i18n（同页 CheckoutCartPanel 有 `ui.fix.102`）→ 补 `data-i18n="ui.fix.102"`。
- 排查法：全库搜中文文案出现处，逐个核对是否有 data-i18n / getTranslation / DynamicText 包裹；同页同类元素（如两个"返回购物车"）一个有标记一个没有 = 漏标典型。

## 13. 纯文本元素漏交互链接（购物车商品/店铺点击无效）
- **症状**：用户报"购物车里的商品点击进不了详情页、点店铺进不了店铺页"。
- **根因**：CartView（components/buyer/CartView.tsx）商品标题/缩略图是**纯文本**（`<DynamicText as="h3">` 没包 Link）、店铺名也是纯文本 → 点击无反应。
- **修复**：
  - 商品标题+缩略图包 `<Link href={/products/${item.productId}}>`（整块 bct-prod 包 Link，加 textDecoration:none; color:inherit）
  - 店铺名包 `<Link href={/stores/${group.storeSlug ?? encodeURIComponent(group.store)}}>`（店铺页 /stores/[id] 支持 OR: [{slug}, {name}] 查询 → 旧数据无 slug 用店铺名也能进）
  - **数据链路**：CartItem（lib/cart-storage.ts）加 `storeSlug?: string` 字段；ProductBuyBox 加 storeSlug prop；PDP（app/products/[id]/page.tsx）传 product.storeSlug；addCartItem 一并存储；groupCartItems 的 group 结构加 `storeSlug: storeItems[0]?.storeSlug`
- **排查法**：用户报"点击 X 没反应/进不去"先 grep 该元素渲染处有没有包 Link/a（纯文本 h3/span/strong 是典型漏链接点），再查数据是否带跳转所需字段（如 storeSlug）。

## 14. i18n 数据字段已随查询返回但渲染层漏用（commodityI18n 实战）
- **症状**：用户报 /account 我的账户页订单表格商品名（"新白色巧克力抹茶派 手工脆脆减压手工球玩具…"）切英文还是中文。
- **根因**：`lib/buyer-orders.ts` 的 `getBuyerOrderRows` 早就返回 `commodityI18n`（首件商品七语言标题，注释写"data-i18n-map 用"），但 `app/account/page.tsx:142` 渲染 `<td>{order.commodity}</td>` **纯文本**，i18n 数据根本没用上。
- **修复**：`<td><DynamicText value={order.commodity} kind="product-title" translations={order.commodityI18n} /></td>`（translations prop 直取商品 i18nJson，零词典依赖、秒级生效）+ 补 DynamicText import。
- **通用排查**：中文残留排查不要只找"无标记文案"，还要查**数据层已带 i18n 字段但渲染层没消费**（grep 数据源字段名 → 看页面是否用了；注释声称"给 X 用"但实际没接是典型）。相关：`lib/buyer-orders.ts:15 commodityI18n`、订单详情/列表页同款。

## 15. 动态统计值：数字与单位必须分离（getTranslation 拼接整段 → DynamicText 查不到）
- **症状**：店铺详情页（app/stores/[id]/page.tsx）统计框"1 products / US / 7 orders"切西语不切换（用户截图"圈住的地方"）。
- **根因**：`<DynamicText value={(n) + getTranslation(lang, "ui.sel.112")} kind="operation" />` —— getTranslation 是 SSR 固化拼接成整段（"1 products"），切语言后 DynamicText 拿整段查词典查不到 → fallback 原文。
- **修复**：数字与单位分离，单位用 data-i18n（客户端实时翻译）：
  ```tsx
  <span>{storeProducts.length} <span data-i18n="ui.sel.112">{getTranslation(currentClientLanguage(), "ui.sel.112")}</span></span>
  ```
- **通用规则**：凡"数字/变量 + 单位/标签"的动态文案，**禁止 getTranslation 拼接整段丢给 DynamicText**；数字裸渲染 + 单位 data-i18n 分离。全站同款：订单数、件在售（`store.pillForSale`，原带 data-i18n-raw 一并改掉）、金额单位等。
- 验证：切语言即时生效（data-i18n 客户端处理），SSR 首屏也正确（getTranslation 当前语言）。

## 16. 动态词典源串必须与页面实际渲染值完全一致（含换行/标点）—— 补了词典仍不翻的根因
- **症状（用户二次反馈）**：rma 售后时间线"拒绝原因：买家举证不足\n拒绝"切英文显示 `Reject原因：买家举证不足 Reject`（半翻译）；第一次补词典（源串"拒绝原因：买家举证不足"）后**仍然不翻**——用户报"还有遗漏的中文，没有完全做完"。
- **根因**：
  1. 售后 reason 里 text 实际是 **`拒绝原因：买家举证不足\n拒绝`（含换行）**——`parseHistoryEntry` 正则 `(.*)$` 的 `.` **不匹配换行** → text 被截断成"拒绝原因：买家举证不足"（\n拒绝 丢失），页面实际渲染值是完整含换行的串。
  2. 补词典用的源串（无 \n拒绝）**与页面实际查询值不一致** → UiTranslation 精确匹配（source 唯一）查不到 → 永远显示原文。
- **修复**：
  1. `lib/aftersale-reason.ts` 的 HISTORY_PREFIX 正则 `(.*)` → **`([\s\S]*)`**（完整保留换行文本）。
  2. 补词典前**先查生产实际值**：`JSON.stringify(row.reason)` 看真实换行/标点（`\\n` 可见），源串必须逐字符一致。
- **通用排查**："词典补了仍不翻"→ 先在生产库把页面实际渲染的字符串 `JSON.stringify` 打出来，与词典 source 逐字符比对（换行/全角冒号/空格都是坑）；数据层文本含 `\n` 时，解析正则用 `[\s\S]*` 而不是 `.*`。
- 注意：动态词典有 localStorage 缓存（`qav-dynamic-dict-v1`），补词典后用户需**硬刷新（Ctrl+Shift+R）**才拉新词典；后台 fetch 也会增量刷新但非即时。

## 17. 搜索只匹配中文标题（其他语言搜不到）—— 匹配池加入 i18nJson 标题
- **症状**：用户报"只有中文搜'手机壳'能搜出来，其他语言不行；英文直接搜 phone case 也应该搜出来"。
- **根因**：`app/search/page.tsx` 的 `searchProducts` 匹配池只有 `${item.title}${item.category}${item.store}`（全中文）→ 英文/西语搜索词 fuzzyScore 为 0 搜不出。
- **修复**：匹配池拼入 `item.i18n?.title` 各语言标题：
  ```ts
  const i18nTitles = item.i18n?.title ? Object.values(item.i18n.title).join(" ") : "";
  const haystack = `${item.title}${item.category}${item.store}${i18nTitles}`.toLowerCase();
  ```
- 验证：本地 node 直接跑 fuzzyScore 模拟（英文搜 "phone case" 带 i18n 命中 1.0，不带 0）。商品 i18nJson.title 全量（6997/6997）已有数据，无需回填。
- **通用规则**：买家端任何语言都该能搜到内容时，搜索匹配池要包含 i18nJson 各语言字段（title 是主字段；类目/描述如有 i18n 同理）。

## 18. 级联删除店铺（外键顺序 + Store 模型字段坑，2026-08-09 删 4 测试店）
- **需求**：删测试店铺（星桥优选店/小飞的百货店铺/The beginning.../南星），订单/物流/售后/会话/钱包/保证金/卖家账号全清。
- **外键删除顺序（必须按序，否则 Foreign key constraint violated，本会话踩 3 次）**：
  1. `OrderItem`（orderId）
  2. `PaymentTransaction`（orderId）
  3. `Shipment`（**orderId** —— `store` 字段是 String 但 Prisma 不接受 `{ in: names }` 删除）
  4. `Order`（storeId）
  5. `SellerWallet` / `SellerDeposit`（storeId —— 不删会挡 Store 删除）
  6. `storeFavorite` / `Conversation`（storeId）
  7. `Store`（id）
  8. `SellerAccount`（id，从 `Store.sellerAccountId` 收集；**不是** storeId 查询）
- **模型字段事实（查询/删除前先核对 schema）**：
  - `Store` 无 `reviewStatus`（用 `status`）；有 `sellerAccountId` 外键指向 SellerAccount
  - `Shipment` 关联订单用 orderId；`afterSaleCase` 无 storeId（用 `storeName: { in: names }` 删）
  - 模型名是 `sellerWallet`/`sellerDeposit`（写 `storeWallet`/`storeDeposit` 会报 "Cannot read properties of undefined (reading 'deleteMany')"）
  - `ProductVariant` 无 `createdAt`（排序用 `sku`）；`OrderItem` 无 `createdAt`（时间走 Order）
- **流程**：删除前先查各关联表 count（订单/售后/会话/流水）评估影响面；删完验证 `count = 0` 才收工。

## 19. 待支付超时配置（settlement-tasks.ts，2026-08-09 用户"待支付时间太长了30分钟差不多"）
- 超时窗口：`lib/settlement-tasks.ts` 的 `UNPAID_CLOSE_HOURS = Number(process.env.ORDER_UNPAID_CLOSE_HOURS ?? 24)`，**默认 24 小时 → 0.5（30 分钟）**（单位小时，0.5=30 分钟）。生产 env 未设置时走代码默认。
- 文案要动态化：`<1h` 显示"超过 30 分钟未付款"而不是"超过 0.5 小时"（`unpaidText = HOURS >= 1 ? \`${HOURS} 小时\` : \`${Math.round(HOURS*60)} 分钟\``）。
- 粒度：settlement cron 每 10 分钟跑一次 → 30 分钟超时实际最长 ~40 分钟关单（可接受；用户要更精确需缩短 cron）。
- 关单副作用链：置 closed → 释放库存（validation 校验订单除外，生成时没扣）→ 取消支付单 → 通知买家。

## 20. 动态词典数字变体（"补充证据 1 份，说明：xxx"每条数字都是独立源串）
- 症状：阿语 rma 时间线"补充证据 1 份，说明：859674"半翻译（"补充"没翻），用户"有几个字一直没纳入翻译"。
- 根因：这类文本**含数字参数，每个数字都是不同的 UiTranslation 源串**（source 唯一精确匹配）——补了 65468546 不覆盖 859674。
- **扫描方法论（一次到位，别只补用户报的那条）**：
  1. 全库扫售后 reason 的 history 条目（`split('｜处理：')` + HISTORY_PREFIX 正则提取 text），按 `/补充/` 过滤去重
  2. 逐个查 UiTranslation `findUnique({ where: { source } })` 找出缺失
  3. 批量补（SiliconFlow 40 并发或串行短串；单条超时重试时加 `AbortSignal.timeout(30000)` + exec 端 `timeout 120`）
  4. 复核缺失数 = 0 才收工
- 同类变体模式：售后历史（拒绝原因/补充证据/补充说明）、审核备注、退款原因——凡"模板 + 参数"的动态中文都会这样，漏翻排查按此扫描。

## 21. 加购不跳转（用户 UX 偏好："加入购物车后不要跳转购物车，应该在原界面"）
- ProductBuyBox `addToBag()` 原实现 `addCartItem(...)` 后 `router.push("/cart")`——用户明确不喜欢（想继续逛/加购多件）。
- **修复**：去掉跳转，停留原页 + 按钮 1.8s 变"已加入购物车"提示：
  ```ts
  setAdded(true);
  window.clearTimeout(addTimer.current);
  addTimer.current = window.setTimeout(() => setAdded(false), 1800);
  // 按钮文字 {added ? getTranslation(lang,"ui.cn.102") : getTranslation(lang,"ui.cn.103")}（102=已加入购物车/103=加入购物车）
  ```
- 坑：`useRef<number | null>(null)` 给 `window.clearTimeout` 传 null 报 TS2769 → 用 `useRef<number | undefined>(undefined)`；`useRef` 要 import。
- 通用：电商"加入购物车"类操作默认停留原页给即时反馈（按钮态/角标），除非产品明确要跳结算。

## 22. 数据多不该堆主页（资金流水独立页，用户偏好）
- **症状**：用户报 /account 主页资金记录 1 万条全显示，把"我的订单"挤到下面，不合理。
- **修复**：
  - 新建 `/account/funds`（分页 20 条/页 + 上下页导航；fundRecords 用 `time: string` 格式化字符串，BuyerFundRecord.time 是 string 不是 number——排序用 `new Date(b.time).getTime()` 比）
  - 左侧导航（BuyerAccountCenter navGroups）"交易管理"组加 `{ key: "funds", label: "资金流水", labelKey: "account.nav.funds", href: "/account/funds" }`，BuyerCenterSection 类型加 "funds"
  - 主页 `/account` 只传 `fundRecords.slice(0, 5)` + "查看全部资金流水（N 条）"链接（getTranslation 拼接，**别用 data-i18n 包变量**——data-i18n 整段替换会吞掉 {N} 变量）
- 通用：主页列表类区块限制条数（5 条内）+ 完整列表独立分页页，避免长列表把主内容挤下屏。

## 23. 列表页信息架构（rma 售后记录太长 → 单开详情页）
- 用户原话："退款与售后单独一个订单呈现太多了…应该单独订单显示单独页面给订单一个消息提示就行了，找其中一个的时候累死了"。
- **已落地（commit 0ab6541 + f894017，本会话后段完成）**：
  - 新建 `/account/rma/[id]` 详情页：单条售后完整展示（商品/服务类型/描述/证据/全量 history/拒绝横幅/申请平台介入/补充证据），数据查询：`afterSaleCase.findFirst({ where: { id, OR: [{ buyerEmail }, ...(allowedOrderNos.length ? [{ orderId: { in: allowedOrderNos } }] : [])] } })`
  - 列表页（app/account/rma/page.tsx）精简：每条只显示编号/关联订单/状态/服务类型/金额/时间 + **最新一条 history 消息提示**（`parsed.history[parsed.history.length-1]` 的 actor+time+text）+ "查看详情"按钮（`account.rma.viewDetail` 键×7）
  - 补键 `account.rma.detail`/`account.rma.backList`/`account.rma.viewDetail` × 7 语言（anchor 用 `account.rma.actor.seller` 各语言值）
  - **坑**：`getBuyerOrderNos` 在 `lib/buyer-account`（**不是** lib/buyer-orders，那只有 getBuyerOrderRows 返回 BuyerOrderSummary 无 id 字段）；`AfterSaleCase.orderId` 存的是 Order.id；列表页原 import 就是 buyer-account 的 getBuyerOrderNos，详情页别抄错
- 通用：列表页全量展开嵌套明细（history 时间线/聊天记录）是可用性反模式；长列表 → 概要 + 详情页/抽屉，消息类给"最新一条"提示即可。

## 24. 通知中心已读/跳转问题（SellerNotificationList，2026-08-09 发现）
- 症状（用户报）：①通知中心左侧列表无提示只有小红点 ②点全部已读后刷新又全部未读 ③点通知不跳转详情、铃铛也点不开。
- 根因（代码层）：`nt-item` 是**纯文本 div 无 onClick/href**（跳转缺失 → 同类 #13 模式）；已读状态是**组件本地 `read` Set**（`useState(new Set())` 初始全未读），后端 `readAt` 已置但组件不读 → 刷新后 read Set 重置全变未读。
- **已落地（commit 443d778，本会话后段完成）**：①page.tsx 加 `targetUrlOf(row)`（templateKey+metadataJson 映射：after_sale→/seller/aftersales/{afterSaleId}、order/shipment→/seller/orders/{orderNo}、deposit/withdraw→/seller/funds、change_request→/seller/account、有 orderNo 兜底）+ items 构造加 `url`/`read`（readAt!=null）②SellerNotificationList：NotificationItem 类型加 `url?: string | null; read?: boolean`；`read` Set 初始 = `items.filter(i => i.read).map(i => i.id)`（**不再初始全未读**）；"全部已读"按钮 onClick 加 `fetch("/api/notifications/read", { method: "POST" })` 持久化；nt-item 有 url 时包 `<Link href={item.url}>`（无则纯展示）
- **后续修复（2026-08-09 用户"资料变更通知点进去空白+404"）**：`change_request` 原映射 `/seller/settings` **该路径根本不存在**（app/seller/ 下无 settings 目录，侧边栏"账号设置"= `/seller/account`、"入驻资料"= `/seller/onboarding`）→ 点通知 404 空白。改 `change_request*`（含 `change_request_result`=资料变更已通过/未通过，admin/change-reviews/[id]/route.ts 52 行发的通知）→ **`/seller/account`**（账号设置=个人资料页）。
- **通用**：①通知/入口跳转映射的 url 必须**核对目标路由存在**（`ls app/seller/` 或 `grep -rn 'href: "/seller'` 对照侧边栏实际路径），凭空写路径极易 404；②"余额到账正常跳资金中心"（deposit_reviewed→/seller/funds）与"资料变更 404"对比 = 映射表里其他路径都要逐个 `ls` 验证（本会话生产通知 templateKey 全量核对 13 类：after_sale*/order*/shipment*/deposit*/payment_*/conversation_message/contact_* 跳转路径均存在才收工）。
- 通用排查："点 X 没反应"先看元素是不是纯文本 div（无交互）；"已读/状态刷新后还原"先看状态是本地 state 还是后端持久化 + 初始值是否读后端。

## 24b. 资料变更 404 二次复报验证（2026-08-09 用户再报同一问题）
- 代码已修（change_request→/seller/account）+ 生产 build 产物确认（服务器 `grep -o 'seller/account' /www/tiktok/.next-build/server/app/seller/notifications/page.js` 命中 + `grep -c 'change_request'` =1）+ 浏览器实测（qa-seller-1 登录→通知中心→点 Profile change approved 通知→location.pathname=/seller/account 且页面渲染正常）→ **用户侧 404 = 旧 JS 缓存**（修复部署于当天早些时候），指导 Ctrl+Shift+R 强刷即可。
- **复报处理流程（#61 同款，本会话两次复报验证有效）**：用户复报同一问题 → ①先验证生产代码是否已修复（build 产物 grep + 浏览器实测复现）②代码已修 + 实测正常 → 用户侧缓存问题（指导强刷）；实测仍坏 → 找未覆盖路径（第二条查询/另一渲染分支）。**别一收到复报就重新改代码**。

## 25. 聊天咨询商品卡片点击直达（ChatContextPanel，#13/#24 同族变体）
- 症状：用户\"买家端和商家聊天的时候，商品链接应该点击后直接跳转商品主页\"。
- 根因：ChatContextPanel 的\"咨询商品\"卡片——缩略图 + 标题是纯文本（只有右下角小字\"查看商品\"按钮可点）。
- 修复：整卡包 `<Link href={`/products/${conversation.product.id}`}>`（`display:"contents"` 包住 thumb + 标题 + 价格，保持原布局），\"查看商品\"按钮保留。
- 通用：#13 系列——商品卡片/缩略图/标题都是链接点，别只给角落里的小按钮加。
- 同一会话用户还拍板删掉了 ChatContextPanel 的"智能摘要"卡片（`conversation.aiSummary` 区块，买卖双方聊天右侧都不显示，保留商品/订单/快捷操作）——用户明确"直接删掉吧"类需求就是删干净，不留隐藏开关。

## 26. 聊天窗口商家头像点击跳转（ChatWindow，#13/#25 变体）
- 症状：用户"买家端和商家聊天页面点击商家头像应该跳转到商家主页"。
- 修复：`components/chat/ChatWindow.tsx` chat-hd 头部商家头像——买家端（`role === "buyer"`）包
  `<Link href={`/stores/${encodeURIComponent(conversation.store)}`}>`（店铺页支持 OR:[{slug},{name}] 查询，
  无 slug 用店铺名也能进）；卖家端不加。conversation 只有 `store` 名（chat-types.ts:38），无 storeSlug。
- 通用：#13/#25 系列第三例——头像/图标类元素也是链接点，别只给文字/按钮加。

## 27. select/下拉 options 翻译不切换（AppleSelect/类目下拉，进行中方法论）
- 症状：用户"卖家商品管理全部类目/类目列表翻译切换都没反应"。
- **根因**：AppleSelect（及原生 select）的 `options` 是**纯字符串 props**（`label: "全部类目 (N)"` /
  `` `${category.name} (${category.count})` ``），data-i18n 不适用于 option 文本；组件**无语言切换监听**，
  切语言不重渲染 → options 永远中文。
- **修复方法论（已落地，见 #41 组件改造）**：
  1. **类目名批量补词典**：FLAT_CATEGORIES 静态中文名（`lib/category-taxonomy.ts`，680 个）词典缺失 →
     提取全部 name → 服务器批量翻译（SiliconFlow 40 并发/批，跳过已有 `findUnique` 查重）→ 补 UiTranslation
     （scope=dynamic）。"全部类目"词典已有（source 精确匹配）。
  2. **组件语言监听**：SellerProductManager 加 `qavlixor-language-change` 监听 → forceUpdate（`useReducer`
     tick）→ options 重新计算。
  3. **options label 用词典查**：`translateDynamicValue(currentClientLanguage(), name)`（lib/dynamic-translations.ts
     客户端词典查询函数），"全部类目 (N)" 用 `translateDynamicValue(lang, "全部类目")` + 数字拼接。
- **通用规则**：凡下拉/select 的 option 文案是动态中文（类目名/状态/枚举），切语言必须：①词典有源串 ②组件监听语言事件重渲染 ③label 运行时查词典。data-i18n 只能管元素文本，管不了 option/属性。
- 后台批量翻译注意：中断恢复后脚本要**跳过已有**（findUnique 查重），续跑幂等；SSH exec 用 `(nohup timeout 900 node ... &)` 避免连接断开中断。

## 28. 收货地址上限 10（买家端，2026-08-09 用户\"最多只能有十个\"）
- 后端硬校验 `app/api/account/addresses/route.ts` POST：`count >= 10` → 400\"最多只能保存 10 个收货地址，请先删除不需要的地址。\"（在 `isDefault` 计算前）。
- 通用：数量上限**先做后端硬校验**（防绕过前端），前端提示/禁用是辅助；用户报\"太长了/太多了\"通常指缺上限约束。

## 29. 提现地址绑定（免每次输入，2026-08-09 用户\"每次提现都输地址太麻烦了\"）
- **需求**：绑定/更改提现地址（放个人资料），提现时自动带出，不用每次输。
- **链路**：
  1. Schema：`User` 加 `withdrawalJson String?`（JSON `{method, account}`）；改 schema 后必须 `npx prisma generate`（本地 tsc 会报字段不存在直到生成）
  2. `/api/account/profile`：GET 返回 `withdrawal`（`JSON.parse(user.withdrawalJson)` try-catch）；PUT 接受 `withdrawalMethod/withdrawalAccount` → 存 withdrawalJson
  3. 个人资料表单（BuyerAccountForms `BuyerProfileForm`）：props 加 `defaultWithdrawal`，新增\"提现方式 select（USDT TRC20/ERC20/BEP20/PayPal/Wise）+ 提现地址/收款账号 input\"区块（提交体带 `withdrawalMethod/withdrawalAccount`）
  4. 提现表单（BuyerBalancePanel）：提现按钮改调 `openWithdraw()`——fetch profile 拉绑定地址自动填入（`setMethod(wd.method)`/`setAccount(wd.account)`），未绑定则清空
- **坑（同文件多组件 replace 误插，本会话 TSC 连环错）**：`BuyerAccountForms.tsx` **一个文件含多个组件**（BuyerProfileForm/BuyerPasswordForm/BuyerAddressForm/BuyerDeactivateAccount）。用 `s.replace('const [message, setMessage] = useState("")', ...)` 这类**通用锚点**会把 state/JSX 插进**第一个匹配的组件**（本会话 wdMethod state 被插进 BuyerPasswordForm/AddressForm/DeactivateAccount 三处，TS2304/TSC 连环报错）。**必须用组件内唯一锚点**（如 `fileRef` 行、`confirmDeleteId` 行），插入后 `grep -n '字段名'` 确认只落在目标组件 + tsc 验证。通用：多组件单文件补代码 = 锚点必须组件唯一。

## 30. 长列表分页（我的订单一页 10 个，2026-08-09 用户\"订单太长，翻页那种搞成\"）
- `/account/orders`：searchParams 加 `page`，`pageSize = 10`，`allOrders.slice((page-1)*10, page*10)`，`safePage = Math.min(page, pages)` 防越界。
- 翻页 UI：上一页/下一页 Link `?status=${filter}&page=N`（**带状态筛选参数**，切 tab 回第 1 页）；中间显示 `N / M（共 X 单）`。
- 补键 `account.pager.prev/next` × 7 语言（anchor 用 `account.nav.funds` 各语言值；pt 的 funds 值是 \"Registros de fundos\" 与 es \"Registros de fondos\" 只差一个字母，插入后必须 grep 数 7 处验证）。
- 通用：列表页全量 `map` 渲染是长页根因；服务端切片 + URL page 参数 + 上下页链接，是最小改动分页。

## 31. 发品表单剩余翻译缺口（shipBy options + placeholder，2026-08-09 用户点名单）
- 用户点名\"卖家上架商品时：商品类目选择、商品标题、规格、SKU、产品参数、发货时间选择，语言不会转换\"。
- **已覆盖**：类目下拉（#27 方法论）；标题/规格/SKU/参数**输入框的值**是商家输入内容，切语言不翻是正常的（渲染层 DynamicText 已处理）。
- **未覆盖缺口（本会话定位未落地）**：
  - 发货时限 AppleSelect options：`[\"48 小时内发货\", \"24 小时内发货\", \"72 小时内发货\", \"7 天内发货\"]` 4 个**裸中文字符串**（SellerProductForm ~476 行）——同 #27 类目下拉同类：options 纯字符串 + 组件无语言监听 → 需词典源串 + `qavlixor-language-change` 监听重渲染 + `translateDynamicValue` 查词典
  - 4 个 placeholder 无 data-i18n-placeholder：SKU 规格名（\"如：黑色 / 加厚款\"）、SKU 编码（\"SKU-001\"）、参数 label（\"如：品牌 / 主体材质\"）、参数 value（\"如：美佳航 / 不锈钢\"）
- 通用：\"表单语言不转换\"排查顺序——①label/placeholder 是否 data-i18n ②select/下拉 options 是否裸中文（#27）③输入值本身是否动态翻译（用户内容不翻，渲染层翻）。

## 32. 满额包邮提示（freeOver 模板从未应用，2026-08-09 用户\"满30U包邮买家端没有说明，支付页也没提示\"）
- **现状事实**：运费模板 `freeOver`（满额包邮门槛）**只有存储层**（lib/shipping-template-repository.ts 读写），
  **结算/订单创建从未应用**——`shippingAmount` 恒 0（全库只有 schema 定义 + 订单详情读取，无计算处），
  买家端也无任何\"满 X 包邮\"说明。
- **本次做的是提示层**（用户诉求是\"没有明确的说明\"，未要求运费真正生效）：
  1. 新 API `app/api/shipping/free-over/route.ts`：`GET ?stores=店名1,店名2`（逗号分隔，≤20）→ 查各店
     shippingTemplatesJson → 返回 `{ freeOverByStore: {店名: 门槛} }`（只回 `freeOver>0 && enabled!==false` 的，
     `import { json } from \"@/lib/api-response\"` 不是 http-utils）
  2. PDP（app/products/[id]/page.tsx）：storeRow 查询加 `shippingTemplatesJson` 字段 → 算 `freeOver` →
     传 ProductBuyBox（props 加 `freeOver = 0`）→ 绿色徽标\"满 {X} USDT 包邮\"（ui.cn.104=满/105=包邮，×7 语言）
  3. 结算页（CheckoutCartPanel）：挂载时 fetch free-over → 每组店铺行头显示徽标
- **坑**：PDP 的 storeRow 原本在 `if (viewerEmail)` 块内 → 块外引用报 TS2304 → 提到块外；
  ProductBuyBox props 解构要加 `freeOver = 0` 默认值。
- **通用**：卖家端"设置了但买家端看不到"的规则 → 先查该字段是否真的被消费（存储层 vs 计算/展示层），
  提示层方案 = 只读查询 API + 页面徽标，不动计算逻辑。

### 32b. 运费模板正式生效（提示层 → 结算计费，用户"默认的运费设置无法启用"）
- 用户二次反馈："买家发货默认的运费设置无法启用，但是在运费设置中是默认的" → 提示层不够，模板要在结算真正计费。
- **结算计费**（app/api/checkout/orders/route.ts）：
  ```ts
  // 每店默认模板（enabled!==false 的第一个；pricing==="free" 跳过）
  const shippingAmount = tpl && subtotal < tpl.freeOver ? tpl.firstFee : 0;  // 满 freeOver 包邮，未满收首重
  const total = Number((subtotal + shippingAmount).toFixed(2));
  ```
  - `Order` 类型（lib/sample-data.ts）加 `shippingAmount?: number`
  - `syncOrderToPrisma`（lib/order-repository.ts）：`subtotalAmount: order.total - (order.shippingAmount ?? 0)`、`totalAmount: order.total`、`shippingAmount: order.shippingAmount ?? 0`（update + create 两处都改）
- **结算页显示**（CheckoutCartPanel）：free-over API 扩展返回 `firstFeeByStore`；每组算 `shipFee`（未满门槛收首重）；应付总额 `payable = total + shipFeeTotal`（含运费）；未满时行内"+ 运费 X USDT"、有运费时加"运费合计"行
- **发货页显示真实模板**（app/seller/orders/[id]/logistics/page.tsx）：服务端查店铺 `shippingTemplatesJson` 取默认模板（`t.isDefault ?? tpls[0]`）→ 传 SellerFulfillmentForm（props 加 `shipTpl`）→ 运费模板区块不再写死"包邮模板"，显示真实模板名 + 计费说明（`满 X USDT 包邮 · 首重 X USDT`）
- **坑**：SellerFulfillmentForm props 签名是多行格式（`{\n orderId,\n logistics,...}`），`s.replace("export function ... ({ orderId, ...})", ...)` 单行锚点匹配不上 → 必须按实际多行格式 patch；物流页模板查询要在 `order` 找到之后、渲染之前
- **口径一致性**：前端 shipFee 计算与后端必须同公式（`firstFeeByStore[store] && group.total < (freeOver || Infinity) ? firstFee : 0`），否则摘要金额与实际扣款不一致

## 33. schema 变更部署顺序坑（db push 在解压前跑 = 误报 already in sync → build 失败）
- **症状**：改了 prisma schema（加字段）部署时，先跑 `npx prisma db push --skip-generate` 显示
  \"The database is already in sync\"（**假象**——服务器还是旧 schema，还没解压新包），随后 build 失败
  （Prisma Client 缺新字段）+ 上传的 tar.gz 被 rm 掉 → 需重传重来。
- **正确顺序（schema 变更时）**：①SFTP 传包 → ②`tar xzf` 解压（新 schema 落地）→ ③`prisma db push` →
  ④`prisma generate` → ⑤`pnpm run build` → ⑥pm2 restart + curl 200 探测。db push 必须**在解压之后**。
- **通用**：任何"先于代码落地的数据库/配置操作"都要等部署包先解压；部署脚本顺序 = 传 → 解压 → db 变更 → 生成 → 构建 → 重启 → 探测。

## 33b. 运费模板设置页"保存后刷新消失"排查结论
- **排查结论（重要）**：生产库模板实际在（FLYYYYYY 店 shippingTemplatesJson 有"按重量计费"）→ **保存链路（POST→persist→Store.shippingTemplatesJson）本身是通的**。"保存后刷新消失"优先怀疑：①浏览器缓存（让用户 Ctrl+Shift+R 强刷）②保存时用的是另一个卖家账号（不同 store 行）。别一上来就怀疑 repository/API 层——先查库 `shippingTemplatesJson` 在不在，库里有=前端/缓存问题。
- 保存后前端链路：submitForm → POST/PATCH → `refresh()`（GET 重拉 setTemplates）+ `router.refresh()`（服务端重渲染）——两者都在，数据该刷新。

## 35. 聊天对话消息正文翻译不切换（ChatWindow/ChatList 缺语言监听；2026-08-09 用户"对话里面商品名称也不翻译"）
- **排查方法论（先查词典覆盖，再查组件重渲染）**：生产 message 表 179 条，96 条中文消息——`findUnique({ where: { source } })` 逐个查词典，**95 条已在 UiTranslation**（翻译链路本身是通的），只缺 1 条（"已创建订单…的买卖会话"含订单号）→ 补 7 语言。**结论：词典不是根因**——"切语言不翻"在词典已覆盖的情况下，下一步查**客户端组件是否监听语言事件重渲染**。
- **真正根因**：ChatWindow/ChatList 是客户端组件，DynamicText 只输出 `data-i18n-dynamic` 属性（依赖 LanguageSync 的 DOM 层 scheduleApply 更新），**React 组件层不重渲染** → 消息正文/会话预览/商品卡片切语言不变。
- **修复（useLanguageTick 模式）**：
  ```ts
  import { useEffect, useReducer } from "react";
  function useLanguageTick() {
    const [, force] = useReducer((x: number) => x + 1, 0);
    useEffect(() => {
      window.addEventListener("qavlixor-language-change", force);
      return () => window.removeEventListener("qavlixor-language-change", force);
    }, []);
  }
  // 组件函数体第一行调用 useLanguageTick()
  ```
  两个文件都加：ChatWindow（消息气泡正文 + 商品/订单卡片）、ChatList（会话列表 lastMessage 预览）。
- **注意**：patch 时 ChatWindow 顶部 import 区出现重复行（`avatarColor, avatarText...` import 加了新块旧的还在）——多行 import 改造后 grep 查重复，清理干净再 tsc。
- **通用**：客户端组件内任何依赖词典/`currentClientLanguage()` 的文本（消息、预览、options label），切语言要即时生效必须挂 `qavlixor-language-change` 监听强制重渲染——这是 #1 的组件级补充（LanguageSync 的 router.refresh 兜底只覆盖服务端渲染，管不到已挂载客户端组件的 state）。


## 36. 搜索类目多语言（类目 slug 英文 + 类目名词典；SiliconFlow 批次大小坑，用户"还没彻底修复完"）
- **用户二次反馈**："只有中文搜手机壳能搜出来，其他语言不行…这个还没彻底修复完"——第一轮只修了商品标题匹配池（#17），类目搜索还没全语言。
- **事实核对（先查数据再改）**：
  - 生产**没有"手机壳"商品**（title contains 手机壳 = 0 条）——用户搜"手机壳"命中的是**类目**（categoryMatches → categoryHits）
  - 类目 slug 是**英文**（`手机壳 → phone-cases`、`磁吸手机壳 → phone-cases-2`、`透明手机壳 → phone-cases-3`）→ 英文搜 "phone case" 命中 slug（fuzzyScore 1.0，本地验证）——英文路径其实已通，用户没生效是缓存
  - 西语搜 "funda" vs `手机壳phone-cases`：0.4（不命中）→ 需要类目名 7 语言词典
- **修复**（app/search/page.tsx）：categoryMatches 匹配池拼入词典类目名：
  ```ts
  const { prisma } = await import("@/lib/prisma");
  const catRows = await prisma.uiTranslation.findMany({ where: { source: { in: FLAT_CATEGORIES.map(c => c.name) } }, select: { source: true, i18nJson: true } });
  const catI18n = new Map(catRows.map(r => [r.source, Object.values(r.i18nJson ?? {}).join(" ")]));
  // haystack: `${category.name}${category.detail}${category.slug}${catI18n.get(category.name) ?? ""}`
  ```
- 验证法：本地 `node -e` 直接跑 fuzzyScore 模拟（加西语类目名后 "funda" 1.0）——改前先模拟确认缺口，改后模拟确认修复。
- **通用**：类目/枚举/标签类搜索词的多语言，匹配池 = 中文名 + 英文 slug + 词典各语言名三者都要。

## 37. SiliconFlow 批量翻译批次大小（最终结论：40 并发单条；20 词/批也超时）—— 假完成排查
- **症状**：类目名批量翻译脚本（40 词/批，`AbortSignal.timeout(60000)`）日志显示"进度 560/591"后"完成"（脚本跑完），**但抽查库 `findUnique({ where: { source: '手机壳' } })` 全是 null**——591 个全部超时失败，仅第一轮中断前成功的 89 个在库。
- **根因**：SiliconFlow 对 40 个词的批量 JSON 翻译请求，60s 超时**几乎必超**（生成 40×7 语言 JSON 太长）；脚本 catch 只记"批失败"继续，无重试 → 全程失败但日志看起来在推进。
- **修正（20 词/批也不行）**：20 词/批 + 90s 实测**仍批量超时**（catfill2.log 全"批失败"）——**最终稳定方案：40 并发单条**（每个词一条独立请求，`AbortSignal.timeout(30000)`，worker 池 40 个 `Promise.all`；680 类目约 15-25 分钟）。批量 JSON 翻译（任何批次）都不稳，单条请求才稳。
- **防假完成**：批量翻译脚本跑完**必须抽查库**（`findUnique` 查 3-7 个代表样本确认 i18nJson.en 非空），不能信"进度 N/M + 完成"日志——超时失败的批也会推进进度计数。
- 通用：任何外呼批量翻译（SiliconFlow/其他 LLM）优先 **40 并发单条**（每条独立请求短超时）；跑后抽查数据落库是必做验证步。

## 38. 聊天消息商品卡片跳转（MessageCard product 卡片，用户再次提"商品链接点击跳转"）
- 前两轮只修了 ChatContextPanel"咨询商品"卡片（#25）——用户再次反馈"聊天的时候商品链接点击后直接跳转"指**消息气泡里的商品卡片**（MessageCard 的 `cardType === "product"` 分支）。
- **数据**：`message.cardPayload` 已有 `productId`（lib/message-repository.ts 发商品卡片时带 `{ productId, title, imageUrl, price }`）。
- **修复**（components/chat/ChatWindow.tsx MessageCard）：product 分支先构造 `card` JSX，再 `payload.productId ? <Link href={/products/${payload.productId}} style={{textDecoration:"none",color:"inherit",display:"block"}}>{card}</Link> : card`（老数据无 productId 保持原样）。
- **通用**：#13/#25/#26/#38 系列——聊天场景所有商品触点（右侧咨询卡片、消息气泡卡片、头像、店铺名）都是跳转点；用户重复提同一诉求 = 还有漏网的同族元素没点，逐个渲染分支排查。

## 39. 发货备注/lastEvent 拼接污染（"预计送达7-12天·仓库：默认仓·时限：今天18:00 前·17TRACK·手动记录·000000000000000000000·No tracking information at this time"一串全删）
- **症状**：买家看到发货备注里一长串（用户"把这一串删掉"）。
- **根因**：`app/api/orders/[id]/fulfillment/route.ts` 发货时把 `note · 仓库：${warehouse} · 时限：${shipBy} · ${providerResult.lastEvent}` **全拼进 lastEvent**；`providerResult.lastEvent` 在 manual 模式是 "No tracking information at this time"（17TRACK 无轨迹占位）——整串展示给买家。
- **修复**：lastEvent 只留真实备注 + 真实轨迹：`[note.trim(), lastEvent && lastEvent !== "No tracking information at this time" ? lastEvent : null].filter(Boolean).join(" · ") || \`${carrier} · ${trackingNo}\``；SellerFulfillmentForm 的 note 初始值 `useState("")`（不再带 logistics.lastEvent）；`lib/batch-ship-service.ts` 批量发货同样过滤占位串。
- **通用**：发货/物流 lastEvent 是**展示给买家的最终文本**，别把内部字段（仓库/时限/供应商占位）拼进去；占位串（"No tracking information"）要显式过滤；排查"买家看到一长串莫名文本"先看发货接口的拼接逻辑。

## 40. 批量库存勾选失效（"只选一件商品增加或减少库存，两件商品库存都变"）
- **根因**：SellerProductManager `submitBulkInventory()` 提交体只有 `{ mode, amount, status: filter, category: categoryFilter }`——**没传勾选的 ids**！API 按 status/category 筛选**全量修改** → 勾选被完全忽略。
- **修复**：前端提交体加 `ids: [...selected]` + 未选提示（`seller.products.needSelect` 键×7）；后端 PATCH（app/api/seller/products/route.ts）`const ids = Array.isArray(body.ids) ? ... : []` 后 targets 过滤 `(ids.length ? ids.includes(product.id) : true)`。
- **通用**：批量操作（批量改库存/批量改价/批量上下架）前端提交体**必须显式带勾选集合**；后端保留"无 ids 按筛选全量"兼容旧调用，但新前端一律传 ids。排查"批量操作作用到未选中的行"= 提交体没带选择集。

## 41. 发品表单翻译组件改造落地（#31 的后续，commit 8c0877c）
- SellerProductForm（单文件多组件同样适用 #29 锚点教训）：加 `useReducer` forceTick + `qavlixor-language-change` 监听；`const lang = currentClientLanguage()`；发货时限 options / 4 个 placeholder / 类目级联 label 全部 `translateDynamicValue(lang, x) || x`（词典查不到回退原文）。
- 坑：监听插入点必须**在组件函数签名 `{ mode, product, operation }: SellerProductFormProps` 之后**（插到签名里会把 `mode, product...` 挤到 lang 后面 → TS1005 连环错）；`useReducer` 要从 react import。

## 34. 运费模板设置页按钮缺口（"没有默认模板按钮和删除按钮"，2026-08-09 用户）
- **症状**：设置页（SellerShippingTemplates.tsx）操作列只有编辑/复制/删除——**没有"设为默认"按钮**；删除按钮原逻辑 `t.isDefault && templates.length > 1 ? null : <删除>` 允许删唯一的默认模板（删光后结算无运费依据）。
- **修复**：
  - 新增 `setDefault(t)`：PATCH `{ id, name, scope, pricing, firstFee, addFee, freeOver, regions, isDefault: true, enabled }`（PATCH 走 `updateShippingTemplate`，仓库层 `normalizeDefault` 会清掉其他默认）→ refresh + router.refresh
  - 操作列：非默认模板显示"编辑 / 复制 / **设为默认** / 删除"；默认模板只显示"编辑 / 复制"（**默认不可删**，要删先设别的为默认）
  - 补键 `seller.shipTpl.action.setDefault` × 7 语言（anchor 用 `seller.shipTpl.action.delete` 各语言值）
- **通用**：默认/主选项类数据（默认模板/默认地址/默认支付）的删除按钮**永远对默认项隐藏**（至少留一个），并提供显式"设为默认"切换入口；用户报"没有 X 按钮"先看操作列渲染条件（条件写反/写死是常见根因）。

## 42. 商品目录缓存失效（"删除后刷新又恢复"——getProductCatalog 60s 缓存未失效）
- **症状（用户带截图）**：卖家商品管理批量删除 → 确认删除成功 → **刷新后已删商品又恢复**；改价/改库存"点击无反应"（列表读到旧值）。
- **根因**：`lib/product-repository.ts` 的 `getProductCatalog()` 有 **CATALOG_TTL_MS = 60_000 缓存**（`catalogCache` 模块级变量 + `loadPrismaCatalogCached`），**删除/编辑/创建 API 从未失效缓存** → 刷新 GET 返回旧缓存（已删商品"复活"、改动读旧值，看起来"无反应"）。数据库其实删成功了。
- **修复**：DELETE/单商品 PATCH/批量 PATCH/POST 4 处 API（`app/api/seller/products/[id]/route.ts` + `route.ts`）成功落库后统一调 `invalidateProductCatalog()`（150 行已有导出：`catalogCache = null; catalogInflight = null;`）。import 要加到 product-repository 的 import 行（`invalidateProductCatalog` 很容易漏 import → TS2304）。
- **通用排查**："删了/改了，刷新又变回去"在**有缓存层的读路径**上第一嫌疑 = 写路径没失效缓存；先 grep 读函数有没有 cache/TTL，再确认写 API 是否调了失效函数。

## 43. 库存上限 9999（用户"库存设置个上限9999件"，2026-08-09 拍板）
- 与 SKU 上限 20（#7）同类拍板：库存上限 **9999**。5 处统一 999999 → 9999：
  - `app/api/seller/products/route.ts` 3 处（SKU stock normalize、单商品 inventory、批量 `Math.min(9999, ...)`）
  - `components/SellerProductForm.tsx` SKU 库存校验 + input `max="9999"`
  - `components/SellerProductManager.tsx` 批量数量 input `max="9999"`
- 通用：上限类约束 = 后端 normalize 硬钳制（Math.min）+ 前端 input max 双保险；改上限值用全库 replace 时 grep 确认全部命中（本会话 5 处）。

## 44. 卖家售后徽标切语言错乱——给用户的"怎么测"（浏览器词典缓存污染排查步骤）
- 用户问"这个怎么测"时给**可复现步骤**（别只说"强刷试试"）：
  1. Ctrl+Shift+R 强刷（清页面缓存）
  2. 仍异常则清词典缓存：F12 → Application → Local Storage → `https://qavlixor.com` → 删 `qav-dynamic-dict-v1` → 刷新
  3. 逐语言切换（英→西→法→葡→英→俄…连切 5 次，每次等 1s）观察徽标是否跟随语言、有无"别语言乱入"
  4. 结果分流：正常 = 旧缓存问题清完即好；乱入 = 让用户截图（含语言选择器状态 + 徽标文字）→ 查渲染层键（data-i18n 键的 7 语言值分布 + 组件是否静态键）
- **背景**：徽标文案键 7 语言齐全（如 `seller.aftersalesList.supplemented` 1877/3908/5938/7968/10026/12841/15732）；静态 data-i18n 键切语言理论上必翻 → 乱入优先怀疑 localStorage 词典缓存污染，其次 LanguageSync DOM 更新时序。测试方法本身是交付物的一部分。

## 45. 批量改价"应用了但没生效"——商品价=首变体价，body.price 必须同步 SKU 变体价格
- **症状（用户二次反馈带截图）**：商品管理勾选 → 批量操作栏"改价"输入新价 → 点应用 → 列表价格不变（看起来"无反应"）。缓存失效（#42）修了仍无效——**这不是缓存问题，是写库写错了值**。
- **根因（读取机制）**：`lib/product-repository.ts` 从 Prisma 读商品时 `price: asNumber(firstVariant?.price, 0)`（91 行）——**商品价格 = 第一个 SKU 变体的价格**。批量改价 `runBulk` 只发 `{ price }`（无 skuItems）→ PATCH 改的是 `product.price`，但 `nextOperation.skuItems` 落到 `baseOperation.skuItems`（**旧价格**）→ `syncProductToPrisma` 写变体 upsert 用 `item.price`（旧价）→ 读回时 firstVariant.price 仍是旧价 → "改价没生效"。
- **修复**（app/api/seller/products/[id]/route.ts PATCH 的 nextOperation.skuItems 构造）：
  ```ts
  skuItems: (skuItems ?? baseOperation?.skuItems ?? []).map((item: { sku: string; name: string; price: number; stock: number; barcode: string }) =>
    body.price !== undefined && Number(body.price) !== product.price ? { ...item, price: Number(body.price) } : item),
  ```
  body.price 变化时**所有 SKU 价格同步为新价**（一个商品所有规格统一改价；item 类型必须完整标注，`{ price?: number }` 会 TS2322）。
- **通用排查**："改了但读回来还是旧值"且写库链路看似正常 → 查**读取端的价格/库存来自哪个字段**（首变体 vs 商品表）；凡是"商品聚合值 = 变体派生"的模型（价=首变体价、库存=变体库存和），修改时必须同步变体，不能只改商品表字段。相关：库存上限 9999 钳制也在同一 normalize 链上。

## 46. 卖家端侧边栏展开箭头过小（nav2-chevron，用户"箭头太小，买家端都比他大，大一点或颜色深一点"）
- `app/globals.css:17470`：`.seller-portal .nav2-head .nav2-chevron { font-size: 11px; color: #9ca3af; }`（卖家端两级导航折叠箭头 11px 浅灰，用户嫌小/浅）→ 改 `font-size: 14px; color: #374151`（深灰）。
- 通用：图标/箭头类控件"看不见/太小"反馈 → 先查 CSS 尺寸 + 颜色对比度（11px 灰 #9ca3af 在浅底上几乎不可见），放大字号 + 加深颜色两件事一起做，别只调一个。

## 47. 聊天商品名"还是不翻译"的进一步排查（#35 的延伸：词典命中率高 ≠ 渲染层已通）
- **事实**：生产 message 表 96 条中文消息，**95 条在词典**（含买家发的整段商品名"白色巧克力抹茶派 手工脆脆减压手工球玩具…"）→ 词典不是问题。
- **渲染层机制**：DynamicText 只输出 `data-i18n-dynamic` 属性，翻译由 LanguageSync 应用：`scheduleApply()` 全量跑（532 行 querySelectorAll）+ **MutationObserver（734 行）只对 `mutation.addedNodes` 触发**（743 行 `addedNodeNeedsLanguageSync`）。ChatWindow/ChatList 挂 `qavlixor-language-change` 监听 forceUpdate（#35 已落地）重渲染是**原地替换** DOM——observer 是否对原地替换触发 addedNodes 存疑；若 forceUpdate 后仍不翻，双保险方案：forceUpdate 后 `requestAnimationFrame(() => window.dispatchEvent(new Event("qavlixor-language-change")))` 让 LanguageSync 在 React 重渲染完成后重跑 scheduleApply。
- **注意**：LanguageSync 的 characterData 分支（740 行）只处理 `.buyer-portal/.seller-portal/.admin-portal` 内的金额文本；聊天消息文本不在 portal 壳内时该分支不覆盖，只能靠 addedNodes 路径。
- **给用户的验证**：先问"切语言后是整条消息不变，还是只有商品名那几个字不变"——整条不变 = 组件未重渲染（useLanguageTick 没生效/没部署）；只有商品名不变 = 词典未命中（源串不一致，查 JSON.stringify 比对）。

## 49. "部分消息需重复切语言才能全译"——report-miss 补译返回后 applyDynamicElements 跳过中文源
- **症状（用户二次反馈）**：买家/卖家聊天消息部分翻译不了，需**重复切语言**才完全翻译；智能摘要/卖家端对话框同样。
- **根因（不是词典缺失、不是缺监听）**：词典命中率其实极高（#47 已证 95/96）。真根因在补译链路：切语言时词典缺的消息显示原文 + 客户端 `reportTranslationMiss`（LanguageSync.tsx 273 行）批量 POST `/api/i18n/report-miss` → 服务端**实时翻译入库并返回** → 客户端 `registerDynamicEntries` + `applyDynamicElements(currentLanguage(), true)`——**`onlyNonChinese=true` 在 535 行跳过中文源**（`if (onlyNonChinese && chineseTextPattern.test(source)) return;`），而聊天消息**几乎全是中文源** → 补译结果没应用到 DOM → 用户再切一次语言才全量应用显示。
- **修复**（LanguageSync.tsx 298 行）：补译返回后改 `applyDynamicElements(currentLanguage(), false)`（全量重翻，含中文源）。注意 `true` 只该用于"中文首屏 SSR 已是中文、避免全量替换回流"的场景，**补译返回场景必须 false**。
- **通用**：实时补译（report-miss）返回后必须**全量重应用**；`applyDynamicElements(onlyNonChinese)` 的参数语义要分清"首屏优化"vs"补译后刷新"，混用就会"差一次切语言"。

## 50. 聊天会话重复（"结束对话后再联系商家生成新对话框"）——复用条件过严，同店需复用最近会话
- **症状**：买家同一店铺咨询商品 A 结束会话 → 退出消息页 → 再点商品详情"联系商家" → 生成**新会话**，卖家端出现两个对话框。
- **数据事实**：生产两个会话 `contextType:"product"` 但 `contextId` 不同（`PD2608091319112949` vs `PD2608090554005079`，两个不同商品）——`ensureBuyerProductThread`（lib/message-repository.ts 716 行）复用条件 `{ contextType: "product", contextId: product.id, buyerEmail }` **只认同商品**，同店不同商品咨询各开新会话。
- **修复**（ensureBuyerProductThread + ensureBuyerStoreThread 两处）：**优先同商品复用 → 否则复用同店同买家最近会话**：
  ```ts
  const recent = await db.conversation.findFirst({
    where: { type: "buyer_seller", storeId: product.store.id, buyerEmail: normalizedEmail },
    orderBy: { lastMessageAt: "desc" },
  });
  if (recent) return getCommerceConversation(recent.id, "buyer", normalizedEmail);
  ```
- **通用**：会话/工单/订单类去重，复用条件不能只看"同上下文"（同商品 contextId），要加"同主体（店/买家）+ 最近优先"兜底；用户报"重复生成"先查生产两条记录的复用键差异（contextId 不同是典型）。已有重复会话保留不动（历史数据），新逻辑只影响之后创建。

## 52. 下线已接入的功能模块（AI 智能客服整体删除，用户"把聊天接的AI智能客服删了吧"）
- **需求**：删除买卖聊天里的 AI 智能客服（AI 自动回复/欢迎语/智能摘要）。删除类需求用户原话"直接删了吧"= 删干净，不留开关。
- **删除清单（4 层，缺一层就有残留）**：
  1. **触发逻辑**：`lib/message-repository.ts` 发消息后的 AI 自动回复块（`input.senderRole !== "ai" && ... && isPlainText && !(buyer_seller && seller)` → `buildSmartAssistantReply/aiReplyFor` 生成 `senderRole: "ai"` 消息）——整块删
  2. **模板函数 + import**：`buildSmartAssistantReply`（组装 LLM 上下文）/`aiReplyFor`（内置模板）函数体 + `import { generateAssistantReply, isAssistantConfigured } from "@/lib/ai-assistant"` 删掉（不删 import → tsc 未使用报错；不删函数 → 死代码残留）
  3. **创建路径**：订单会话创建时的 AI 欢迎消息（`senderRole: "ai", cardType: "ai_summary"`）从 messages.create 数组移除（product/general 会话只有 system 消息，无需动）
  4. **历史数据**：生产 `message.deleteMany({ where: { senderRole: 'ai' } })`（本会话删 92 条）——不清理则旧会话仍显示 AI 消息气泡
- **验证**：tsc 0 + 部署 200 + 生产清理 count 确认。聊天页发消息后只有对方回复，不再插 AI。
- **通用**：删除已接入功能 = 触发点 → 模板/工具函数 → import 引用 → 历史数据四步走；只删触发点会留死代码和幽灵数据。"删功能"类需求确认边界（自动回复/欢迎语/摘要是否都算）后一次性删全，别让用户二次反馈"还有残留"。

## 51. 同一数据不同展示位计数口径不一致（工作台待办售后 0 vs 侧边栏徽标 2）
- **症状**：卖家工作台待办"待处理售后 0 笔"，侧边栏"售后工单"徽标 2——用户报"比数不符"。
- **根因**：两处查询口径不同——徽标（`app/api/seller/nav-counts/route.ts`）=`status notIn ["已退款","已关闭","refunded","closed"]`（**未完结**，含"已拒绝"可申诉，2 笔）；工作台（`app/seller/page.tsx` 58 行）= `status: "商家处理中"`（仅处理中，0 笔）。FLYYYYYY 店实际：已拒绝 2 + 已退款 3。
- **修复**：工作台对齐徽标口径（未完结 + 店名/订单归属双口径，与 nav-counts 同公式）。生产验证 `groupBy status` 后 count 未完结 = 2 ✅。
- **通用**：同一实体（售后/订单）多处展示计数（徽标/待办/列表页合计），**必须共用同一查询口径**（状态集合 + 归属判定），否则数字对不上；排查"两个数不一样"先 `groupBy status` 列出实际分布，对照两处 where 差异。

## 48. 聊天/店铺详情真实头像（用户"头像改了但聊天/店铺页都不显示"，#13/#26 系列变体）
- **根因（不是缓存/不是没存，是压根没渲染）**：聊天会话列表/聊天窗口头部/店铺详情页的头像**一直是"色块+首字母"占位**（`avatarColor(peerName)` + `avatarText(peerName)`；店铺详情页 `qsp-avatar` 只显示 `store.name.slice(0, 2)`）——代码里从未渲染头像图片，怎么改头像都不显示。
- **头像存储事实**：卖家改头像（`app/api/seller/account/avatar/route.ts`）**写两处**——`User.avatarUrl` + `Store.logoUrl`（同一 URL）。买家改头像只写 `User.avatarUrl`。生产确认：FLYYYYYY 店 logoUrl ✅ 在库、qa-seller-1 avatarUrl ✅ 在库（qa-buyer-2 没设过头像 = 空，属正常）。
- **修复链路（peerAvatar 三件套）**：
  1. `lib/message-repository.ts`：`ChatConversationSummary` + `CommerceConversation` 类型加 `peerAvatar?: string | null`；`getChatConversationList` 构造 `peerAvatar: role === "buyer" ? (row.store?.logoUrl ?? null) : (avatarByBuyer.get(row.buyerEmail) ?? null)`（**买家视角=店铺 logo，卖家视角=买家 avatarUrl**——先批量查 `db.user.findMany({ where: { email: { in: buyerEmails } } })` 建映射）；`mapConversation` 默认 `row.store?.logoUrl ?? null`，`getCommerceConversation` 里 `role === "seller"` 时覆盖成买家头像
  2. `components/chat/chat-types.ts`：`ChatSummary` + `ChatConversation` 加 `peerAvatar?`
  3. 渲染：ChatList / ChatWindow 头像 `item.peerAvatar ? { backgroundImage: url(...) cover center } : 色块`（有图显示图，无图色块兜底）；店铺详情页 `qsp-avatar` 加 `store.logoUrl ? <img style={{width:"100%",height:"100%",objectFit:"cover"}}/> : 首字`
- **通用排查**：用户报"头像改了不显示"→ **先查渲染处有没有 img/background-image 逻辑**（占位色块是典型），别先怀疑缓存/存储——占位实现从根上就没接图片。头像类显示要记"对方是谁"的角色视角（店铺 vs 用户），会话两侧视角不同。

## 53. 聊天已读/未读硬编码中文 + QA 实测账号（本会话收尾）
- **已读/未读**：ChatWindow 消息时间戳 `mt += read ? " · 已读" : " · 未读"` 是**硬编码中文**（切西语仍"已读"）→ 改 `getTranslation(currentClientLanguage(), "chat.read"/"chat.unread")`（键×7 已有，`chat.read`/`chat.unread` 都存在；需补 `import { getTranslation, currentClientLanguage } from "@/lib/translations"`）。
- **通用排查**：客户端组件里"时间戳/回执后缀/单位"这类拼接在字符串里的文案最容易漏翻译——`mt +=` 拼中文后缀 = 硬编码残留典型；grep `+= "` 或 `· ` 中文后缀。
- **QA 实测账号（用户提供，2026-08-09 确认可用）**：买家端 `<EMAIL-REDACTED> / Ht123123`（此前 memory 记录"qa-buyer-1 密码失效"已过时——**登录自动化验证用这个**）；卖家端 `<EMAIL-REDACTED> / QaTest!2026`（同店 FLYYYYYY测试店铺）。浏览器实测翻译/头像/会话类反馈：登录后切语言看结果，比代码层推断快且准。
- **实测确认**：英文→西语一次切换，会话列表/商品卡片/消息正文/买家发的商品名消息**全部即时翻译**（#49 修复生效）——之前"不翻译/需重复切"对用户侧的最终答案是**强刷清词典缓存**（localStorage `qav-dynamic-dict-v1`）+ 一次切语言。
- **会话复用验证**（#50 后续）：生产两会话 contextId 不同（PD2608091319112949 vs PD2608090554005079）= 两个不同商品，复用条件过严实证；同店复用修复后新咨询进现有会话，已有重复会话保留不动。

## 54. 改价/改库存"按钮卡灰数据没动"——PATCH 挂起真根因（i18nJson=null 触发同步翻译 20s+）
- **症状（用户两次反馈"认真修复漏洞"）**：点"应用"后按钮从黑变灰（busy）卡住，**数据看着没动**；响应不是秒级。缓存失效（#42）、SKU 价格同步（#45）都修了仍无效。
- **根因链（浏览器实测定位）**：
  1. `performance.getEntriesByType('resource')` 看 PATCH 请求：`dur: 20001, size: 0` = fetch 20s 超时无响应（服务端实际 20s 后写成功——所以数据最终变了但 UI 像"没动"）
  2. 查该商品：**`i18nJson = null`**（如 PD2608091604211663，标题/变体 i18n 全空）
  3. PATCH（app/api/seller/products/[id]/route.ts）里 `const i18n = contentChanged || !product.i18n ? await buildProductI18n(...) : product.i18n`——**i18n 为空时触发整品同步翻译**（SiliconFlow 6 语言 20s+）→ PATCH 挂起
- **修复（三层）**：
  1. **写路径不挂同步翻译**：改 `const i18n = contentChanged ? (await buildProductI18n(...).catch(() => undefined)) ?? product.i18n : product.i18n`——非内容变更（改价/改库存）不再同步翻译，i18n 由后台 sync-content-i18n cron（2 分钟）补齐
  2. **syncProductToPrisma 图片写入 upsert**（lib/product-repository.ts）：`productImage.create` 固定 id（`${product.id}-image-00`）在 PM2 4 实例并发时 **Unique constraint failed on (id)** 中断写库（pm2 logs grep 'prisma:error' 可见）→ 改 `upsert({ where: { id }, update: {...}, create: {...} })`
  3. **前端防挂起 + 失败可见 + 自动刷新**（SellerProductManager runBulk/StockStepper/submitBulkInventory）：fetch 加 `signal: AbortSignal.timeout(20000)`；失败收集 `firstError`（`result.message ?? HTTP ${status}`）全失败时 `setNotice(操作失败：firstError)`；成功/失败后 `router.refresh()`（完成自动刷新列表，用户明确要求"加个自动刷新"）
- **实测验证（qa-seller-1 登录浏览器）**：勾选改库存 12 → PATCH **562ms**（原 20s）→ 库存 10→12 秒级生效 + "Completed: 1 succeeded" 提示 + 列表自动刷新 ✅
- **通用教训**：①"按钮卡灰"= busy 挂起，先看请求耗时（performance entries）再查服务端慢在哪；②**同步翻译/任何外呼 LLM 不能放在写 API 主路径**，改价改库存必须秒级；③PM2 多实例下固定 id create → upsert；④用户要"自动刷新"= 写操作完成后 `router.refresh()` 兜底，别只靠本地 setState。

## 55. 删功能实操补充（"卖家端批量上传功能删除"，#52 四层法第二个实例）
- 批量上传是"待接入"假功能（modal 标注"后端待接"）——删按钮（工具栏）+ modal（SellerProductManager 482-504 行）+ state（`uploadOpen`）。
- **坑**：用 `patch old_string` 删 state 行时锚点不唯一（`const [uploadOpen...]` 前后行与 `delRiskOpen` 相邻，replace 误删了 `delRiskOpen`（批量删除确认弹窗的 state）→ 补回。**删 state 用唯一锚点（行内容本身含功能名），删完 grep 确认其他 state 没被误伤 + tsc**。
- 通用：#52 四层（触发点→模板/import→创建路径→历史数据）+ 本会话补充：删除时**逐行核对相邻 state/变量**，一次 patch 删多行风险高。

## 56. 全站同类问题排查（用户"类似的问题还有吗，全站再查一遍"）——9 类模式扫描法
- 一轮大修复收尾时用户要求"全站再查一遍类似问题"——把已修问题抽象成**可 grep 的模式清单**并行扫，每类一个 grep 模式：
  1. **固定 id create（Unique 冲突风险）**：`grep -rn 'id: \`\${' app/api/ lib/` 过滤 create/upsert——产品图片修了 upsert（#54）；提现地址**本来就是 upsert**（别只看 create 行误判成问题）
  2. **同步 LLM 翻译在写 API 主路径**：`grep -rln 'buildProductI18n\|translateToAllLanguages' app/api/`——单商品 PATCH 已修（#54）；批量 PATCH 无翻译（安全）；POST 创建同步翻译合理保留
  3. **TTL 缓存未失效**：`grep -rn '_TTL_MS\|catalogCache' lib/`——目录缓存已统一失效（#42）；payment-intents 的 TTL 是正常时效业务
  4. **同一实体 count 口径**：`grep -rn 'afterSaleCase.count' app/`——卖家工作台已对齐（#51）；管理端看板（未关闭）vs 徽标（平台介入）口径不同但**语义不同**（总量 vs 待仲裁），评估保留
  5. **会话/工单复用**：`grep -rn 'ensureBuyer.*Thread' app/ lib/`——product/general 已加同店复用（#50）；订单会话按订单维度合理
  6. **硬编码中文（无 data-i18n）**：`grep -noE '>[一-龥][^<>{}]{2,40}<' <页面>` 逐页扫——**发现 funds 分页"上一页/下一页"真硬编码**（orders 页已有键，funds 漏了）→ 补 `data-i18n="account.pager.prev/next"`；seller/page.tsx 等"命中"行其实有 data-i18n（fallback 文本）——**grep 命中后必须看行上下文**，别直接当问题改
  7. **头像/logo 色块占位**：`grep -rn '\.slice(0, 2)}\|slice(0, 1)}'`——rma 详情/店铺详情/管理端全是"图+文字兜底"（安全）
  8. **占位功能（待接入/演示）**：`grep -rn '待接入\|演示占位'`——**删了卖家提现表单"地址簿"按钮**（演示占位假按钮，`opacity: 0.72` + "待接"标签）；订单导出按钮仍"待接"（用户未抱怨，待拍板）
  9. **批量操作参数遗漏**：`grep -rn 'method: "PATCH"' components/seller/`——批量库存已传 ids（#40），无其他遗漏
- **排查纪律**：grep 命中 ≠ 是问题（fallback 文本、upsert 包 create、语义不同的口径都算"安全"）；逐条看上下文再动手；确认问题才改，评估保留的列出来给用户拍板（本会话保留了管理端口径差异 + 订单导出占位，明确告知用户）。
- **通用**：一轮大修后做"同类问题全站扫描"是防复发标准动作——把已修 bug 抽象成模式清单（数据层：固定主键 create/缓存失效/写路径外呼；展示层：硬编码中文/占位色块/占位功能；业务层：口径/复用/参数遗漏），每类一个 grep 模式，命中后分流"真问题 / 安全 / 评估保留"。

## 57. 下拉按钮占位文字漏翻译（类目按钮"一级/二级/三级/四级类目"，#27/#41 的双层检查教训）
- **症状（用户三次反馈"类目选择不转换，不能毫秒级"）**：发品表单切英文——类目**下拉选项**全英文（词典生效），但**四个类目按钮显示"一级/二级/三级/四级类目"还是中文**。
- **根因**：选项（AppleSelect `options`）已用 `translateDynamicValue`（#41 已落地），但按钮**未选时的占位文字是 `ariaLabel` 属性里的静态中文**（`<AppleSelect ariaLabel="一级类目" .../>`）——data-i18n/词典都管不到属性，切语言不变。
- **修复**：补键 `seller.productForm.catLevel1/2/3/4` + `seller.productForm.other`（"➕ 其他"自定义类目选项同款硬编码）× 7 语言；ariaLabel 改 `getTranslation(lang, "...")`；其他选项 label 改 `"➕ " + getTranslation(lang, "seller.productForm.other")`。
- **补键锚点坑**：`seller.productForm.shipByHint` 各语言值不同（es 1636/fr 3670/pt 5705/ru 7740/ar 9803/zh 12559/en 15455 行）；execute_code 大文件（1.2MB translations.ts）split+循环+write 在沙箱会**超时被杀**——先 grep 确认行号，再按行号最小插入（从后往前插防偏移），或用 patch 工具逐语言插。
- **实测（qa-seller-1 浏览器）**：切英文 → 类目按钮 Level 1-4 ✅ 类目下拉 Beauty care 等全英文 ✅ placeholder/提示全英文 ✅（forceUpdate 同步重渲染，毫秒级，无网络请求）。
- **通用双层检查**：下拉/选择器组件 = **选项文案 + 按钮占位（ariaLabel/placeholder 文本）两层**都要动态化——修了 options 忘记按钮占位是典型遗漏；用户报"下拉/选择不转换"先分别看这两层。表单类"切语言不生效"还有第三层：**输入框的值**是用户数据不翻（保存后买家端按 i18nJson 显示），编辑态不翻译输入值是设计行为，要向用户说明而不是当 bug 修。

## 59. 买家端 getTranslation 按钮切语言不刷新（加入购物车/结算页，#35 useLanguageTick 家族延伸）
- **症状（用户又一轮）**：买家商品详情\"加入购物车\"按钮切语言不翻译。
- **根因**：按钮文案用 `getTranslation(currentClientLanguage(), \"ui.cn.102/103\")`（SSR 固化值），且 **ProductBuyBox 组件没有 `qavlixor-language-change` 监听** → 切语言组件不重渲染，按钮文字停留旧语言。（getTranslation 是 JS 运行时算的，LanguageSync 的 data-i18n 只管标记元素，管不到纯 getTranslation 渲染的文本。）
- **修复（useLanguageTick 家族补全清单）**——全站给\"getTranslation 按钮但无监听\"的客户端组件加监听 + `useReducer` forceUpdate：
  - `components/buyer/ProductBuyBox.tsx`：加 `const [, forceLang] = useReducer((x: number) => x + 1, 0)` + useEffect 监听（**import 必须含 useEffect**，本会话漏 import → TS2304）
  - `components/buyer/CheckoutCartPanel.tsx`：同款监听（跨店拆分文案 getTranslation 拼接 + \"满 X 包邮\"徽标）
  - 已有：#35 ChatWindow/ChatList、#41 SellerProductForm、#27 SellerProductManager
- **CartView 硬编码残留**：\"商品已下架，无法购买\"（非\"已删除\"分支）是裸中文 → 给 DynamicText 加 `data-i18n-dynamic={...}` 属性（词典兜底，LanguageSync 处理）——注意三态：`validity.status === \"已删除\" ? getTranslation(ui.sel.307) : data-i18n-dynamic=\"商品已下架，无法购买\"`。
- **坑**：`s.replace` 给 CheckoutCartPanel 加 useEffect import 时锚点里已有 useEffect → 产出 `import { useEffect, useEffect, ... }` 重复标识符 TS2300——加 import 前先 grep 现有 import 行，用整行替换而非字符串替换。
- **通用清单法**：查\"哪些客户端组件有 getTranslation 但没监听\"——`grep -l 'getTranslation' components/ | xargs grep -L 'qavlixor-language-change'`，逐个人工判断是否渲染切语言敏感文本（按钮/徽标/拼接文案），是则补监听。纯 getTranslation 文本（无 data-i18n 标记、无监听）= 切语言不刷新的三类残留根因之一（另两类：#1 SSR 固化文本、#16 词典源串不一致）。

## 58. 占位功能删/留要用户拍板（批量上传删、地址簿恢复、订单导出保留）
- **本会话经过**：全站扫描（#56）把三类"待接入"占位功能列出——批量上传（商品管理工具栏按钮+modal）、卖家提现"地址簿"按钮（`opacity:0.72`+"待接"标签）、订单导出按钮（提交为 demo toast）。
- **决策结果**：批量上传用户拍板**删**（"卖家端批量上传功能删除"）；"地址簿"我删了用户**要求加回**（"地址pu也给我加回来"）；订单导出**明确保留**（"订单导出不删，保留"）。
- **教训**：占位/假功能不要一次性自作主张全删——**删哪个留哪个必须让用户拍板**；用户对"假按钮"的态度不一致（有的嫌碍事删、有的当规划占位留着）。改动前列出清单问一句，改完撤销成本高。恢复删除的东西 = 原样加回（diff 反向）。
- 通用：扫描发现的"评估保留"项（#56 的管理端口径差异、订单导出占位）要**明确列给用户**拍板，别静默处理也别全删。

## 60. 删"批量改库存"功能（#52/#55 删功能模式第三实例，用户"卖家端批量改库存删掉"）
- 与删批量上传（#55）不同：批量改库存是**真实功能**（不是占位），删除范围 = 触发点 + 调整栏 + state + 函数：
  1. 工具栏按钮（`onClick={() => setShowBulkPanel(...)}`，`data-i18n="seller.products.bulkStock"`）
  2. 调整栏 JSX（`showBulkPanel ? <div className="batchbar show">` 整块：方式 select/数量 input/提交调整/取消）
  3. state：`showBulkPanel`/`bulkMode`/`bulkAmount`
  4. `submitBulkInventory` 函数
- **坑（patch 后残留）**：JSX 大块删除后**残留 `</div> ) : null}` 闭合符**（showBulkPanel 条件块的外壳）——删完必须看 patch diff 尾部的闭合标签是否成对，残留会导致 JSX 结构错乱。删 state 用包含功能名的唯一行锚点（`const [showBulkPanel...`），别用相邻通用行（#55 误删 delRiskOpen 同款教训）。
- **保留边界（明确给用户）**：行内库存步进器（±/输入，每行商品）+ 勾选批量操作栏的"改库存"（runBulk，bulkStock 输入+应用）+ 后端批量 PATCH API 都保留——删的是"按当前筛选批量库存调整"这一个入口。用户截图红框只标了工具栏按钮+调整栏，就只删这些，别扩大。
- 通用：删功能先看用户截图/点名**精确边界**（删哪几块、保留哪几块），删完 grep state/函数零残留 + tsc + diff 检查闭合标签。

## 61. 收藏店铺头像不显示（#48 头像模式变体：API select 缺字段，不是前端没渲染图片）
- **症状**：买家个人中心 → 收藏 → 店铺头像不显示（只有"店名首字"色块）。
- **根因（与 #48 不同）**：这次前端**不是没有图片渲染逻辑**，是**后端 API 没返回字段**——`app/api/account/store-favorites/route.ts` 的 `include: { store: { select: { id, name, slug, country } } }` **漏了 `logoUrl`** → 前端 `item.logoUrl` 恒 undefined → 走色块兜底。
- **修复**：①API select 加 `logoUrl: true` ②前端 `StoreFavoriteItem` 类型加 `logoUrl?: string | null` ③渲染 `item.logoUrl ? <img style={{width:"100%",height:"100%",objectFit:"cover",borderRadius:"inherit"}}/> : <i>{item.name.slice(0, 2)}</i>`（有图显示图，无图色块兜底）。
- **通用排查**：头像/图片"不显示"且前端已有 img/backgroundImage 逻辑 → **先查 API select/返回结构缺不缺字段**（`grep -rn 'select:'` 数据源看是否含 logoUrl/avatarUrl/imageUrl），别一上来改前端——#48 是"渲染层没接图"，#61 是"数据层没给字段"，两类都要查。头像/logo 类字段做展示时，API select 清单和前端类型定义同步核对。
- **★二次复报"还是不显示"= 第二查询路径遗漏（2026-08-09 用户再次反馈实锤）**：#61 修复的是 API route（`app/api/account/store-favorites/route.ts`，DELETE 用），但页面 **`app/favorites/page.tsx` 是服务端组件直接查 prisma**（`prisma.storeFavorite.findMany({ include: { store: { select: { id, name, slug, country } } } })`——**同样漏 `logoUrl`**）→ 用户"还是不显示"。修复：page.tsx 的 select 加 `logoUrl: true` + `storeFavorites` map 加 `logoUrl: row.store.logoUrl ?? ""`（类型 StoreFavoriteItem 已有 logoUrl?: string | null，tsc 0）。**通用：同一数据多条查询路径（API route + 服务端组件直查）都要核对 select 字段——修了一条路径用户复报 = 找第二条**。
- **复报处理流程（本会话两次复报验证有效）**：用户复报同一问题（404 跳转/头像不显示）→ ①先验证生产代码是否已修复（服务器 grep build 产物：`grep -o 'seller/account' /www/tiktok/.next-build/server/app/seller/notifications/page.js`、`grep -c 'change_request'`；或浏览器 fetch chunk 查特征串 #65）②浏览器实测复现（qa 账号登录走真实点击链路）③代码已修 + 实测正常 → 用户侧是旧 JS/词典缓存（指导 Ctrl+Shift+R 强刷）；实测仍坏 → 找未覆盖的路径（第二条查询/另一渲染分支）。**别一收到复报就重新改代码**——先验证，避免在已修好的地方空转。
- **浏览器实测收藏店铺头像**：登录买家端 → `/favorites?tab=stores` → `document.querySelectorAll('.bac-fav-thumb')` 逐个查 `hasImg / img.src / fallback textContent`——有 logoUrl 的显示 img，无 logo 的显示"店名前 2 字"占位（**店铺本身没设 logo = 正常**，不是 bug，别当问题修）。

## 62. LanguageSync 切语言整页 refresh 丢表单输入（发品/编辑表单必须排除）
- **症状**：发品页输入标题后切语言 → 400ms 后页面整页刷新 → **已填的表单数据全部清空**（浏览器实测：输入"测试苹果手机壳"切英文后标题输入框变空）。
- **根因**：LanguageSync（components/LanguageSync.tsx）的 `handleLanguageChange` / `handleStorage` 在 `scheduleApply()` 后总是 `router.refresh()`（防抖 400ms，全站切语言兜底 #1）。对**有表单输入的页面**这是灾难——整页刷新 = state 全丢。
- **修复**：refresh 前排除发品/编辑表单路径（这两个页面自身有 `qavlixor-language-change` 监听 forceTick 即时刷新，不需要整页兜底）：
  ```ts
  if (!/\/seller\/products\/(new|[^/]+\/edit)/.test(window.location.pathname)) {
    window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(() => router.refresh(), 400);
  }
  ```
  handleLanguageChange + handleStorage **两处都要加**。
- **通用**：LanguageSync 的全站 router.refresh 兜底对"有输入状态的页面"（表单/编辑器/搜索框）是副作用源——凡客户端组件已自行监听语言事件强刷的页面，refresh 兜底应排除（本会话表单页 = 排除清单；以后加表单页记得同步）。

## 63. 发品表单"输入即翻"（用户拍板：编辑时输入框内容随语言切换显示翻译；不加状态提示）
- **需求**：用户明确"编辑时输入内容即时翻译显示（切语言输入框内容也跟着变）"+"不加提示"（不加多语言状态提示条）。这是**数据内容翻译**不是 UI 文案翻译——输入框里的中文值切英文后显示英文。
- **架构（form-translate API + fieldI18n 缓存 + tr() 显示函数）**：
  1. 新 API `app/api/i18n/form-translate/route.ts`：POST `{ fields: Record<string, string> }`（≤40 字段、每字段 ≤500 字符）→ `translateToAllLanguages(fields)`（lib/machine-translator.ts 33 行，一次翻 **7 语言**）→ 返回 `{ ok, translations: Record<key, TranslationMap> }`。**一次翻全语言**，前端缓存后切任意语言毫秒级（不再请求）。
  2. 组件（SellerProductForm）：
     - `const [fieldI18n, setFieldI18n] = useState<Record<string, Partial<Record<string,string>>>>({})`——缓存 key = **`${字段标识}::${原文}`**（原文变 key 变，自动失效）
     - `fieldRef`（useRef）存最新字段值，`fieldRef.current = {...}` **必须在所有 state 声明之后**（否则 TS2448/TS2454 block-scoped before declaration——本会话踩）
     - `useEffect([lang])`：lang 非中文时 collect 所有非空输入（title/brand/customCat/sellingText/shippingNote/skuItems[].name+sku/descRows[].label+value）→ 过滤已缓存 → POST form-translate → `setFieldI18n` 合并
     - 显示函数：`const tr = (fieldKey, text) => (!text || lang === "zh-CN") ? text : fieldI18n[`${fieldKey}::${text}`]?.[lang] ?? text`——**中文显示原文，其他语言显示缓存翻译，未翻译完回退原文**（不破坏编辑）
     - 输入框 `value={tr("title", title)}` + onChange 更新原文 state（9 处输入框：标题/品牌/自定义类目/规格名/SKU编码/参数label/参数value/卖点/发货备注）
  3. **保存机制澄清（答复用户"怎么确认保存了"）**：发品表单"下一步"**不保存**（只是 step 切换，数据在页面内存）；**只有第 4 步"保存草稿/提交审核"（新建）或"保存修改"（编辑）才 POST/PATCH 落库** + buildProductI18n 生成 7 语言 i18nJson（失败后台 sync-content-i18n cron 2 分钟补 + 买家端动态词典兜底）。买家端按浏览语言从 i18nJson 取标题/规格/详情。
- **踩过的坑**：
  1. `fieldRef.current = {...}` 赋值放在 state 声明前 → TS2448/TS2454（title/brand/customCat 未声明）——赋值必须移到所有相关 state 之后
  2. **语言码是 `"zh-CN"` 不是 `"zh"`**（LanguageCode 类型：`"en"|"es"|"fr"|"pt"|"ru"|"zh-CN"|"ar"`）→ `lang === "zh"` 报 TS2367 类型无重叠
  3. **最终收尾方案（重要）——翻译触发不能只靠 `useEffect([lang])`，必须挂语言事件用事件 detail**：
     - **坑**：`useEffect([lang])` 依赖 `currentClientLanguage()`（读 localStorage），①语言切换写 localStorage 后 `currentClientLanguage()` 可能滞后/读不到（Browserbase 测试环境实测 localStorage 空、cookie 也空 → lang 恒 "en" → effect 只在挂载跑一次，当时输入为空 → 之后输入标题+切语言**永不触发翻译**）②翻译返回后 `setFieldI18n` 更新了 state 但 tr() 渲染闭包读到的还是旧缓存（"缓存写进去了 UI 不更新"）
     - **最终方案（commit 1011338 已部署）**：
       ```ts
       // 语言事件 detail 优先（不依赖 localStorage）
       const [eventLang, setEventLang] = useState<string>("");
       const tr = (fieldKey, text) => {
         const active = eventLang || lang;   // 事件语言优先，localStorage 兜底
         if (!text || active === "zh-CN") return text;
         return fieldI18n[`${fieldKey}::${text}`]?.[active] ?? text;
       };
       // 翻译逻辑抽成 translateFields(nextLang)（async，用 fieldRef/fieldI18nRef 取最新值，
       // fieldI18nRef.current 每次渲染同步，避免 effect 闭包旧值重复请求）
       // 事件监听里触发（detail || lang），forceTick 重渲染：
       window.addEventListener("qavlixor-language-change", handle);  // handle: setEventLang(detail); forceTick(); translateFields(detail || lang);
       // 翻译落缓存后 setTimeout(() => forceTick(), 0) 保险重渲染
       ```
     - 要点：①触发源用**事件 detail**（LanguageSwitcher dispatch 的 `detail: normalizedLanguage`），不依赖 localStorage 可读性 ②显示值 `eventLang || lang` 双源 ③翻译完成后再 forceTick 一次（React 18 setState 批处理下不保证立即重渲染，保险必加）
     - **测试技巧**：浏览器 console 手动触发 `window.dispatchEvent(new CustomEvent('qavlixor-language-change', {detail: 'en'}))` 可绕过 UI 直接验证翻译链路；`performance.getEntriesByType('resource').filter(e => e.name.includes('form-translate'))` 查请求耗时/是否发出
  4. execute_code 改 1.2MB translations.ts 大文件会沙箱超时（#57 同款）——按行号最小插入。
- **通用**：输入即翻类需求 = 原文 state + 全语言翻译缓存 + 显示层 tr() 函数；缓存 key 带原文保证自动失效；**触发不能依赖 localStorage 语言值（切语言写 localStorage 可能滞后/环境异常），用语言事件 detail 是稳的**；必须处理"翻译返回后重渲染"（forceTick 保险），否则缓存写进去了 UI 不更新。别用 getTranslation 拼接（#15 教训），也别把输入框 value 直接替换成翻译值（会破坏原文 state）。

## 64. ★翻译键语言区整体错位（"加入购物车按钮翻译不彻底"的终极根因——getTranslation 返回错误语言）
- **症状**：用户三次反馈"加入购物车按钮翻译没彻底修复"。组件监听（#59）、缓存（#42）、SKU 价格同步（#45）全修了仍错乱：SSR 输出按钮是 "Añadir al carrito"（西语），但页面其他文案是英文——**同一组件里 getTranslation 两个键一个英文一个西语**，绝无可能，指向键本身错位。
- **诊断方法（tsx 直测，比浏览器实测快一个数量级）**：
  ```bash
  npx --yes tsx -e "import { getTranslation } from './lib/translations.ts'; console.log(getTranslation('en','ui.cn.103')); console.log(getTranslation('zh-CN','ui.cn.103'));"
  # 结果：en → "Añadir al carrito"（西语！）  zh-CN → "Add to Cart"（英文！）= 语言区错位
  ```
  再打印 7 语言序列确认错位链：`['zh-CN','en','es','fr','pt','ru','ar'].map(l => getTranslation(l, key))`——完美错位模式 = zh 区放英文、en 区放西语、es 区放法语…（每个区放了"下一个语言"的值）。
- **根因**：某次批量插键/生成时语言列表循环错位一位。本会话实锤：**`ui.cn.89~ui.cn.105` 共 17 键**（加入购物车/已加入/立即购买/已确认收货/满X包邮/填写收货信息/跨店拆分/买家付款/商家发货/交易成功 等）在 **7 个语言区全部错位**——之前所有"按钮不翻译"修的都是组件层，病根在数据层键值。
- **grep 行号会骗人（关键教训）**：`grep -n '"ui.cn.103"'` 显示 10597 行 "Add to Cart"、13575 行 "Añadir al carrito"，**看着像 en 区正常 es 区正常**——但 translations.ts 的对象边界不是直觉的"zh→en→es"顺序，实际是：`esFull(32-2069)/frFull(2070-4108)/ptFull(4109-6148)/ruFull(6149-8188)/arFull(8189-10257)/zh(10258-13151)/en(13152-16052)/es(16053-16951)/fr(16952-17850)/pt(17851-18749)/ru(18750-19647)/ar(19648-20517)`——10597 行其实在 **zh 区**、13575 在 **en 区**！**必须用 getTranslation 实际调用验证，不能凭 grep 行号判断语言区归属**。
- **修复**：按对象行号区间把 17 键 × 8 区（含 arFull 区）的值全部替换为正确语言。**坑**：①arFull 区（8189-10257）里也有这些键（中文源块），要替换成**阿拉伯语**——区间扫 0-10257 统一填中文会污染 ar；②替换脚本 key 映射别写 `lang_vals["zh"]`（vals 里是 `"zh-CN"`）→ 会把 zh 区刷成空串；③修完必须 tsx 重打 7 语言确认，别只看 grep。
- **修复后验证**：curl 服务器 SSR `grep -oE 'pdp-add-cart[^>]*>[^<]{0,20}'` → "Add to Cart"（修复前 "Añadir al carrito"）；`立即购买` data-i18n fallback 保持中文不受影响。
- **同类排查**：全量扫描 zh 区非中文键（防再发）：
  ```bash
  npx --yes tsx -e "import { translations } from './lib/translations.ts'; const cjk=/[\u4e00-\u9fff]/; for (const k of Object.keys(translations['zh-CN'])) { const v=translations['zh-CN'][k]||''; if (!cjk.test(v) && !/^[\s，。；、（）：""''!?]+$/.test(v) && !/^ui\./.test(v)) console.log('ZH非中文', k, '=', v.slice(0,30)); }"
  ```
  （标点/占位键如 ui.fix.N 是正常，区分开。）已有可复用脚本：`scripts/verify-i18n-langs.mts`（tsx 直测指定键 7 语言 + 扫 zh 区污染）。
## 65. 翻译体系机制化（用户"翻译问题反反复复修不完"→ 体检脚本 + 自动修复 + 裸中文兜底）
- **用户情绪信号（最高优先方法论）**：用户原话"这个翻译问题反反复复修了好多遍，怎么总感觉有修不完的bug和漏洞"——反复修单点 = 打地鼠，**翻译类问题第二次复现时先做机制化防线再修点**：①全量体检脚本找所有错位/缺失键一次修完 ②把体检纳入流程防再发。别再只修用户报的那个键。
- **已落地的机制（commit 0eeb34d，可复用）**：
  - `scripts/check-translations.mts`：**体检脚本**——扫全部 2921 键 × 7 语言区，检测缺失/zh区非中文/ru区非西里尔/ar区非阿文/占位未填/重复；误报过滤模式（eyebrow/品牌名/术语 SKU-USDT-JPG/格式占位 → fakePattern 排除）；`npx --yes tsx scripts/check-translations.mts` 跑。**改翻译文件后必跑**。
  - `scripts/fix-shift-i18n.mts`：**循环错位自动修复**——检测错位链（esFull=中文 && frFull=英文 && ptFull=拉丁 && zh=西里尔 && en=阿拉伯，≥3 项命中）→ 8 区值循环移位闭环（zh←esFull、en←frFull、es←ptFull、fr←ruFull、pt←arFull、ru←zh、ar←en；es 区缺失时在 es 区开头插入）。**路径注意**：`new URL(..., import.meta.url).pathname` 在 Windows 会拼出 `D:\D:\...` 双盘符 → 直接相对路径 `"lib/translations.ts"`（从项目根运行）。
- **实测修复量**：售后徽标 `seller.aftersalesList.supplemented/supplementedFollow` 2 键 8 区循环错位（zh 区存俄语 = "徽标俄语乱入"根源）——体检 444 条问题里这 2 键是"真错位"，其余多为误报（装饰英文 eyebrow/品牌/格式）和历史无用键（ui.cn.1-30 zh 区缺失，getTranslation fallback 兜底）。
- **裸中文兜底（亚马逊/TikTok 式整体切换的最后防线，commit cfd892d）**：LanguageSync 新增 `applyBareChinese(language)`——切语言后 TreeWalker 扫全站**未标记 data-i18n 的中文文本节点**（按钮/label/表头等界面文案）→ `translateDynamicValue(language, trimmed, "operation")` 查词典翻译 + 缺失词 `reportTranslationMiss` 秒级补译回填。排除规则：中文语言不跑、>40 字长文本（数据走 i18nJson）、含数字/字母/货币符号（拼接/数据）、已标记元素（`[data-i18n], [data-i18n-dynamic], [data-i18n-map], [data-no-translate], input, textarea, select, script, style, [contenteditable]`）。report-miss 返回后（LanguageSync ~300 行）也要 `applyBareChinese(currentLanguage())` 重扫。**效果：不用逐个组件补标记，未标记死角自动翻**。
- **report-miss 实时补译失效排查（返回 `{ok:true, translations:{}}` 空）**：先查服务器环境变量——`translateToAllLanguages` 依赖 `SILICONFLOW_API_KEY || TRANSLATE_API_KEY`，**两 key 都不存在时直接返回 null** → 实时补译静默失败（cron 2 分钟兜底仍工作，所以"大部分翻译正常、个别死角要等/强刷"）。验证：`cd /www/tiktok && npx tsx -e "import {translateToAllLanguages} from './lib/machine-translator.ts'; console.log(await translateToAllLanguages({text:'余额支付'}))"`（NULL = key 未配置）。修复：`echo 'SILICONFLOW_API_KEY=sk-xxx' >> /www/tiktok/.env.local && pm2 restart`。**部署后验证翻译通道 env 是必做步**（本项目多次因 key 缺失/换通道导致"翻译不生效"假象）。
- **★ tsx/node 脚本不自动加载 .env.local（key"不存在"误判根因，本会话实锤）**：`npx tsx -e "console.log(process.env.SILICONFLOW_API_KEY)"` 在服务器输出 undefined = **误判**——tsx/node 直接跑不加载 `.env.local`（只有 Next.js `next start` 运行时才自动加载）。本会话因此一度错误结论"生产 key 不存在"，实际 `.env.local` 里 `SILICONFLOW_API_KEY`（51字符）/`TRANSLATE_API_KEY`（35字符）/`SILICONFLOW_BASE_URL` 全都在。**服务器上测翻译通道/任何依赖 env 的代码，必须先手动解析 .env.local**：
  ```js
  import { readFileSync } from 'node:fs';
  const env = readFileSync('.env.local', 'utf-8');
  for (const line of env.split('\n')) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
  ```
  排查顺序：先 `grep -cE 'SILICONFLOW_API_KEY' /www/tiktok/.env.local` 确认 key 在不在文件里（在 = 通道配置没问题，问题在别处），别用裸 tsx 测 env。
- **B 方案：裸中文词批量翻译入库（词典预置，秒级命中不等补译，commit a4fcd3e）**：裸中文兜底（applyBareChinese）上线后，未标记界面词首次切语言仍要走 report-miss 补译（十几秒）。**预置法**：`scripts/batch-bare-words.mjs` + 扫描提取唯一词（`_bare-words.json`）——全站扫 62 文件 199 处裸中文 → 提取 89 个唯一界面词（排除含字母数字/长文本）→ **SiliconFlow 40 并发单条**（复用 #37 策略）→ `uiTranslation.upsert`（scope=dynamic）→ 客户端切语言直接命中（无需等补译）。实测：结算页切西语"余额支付"→"Pago con saldo"即时；仅剩"TRC20 · 当前可用"（含链名被字母排除规则跳过，属设计）。**裸中文兜底 + 词典预置 = 整体语言切换闭环**：data-i18n 标记元素（LanguageSync 即时）+ 未标记中文（applyBareChinese 词典秒级）+ 新词（report-miss 补译回填）。
- **部署验证技巧（minify chunk 查新代码）**：webpack 压缩后**函数名被改名**（grep `applyBareChinese` 静态 chunk 全空但 webpack cache 58.pack 有）——验证部署是否生效改用**字符串字面量** grep（如新代码独有的 `data-no-translate`、`data-i18n-dynamic-kind`），或浏览器 `fetch(chunkUrl).then(r=>r.text())` 查特征串；浏览器实测前**先 location.href 整页重载**（browser_navigate 同 URL 是 Next.js 客户端导航，不会重新拉 HTML，测到的是旧 JS）。
- **动态词典结构**：localStorage `qav-dynamic-dict-v1` = `{ dynamic: {...}, console: {...} }`（**嵌套**，查词要 `JSON.parse(raw).dynamic['词']`）；词典 9789 条多为商品标题，**界面词（余额支付/商品/店铺）往往不在** → 裸中文兜底靠 report-miss 补。
- **全站裸中文死角扫描**（62 文件 199 处）：`grep -noE '>[一-龥][^<>{}]{2,40}<'` + placeholder/aria-label 属性中文（排除 data-i18n/getTranslation/注释行）——#11/#12/#56 同族，裸中文兜底上线后这些不再需要逐个标记（兜底自动翻），但**首屏 SSR 语言**仍需词典有词（兜底是客户端行为）。

## 66. 用户红线收敛 + 全平台"不走翻译体系"清单 + i18nJson=null 反复根因（本会话收尾）
- **用户红线（2026-08-09 最新拍板）**：被翻译问题反复折磨后，用户明确**只保留 3 项不翻译规则**：①数据行（≥6位数字/邮箱/URL）②货币代码（USDT/US$）③链名/专有名词（TRC20/PayPal/Wise）。**其余全部要走翻译体系**——这是排查/补翻译的取舍依据：技术层的其他跳过规则（长文本>40字、混合文本、属性中文）都是"待消灭"目标，不是用户认可的红线。
- **用户工作方式（情绪信号强化）**：用户原话"先出方案再决定做不做"——对**优化类大改动**（非 bug 修复）必须先给分期方案（P1 管道统一/P2 全局语言/P3 存量清零/P4 词库后台）+ 拍板点（是否全量扫描/LLM 质量/执行范围），确认后才动手。翻译类问题反复时用户会烦躁，回复先共情+根因复盘，再给机制化方案，别再打补丁。
- **i18nJson=null 反复出现的根因（用户"之前不是补齐过好几次吗"）**：①新建/编辑商品 POST/PATCH 同步翻译失败（SiliconFlow 慢/超时）→ catch 静默 → **null 落库**；②`scripts/backfill-product-translations.mjs` 是**一次性手动脚本**（只清跑当时存在的 null）；③2 分钟 cron（sync-content-i18n.mjs）**只处理 TranslationMiss 词典词，不补商品 i18nJson=null** → 新 null 持续产生且无自动补。修复方向（未落地，方案已给用户）：写路径翻译失败不静默（保留旧值+进补译队列）+ cron 加商品 null 自动补（每轮 N 个）+ 全量 backfill 清存量。
- **全平台"不走翻译体系"完整清单（用户要求找全，代码实测盘点）**：
  - **A 用户红线 3 项**：数据行（LanguageSync.tsx:268 missDataLikePattern `\d{6,}|@|https?://` + report-miss:11 DATA_LIKE）、货币代码（applyBuyerCurrency 换算不翻译）、链名（混合文本字母排除）
  - **B 技术层**：中文界面不扫（applyBareChinese:648）；长文本 >40 字（:657）；含数字/字母/货币符号混合文本（:658 `/[0-9A-Za-z$€£¥]/`）；已标记元素（:661）；input/textarea/select/script/contenteditable（:661）；report-miss 长度 <2 或 >190/纯符号/限流（IP 10次/分、批 30、实时 ≤8）；**商品 i18nJson 字段缺口**（product-i18n.ts 只翻 title/detail/SKU 名——brand/自定义类目/卖点/发货备注不生成；description>300 字不翻）；data-currency-fixed 区域（保证金固定币种不随语言）
  - **C 结构性遗漏（裸中文兜底够不到）**：**属性类裸中文 49 处**（未标记的 placeholder/aria-label/title 属性——applyBareChinese 用 TreeWalker SHOW_TEXT **只扫文本节点，不处理属性** → 永远不翻；样本：BuyerHeroCarousel aria-label"首页促销轮播"、LanguageSwitcher"选择语言"、SellerProductManager"库存减一"、AccountProfileForm placeholder"请输入姓名"等）；图片内文字；用户上传文件名/证件内容
  - **D 设计层**：编辑表单输入值（显示层输入即翻 tr()，提交保存值始终原文）；底层 DB 状态值（30 状态词判断逻辑保持中文原值，渲染层翻）
  - **扫描命令**：属性类裸中文 = `re.finditer(r'(?:placeholder|aria-label|title)="([^"]*[一-龥][^"]*)"', line)` 排除 data-i18n 行（49 处）；JSX 文本类 = #65 的 `>[一-龥][^<>{}]{2,40}<`（199 处，兜底已覆盖 40 字内纯中文）
- **通用教训**：用户说"只保留 X 项不翻"时，先把**代码里实际的全部跳过规则**列出来给他看（别只说口头红线）——技术层累积的跳过规则（长文本/混合文本/属性）往往比用户记忆中的多，清单本身就是"待消灭目标"；补齐方向 = 属性扫入兜底/放宽 40 字/混合文本拆翻/商品字段扩展。排查"为什么还有中文"先分清：用户红线（保留）vs 技术层（可放宽）vs 结构性遗漏（要补机制）vs 设计层（向用户说明）。

## 68. P1+P3 商品翻译自动化落地 + backfill 401 根因 + 部署提速（一键 deploy.py 98s）
- **backfill 401 根因（\"补了好几次还有 null\"的真凶，本会话实锤）**：`scripts/backfill-product-translations.mjs` 的通道判断是**旧版**：`isSiliconflow = !!SILICONFLOW_API_KEY && !process.env.TRANSLATE_PROVIDER`（带 `&& !TRANSLATE_PROVIDER`）→ 服务器 `.env.local` 残留 `TRANSLATE_PROVIDER=deepseek`（早期 deepseek 通道旧值）→ isSiliconflow=false → 走 deepseek 分支；且 `baseUrl = process.env.TRANSLATE_BASE_URL || ...` 读到的也是 deepseek 旧 base_url → **SiliconFlow key（...aoww）发给 deepseek 服务器 → 401**（日志：`Authentication Fails, Your api key: ****aoww is invalid`）。**修复**：①isSiliconflow 改为 `!!SILICONFLOW_API_KEY`（key 存在即优先，与 machine-translator.ts 一致）②baseUrl 在 isSiliconflow 时**硬编码 `https://api.siliconflow.cn/v1`**（不读 TRANSLATE_BASE_URL）。**通用铁律**：所有翻译脚本（machine-translator.ts / i18n-scan-lib.mjs / backfill）的通道判断必须完全一致；服务器 `.env.local` 的旧 provider/base_url 残留是持续劫持源——排查 401 先 `grep -E 'TRANSLATE_PROVIDER|TRANSLATE_BASE_URL' .env.local` 看残留。修复后实测：回填完成 成功2 跳过6995 失败0 → **存量 null 清零**。
- **P1 商品翻译自动化（已落地）**：①POST 保存**秒回**——`app/api/seller/products/route.ts` 移除同步 `buildProductI18n`（`product.i18n = undefined`），翻译由 worker 后台补（原同步 20s+ 卡）②`scripts/sync-content-i18n.mjs`（2 分钟 cron）新增\"商品 i18nJson=null 补译段\"：`NULL_PRODUCT_PER_RUN`（默认 30）个/轮，`orderBy updatedAt asc` 老优先，失败**下轮自动重试**（null 还在=天然重试队列），成功同步写 UiTranslation 词典（买家端秒级）③backfill cron 本就 10 分钟跑（`*/10 * * * * node scripts/backfill-product-translations.mjs`）——双保险。**PATCH 失败保留旧值**（`buildProductI18n(...).catch(() => undefined) ?? product.i18n` 已对）。
- **GLM-5.2 模型提速**：SiliconFlow 上 `zai-org/GLM-5.2` 单条 11.7s vs `deepseek-ai/DeepSeek-V4-Flash` 20s+（Qwen3.5-27B/9B 实测 ERR 不稳定）。model 三处改读 `TRANSLATE_MODEL`（machine-translator/i18n-scan-lib/backfill），服务器设 `TRANSLATE_MODEL=zai-org/GLM-5.2`。**并发不是越高越好**：SiliconFlow 40 并发实测排队严重（单条拖到 45s，1 条超时）——20-40 并发够用。cron 并发：sync-content 40 / backfill 40（`SYNC_CONCURRENCY`/`BACKFILL_CONCURRENCY` 可配）。
- **坑：脚本变量名误改致 cron 崩溃**：给 sync-content-i18n.mjs 加补译段时把 `let added = 0, failed = 0` 误改成 `done`（后面引用还是 `added`）→ 每 2 分钟 cron 报 `ReferenceError: added is not defined`。**改脚本变量名后必须 grep 全部引用**（`grep -n 'added' scripts/`），部署后跑一次脚本验证再走。
- **部署提速（一键 98 秒，原 6-8 分钟）**：`scripts/deploy.py`（paramiko 全自动）：①本地 `npx tsc --noEmit --incremental`（tsconfig 已有 incremental → **2 秒**，原 1-2 分钟）②git commit ③`git archive | gzip` ④SFTP 上传 ⑤服务器 `pnpm exec next build --no-lint`（`next.config.ts` 加 `typescript: { ignoreBuildErrors: true }`——**前提：本地 tsc 已把关**，build 从 ~3min 降 ~1.5min）⑥`pm2 restart ×2` + curl 200 探测。用法：`python scripts/deploy.py \"改动说明\"`。**注意**：`next build` 默认跑 typecheck+lint，跳过必须在 next.config 显式配。
- **任务4 收尾**：发品表单发货时限 AppleSelect options（\"48 小时内发货\"等 4 词，含数字但 4 位以下数字 DATA_LIKE 不排除→可进词典）批量翻译入库预置（`translateToAllLanguages` + `uiTranslation.upsert`，tsx 跑因 import .ts 必须 `npx tsx`，node 直接跑 .mjs import .ts 报 ERR_MODULE_NOT_FOUND）；`aria-label=\"移除图片\"` 补 `data-i18n-aria-label=\"seller.productForm.removeImage\"`（属性类裸中文 #66-C 的唯一发品表单残留）。**注意**：patch 时别误改 className（img-del→thumb-del 样式会变）。
- **任务5 发货备注清理**：`SellerProductForm` composedShippingNote 原本拼 `[getTranslation(ui.sel.149)+shipBy(中文选项值), shipFeeText, 备注]`——**shipBy 存中文选项值 + 前缀按保存时语言翻译 = 中英混合乱码**（\"那串英文+时间\"）；且自定义运费文本 `首件 (feeFirst)` 是**未替换的字面量占位符 bug**。修复：删掉发货时限拼接（shipBy 不用于业务催发，order-repository 的 shipBy 是独立计算值）+ `(feeFirst)`→`${feeFirst}`；买家配送栏只显示 运费方式+卖家备注。**通用**：模板字符串里出现 `(变量名)` 字面量 = 占位符没替换，grep 模板字面量查 `\(\w+\)` 模式。
- **任务6 批量勾选残留**：#40（提交体不带 ids）之外的另一根因——`SellerProductManager` 的 `selected` Set **跨筛选/搜索残留**（切类目/搜索后不清空，用户\"只选一件\"实际勾选多个）→ 修复：类目/搜索 onChange 里 `setSelected(new Set())`。**通用**：批量勾选 = 提交体带 ids（#40）+ 筛选变化清空勾选（防残留误操作）双保险。
- **发货时限词预置验证**："48/24/72 小时内发货""7 天内发货"4 词全缺词典 → 预置后 `AppleSelect options` 走 `translateDynamicValue(lang, label) || label`（#41 已接）→ 切语言秒级命中。

## 69. 卖家端聊天对话框头部买家头像不显示（#48 头像模式变体：同组件角色分支遗漏）
- **症状**：卖家端聊天对话框**顶部**不显示买家头像（只有色块/首字）；**左侧会话列表**显示正常。用户原话\"买家头像只在左侧对话列表中有显示，对话框顶部却不显示\"。
- **根因**：ChatWindow chat-hd 头部头像（components/chat/ChatWindow.tsx ~125-131 行）按 `role` 分两分支——**买家端分支**（`role === "buyer"`）有 `conversation.peerAvatar ? backgroundImage : 色块` + Link 跳店铺；**else 分支（卖家端）漏了图片逻辑**，只有 `avatarColor(peerName)` + `avatarText(peerName)` 色块占位。左侧列表（ChatList）正常是因为列表是另一段正确渲染——同组件两分支一个渲染图片一个没渲染。
- **修复**：else 分支同样加 `conversation.peerAvatar ? { width:34, height:34, backgroundImage: url(...), backgroundSize:"cover", backgroundPosition:"center" } : 色块`（卖家端视角的 peerAvatar = 买家 avatarUrl，#48 数据链路已给）。
- **通用**：同一组件按角色/状态分多个渲染分支时，**新能力（头像/跳转/翻译/徽标）必须所有分支同步**——#48 修了买家端视角，卖家端视角漏 = 用户报\"另一侧不显示\"。排查\"一侧正常一侧不正常\"先看分支条件（role 判断 / else 分支），别重查数据链路（数据两边共用，正常）。

## 70. 聊天买家名显示邮箱（卖家对话框显示 buyerEmail 而非真实名 + 无名字占位拍板 🎮）
- **症状**：卖家端对话列表/对话框顶部买家\"明明有名字\"（User.displayName 如 \"Notto Mio\"）却显示邮箱（<EMAIL-REDACTED>）。用户拍板：\"改成显示买家名字好一点，没名字的再显示🎮\"。
- **根因（两层）**：
  1. **存量数据**：早期创建会话时 buyerName 兜底存了 `normalizedEmail`（生产实测：`buyerName: \"<EMAIL-REDACTED>\"`、`\"<EMAIL-REDACTED>\"` 全是邮箱；部分是真名 \"Salad\"）——`peerNameFor` 的 seller 分支 `row.buyerName || row.buyerEmail` 直接用了邮箱。创建处（297 行）其实已优先 `displayName`，问题在**存量行**。
  2. **窗口头部用原始字段**：ChatWindow `const peerName = role === \"buyer\" ? conversation.store : conversation.buyer`——用 `conversation.buyer`（mapConversation 168 行 `row.buyerName || row.buyerEmail`），**不是列表用的 peerName**（API 计算好值）——列表已改但窗口没变。
- **修复（三处，commit 链）**：
  1. `getChatConversationList`（lib/message-repository.ts ~583）：buyer join 查询从 `select: { email, avatarUrl }` **扩展加 `displayName`** → 建 `nameByBuyer` map → `peerName`（seller 视角）= `nameByBuyer.get(buyerEmail) || (buyerName 非邮箱 ? buyerName : null) || (seller_support ? \"平台客服\" : \"🎮\")`（**不再 fallback 到 email**）
  2. `getCommerceConversation`（~247 卖家视角块）：buyerUser 查询加 displayName → `mapped.buyer = displayName || 非邮箱buyerName || (seller_support ? \"平台客服\" : \"🎮\")`（对话框头部同款纠正）
  3. `peerNameFor` seller 分支（~560）：`(buyerName && !includes(\"@\") ? buyerName : null) || (seller_support ? \"平台客服\" : \"🎮\")`——**含 @ 的名字一律当邮箱丢弃**，兜底 🎮 不显示邮箱
- **实测（qa-seller-1 浏览器）**：列表 + 对话框头部都显示 \"Notto Mio\"（qa-buyer-1 的 displayName）✅；无 User 记录/无名字的会话显示 🎮（\"2132 111\" 那种买家也是 Notto Mio——同一买家多会话，join User 后统一真实名）。
- **通用教训**：①\"显示名字却见邮箱\"= 存量数据 buyerName 被 email 污染 + 兜底链把 email 当名字——**先查生产 `conversation.buyerName` 实际值**（`JSON.stringify`），再决定是改数据还是读取层纠正（本项目选读取层 join User，存量不动）②**兜底链禁止 fallback 到 email**（显示层邮箱是隐私/体验双败），无名字用用户拍板的占位符 ③同一实体（会话）多处展示（列表 peerName vs 窗口 buyer）**字段口径要一致**——窗口直接用了原始字段，没复用列表的计算值，是\"一侧正常一侧不正常\"的又一形态（#69 是分支遗漏，这条是字段口径不一）。
：写 `D:\跨境商城\会话产物\xxx-待核实.html`（每项一张红框卡片：编号徽章 + 位置(文件:行号) + 内容 + 现状 + 性质标签；顶部列"已确认项"省用户时间；底部说明核实方式），`cmd /c start "" "路径"` 用系统 Chrome 打开；用户逐项回"编号+决定"（如"1 保持，2 翻"）。用户偏好**逐项可见可核**的清单而不是长文描述——每项必须带代码位置证据。
- **逐项核实结果（2026-08-09 用户拍板，8 项 data-i18n-raw）**：
  - **改翻译（移除 data-i18n-raw，14 处）**：AppleSelect 下拉选项(2)、运费模板名/仓库/时限/承运商/适用范围(5)、账号设置"审核中：新昵称/新店名"+未满足项数(3)、资金中心指标点(1)、管理端用户类型标签(1)、管理端测试订单 SKU 规格值(1)、管理端提现审核备注(1)
  - **保留不翻**：语言切换列表（用户早先指定）、管理端变更审核 TYPE_LABEL/STATUS_LABEL+审核备注（用户拍板"审计原文不翻译"）
- **最终"不翻"清单 6 项（全项目定稿，docs/翻译铁律.md）**：①语言切换列表 ②物流追踪号（=快递单号如 LP00123456789，用户确认不翻）③数据行（≥6位数字/邮箱/URL）④货币代码（USDT/US$）⑤链名/专有名词（TRC20/PayPal/Wise）⑥管理端变更审核（审计原文）。**其余全部翻译**（聊天/国家名/订单快照/卖家资料"名字翻号码不翻"等）。判断表 + 机制保障 + 维护规则见 `docs/翻译铁律.md`（新 AI 接手先读它）。
- **★误伤 bug（裸中文兜底会翻"指定不翻"内容）**：applyBareChinese 的排除选择器（LanguageSync ~661 行）原本 `[data-i18n], [data-i18n-dynamic], [data-i18n-map], [data-no-translate], input, textarea...`——**漏了 `data-i18n-raw` 和 `.language-switcher`**！而 addedNodeNeedsLanguageSync（~357 行）有这两项 → 切语言时语言列表里的"简体中文/中文"（含中文，词典有"Chino simplificado"等）**会被裸中文兜底翻译掉**。修复：661 行排除列表补 `[data-i18n-raw], .language-switcher`（与 357 行一致）。**通用**：任何"跳过翻译"保护标记（data-i18n-raw/data-no-translate）必须在所有扫描路径的排除列表里同步——两处排除列表（裸中文兜底 + addedNodes 判断）各加各的，漏一处就是误伤源。
- **data-i18n-raw 全站盘点法（找"指定不翻"完整清单）**：`grep -rn "data-i18n-raw" components/ app/ --include="*.tsx"`——本会话 21 处（LanguageSwitcher 4 + 8 类 16 处 + LanguageSync 排除规则 1）。改翻译 = 移除属性（`s.replace('<span data-i18n-raw>{x}</span>', '<span>{x}</span>')` 批量，14 处一次改完）；保留 = 不动。改完 `grep -rn "data-i18n-raw" | grep -v LanguageSwitcher\|AdminChangeReviews` 应为 0（只剩 LanguageSync 保护规则本身）。
- **用户情绪安抚（重要，翻译类长期反复时的处理模板）**：用户原话"我有点迷茫畏手畏脚不敢改了…不确定哪些需要翻译哪些不需要"——此时给**一句话铁律** + 安心三事实：①"凡是给外国人看的文字就翻译；凡是机器认的数据/钱/专有名词就不翻译"②翻译是显示层换肤不改数据（翻错只是显示问题，不会破坏订单/金额/逻辑）③裸中文兜底已上线=不需要提前决定每处翻不翻，漏的自动查词典+新词自动补。再把铁律写进 docs + memory 固化，让用户以后"看到哪没翻告诉我"即可，不再手动决定。
- **部署后验证**：移除 data-i18n-raw 后这些内容走裸中文兜底/词典（运费模板名等卖家自填词首次切语言走 report-miss 补译，1-2 秒回填）；管理端变更审核保持中文是**预期行为**（不是 bug）。






