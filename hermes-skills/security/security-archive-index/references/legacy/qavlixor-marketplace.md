<!-- archived from /root/.hermes/skills/security/qavlixor-marketplace/SKILL.md on 2026-10-21 -->

---
name: qavlixor-marketplace
description: >-
  测绘引擎·维护 Qavlixor 跨境商城 i18n 补键、AppleSelect、prisma dev schema、页面审核。
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-marketplace`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-marketplace/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-marketplace（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-marketplace/`

溯源（仅标记）：`hermes/software-development`

---

# Qavlixor Marketplace 项目维护

跨境商城独立站（买家端根路径 / 卖家端 /seller / 管理端 /admin）。Next.js 15 App Router + TypeScript + Prisma + 全站 i18n（`lib/translations.ts` zh/en 双区 + LanguageSync 客户端词级翻译）。

## 新坑速查 → 详见 refs/（按日期归档）
/#订单号时间戳根因+生产psql直查+改单号同步纪律→refs 2026-08-13-test-order-time-fix
/批量上传模板16列+恶意xlsm警告→refs 2026-08-11-batch-upload-template
/#169商品审核通知+补键脚本定稿法+.btn样式→refs 2026-08-10-product-review-notify
/#172-192→refs 2026-08-11-pay-deadloop-routesegment
#193-197 flexWrap/余额精度/插键区序/已支付拦截→refs 2026-08-11-tail-fixes
#198onebound铺货→refs onebound-shelf.md
#199删号/密码重置→refs 2026-08-11-account-deletion
#200保证金死锁(草稿计入应缴)→refs 2026-08-11-deposit-deadlock
#201类目二三级→refs 2026-08-11-custom-category-levels
#202上品工具+木马→refs 2026-08-11-auto-shelf-tool|2026-08-11-malware
#203-205客服三波→refs 2026-08-12-support-chat-stock-sku|support-chat-iteration|support-agent-admin
/#206客服角色页UI方案A→refs 2026-08-13-staff-create-roles-ui
/#2026-08-14订单生成真实化+时区三件套+扣库存+通知补发+待结算eta+翻译铁律→refs 2026-08-14-real-order-gen-timezone-stock
#165见refs late-session
#167代充不发通知/通知角色/动态import prisma→refs 2026-08-10-admin-transparency
#166+通知16类型清单见refs 2026-08-10-notification-types(PREF_GROUP分组/触发场景/DB分组查询脚本/给用户做类型一览HTML模板)
①切语言一步到位（SSR 固化→data-i18n/语言监听/LanguageSync refresh 兜底）
②时区偏移（前端传 Unix 毫秒时间戳，禁 toISOString 依赖浏览器时区）
③售后 history actor 是中文标签（判 `=== "买家"` 不是 "buyer"）
④售后证据 CDN 白名单（cdn.qavlixor.com 需放行）
⑤部署包禁止 git 跟踪（自我包含 → tar.gz 解压 EOF）
⑥校验订单定时创建（ScheduledOrderJob/Item + cron 每分钟 + 按 storeId 分组 + CRON_SECRET 内联）
⑦SKU 上限 20 + trim-over-sku 存量收敛（保留订单引用；按钮保留可点+点击提示，禁隐藏入口）
⑧物流 lastEvent 17TRACK JSON 兜底乱码
⑨布局"太靠两侧"= 贴边问题（space-between + padding），不是改居中
⑩translations.ts 插键语言区顺序 zh→en→es→fr→pt→ru→ar，锚点必须用语言特定值（禁裸键名 replace），插前查键号占用、插后验 7 处分布
⑪data-i18n-raw = 跳过翻译（动态中文值禁用它，改 DynamicText；排查页面不翻译先扫它）
⑫按钮/链接漏 data-i18n 标记（同页同类元素一个有标记一个没有 = 漏标典型）
⑬纯文本元素漏交互链接（商品/店铺名没包 Link = 点击无效；数据缺跳转字段如 CartItem.storeSlug）
⑭i18n 数据字段已随查询返回但渲染层漏用（commodityI18n 纯文本 td；查数据源字段→看页面是否消费）
⑮动态统计值"数字+单位"禁止 getTranslation 拼接整段给 DynamicText（查词典失败），数字裸渲染+单位 data-i18n 分离
⑯动态词典源串必须与页面实际渲染值逐字符一致（含 \n/全角标点）——补词典前先生产 JSON.stringify 实际值；解析文本含换行用 `[\s\S]*` 禁 `.*`（rma 时间线二次不翻根因）
⑰搜索匹配池只含中文标题 → 其他语言搜不到；拼入 item.i18n.title 各语言（Object.values 加入 haystack），商品 i18n 全量无需回填

## 触发条件
- 任何 Qavlixor 项目页面/组件的 i18n、布局、资金、审核、管理端功能改动
- 出现 `data-i18n` 键名泄漏（显示 "seller.xxx.yyy" 原文）、中英混排、金额被换算成 $/USD
- prisma generate / db push / 新增表后的 dev 恢复

## 核心流程

### 1. i18n 批量补键（坑 #32，最高频）
症状：页面显示键名（如 `admin.merchants.col.store`）或半译（"营业执照和法人信息Pending review"）。根因：translations.ts 键被批量脚本误删过（坑 #32 重灾区：SellerProductForm 58 键、AdminMerchantManager 26 键全缺失）。
流程：
1. `execute_code` 用正则从组件提取：`data-i18n="key">中文原文<` + `data-i18n-placeholder="key"`（注意 placeholder 与 data-i18n-placeholder 属性顺序两种写法都要匹配）
2. 键前缀按页面/组件：`admin.merchants.*`、`seller.productForm.*` 等
3. **锚点精确替换插入** zh/en 双区（先 grep 确认锚点 count==1，如 `"admin.nav.merchants": "商户总管理",`），插入后 grep 校验键存在
4. **键值禁英文双引号**（破坏 TS 语法——吃过多次亏；zh 值里的英文引号换中文「」）
5. `npx tsc --noEmit` 必须 EXIT 0
6. 数据值/变量渲染（`{...}` 三元、DynamicText、状态值）不加键

**七国翻译现状（2026-08 已全量机翻完成）**：zh 2013 + en 1984 真双语；**es/fr/pt/ru/ar 各 2013 键已批量机翻**（deepseek，`scripts/gen-ui-lang-packs.mjs` + 合并进 translations.ts 的 `xxxFull` 变量，文件 14185 行，build 后共享 chunk 无膨胀 102kB）。结构：`{ lang: { ...zh, ...en, ...langPack, ...lang, ...langFull } }`。翻译通道**固定 deepseek**（用户指示：翻译以后都走 deepseek 不再走 fkcodex——fkcodex 中转会 503 通道耗尽）。en 缺键无害模式（zh 值即英文）勿修。详见 `references/pitfalls.md`「七国翻译现状」「UI 键批量机翻工作流」。

**自动翻译架构（用户问"不是有个自动翻译吗"）**：机翻只管**动态内容**（商品描述/通知/聊天/工单，UiTranslation 表 + cron + deepseek API，生产 ~8500 条已入库，页面即生效无需部署）；translations.ts 的 **UI 键不走机翻**（所以切 es/fr/pt/ru/ar 显示英文）。链路与机翻 cron 崩溃根因（.env.local 的 sqlite DATABASE_URL 覆盖）见 `references/pitfalls.md`「自动翻译架构」「loadEnvFiles 的 .env.local sqlite DATABASE_URL 覆盖」。

### 2. prisma dev/prod 双 schema（2026-08 重大基建）
- 生产 schema=postgresql（真源）；dev 本地库 `prisma/dev.db` 是 **sqlite**
- **dev 环境禁用裸 `prisma generate`/`db push`**：generate 成功会把 client provider 切成 postgresql → dev.db 连不上 → dev 全崩（曾踩）
- dev 一律用：`pnpm db:gen:dev`（派生 sqlite schema → generate）和 `pnpm db:push:dev`
- `scripts/make-dev-schema.mjs` 从主 schema 派生 `prisma/schema.dev.prisma`（模型自动同步）
- **prisma generate EPERM**：dev 进程占用 query_engine DLL → 需停 dev（process kill + netstat 清 PID）→ generate/db push → 重启 dev

### 3. AppleSelect 与数据值豁免
- AppleSelect 的 label span 是 `data-i18n-raw`（**跳过词翻译**）——数据值（类目名/筛选值/风险等级"低中高"/"全部店铺"）英文态显示中文属正常豁免，不要"修"
- **【2026-08-08 新增 labelKey 支持】**`AppleSelectOption` 加可选 `labelKey`：渲染时 `data-i18n={item.labelKey ?? undefined}` + `data-i18n-raw={item.labelKey ? undefined : item.label}`（**有 labelKey 走翻译键，无则 raw 原样**）——下拉选项（如售后类型"部分退款/全额退款"）要翻译时给选项传 labelKey，别把选项值改成英文（value 是中文数据提交不可改）
- UI 文案（按钮/表头/标题）必须 data-i18n 键；筛选 options 的 value 是中文数据不可改
- AppleSelect label 已全局加 `overflow:hidden;text-overflow:ellipsis`（长文本截断不溢出）

### 4. 金额与占位符
- 所有 USDT 金额文本（含表头/键值里的 "USDT" 字样）加 `data-currency-lock`，否则被货币系统换算成 USD
- 含占位符文案禁 data-i18n 整段替换（坑 #34：`{count}`/`{max}` 被当字面）→ 拆静态 label 键 + 数字独立渲染
- **货币换算系统（2026-08 已全站 USDT 化）**：`lib/currency-constants.ts` 的 `CURRENCY_BY_LANGUAGE` 按语言映射展示币种——历史 `zh-CN→CNY` 就是中文界面一直冒人民币的根源（用户问"为什么一直出来 cny，谁规定的"）。已改：7 语言全→USDT + `SUPPORTED_CURRENCIES` 加 USDT 置首 + `CURRENCY_LOCALES` USDT→en-US + `FALLBACK_RATES` USDT:1。换算 target=USDT 时 rate 恒 1；Intl 无 USDT 币种 → catch fallback 显示 `"USDT 89.00"`（正好符合展示需求，幂等）。**CNY/EUR 等仍留在 SUPPORTED_CURRENCIES 供手动切换**；采集导入 `sourceCurrency`（1688/淘宝=CNY）是数据源标记，与界面货币无关勿动

### 5. 验证
- 语言切换真源 = **localStorage**（客户端）+ cookie（SSR）：验证中英须用页面右上角 LanguageSwitcher 点击，直接 document.cookie 不触发（坑 #36）
- 登录：卖家 <EMAIL-REDACTED> / 管理端 <EMAIL-REDACTED>（密码见 docs/internal-test-accounts.txt）
- 每次改代码后写 `docs/ops-log/YYYY-MM-DD-操作日志.md` + 完成单元自动 commit（不 push）

### 6. 用户删除型需求
用户常"删掉吧/直接删了"——删干净：JSX 块 + 相关 state/函数 + translations 键（zh/en）+ API 参数，别留死键死代码。

### 7. 子代理批量 i18n 任务书必须覆盖组件层
管理端 11 页加固时第一批子代理**只处理了 page.tsx**，`components/admin/` 下 10 个组件 101 处裸中文漏网（AdminTestOrdersClient 27 处、LogisticsTest/ChainTest/MailTest/SmsTest/AlertTest/StorageTest 等测试面板 + TopUpForm/ChangeReviews/PaymentReviewForm）→ 需第二批子代理重扫。**任务书必须写明"page.tsx 及其引用的组件文件都要扫"，并给出组件清单**；交付前用 grep 全 components/admin 扫裸中文兜底。

### 8. 买家端安全审计（2026-08 全量扫描）已知缺陷
全量扫过 app/ 根路径页面 + app/api 买家 API + components/ 买家组件，产出 19 项缺陷（2 严重 / 8 中 / 9 低），**完整清单含 file:line/攻击场景/修复见 `references/security-audit-buyer-2026-08.md`**。改到以下位置前必读，多数是设计遗留：
- `/api/buyer/recharge` **提交即到账**（dev 演示链路，生产未关）= 免费印钱 + 提现套现闭环（S1）
- `lib/auth-model.ts` 硬编码 7 个 admin 明文密码，生产可登录全权限后台（S2）
- checkout 多 SKU 商品**按首 SKU 价格计价**（M2）；`reserveProductStock` Prisma 失败吞错仍返回 ok → 超卖（M3）
- 收银台 `/api/pay/[intentNo]` 无认证，intentNo 即凭证（M4）；`orders/[id]/confirm` 可重复确认无限重置 30 天售后期（M5）
- `messages/[id]` 会话不存在时兜底建会话可伪造他人 buyerEmail（M6）；下单无幂等键（M7）；停用账号会话 7 天内仍可提现（M8）
- 审计方法（可复用）：先读 session/requireRole 层 → 资金路径（充值/提现/意向）→ 订单状态机 → 消息 → 最后 grep `dangerouslySetInnerHTML`/`queryRaw|executeRaw`（本项目 0 命中，XSS/SQLi 面干净）

### 9. 卖家端安全审计（2026-08-07 全量扫描）已知缺陷
全量扫过 /seller 页面 + app/api/seller 全部 21 路由 + 共享路由（fulfillment/aftersales/messages actions）+ lib 资金/订单/物流，产出 17 项缺陷（5 严重 / 7 中 / 5 低），**完整清单含 file:line/攻击场景/修复见 `references/seller-security-audit.md`**。改到以下位置前必读：
- 资金公式**双口径不一致**（S 级功能缺陷）：prismaSnapshot 用保证金净额（pay−refund−deduction），refreshSellerWallet 只减 kind=pay approved → 保证金退还/罚扣后提现闸门双重锁定，退还资金卡死；提现闸门读 wallet.availableAmount（funds-repository.ts:113 vs 221-223 + withdrawals:56-62）
- 资金路由 check-then-act **TOCTOU**：提现（withdrawals:54-100）、保证金划转（transfer:33-56）、保证金退还（refund:27-63）、取消订单（cancel:29-67）全无事务/条件写，并发可超提/幽灵保证金/双回补库存
- **鉴权按 store.name 而非 storeId** + Store.name 无唯一约束 + account PATCH 可自助改名 → 同名店跨店越权（cancel/products/fulfillment/batchShip/aftersales/funds 全中招）；鉴权点 = 全局搜 `scope.storeName`
- 商品审核可绕过：POST/PATCH 接受客户端 status=已上架 → prismaStatus 直接 reviewStatus=approved（product-repository.ts:39-45）
- 售后部分退款把订单置 completed 且不写 afterSalesAvailableUntil → 未妥投订单货款立即可提现（aftersales/[id]:88-90）
- requireRole 不查 sellerAccount.status，suspended/待审核商户全功能可用；sellerApproved 会话标记签了但无 API 消费
- 审计方法（可复用）：鉴权按 storeName 全局搜 → 资金两路径公式逐项对齐 → check-then-act 逐一验证事务性 → 客户端 status 入参查 prismaStatus 映射 → 状态机守卫读 local-db 镜像处交叉验证主库

### 10. 管理端安全审计 + 三端修复状态（2026-08-07 全量扫描）
三端并行扫描（买家/卖家/管理）产出 **26 项真实缺陷 + 2 项设计使然**，**24 项已全部修复并验证提交**（commit `acafcfd`，tsc EXIT 0 + 运行时回归通过）；**收官 2 项也已修复并全量部署上线**（commit `70a5b64` + `8e07b15`，生产 build 15.7s + 4 实例 + 生产实测验证）。**完整修复清单/通用修复模式见 `references/security-audit-fixes-2026-08.md`**；管理端 21 项原始清单见 `references/admin-security-audit.md`。改到以下位置前必读：
- **admin 路由鉴权**：storage/health 曾是全项目唯一无鉴权 admin 路由（已修）；requireAdminPermission 需配合 requireRole 写入的 AdminUser.status 缓存才全面拦禁用员工
- **校验订单资金污染**：test-orders 生成的单必须从资金口径排除（refreshSellerWallet 过滤 `orderChannel !== "validation"`），否则校验单 7 天后全额可提现
- **管理端处理类 API 状态机**：提现处理（submitted/paying 才可动）、confirmIntent（cancelled/rejected 拒确认）、财务驳回（仅未发货待付款）——一律 updateMany 条件写 count===1
- **通用修复模式**（跨三端）：条件原子写 `updateMany({where:{status/gte},data})` count===1 = 状态机守卫+并发防重一体两用；create 后复检回滚（卖家提现/保证金退还）；requireRole 状态校验（admin→AdminUser.status、seller→sellerAccount.status=approved 带入驻豁免参数、buyer/seller→User.status）；服务端不信任客户端 status（POST 已上架→待审核、PATCH 内容变更回审核）；资金统计过滤 orderChannel=validation
- **【2026-08-07 入驻豁免坑】requireRole 加 approved 校验后，入驻向导 API 必须一并豁免**（`{ allowUnapprovedSeller: true }`），否则员工测试反馈\"商户入驻尚未审核通过，暂时无法使用卖家端，无法提交资料\"：豁免清单 = `application/draft` + `application/submit`（已豁免）+ **`/api/uploads`（营业执照/证件上传）** + **`/api/email-verification/send`（purpose=contact 联系人邮箱验证）**。豁免后业务 API（商品/资金）仍 403 锁死未审核卖家。验证：draft 卖家登录 entry=/seller/onboarding → 草稿保存 200 / 上传放行到表单校验 / products 403。**测试入驻流程需 DB 直建 User + SellerAccount(draft)（必填 contactName/contactEmail）**——纯 User 无 sellerAccount 登录报\"该账号不是商户账号\"
- **git add -A 会误提交 work/ 中间产物**（ui-pack-*.json 等）——.gitignore 已加 work/；提交前 git status --short 检查
- **收银台归属校验（M4 已修）**：`app/api/pay/[intentNo]` POST/renew 用 `assertIntentOwner`——注册用户 session 邮箱须 == intent.createdByEmail（403），游客仅限 guest 单（创建者无注册 User 行）且 IP 限流 10 分钟 20 次（内存 Map）；GET 保持公开（游客支付页渲染）。**实测三场景**：游客提交已注册单 403 / 本人通过 / 他人账号 403
- **权限矩阵最终形态（用户拍板收紧）**：`lib/api-auth.ts` adminPermissions——ops=`["ops"]`（去 risk，冻结结算归风控）、risk=`["risk"]`（去 system，sms/mail 测试 + production/status 仅 root）、arbitration 仍含 service。验证模式：risk/ops 调 `/api/admin/sms/test` 403、root 400（权限过、参数拦）
- **【2026-08-07 测试期首个真实反馈已修】商户审核 draft 状态断裂**：/admin/sellers 点"通过/驳回"报「该商户当前状态(draft)不允许审核操作」——根因是前端 `cnStatus` **兜底把 draft 显示为"待审核"** + 每卡无条件渲染 AdminSellerQuickReview（disabled 只判"已通过"），点击被服务端 409 拦（**服务端守卫正确**）。修复（commit e7b5be9+fb7d90b）：cnStatus 补 draft→草稿/suspended→已限制/closed→已关闭（SellerApplication 类型同步扩展）；快捷审核按钮 `disabled={seller.status !== "待审核"}`；详情页非 submitted 不渲染审核表单改提示原因。验证：draft 不再计入待审核计数（Pending=2 而非 3）。**通用模式：前端状态枚举兜底 + 无条件渲染操作按钮 vs 服务端状态机守卫 = 体验断裂**——状态映射兜底必须补全（draft/suspended/closed 等），操作按钮只按"可操作状态"渲染

- **【2026-08-08 测试期反馈已修】商户审核筛选 tabs 点击无反应**：/admin/sellers 的 status-tabs（全部/待审核/已通过/平台校验店铺）原是**纯展示 span（无点击事件）**。修复（commit 32b3406）：tabs 改 `<Link href="/admin/sellers?status=pending|approved|test">` + 服务端 `searchParams.status` 过滤列表 + 新增 `.status-tab` 黑胶囊样式（`.active` 黑底白字）。**通用模式：管理端筛选 tabs 一律用 Link+URL 参数服务端筛选**（无 JS 状态、可分享、刷新保持），别用纯 span 装样子。验证：curl 各 ?status= 卡片数正确 + HTML 含 `status-tab active`。**已复用：物流监控页（commit 0d7a910）同款 5 状态 tabs（全部/异常/待揽收/运输中/已签收，各带计数 + 空状态"该状态下暂无物流记录"）**——用户两次要求"加筛选区分"都落这个模式\n\n### 10.5 DynamicText 词级半译坑（2026-08-08 售后申请页修复实录）
症状：页面状态文字中英混合——"Un已发货"/"已Shipping"/"未Shipping"（用户截图反馈"页面混乱"）。
根因：`<DynamicText value={...} kind="status">` 的 value 用了**翻译表无键的词** → DynamicText 词级半译（拆词逐字翻，如 "Unshipped"→"Un"+已发货、"未发货"→"未"+Shipping）。触发场景：① value 用英文值（statusText 映射 "Unshipped"/"Shipped"）② value 用自定义中文词（"未发货"不在 translations.ts 键值里——翻译表是 `account.status.unshipped: "待发货"`）。
**规则：DynamicText 的 value 必须用 translations.ts 已有键的中文值**（中→各语言正确映射；无键词无论中英都会半译）。订单状态词标准表（从订单详情页 app/account/orders/[id]/page.tsx 复制，勿自造词）：`pending_payment→待付款 / paid,awaiting_shipment→待发货 / shipped→待收货 / delivered,receipt_confirmed→已签收 / completed→交易成功 / after_sales_pending→售后中 / closed→交易关闭`。
验证：SSR HTML + 英文界面（qavlixor-lang=en cookie）grep 无 "Shipping"/"Un" 残留；中文界面显示标准词。
同类：硬编码英文长文案（如"After-sale records are written..."）直接改中文短句（DynamicText 中文有键可翻）。

### 10.6 UI 拥挤/杂乱优化模式（2026-08-08 售后申请页宽松化实录，用户反馈"太拥挤了，你自己看一下"）
症状：用户反馈页面"混乱/拥挤"，截图红箭头指布局。**用户说"你自己调用 API 看一下觉着合适吗"= 授权自主评估直接调**（此场景无需 HTML 多方案预览——已有明确页面+问题，浏览器实测后直接改）。
优化手法（commit f4f4c56，全部**页面级专属 CSS**，不动全局类影响其他页面）：
- `.buyer-aftersale-page { max-width: 1080px; margin: 0 auto; }`（原全宽贴边→限宽居中）+ 页面内 `.buyer-checkout-layout` gap 28px、`.market-form-card` padding 28px 30px、`.field` margin-bottom 20px、`textarea` min-height 120px、`.seller-upload-grid` gap 14px、`.actions` gap 12px + margin-top 24px
- **长标题截断**：AppleSelect options 的 label 截断（`full.length > 48 ? full.slice(0,48)+"…" : full`），**value 保持完整**（提交不受影响）——长商品英文标题（100+ 字符）撑爆下拉是拥挤主因
- 验证：dev `browser_vision` 对比（限宽居中/留白加大/凭证按钮区舒展）→ 生产 SSR 抓取确认（`html.includes('buyer-aftersale-page')` + 截断生效）→ 部署
- **通用模式：UI 布局类问题先用 `browser_vision` 看实际渲染再动手（dev 复现 + 生产同款订单对比）——布局问题常是数据差异（长标题/长文案）而非 CSS 本身**；优化一律页面级 class 前缀（`.xxx-page .yyy`）避免伤及其他页面


原实现"提交即到账"（POST 直接 increment 余额 + approved）= 注册即无限套现 → 提现 → 财务打款闭环。已改为与卖家充值同款**收银台金额指纹核验**：
- schema：BuyerRecharge `status default "pending"` + 加 `txHash/network/paidAt`（**管理端代充必须显式传 `status: "approved"`**，否则 default 改后变 pending 不到账——users/[id]/balance 已改）
- `lib/payment-intents.ts`：新增 `createBuyerRechargeIntent`（kind=`"buyer_recharge"`，金额指纹 = base + 唯一尾数）+ `confirmIntent` 加 buyer_recharge 分支（pending→approved + BuyerWallet upsert increment + 通知；chain-auto 自动确认 / finance 人工确认均可）
- `/api/buyer/recharge`：创建 pending 单 + intent → 返回 `payUrl`（不再直接到账）；前端 BuyerBalancePanel 充值提交后 `window.location.href = payUrl` 跳收银台
- 链上自动确认复用 runPaymentWatch（按金额指纹匹配 pending intents）；TRON key 生产已配
- **端到端实测已通过（2026-08-07 生产）**：测试买家充值 66 → 返回 payUrl、余额 0 + 单 pending（后门已堵）→ 财务确认（POST /api/admin/pay-intents/[intentNo]）→ 余额 66 + approved + txHash。测试账号模式：生产 DB 直插（绕过邮箱验证码），测完禁用+清数据（见 references/real-launch-2026-08.md 第 8 节）

### 12. AdminUser 密码迁移（真实上线项）
- 登录逻辑（login/route.ts admin 分支）：**AdminUser 表优先**（findUnique 全字段 → status disabled 403 → verifyPassword(passwordHash) → cookieLogin），表内无记录回退硬编码（迁移期）；密码迁移完成后硬编码可移除
- 生产迁移：7 角色随机 16 位强密码（大小写+数字+符号）→ `sha256:salt:hash`（lib/password.ts 格式，crypto.createHash('sha256').update(`${salt}:${password}`)）→ upsert AdminUser
- 验证模式：新密码 200 / 旧密码 401（**若旧密码仍 200 = 登录代码没生效或 DB 挂**——先查 pm2 logs 的 prisma:error，见生产部署速查的 DATABASE_URL 坑）
- 密码交付：明文只在聊天给用户一次，本地临时文件用完删；勿写入 docs/ 文档

### 13. 上线前全员测试体系（2026-08-07，生产已建）
3 个线下员工分工测试（买家端/卖家端/管理端），QA 账号全部 **@qavlixor.test 测试域**隔离（与真实商家数据完全隔离，测完整体禁用）：
- 买家：`qa-buyer-1/2/<EMAIL-REDACTED>`（密码 `QaTest!2026`，管理端代充 200 USDT 各）
- 卖家：`<EMAIL-REDACTED>`（approved + 店铺"QA测试店铺" + SellerWallet 500）
- 管理端：7 角色现有账号（新密码在用户桌面《Qavlixor管理密码.txt》，勿写入 docs）
- **【最终版·用户要求逐按钮颗粒度】504 条逐项测试用例**（C-01~C-200 买家 / S-01~S-167 卖家 / A-01~A-137 管理端）在 **docs/qa/** 四个文件（总览与分工/买家端/卖家端/管理端，桌面同步一份给员工用）。**用户 2026-08-07 明确纠正过粗版方案"太粗糙"——测试方案必须覆盖每个按钮/输入框/下拉/弹窗/二次确认/禁用态/空态/错误提示/状态机边界/权限隔离/跨端联动，每条含【步骤】+【预期】+ 边界，不能写"测试某页"这种粒度**。编制方法论（子代理提取三端交互清单 → 逐按钮转用例）见 `references/qa-test-cases-2026-08.md`
- **测试红线**：提现只申请小额且管理端一律【驳回】不真打款；买家充值走收银台流程、财务确认由管理端模拟；不碰真实商家（星桥优选店等）数据；破坏性操作（删店/批量删品）禁止
- 缺陷反馈模板：D-日期-序号 + 所属端 + 用例编号 + 操作步骤 + 实际/期望 + 截图 + 严重程度；验收标准：严重 0、中等 ≤3 全修复、504 条执行率 100% 通过率 ≥98%、资金链路零缺陷、7 语言无乱码、测试数据清理完

**卖家测试账号创建（SellerAccount/Store 关系坑）**：
- SellerAccount **无 displayName 字段**（TS 未知字段报错）；Store 通过 `sellerAccountId @unique` 关联（**SellerAccount 无 storeId 字段**）
- 创建顺序：`sellerAccount.create`（必填：businessLicenseNumber 唯一/businessEntityName/businessEntityType/businessRegisteredCountry/businessRegisteredAddress/legalRepresentativeName/legalRepresentativeIdType/legalRepresentativeIdNumber/contactName/contactEmail/contactPhone/reviewedByAdminId="seed-admin"）→ `store.create({ sellerAccountId: sa.id, name, slug 唯一 })` → `sellerWallet.upsert`
- 测试买家绕过邮箱验证码：DB 直插 `user.create`（hashPassword）+ `buyerWallet.upsert` + `buyerRecharge.create({ status: "approved" })`（代充记录）；卖家钱包同理
- 登录验证：`POST /api/auth/login`（role 字段必传）200 才算建好

### 15. 买家余额支付（2026-08-07，用户反馈\"买家端支付没有余额支付选项\"后接入）
结算页 PAYMENT_METHODS 新增 `balance`（label 余额支付，note 实时显示 `可用余额 N USDT`，来自新 API `/api/buyer/wallet`）：
- 下单 API `checkout/orders` 解析 `paymentMethod`（usdt|balance）：
  - persist 循环里 balance 时**先把内存 order.status 改\"待发货\"再 syncOrderToPrisma**（否则 Prisma 落库还是待付款/pending——paymentStatus 由 syncPaymentForOrder 显式传 `paid` + escrowStatus `released` + method `balance` + providerReference `balance`）
  - persist 后 balance 分支：`buyerWallet.updateMany({ where: { userId, availableAmount: { gte: totalAll } }, data: { decrement } })` **count===1 作为唯一闸门**；不足/未登录/并发失败 → **回滚已落库订单（prisma.order.delete orderNo）+ 回补库存（releaseProductStock）** → 400/409 返回；写操作日志+业务事件
  - **balance 跳过 createOrderIntent**（不走收银台，payUrl=null，前端直接跳 success）
- 前端 submit：balance 前置校验（`balance < total` → 提示\"余额不足：当前可用 X USDT，需 Y USDT\"）；非 usdt/非 balance 仍跳 payment-restricted
- schema：PaymentMethod enum 加 `balance`（dev db:gen/push + 生产 db push 都要）
- 资金记录：`account/page.tsx` 查 `paymentTransaction where buyerEmail+method=balance+status=paid` 加\"消费\"条目（BuyerFundRecord kind 扩展 `\"pay\"`，BuyerBalancePanel 显示\"消费\"）
- 实测模式：登录买家 → `/api/buyer/wallet` 查余额 → balance 下单 → 验证 payUrl 无/订单待发货/余额精确扣减 → 超额单 400 且余额不变/库存回补 → USDT 对照仍跳收银台；**测完清理：删测试订单（orderItem→paymentTransaction→shipment→order）+ 余额回补**
- 资金记录展示：账户页资金记录 = BuyerRecharge（充值）+ BuyerWithdrawal（提现）+ PaymentTransaction(method=balance,status=paid)（余额支付消费）三源合并，`kind: "recharge" | "withdraw" | "pay"`

### 15.5 买家提现规则全局统一 + 资金记录点击式（2026-08-08 用户反馈）
用户要求"全局修复一下，单笔提现最低 50（手续费 1.5% 定死），提现弹窗底下那串也改成一致的，资金记录两个小项改成点击式的，提现记录改消费记录"：
- **提现规则标准文案（三处统一）**：`单笔提现最低 50 USDT · 手续费 1.5%（0.75 USDT 起）`——① BuyerBalancePanel 弹窗底部 hint（原"提现手续费 1.5%，最低 1 USDT"是**错的**）② 前端 submit 前置校验（`value < 50` → 拦截提示，原只靠后端）③ 后端 /api/buyer/withdrawals 400 文案（补 USDT 单位）。常量化 `WITHDRAW_MIN=50` + `WITHDRAW_FEE_RATE=0.015` 放组件顶部
- **资金记录点击式 tab**：副标题"最近充值 / 提现记录"→ 胶囊 tab（全部/充值/消费记录，黑胶囊选中态），state `fundFilter: "all" | "recharge" | "consume"`；消费记录 = `kind !== "recharge"`（提现 + 余额支付）过滤
- **用户偏好信号**：金额规则类需求要"全局统一"——**前端弹窗文案/前端校验/后端 API 文案三处必须一致**，改一处必须查另两处（grep 全局该规则相关文案）
- 验证：提现 30 → 400 文案正确；账户页 HTML 含"消费记录"tab、不含旧副标题

### 15.6 买家退款后余额回补（2026-08-08 用户反馈"订单退款后余额未回到账户"）
- **根因**：`markPaymentRefunded`（lib/payment-repository.ts）只把 paymentTransaction 置 `refunded`，**未回补 BuyerWallet**——余额支付扣的是买家余额（checkout balance 分支 decrement），退款必须对称回补
- **修复（commit 8b745c0）**：markPaymentRefunded 内 `updateMany(...)` 返回 **`result.count > 0` 作为"首次真正退款"判定**（幂等：已 refunded 的单 count=0 不二次回补）→ 查 `method: "balance"` 支付单（buyerEmail/amount）→ `buyerWallet.updateMany({ where: { userId }, data: { availableAmount: { increment: amount } } })`。所有退款入口（卖家取消/售后全额退款/仲裁）统一走此函数自动覆盖
- **验证模式**：造 balance 支付单（order + paymentTransaction method=balance status=paid + buyerEmail）→ 模拟退款（条件更新 + 回补）→ 余额 +amount ✅ → **清理测试数据 + 余额 decrement 还原**
- **历史回填**：修复前已退款的历史 balance 单不会自动补（幂等判定 count=0）——一次性 SQL/脚本按支付单回填（生产 3 笔 qa-buyer-1 共 54.99 USDT）
- **通用模式：资金扣减必须对称回补**——排查"退款/取消后资金没回来"先搜扣减点（decrement/increment BuyerWallet）核对对称性；回补幂等 = 条件更新 count>0 判定首次（与状态机守卫同一模式）
- **【2026-08-08 第二轮：部分退款也回补（commit 244f601）】`aftersales/[id]` 部分退款分支（isPartial，只记 refundedAmount、不调 markPaymentRefunded）也必须单独回补**——查 balance 支付单 buyerEmail → `buyerWallet.updateMany increment effectiveRefund`。**排查\"退款没回补\"别只查 markPaymentRefunded 一个函数——全额/卖家取消/仲裁走它，部分退款是独立分支，两处都要核对**（grep aftersales 的 isPartial 分支看有没有回补）
- **【第二轮教训·部署后用户报\"还没修复\"的排查顺序】**：① SFTP 读服务器源码 grep 新逻辑（文件在=代码对）→ ② 手动执行回补等价逻辑（查 balance 单→buyer→increment）验证查询可用 → ③ 手动跑通了但历史单没回补 = **当时运行时是旧产物**（pm2 restart 可能加载旧 .next——**凡部署后用户反馈\"还没生效\"先二次 restart 或对照产物时间戳**，坑 #51 反复出现）→ ④ 历史已退款单手动回补（幂等判定 count=0 不会自动补）
- **【aftersales 退款 API 参数坑（e2e 实测）】**：① `reply` 字段必填（缺了 400\"请填写处理说明\"——result/note 都不是它）② `refundAmount` 传等于订单总额可能因浮点边界 400\"本次退款将超过订单总额\"（1.99 vs 1.9900000000000002）——**不传 refundAmount 走全额退款（effectiveRefund=orderTotal）最稳**；e2e 下单→退款测试后**删单必须回补余额**（下单扣的钱），否则 QA 账号余额被测试污染（3 次 e2e 残留 -5.97 要统一回补）③ **DB 直建 AfterSaleCase 必填**：id/orderId/**buyer**/storeName/reason/status（buyer 易漏——只传 buyerEmail 会 create 失败；refundAmount/evidenceJson 可空）

### 16. 三端页面/组件全景图 + 交互清单格式（2026-08-07 全量提取）
三端交互清单已全部产出（买家 12.8K / 卖家 12.7K / 管理端 12.1K 字符），**页面→组件映射/关键架构事实/交互清单交付格式见 `references/seller-pages-map.md`（卖家端）+ `references/qa-test-cases-2026-08.md`（三端清单与用例）**。改任何页面或再做交互清单前先读：
- **卖家导航壳不在 app/seller/layout.tsx**（空壳 `return children`），在 `components/PortalShell.tsx`（sellerNavGroups + ConsolePortalShell：分组折叠/角标 60s 轮询 /api/seller/nav-counts/切换账号）
- **components/seller/ 目录含管理端组件**（AdminWithdrawal/AdminLogisticsUpdate/AdminSellerReview/AdminProductReview/AdminAutoConfirm/AfterSaleQuickActions）**和买家端组件**（BuyerAfterSaleRequestForm）；SellerProductManager/SellerProductForm 在 `components/` 根目录
- 消息页复用 components/chat/ChatWorkspace（role="seller"；轮询 4s/10s）
- 交互清单交付格式（用户指定）：`### 页面路径` + `- [元素类型]「文案」：行为描述；边界/异常`，覆盖所有可交互元素（含弹窗/批量栏/校验/禁用/空态/锁定态/notFound），不写测试步骤；提取流程=find app/seller + components/seller → wc -l 分批并行 read_file → 补查被引用的共享组件与导航壳

### 17. 三端消息角标同步（2026-08-08 用户反馈"点击后角标不减少/不消失"）
- **根因**：通知铃铛（卖家/管理端 NotificationBell）count = **7 天内通知总数（不区分已读）**且**无已读 API/字段** → 点开面板、看完通知角标永不减。chat 消息体系（买家/卖家导航 ChatUnreadBadge）已读链路本来就正常（readAt 口径 + 15s 轮询 + ChatWorkspace 打开会话/收到对方消息即 POST read）
- **排查三步**：① count 口径是否区分已读（grep notifications-recent 的 count 计算）② 已读 API/字段是否存在 ③ 前端打开/点击是否调已读。**角标分三类语义**：已读类（chat/通知——点击应减）、待办类（nav-counts 的订单/售后/审核队列——处理完才减，语义正确勿改成已读）
- **通知已读体系修复模式**（commit f7ca07d）：schema NotificationMessage 加 `readAt DateTime?` → 已读 API `POST /api/notifications/read`（updateMany where recipientEmail + channel=in_app + readAt null）→ notifications-recent（seller+admin 两个文件）count 改 `!row.readAt` → NotificationBell 打开面板即调已读 API + `setCount(0)` 本地立即清零（不等 60s 轮询）→ 通知中心页（/seller/notifications）进入即 updateMany 已读 → **新建 /admin/notifications 通知中心**（原铃铛"查看全部"指向 404 页；复用 SellerNotificationList **纯展示组件** tabs/items 由服务端传入，admin/seller 通用）
- 验证：DB 插一条测试通知 → 登录 → notifications-recent count=1 → POST read 200 → count=0；chat 同理（unread 10→9）；测完清理测试通知（deleteMany title 前缀）\n- **【2026-08-08 用户截图反馈】待办类角标口径：draft 草稿不计入待审核**：管理端侧栏「商户审核」角标显示 2 且永不减——原口径 `status notIn [approved, rejected]` 把**16 天未提交资料的草稿商户**（<EMAIL-REDACTED>）也算待审核。修复（commit befae60）：admin nav-counts sellers + 总览 KPI 两处改 `status: \"submitted\"` only（列表页 cnStatus 此前已正确显示\"草稿\"）。**通用模式：`notIn[终态]` 不等于\"待办\"——凡有草稿/未提交中间态的口径必须显式白名单**（submitted/submitted_for_review），grep 全局 `notIn.*approved` 或 `in.*draft` 排查；KPI 卡/角标/列表计数三处口径要逐一核对
- **【2026-08-08 用户反馈】卖家端售后工单角标恒 0 = 状态枚举中英双轨**：nav-counts 售后口径原查 `status: \"商家处理中\"`（中文），但生产 afterSaleCase.status **中英双轨**（有\"已退款/已关闭/商家处理中\"中文值，也有 `seller_reviewing`/`seller_refund`/`seller_approved` 英文枚举）→ 英文状态的工单永远查不到 → 角标恒 0。修复（commit ecb10b4）：口径改 `status: { notIn: [\"已退款\", \"已关闭\", \"refunded\", \"closed\"] }`（未完结都提醒；>99 显示 99+ 的红色角标渲染层本就有，与订单同款）。**通用模式：状态枚举查询/筛选前先 `groupBy` 查生产实际分布**（本项目状态值中英文混存不止一处——afterSaleCase.status、orderStatus 也有中文镜像历史），别假设枚举是单一语种；角标类问题排查顺序 = 渲染层有无 badgeKey/计数（有）→ 口径查询是否命中实际数据（groupBy 对照）→ 修复口径
- **【2026-08-08 第二轮·用户报\"还没修复完\"】售后角标根因在脏数据：storeName 存了邮箱**——口径修对后仍有未完结售后单（A-1783266060100-9136）查不到：其 `storeName` 是**卖家邮箱**（`<EMAIL-REDACTED>`）而非店铺名（\"星桥优选店\"）→ 按店铺名查恒 0（买家申请创建的源头代码是对的 `storeName: order.store.name`，脏数据是历史旧代码遗留）。**修复（commit cd35f87+b44b4a0）**：① nav-counts 与卖家售后列表（app/seller/aftersales/page.tsx）改**按订单归属兜底**：先查该店全部订单 orderNo 集合 → `OR: [{ storeName: 店名 }, { orderId: { in: 店订单 } }]`（双口径并集，未来脏数据也免疫）② 存量脏数据修复脚本（未完结售后单逐条对齐订单店铺名）③ scope 可能为 null 的 tsc 处理。**通用教训：归属类查询（按店名/按邮箱）先 `groupBy storeName` 对照真实数据分布——本项目 storeName 字段有\"店名/邮箱/乱值\"三种形态**；用户报\"还没修复\"时先验证数据侧（groupBy 实际分布）而非只改代码口径

### 18. 批量生成/大列表渲染提速模式（2026-08-08 用户反馈"勾选店铺多后跳转/点击操作都很慢"）
校验订单批量生成（/api/test-orders + /admin/test-orders）两处慢的根因与修复（commit 71ae825）：
- **串行 DB 写是批量慢的根源**：双重 for 里每单 6-8 次 await DB 往返（syncOrderToPrisma+findUnique+update+paymentTransaction.upsert）→ 200 单 ≈ 1400 次串行操作 ≈ 30s。**修复模式：先纯内存预生成全部订单对象（数组 push，毫秒级，注意时间分布索引用 jobs.length 而非 created.length）→ 再按每批 10 单 `Promise.all` 并发落库**（批量内无依赖可并行；批次间顺序保持 created 顺序）。实测：dev 30 单 1275ms（原 ~4.5s）、**生产 40 单 355ms（原 5-8s，提速 15-20 倍）**
- **大列表全量渲染卡交互**：328 店 checkbox 行 + 勾选多店后商品/变体上千行全渲染 → React 每次 setState 全量重渲染卡死。**修复模式：无搜索时 `slice(0, 100)` 渲染 + 提示"共 N 家，输入名称搜索查看更多"（搜索时全量，结果通常少）；商品明细区 `slice(0, 3)` 店 + 提示"其余店铺按全部商品随机生成"**——功能不受影响（未展示店铺仍参与生成）
- **验证模式**：生产小批量实测计时（登录管理端 → POST /api/test-orders → 打印耗时）→ **测完必须清理测试订单**（paymentTransaction.deleteMany orderNo in → shipment → orderItem → order.deleteMany）——校验单进真实订单/结算链路，不清理污染生产数据
- **通用教训：任何"批量 N 次 DB 写"先问能不能并发批次；任何"列表渲染 N 行"先问要不要全量渲染（截断+搜索兜底）**

### 19. 库存"不减反增"= 校验订单不扣库存但回补（2026-08-08 用户反馈"上架22件发货很多库存越来越多"）
- **根因**：校验订单（orderChannel=validation，管理端生成）走 syncOrderToPrisma **直建不扣库存**（reserveProductStock 只在 checkout 真实下单调用）；但校验单在卖家端可见（待发货列表），**取消/超时关单/售后退款走 releaseProductStock 回补逻辑 → 没扣过却回补 = 库存白涨**；发货不扣库存（下单已扣）→ 测试中校验单越多/操作越多库存越涨
- **修复（commit b7baeba）**：4 处回补调用方（seller/orders/[id]/cancel、aftersales/[id] 全额退款、settlement-tasks 超时关单、orders/[id]/cancel 买家取消）全部加 `if (order.orderChannel !== "validation")` 跳过回补——**校验单全程不碰库存（不扣也不回补）**
- **releaseProductStock 防错位**：回补目标原为 `variants.find(sku) ?? variants[0]`（fallback 第一个变体）→ 改 `sku ? find(sku) : variants[0]`，**匹配不到（变体被改/删）则跳过不回补**——避免扣 A 补 B 的变体间错位虚增
- **验证模式**：生产登录 admin → test-orders API 生成 1 单校验单 → 商品变体库存前后不变（根因确认）→ 清理测试单
- **通用模式：测试通道/校验通道的订单必须全程不碰真实业务资源（库存/资金），要么扣+回补对称，要么都不碰**——排查"库存/金额异常增长"先搜回补调用方（releaseProductStock/increment）逐一核对扣减-回补对称性
- **遗留**：已虚增库存无法自动追溯，需卖家编辑商品手工校正

### 19.5 订单/商品列表缩略图渲染模式（2026-08-08 用户反馈"图片显示数字"）
管理端订单详情商品区原 `<div class="seller-product-thumb mini"><span>{item.productId}</span></div>`（缩略图位渲染 ID 数字文本）。**修复模式（commit b1c0c49）**：商品查询 select 补 `images: { select: { url: true }, orderBy: { sortOrder: "asc" }, take: 1 }` → 渲染 `<img src={首图}>`（width/height 100% + objectFit cover + borderRadius 8），无图显示"无图"。**通用模式：任何缩略图容器禁止渲染 ID/SKU 文本占位**——有图渲染 img，无图显示占位文案；查 ProductImage 模型（id/productId/url/sortOrder）。验证：SSR HTML 含 `<img src="cdn...">`

### 19.6 类目误映射数据质量（2026-08-08 用户反馈\"食品饮料类目很乱：坚果里是螺母、巧克力里是假发\"）
- **根因**：商品导入时**英文关键词 → 类目映射误判**——`nut`（螺母，机械五金）被映射到\"坚果\"类目（nuts）；`Chocolate Brown`（假发颜色）被映射到\"巧克力\"类目。症状：坚果类目 8 个商品全是 DIN934 六角螺母/铆螺母，巧克力类目 22 个里 10+ 个是 Chocolate Brown 色假发（Lace Front Wig 等）
- **修复模式（生产数据修正脚本）**：先 `groupBy categoryId`/按类目查商品 title 样例确认误判 → 坚果类目全部商品移到\"工具五金\"（tools-hardware）；巧克力类目按关键词正则（`/wig|hair|lace|bob|crochet|frontal|braid|weave|human hair|density/i`）移假发到\"假发片\"（wig-accessories-1），**剩余保留**（巧克力主题香水/玩具/模具算相关）→ 验证两类目剩余均为主题相关商品 + 糖果类目按食品关键词正则（candy/gummy/chocolate/nut/seed/dried/...）扫杂物（0 命中=干净）
- **通用模式：关键词映射类目（英文词→中文类目）必然有上下文误判（同形词/颜色词/品牌词）**——用户报\"某类目很乱\"先列该类目全部商品 title 看误判模式，再按误判特征（同形词 nut、颜色词 chocolate brown、品牌词）批量移到正确类目；源头是一次性迁移脚本（import-local-db-to-prisma.mjs）不会重跑，**只修存量即可**；验证用类目商品 title 列表（勿只看数量）

### 19.7 类目错乱全平台扫描修复方法论（2026-08-08 用户\"类似问题全局查找修复\"，681 类目 × 6997 商品）
用户报过坚果/巧克力错乱后要求**全平台扫描**。可复用流程（生产数据修复，无代码改动无需部署）：
1. **先看全貌**：`groupBy categoryId` 全类目商品数分布 + 每个类目 take 6 title 样例（勿只按数量判断——\""巧克力 22 个\"\"数量正常但全是假发）
2. **15 组高置信特征规则**（产品类型词 > 原料词优先级）：假发（lace front wig/human hair wig/bob wig/crochet hair/weave/frontal/closure）、五金（din934/din315/hexagon nut/rivet nut/screw set/wrench set）、宠物（cat tree/cat scratch/catnip/pet leash/dog collar/litter box）、婴儿（baby bottle/pacifier/stroller/diaper）、坚果（peanut/almond/cashew/dried mango/sunflower seed/mixed nuts）、巧克力（chocolate bar/cocoa powder/hot chocolate）、美妆（lipstick/mascara/eyeliner/foundation stick）、香水（perfume/eau de/cologne/parfum）、运动鞋（running shoes/athletic shoes/sneakers）、背包（backpack/rucksack/hiking pack）、电子（phone case/power bank/earbuds/usb-c hub/charging cable）、瑜伽（yoga mat/resistance band/dumbbell）、手表（smart watch/wristwatch/watch band）、眼镜（sunglasses/polarized/cycling glasses）、灯具（floor lamp/led strip/night light）
3. **词边界防子串误判（关键坑）**：`rivet` 匹配 \"Tri**vet**\"（隔热垫）、`pet` 匹配 \"**PET** 材质\"、`sport shoe` 匹配 \"sport**s**\"、`stainless steel` 太泛（餐具/水瓶/砧板全中）——关键词必须用**带空格/组合的短语**（'hexagon nut' 而非 'nut'、'pet leash' 而非 'pet'），**删泛化词**（stainless steel 单用必误判）
4. **ok 前缀保护同类目群**：每条规则带可接受类目 slug 前缀列表（美妆 ok 含 beauty-/makeup/eye-makeup/base-makeup/lip-makeup/sponges-puffs/lash-supplies；宠物 ok 含 pet-/dog-/cat-toys；瑜伽 ok 含 running-training/massage-care），当前类目 slug 命中 ok 前缀则不动——**防同类目体系内误移**（遮瑕→美妆刷具、表带→手表、猫玩具→宠物都是内部移动，不该动）
5. **dry-run 先行迭代**：先只统计输出（来源类目→目标类目 + 样例标题），人工审 2-3 轮规则（本轮 559→713→349→228→201 五轮收敛），确认无误才执行；**执行后必须检查误移并回滚**（本轮回滚：童鞋 27 个误入成人运动鞋→按标题 kid/child/boy/girl 特征移回 kids-shoes；花生酱/果酱→回 honey-jam；品牌词 'Monster Jam' 包、'Dog Licking Mat'、pistachio 味香膏、成人 onesie 睡衣都是边界误判——产品类型词（perfume）优先级高于原料词（pistachio），回滚脚本按来源类目名 + 标题特征定位）
6. **无特征词的历史杂物**（标题无任何食品/电子词，如果酱类目里的路由器/翻盖手机/LED 灯）规则判断不了——单独列出按明显特征人工移（WiFi/phone→电子、light/lamp→灯具），移完目标类目归零即干净
7. **验证**：关键类目（用户点名的+重灾区）取商品 title 抽检 + 移动/回滚计数汇总
- **通用教训：数据质量修复（类目/归属/状态）三步走——① groupBy 看实际数据分布（别假设枚举/归属形态）② dry-run 迭代规则到高置信（词边界+ok 前缀+优先级）③ 执行后回滚误移（记录来源类目便于定位）**——自动修复必须配套回滚机制，误判是常态不是意外

### 19.8 大类目商品错位清理（2026-08-08 用户第二轮反馈"家具日用有玩具/厨房有珠宝/母婴有宠物玩具/宠物有护肤品/食品有玩具工具"）
小类目级规则（19.7）清完后用户报**一级类目树内仍有错位**（大类目页面混入异物商品）。可复用流程（生产数据修复）：
1. **先验证一级类目挂载本身是好的**（`parentId=null` 的 roots + 直接子类目 groupBy）——本轮一级挂载正常（厨房餐厨→厨房工具/餐具水具/小家电配件），**错位在商品级**（商品 categoryId 挂错大类目树）
2. **树级扫描**：`treeIds(rootId)` 递归收集一级类目树下全部类目 id（parentId 遍历，注意父子级 id 可能混存 string）→ 树内商品全量 → 8 组强特征词**词边界正则**匹配其他大类目
3. **树级排除（关键，防同类误移）**：当前商品所在类目 ∈ 目标一级树 → 不动（积木类目在母婴玩具树内、猫玩具在宠物树内都是正常的）；再叠加**类目名排除**（/玩具|积木|母婴/、/珠宝|首饰|表/、/美妆|彩妆|唇/、/食品|零食|餐/、/收纳|盒|袋|架|箱/ 等）
4. **误判黑名单（本轮实测）**：颜色词（`candy color`/`candy colour`/`chocolate brown`/`marshmallow` 是色名不是食品）；品牌词（`Judydoll` 眼线笔含 doll 误判玩具——品牌无法穷举，靠类目名/树排除兜底）；**子串**（`suit` 匹配 `suitable`、`dress` 匹配 `dresser`——必须 \b 词边界）；**双关**（`pendant lamp` 吊灯 ≠ 吊坠——珠宝规则排除 `pendant (lamp|light)|ceiling lamp`）；`pet` 匹配 PET 材质
5. **目标类目**：一级树内 findTarget（类目名匹配）/玩具|饰品|用品/ 等，找不到 fallback 一级类目本身（大类目对即可，后续可再细分）
6. **残留清理**：第一轮后按大类目特征词复查残留（如宠物树内 serum/ampoule/hand cream、食品树内 fidget/squishy/simulated toy、家居树内 Baby Crawling）——逐个按明显特征补移
7. **验证**：每个大类目配"异物特征词"（家居树查 toy/smart watch/necklace、厨房树查 jewelry、宠物树查护肤品词、食品树查 toy/tool）→ 残留应 ≈0（个别边缘项如"帽子收纳盒"保留并说明）
- **本轮累计**：小类目 201 + 大类目 128 = 329 个商品类目修正；全部纯数据修复无需部署

### 19.9 E2E 测试删单必须按外键顺序且验证结果（2026-08-08 用户"订单记录莫名多1.99待发货"）
- **事故**：E2E 退款测试脚本结尾删单 `order.deleteMany({ where: { orderNo } })` 被 **Shipment_orderId_fkey 外键拦截**（报错被 `.catch(() => null)` 吞掉）→ 4 个 1.99 测试下单残留待发货列表，用户看到"莫名订单"。清理时发现 paymentTransaction/orderItem 都删光了但 order 还在（`Shipment_orderId_fkey`）
- **正确删单顺序（必须 Shipment 先删）**：`shipment.deleteMany({ where: { orderId } })` → `paymentIntent.deleteMany({ where: { orderId } })` → `orderItem.deleteMany({ where: { orderId } })` → `order.delete`。**删完必须验证 `order.count({ where: { orderNo: { in } } }) === 0`**
- **铁律：测试脚本的清理段不允许 catch 吞删除错误**——删除失败要打印/失败退出，否则测试数据静默残留污染生产（用户发现才处理）
- **清理模式**：按特征查全库（`totalAmount ≤ 2 + orderStatus 待发货` + buyerEmail）→ 确认测试来源（时间戳/orderChannel）→ 外键顺序删 → **余额对账回补**（删除前逐单记扣款额，扣除已回补部分再补，避免重复/漏补；本次 5 单 12.95，已补 3.98 → 再补 8.97）→ 复查 `count === 0`
- **验证残留**：`order.count` + 全库按金额/状态复查（≤2 待发货 = 0）

### 19.10 商品列表"跳至N页"页码跳转（2026-08-08 用户"页码过多(219页)无法输数字跳转"）
- **实现（commit 160fff6，已部署 build36）**：新增客户端组件 `components/buyer/CatalogPageJump.tsx`——输入页码 + Enter/黑胶囊按钮跳转；`useSearchParams` 读当前全部参数 → `params.set("page", N)` → `router.push("/products?" + params)`（**保留类目/价格/排序等筛选**）；校验 `Number.isInteger && 1 ≤ page ≤ totalPages`（超界不跳）；渲染在分页条右侧（`.catalog-jump` 左侧 1px 分隔线，input 52px + 黑胶囊按钮）
- **分页条在服务端组件（app/products/page.tsx）**，跳转组件是客户端——服务端传 `currentPage/totalPages` props 即可，URL 构造放客户端
- **翻译键 7 语言**：`catalog.jumpTo/jumpPage/jumpGo`（跳至/页/跳转）
- **【插键坑·同值键漏插】多个语言包键值相同（es/pt 都是 "Anterior"）时用 `s.find("...Anterior...")` 只命中第一个（es），pt 被静默跳过**；ru 的 prevPage 是 "Назад" 不是猜的 "Предыдущая"。**批量插键必须按语言包实际键值逐个定位**（先 `grep -n '"catalog.prevPage"'` 看每包真实值，再按值定位插入；或按包边界/行号），插完 `grep -c '"catalog.jumpTo"'` 必须 == 7
- 验证：dev 商品少（一页）不分页不渲染——**必须生产验证**（219 页场景）：`curl /products | grep -c catalog-jump-input` 应为 1 + grep "跳至"
- 同类页面（search/stores 分页）可复用同组件（pageHref 前缀参数化）


**用户定义（原话）**："已售出 就算 销量增加，有买家付款或者有核验订单生成就算销量增加"——**不是确认收货驱动**（第一版做成"确认收货才加"被用户纠正）。规则文档：《Qavlixor销量规则.txt》桌面 + docs/qa/（v2 已确认）。

**口径明细（最终版，commit 8600513 + c1bf5fd）**：
- **+销量**（按订单件数累加）：① 收银台付款确认（confirmOrderPaid，chain-auto/财务人工）② 余额支付成功（checkout balance 分支扣款后）③ **校验订单生成**（test-orders API 落库后，生成即算已售出）④ 管理端人工确认收款（走 confirmOrderPaid 同函数）
- **-销量（唯一触发）**：卖家取消订单（真实单+校验单都减）
- **不减（0，用户明确拍板"售后退款不减销量件数"）**：售后**全额退款、部分退款都不减**——销量只增不减（仅卖家取消为减）；已发货订单全额退款也不减（货已发出）
- **不动（0）**：下单未付款（待付款不算）、买家取消待付款单、超时自动关单（未付款没加过）

**实现要点（commit 8600513）**：
- reserve/release 里**移除 sold 增减**（下单/取消/退款不再自动碰销量——销量只由显式调用驱动，避免下单失败回滚误减、口径混乱）
- 新增辅助函数 `incrementProductSold` / `decrementProductSold`（productId+quantity）：productOperationMetric upsert（increment / Math.max(0, sold-amount)）+ `invalidateProductCatalog()`（销量立即刷新不等 60s 缓存）；失败 catch 不阻断主流程
- 接入点：`lib/payment-confirm.ts`（confirmOrderPaid 置 paid 后）、`checkout/orders` balance 分支、`test-orders`（生成后）、`seller/orders/[id]/cancel`（唯一减点）
- **注意：aftersales/[id] 全额退款处只回补库存、绝不 decrementProductSold**（用户拍板：退款不减销量；库存与销量独立——校验单**库存不碰**（见第 19 节）但**销量计入**，改一个不要顺带改另一个）
- 验证模式：生产登录 admin → test-orders 生成 1 单 → metric.sold +1（实测 1→2）→ 清理测试单时手动回补 sold

**教训（用户纠偏）**：用户反馈业务口径问题（"确认收货了销量还是0"）时，**先按字面理解实施会被纠正**——业务口径类需求必须先给规则草案确认（"发一份规则文档给我审核修改"= 用户明确要求文档化交付）或先问清口径再动手；文档交付模式：桌面 txt + docs/qa/ 双份 + 列出待拍板点，用户拍板后立即更新文档并撤掉代码里的旧口径分支。

### 20.5 卖家端发货表单（2026-08-08 用户要求"不要保存草稿"）
SellerFulfillmentForm 只保留**「保存并标记发货」**一个按钮（commit d6c756a）：删除"仅保存草稿"按钮 + submit 去掉 draft 分支（mode 固定 "ship"、status 固定 "运输中"、saving state 简化为 boolean）；后端 fulfillment API 的 draft 分支保留但前端已无入口。**用户偏好：履约类表单只要最终动作按钮，不要中间态草稿保存**。

### 21. 管理端权限矩阵（2026-08-08 用户要求"超管勾选权限+无权限直接看不到"）
用户原话："把可勾选权限功能打开并完善，别的管理员登录后只能看见自己有权限的功能，没有权限的直接看都看不到，不然功能太混乱"。

**实现（commit 4dd40f5 + 195fb0e，生产已部署）**：
- **schema**：AdminUser + `permissionsJson String?`（JSON 数组覆盖角色默认权限；null=按默认 map；root 恒 all 不可改）
- **权限读取零改动兼容模式（关键）**：`requireAdminPermission` 是**同步函数且 66 处调用**——不要改成 async！改法：`requireRole`（本来就 async 查 AdminUser）把 `permissionsJson` 解析挂到 auth 对象 `adminPermissions` 字段 → `requireAdminPermission` 优先用 `auth.adminPermissions ?? adminPermissions[email]`——**66 处 API 守卫零改动自动兼容 DB 权限**。另加 `getAdminPermissions(email)`（async，30s 缓存 + `invalidateAdminPermCache`）供服务端 layout/导航用
- **7 权限点**：ops(经营运营)/finance(资金财务)/risk(风控监管)/logistics(物流监控)/service(客服服务)/arbitration(售后仲裁)/system(系统管理)
- **导航过滤**：`adminNavGroups` 每项加 `perm` 字段（NavItem 类型扩展）→ PortalShell 加 `adminPermissions` prop → `filterNavGroups`（无 perm 的项全可见；有 perm 的按权限过滤；空分组剔除）→ admin layout 传当前权限
- **页面级守卫（"看都看不到"= 404 而非 403）**：middleware 设 `x-pathname` header → admin/layout.tsx 用 `headers()` 读 pathname → `ADMIN_PAGE_PERMS` 最长前缀匹配 → 无权限 `notFound()`。注意 Next 15 服务端组件拿不到同步 pathname，必须靠 middleware 传 header（matcher 已含 /admin/:path*）
- **权限→菜单映射表**（改映射时同步改 layout 守卫表）：总览/通知中心=通用；商户总管理/用户总管理/商户审核/商品审核/类目审核/资料变更/校验订单=ops；订单监管=risk；提现队列/保证金=finance；物流监控=logistics；联系请求=service；售后仲裁=arbitration；角色权限/操作日志/平台规则=system
- **勾选 UI**：/admin/roles 改为服务端列 AdminUser + 客户端 `AdminPermissionsManager`（7 权限点 checkbox 卡片 + 保存按钮；root 行只读显示"全部权限"）；保存 API `POST /api/admin/permissions`（**仅 root**；校验 targetEmail 非 root；permissions 白名单过滤去重；写库后 `invalidateAdminPermCache`）
- **验证模式**：dev 保存权限 200 → DB permissionsJson 写入 → 权限判断（finance+risk 可见订单/提现、system 不可见）；导航过滤逻辑单测（finance → 只见总览+提现队列）；生产实测后**还原默认权限**（测试污染清理）
- **注意：旧 /admin/roles/edit 只读页变孤儿（无链接入口，无害可留）**
- **【2026-08-08 用户截图 bug】双重壳嵌套：根 AppShell + admin layout 双 PortalShell**——根 layout 的 `AppShell.tsx` 本就按 pathname 渲染 PortalShell（admin 路径→portal=\"admin\"，**无权限过滤**），admin layout 再加一层 PortalShell（带过滤）= **页面内嵌套完整控制台壳**（外层全菜单壳 + 内层过滤壳，用户截图\"管理端后台成这样了\"）。**修复（commit a3e947b）**：AppShell 对 admin 路径直接 `return <>{children}</>`（壳由 admin layout 独家渲染带权限过滤）。**通用教训：给子 layout 加壳前必须先查根 layout 是否已有 AppShell 类壳组件（components/AppShell.tsx 按 pathname 分发 portal）——重复加壳 = 嵌套壳 bug**；验证用数侧栏特有链接出现次数（单壳=1 次/项），别数\"平台总后台\"等一壳内出现多次的文案。seller/buyer layout 是空壳（壳只在 AppShell），只有 admin 双重壳

### 21.5 生产部署坑：db push 必须跟 prisma generate（--skip-generate 会 build 失败）
部署新 schema 字段时：`npx prisma db push --skip-generate` 虽快但**生产 node_modules 的 Prisma client 类型不含新字段 → 服务器 `pnpm run build` 报 `Type error: ... does not exist in type`**。修复：`npx prisma generate` 后再 build（5s）。**凡 schema 改动部署：db push 后必须 generate，否则 build 必挂**。

### 21.6 资金中心台账 vs 可提现口径（2026-08-08 用户反馈"总览显示进入可提现但实际提现无金额"）
- **根因**：funds-repository 的台账（runningLedger）只记**订单结算/钱包充值/提现**三类流水，**不体现已缴保证金净额占用**——而 `available = completedTotal + rechargeTotal - 提现中 - 已提 - deposit.balance.net`。测试店场景：完成过保护期 25 USDT（台账显示"订单完成且过售后保护期，进入可提现余额。"）+ 测试期缴保证金净额 10726.25（后台直充）→ available=0 → 提现处无金额，**用户被台账文案误导**（"进入可提现余额"≠ 可提现余额）
- **修复（commit febca19）**：台账构建末尾（提现流水后）补一条**"保证金占用"流水**：`if (deposit.balance.net > 0) { balanceAfter -= net; push({ type: "保证金占用", amount: -net, note: "已缴保证金 X USDT 占用可提现余额（申请退还后释放）。" }) }`——台账末值 = available，口径一致；提现弹窗（SellerWithdrawRequestForm）加红字提示（`withdrawable <= 0 && available > 0` 时"被已缴保证金占用，可申请退还后提现"）
- **排查方法**：用户说"明细/台账说有 X，但实际没 Y"——先还原计算链（completedTotal/recharge/withdrawals/deposit.net 逐项打印）对比台账流水的 balanceAfter 末值，差异项 = 台账漏记的扣减
- **通用模式：台账/明细流水必须与总览数值同口径（每项扣减都要有对应流水）**——漏记任何扣减（保证金占用/冻结）都会造成"有进账提示但余额 0"的误导；保证金占用是资金模型设计（缴了从可提现扣、退还释放），不是 bug，要修的是**展示透明**（流水 + 弹窗提示），别去改 available 公式（资金模型勿回退）
- **【2026-08-08 第二轮·用户仍报"没修复"的根因=总览数字没改】**：只补台账占用流水还不够——总览"可提现余额"卡数字仍显示 `snapshot.available`（未减保证金占用），与提现处 `withdrawable = available - deposit.gap` 不一致。**修复（commit febca19 后续）**：① 总览数字改 `num(withdrawable)`（与提现处同口径），副文案区分两态（占用时"可用余额 X USDT（保证金占用后实际可提 Y）"；无占用"与提现处一致，可直接申请提现"）② 台账"订单结算"note 文案从"进入可提现余额"改为**"计入结算余额（扣除保证金占用后为实际可提现）"**（用户反复引用这句文案=它最误导）。**通用教训：用户报"显示 X 但实际没 Y"且修过一次还报"没修复"——检查是否所有展示该数值的位置都改了（总览卡/台账流水/提现弹窗三处逐一对口径），文案里凡是暗示"可提现"的词都要跟着口径走**

### 21.7 保证金规则：先进余额、只能余额划转（2026-08-08 用户澄清，含"删功能前先确认"教训）
- **用户原话**："先进余额保证金只能自己从余额划转，不要直接到保证金里面去"——**正确解读：管理端充值/代充必须先入卖家余额，保证金缴纳只能由卖家在资金中心从余额划转，任何入口都不得直接创建保证金净额记录**（原直充 API 直接建 approved sellerDeposit 不经过余额 = 可提现被虚高保证金占用 10727 的根因）
- **【教训·我先删错了被用户纠正"不对，你把管理端直充删了干什么"】**：把"不要直接到保证金"理解成"删除直充功能"→ 删了 top-up API + 表单 + 页面引用 → 用户立刻纠正（功能要保留，改链路）。**凡用户描述的是"业务链路/数据流向"问题（先进X再Y、不要直接到Z），先确认是"改造链路"还是"删除功能"再动手——删除用户现有入口是高危操作，理解歧义时先问或用 git 可回滚的轻改动试探**；恢复=git show 旧版文件 + 改造
- **改造（commit 7ed7bf3+fe6a178，已部署 build34）**：top-up API 保留 finance 权限但改为**充值进 SellerWallet.availableAmount + walletRecharge 记录**（与 /api/admin/users/[id]/balance 商户代充同口径），**不再创建 sellerDeposit**；返回提示"已充值到余额，保证金请卖家从余额划转"；AdminDepositTopUpForm 文案改"充值到余额"（eyebrow/lead/成功提示三处）；页面引用恢复
- **存量处理**：旧版直充已进保证金的测试店（FlyGlobal 10727.5 等）——让卖家在资金中心退还超额保证金差额（净额−应缴额退到余额）后即可提现；新链路充值只进余额不会再产生占用
- 卖家端保证金缴纳入口（SellerDepositTransferPanel）本来就是余额划转（"保证金余额划转面板(2026-08-06 用户: 保证金按余额划转做——不可直充)"），无需改

### 21.8 资金规则最终形态：货款直接进余额可提现，保证金占用只算"余额划转"（2026-08-08 用户第三次澄清，commit 4fa36f0 已部署 build35）
- **用户原话**："买家购买卖家的商品，这个钱进了卖家账户，也是直接进余额，不直接进保证金"——**资金流向三规则（最终版）**：① 买家付款（货款）→ 卖家余额（**先入"待结算" pendingSettlement，不可提现；用户 2026-08-09 纠正"不应该是确认收货之后才能提现吗"——手册曾误写"付款即进可提现"**）② 管理端充值 → 进余额（21.7 已改）③ 保证金只能卖家从余额划转，**划转的钱才占用可提现**（退还可释放）。**完整口径：付款 → 待结算（delivered/shipped/awaiting_shipment/paid）；确认收货（手动/自动，completed/receipt_confirmed）→ 转可提现立即（21.9）**
- **根因**：`refreshSellerWallet`/`prismaSnapshot` 的 available 公式减 `deposit.balance.net`（**全部已缴保证金**）——旧版平台直充（不经过余额）的 10727 也占用 → 货款 25 被吃光、可提现 0（用户反复报"总览说进入可提现但提现没有"的深层根因，前两轮只修了展示层）
- **修复（三处统一口径，只减 reason="余额划转" 的保证金）**：
  - `refreshSellerWallet`：`sellerDeposit.findMany({ where: { storeId, kind: "pay", status: "approved", reason: "余额划转" } })`（原无 reason 过滤）
  - `prismaSnapshot`：`transferredNet = deposit.balance.net - aggregate(非"余额划转"的 pay approved 之和)`（直充/平台缴纳不算占用）——注意函数参数是 `storeName`，aggregate 的 where 用 `store.id`（81 行 store 查询）
  - 台账"保证金占用"流水：改用 `transferredNet > 0` 才 push（note 同步"余额划转保证金 X 占用可提现（申请退还后释放）"）
- **链路不变**：transfer 划转（reason="余额划转"）扣表 + net 加；退还（depositWithdraw）释放——划转的钱才从可提现消失
- **验证模式**：生产按新口径重算（completedTotal + recharge − 提现中 − 已提 − 划转占用）→ FlyGlobal 直充 10575 不占用 → 货款 25 可提现 ✅
- **通用教训（资金流向规则）**：用户说"钱进哪"（进余额/进保证金/进可提现）是**资金流向定义**——先画清"钱从哪出、进哪个池、占用什么"再改公式；**占用/扣减口径必须与"钱实际从哪出"一致**（直充没从卖家余额出 → 不占用卖家可提现）；三处口径（refreshSellerWallet 表 / prismaSnapshot 展示 / 台账流水）必须同步改，漏一处就是"资金中心与提现不一致"复现

### 21.9 确认收货即过保护期（2026-08-08 用户第四次资金规则澄清，commit eec272c 已部署 build37）
- **用户原话**："买家确认收货或者自动确认收货的，就算度过保护期了"——**货款确认收货（手动/自动）后立即进入可提现余额，不再冻结 30 天**
- **改动（funds-repository 两处）**：`prismaSnapshot` 的 `withdrawableCompleted = completedOrders`（全部，`heldCompleted = []`）；`refreshSellerWallet` 的 `completedTotal = 全部 completed`（`heldCompletedTotal = 0`）——移除 30 天窗口过滤；台账 note 改"订单完成并确认收货，货款计入结算余额（扣除保证金占用后为实际可提现）"；冻结明细无"售后保护期"项
- **售后申请窗口仍保留**（确认后 30 天，`afterSalesAvailableUntil = now + 30天` 继续写）——确认收货 API/settlement-tasks 自动确认处**不要改**（窗口独立控制售后申请；aftersale 申请检查 `completed && afterSalesAvailableUntil < now` 拦截）
- **验证**：生产 completed 订单全部计入可提现（含原窗口内的）——FlyGlobal 3 单 75 全可提 ✅（注意验证脚本别按旧口径算 held——新代码 held=[] 全计入）
- **通用模式：用户说"X 就算过 Y"是状态机口径收窄——先分清两个窗口**：货款冻结窗口（取消）vs 售后申请窗口（保留），改冻结口径时别顺手改掉申请窗口

### 21.10 卖家端首页「可提现余额」显示不一致（2026-08-08 员工测试反馈 177.5 vs 25，方案待用户拍板）
- **症状**：卖家端首页（app/seller/page.tsx:151-152）「可提现余额」卡显示 `store.wallet.availableAmount`（**表值 177.5 = 货款 25 + 充值 152.5，未扣保证金缺口**）；提现弹窗显示 `withdrawable = 表值 − 保证金未缴差额(gap) 152.5 = 25`（且 25 < 最低 50 提不了）→ 员工困惑"显示可提 177.5 实际只能提 25"
- **原因**（非数字错误）：**首页显示表值（未减 gap），提现处减了 gap**——两处口径不一致；gap 152.5 = 保证金应缴额(required) − 已缴(net)，**保证金未缴满前可提现 = 余额 − 缺口**（防提空不缴保证金）。保证金补缴满后 177.5 全可提
- **【2026-08-08 用户已拍板：方案 B，勿按 A 实施】**用户对"提现口径怎么定"明确回复 **B. 保留扣缺口（现状 25）：缺口是真实风控，先补缴再提**——**可提现 = 货款 + 充值 − 提现中 − 已提 − 保证金缺口(gap)**，缺口拦截提现是**正确行为不是 bug**（员工反馈"75 已结算只能提 25"时，先按 21.10/21.8 的公式还原计算链，得出"25 = 75 货款 − 缺口 50"，向用户解释缺口构成（扣款/应缴差额）并给出补缴路径，**不要改公式、不要按旧指示实施方案 A**）。缺口消除路径：卖家从余额划转补缴，或退还测试期误扣款（deduction）后缺口自动消失
- **【2026-08-08 资金构成现状排查三步（可复用脚本模式）】**用户问"该店铺资金构成现状"时，服务器 node 脚本按三步聚合（全在 prisma 客户端，注意模型名）：① `sellerWallet.findUnique`（available/pending/frozen/withdrawn 表值——**表值可能是旧缓存，提现 API 会先 refreshSellerWallet 再读表**，与页面实时快照（prismaSnapshot）是两套口径）② `order.findMany({ where: { storeId } })` 按状态聚合净额（`totalAmount − refundedAmount`）：completed+receipt_confirmed=可提现、delivered/shipped/awaiting_shipment/paid=待结算、after_sales_pending=售后冻结、paymentStatus=refunded=已退款（不计）③ `sellerDeposit.findMany` 三分类聚合：kind=pay approved（缴存）/kind=refund approved（退还）/kind=deduction approved（扣款），净额 = pay−refund−deduction；扣款逐条列 reason（缺货/仲裁强制退款是测试期常见来源）——**缺口 = 应缴(requirement) − 净额**，可提现 = 货款+充值−提现−缺口（规则 B）；验证"修复没生效"先还原这条计算链，缺口的扣款明细就是解释用户"为什么 75 只能提 25"的依据
- **排查方法**：用户报"显示 X 但提现 Y"——grep 所有渲染该数值的位置（seller/page.tsx 首页 / SellerFundsCenter 总览 / SellerWithdrawRequestForm 弹窗），逐处核对减没减 `deposit.gap`；**生产查不到对应店铺数据时（员工可能测 dev/临时数据）按机制分析即可**（表值−gap 公式不变）

### 21.11 保证金足额上限：只能足额缴纳，不能超额预缴（2026-08-08 用户拍板 B 方案后追加，commit 40c6959 已部署 build46）
用户确认 21.10 方案 B（保留缺口拦截）后又要求："给保证金加个上限吧，只能足额缴纳，不能超额预缴"——**划转校验链加一环：金额 ≤ 缺口(gap)**：
1. **API**（app/api/seller/deposit/transfer/route.ts）：现有校验顺序（金额 ≥1 → ≤ 可提现余额）后追加：`gap = snapshot.deposit.gap`（getFundsSnapshot 的 deposit.gap）——**【2026-08-09 用户拍板 A·规则已更新，勿按旧版拦截"已足额"】**：`maxTransfer = gap > 0 ? gap : 100`；`amount > maxTransfer` 返回 400"保证金只能足额缴纳：当前缺口 N USDT，最多划转 N / 应缴为 0，最多划转 100 USDT"。**应缴 0（无在售商品，liveProducts=published+approved 为空）不再拦截"已足额"——允许划转但上限基础档 100**（用户反馈"卖家端无法划转，应缴是 0"后拍板 A；commit e8a997c build49）
2. **表单**（SellerDepositTransferPanel）：初始值 `gap > 0 ? gap : "100"`（**应缴 0 时默认 100**，原来改过 `""` 又按 A 改回 100）；提交前校验 `value > maxTransfer` 拦截（gap>0 用 gap，否则 100）；输入框"最高"提示显示 `{gap > 0 ? gap : 100}`；按钮 `disabled={saving || balance < 1 || Number(amount) > (gap > 0 ? gap : 100)}`
3. **新键 ui.cn.70-73 × 7 语言**（（已足额）/保证金只能足额缴纳：当前缺口 / USDT，最多划转 / USDT。）；SiliconFlow 6 并发翻译
- **验证**：tsc 0；登录态 qa-seller 超限划转测试——注意该校验在 available 校验**之后**（余额不足会先被拦，测 gap 校验需先有余额的店）；资金 API 结构 = `snapshot.deposit.gap`
- **【2026-08-08 存量超缴已处理（commit 5a467d5，build47）】超缴退还执行实录**：
  - **应缴精确核算（别手动近似）**：`computeDepositRequirement` 的真实口径 = liveProducts（`status=published + reviewStatus=approved` 的商品类目，非全部商品）→ rootCategoryOf 映射根类目 → 类目档 `DEPOSIT_TIERS[tierIndex]`（未知类目兜底普通 100）；GMV 档用 `orderStatus notIn [pending_payment, closed]` 的 paid 订单近 90 天总额查 `GMV_DEPOSIT_LADDER`；`requiredAmount = max(类目档, GMV档)` 封顶 5000；无在售/在途商品应缴 0。FlyGlobal 实测：键鼠套装键盘→未知类目普通 100，GMV 28035→档 1000，应缴 **1000**（此前推断的"缺口 50"是错的——净额 10422.5 ≫ 应缴 1000）
  - **超缴 = 净额(pay−refund−deduction) − 应缴** = 10422.5 − 1000 = **9422.5**（不是早前估的 10227.5——那个数字来自旧应缴推断）
  - **【新坑·退还转回余额不计入可提现 = 真 bug】**：refund route 创建 kind=refund approved 后只调 refreshSellerWallet，但 `availableAmount` 公式（completedTotal + recharge − active − withdrawn − depositPaidTotal）**不含退还金额** → 退款转回后可用余额不变（用户提现还是老数字）。**修复：prismaSnapshot + refreshSellerWallet 两处 available 公式都加 `refundTotal`**（`sellerDeposit.aggregate({ where: { storeId, kind: "refund", status: "approved" }, _sum: { paidAmount } })`）——退还的钱要回可提现池
  - **执行退还**：服务器 node 脚本创建退款单（`kind: "refund", status: "approved", reason: "差额退（超缴清零）"`，绕过 `!hasOpenOrders` 条件——测试店管理员操作）；**refreshSellerWallet 是 .ts 不能 require**——脚本里手动复制公式算 availableAmount 后 `sellerWallet.upsert`；验证：退款后净额=应缴、available = 货款 + refundTotal
  - **新规员工测试手册已交付**：`docs/qa/新规员工测试手册-20260808.md` + 桌面副本（六章：资金模型新规/确认收货即过保护期/提现口径/售后退款不减销量/默认英文多语言/类目验证，每项【步骤】+【预期】+测试记录模板）——用户要求新规配套员工测试手册时按此模板出
- **通用模式：资金划转/充值类 API 的校验链 = 下限（金额 ≥1）→ 可提现余额 → 上限（缺口/风控额度），用户"加个上限"需求 = 校验链加一环 + 表单三处同步（初始值/提示文案/按钮禁用）**——只改 API 不改表单，用户会在输入框看到可划全部余额的误导提示

### 22. 全站翻译批量扫描修复流水线（2026-08-08 用户"三端所有页面翻译问题全部找出修复"，479 处/70 文件一次修完）
用户报"申请售后页部分翻译转化不了"→ 直接要求**全站扫**。可复用流水线（一次会话内 479 处硬编码中文 → 147 键 × 7 语言上线）：
1. **扫描**（python execute_code）：遍历 app/ + components/ 全部 .tsx（排除 preview/docs/api），三类模式——① 文本节点 `>([^<>{]*[\u4e00-\u9fff][^<>{]*)<` ② 属性 `\b(placeholder|title|aria-label)="[^"]*[\u4e00-\u9fff][^"]*"` ③ option `(<option[^>]*>)(中文)(</option>)`；跳过已含 `data-i18n` 的行
2. **改文件（关键坑，防语法破坏）**：
   - **含 `{` 的行整行跳过文本节点处理**（模板串 `>共 {n} 单<` 会被正则拆坏成 `< {n}` 语法错——TS1381）
   - 文本节点 → `><span data-i18n="key">原文</span><`（原文保留作 fallback）；属性 → 同标签后加 `data-i18n-placeholder/title/aria-label="key"`；**option 内不能放 span（HTML 限制）→ 直接给 option 标签加 `data-i18n` 属性**
   - **同一行多个替换点必须从后往前应用**（`sorted(reps, key=-start)`），否则前一个替换改变行长度后后续 m.start() 偏移错位（TS1003 Identifier expected）
   - **脚本只允许跑一次**（跑了两次 → 同一属性插两遍 → `JSX elements cannot have multiple attributes with the same name` TS17001）；防重复：处理前 `if "data-i18n" in line: continue`（含 ui.fix 键的行也要跳过——第一次跑完第二次必须全量 git checkout 重来，别在已改文件上续跑）
   - 已有翻译键的行（如 LanguageSwitcher 的 `data-i18n-aria-label="language.switcher.label"` 与另一行 `aria-label="选择语言"`）——**同一元素别重复加键**（手动修：删掉新加的，保留原有键）
3. **键命名**：`ui.fix.N` 序号键（文案去重 → 同文案同键），批量修复不追求语义键名
4. **deepseek 批量翻译**（通道固定）：环境变量 **`TRANSLATE_API_KEY`** + **`TRANSLATE_BASE_URL`（注意要拼 `/chat/completions`——base 是根域名，直接 POST 根 404）**；prompt="Translate UI strings from Chinese to {lang}. Return ONLY JSON object mapping same keys, no explanations"；**翻译结果的键是中文原文**（不是 ui.fix.N）→ 用 uniq 映射（文案→键）转回；一次 80 键以内分批发（大 batch 容易截断/缺键，每语言 2 批）；缺键比例 >10% 重试
5. **插键（锚点格式坑）**：translations.ts 的语言包是 **`const zh: TranslationMap = {`**（不是 `"zh-CN": {`）——锚点按 `const {var}: TranslationMap = {` 找，在 `{` 后首个换行插入整块键
6. **验证**：tsc EXIT 0 → 提交部署 → 生产登录态抓 SSR HTML 数 `data-i18n` 计数（未登录页会 302 跳登录，别拿它验证）；`grep -c '"ui.fix'` 生产页面应 >0
- **含 `{` 变量行的文案与 JS 字符串错误消息（setMessage）两类不在本流水线覆盖**（模板串需手动拆分静态 label + 变量渲染；错误消息是交互反馈非页面文案）——用户再报时按类补
- **通用模式：全站性文案改造（翻译/文案统一）先扫描定规模（去重数/文件数）再决定自动化**；自动化脚本必须"单次幂等 + 从后往前替换 + 处理前跳过已标行"，三缺一必出语法错

### 22.5 JS 提示消息 getTranslation 化（2026-08-08 第二批，用户"所有组件包括提示文字默认全部英文"）
第 22 节流水线只覆盖 JSX 文本/属性；**JS 字符串（setMessage/setNotice 提示、三元 fallback "包邮"、`?? "待填写"`）也要英文化**。可复用流程：
1. **只替换安全形态**：`setMessage("纯中文")`（**双引号字符串**，正则 `(setMessage|setNotice|setError|setSuccess|setInfo)\(\s*"([^"]*中文[^"]*)"\s*\)`）→ `setMessage(getTranslation(currentClientLanguage(), "ui.msg.N"))`；**反引号模板串（含 ${}）绝不替换**（会把 `${x}）没有已上架商品` 拆成乱码，TS1127/TS1002——只处理无变量的纯字符串）；`=== "中文"` 状态比较、对象键（`{ "已退款": ... }`）不替换（翻译会破坏比较逻辑——这类是状态映射，走 DynamicText/status 键体系）
2. **getTranslation 是 2 参数且顺序是 (language, key)**（TS2554 Expected 2 arguments）——组件里没有 language 变量 → **在 translations.ts 加 `currentClientLanguage()`**：`typeof window === "undefined" ? defaultLanguage : normalizeLanguage(localStorage.getItem(languageStorageKey))`（服务端返回 en，客户端读 localStorage）
3. **import 管理（脚本重复跑的坑）**：每组件加 `import { getTranslation, currentClientLanguage } from "@/lib/translations"`——脚本跑两次 = 重复 import（TS2300 Duplicate identifier）+ 同一 import 行内重复名（`getTranslation, currentClientLanguage, currentClientLanguage`）——**import 去重脚本**（正则拆 `{}` 内名字 set 去重）+ **只允许跑一次**（第二遍前必须全量 `git checkout -- app/ components/`）
4. **deepseek 翻译批次坑**：**70 键/批会输出截断 → JSON 解析失败 → 整批返回 {}（静默全丢）**——`30 键/批 + max_tokens: 4000` 必成（实测 132 键 5 批全过）；每批后打印 `批N/总: len(r)` 盯缺键；**翻译结果 JSON 的键是中文原文**（不是 ui.msg.N）→ 用 uniq 映射（文案→键）转回再插
5. **插键值必须转义**：deepseek 返回可能含 `"`/换行 → `v.replace("\\","\\\\").replace('"','\\"').replace("\n","\\n")`，否则 translations.ts 语法错（TS1005 ',' expected）
6. **含 `{` 的 JSX 变量行拆分**（第二批）：`>下单时间 {x}<` → `><span data-i18n="k">下单时间</span> {x}<`（静态段 span + 变量保留）——只处理**无复杂表达式**（`? :`/`||`/`&&`/`=>` 的行跳过）的简单 `>文本 {var}<` 形态；拆分脚本同坑：从后往前应用 + 含 data-i18n 行跳过
7. **验证**：tsc 0 → 部署 → 服务器源码 grep 新键/函数/调用（编译产物 grep 可能落空——chunk 拆分/压缩，别拿产物 grep 下结论）→ home 200

### 22.6 默认语言=英文 + 用户句式解读教训（2026-08-08 用户两次纠正）
- **规则（用户原话）**："买家端和卖家端的默认语言是英语，不是中文" + "默认语言，以及所有组件，包括提示文字，乱七八糟这些，默认全部都是英文，使用英语的广泛目标才是我们的主要客户"——**defaultLanguage 恒为 "en"，勿改 zh-CN**（fallbackLanguage 保持 zh-CN 是源码语言，与默认语言是两回事）
- **【教训·我理解反了被纠正"不是中文，是英文你看不懂吗"】**：用户说"X 是英语，不是中文"（陈述句）——**意思是"应该是英语"（现状/期望是英语），不是"把它改成中文"**。**解读规则：用户用"是 Y 不是 Z"句式描述语言/配置现状时，Y 是期望值，Z 是"不该出现/被误解为"的东西——改之前先复述确认（"你是说默认应该是英文对吧"），尤其改的是 defaultLanguage 这种一行定全站的配置**；我第一反应把 en 改成 zh-CN 是反向操作，用户立刻纠正
- **未翻译残留的预期**：默认英文下，未覆盖的硬编码中文（JS 状态映射、复杂模板串）会显示中文——用户说"乱七八糟"指这个；已分批补（22/22.5），仍有残留时按 22.5 第 1 条的安全形态继续补，**别动状态比较/数据值**
- **【翻译筛选清单·2026-08-08 用户已选"全翻"】**：`D:\跨境商城\会话产物\翻译筛选清单_状态映射三元模板串.txt`（510 条：对象值 196/三元 161/模板串 93/??兜底 60；其中 82 条已标注"已有翻译键无需处理"，**实际待处理 428 条**，含文件:行号）。**全项目扫描确认：键为中文的状态映射对象（`statusText = { "已退款": ... }`）= 0 个**（已全部改英文键+翻译键）——用户举例的形态不存在，实际残留都是"值中文"的对象值/三元/模板串，判断逻辑（`=== "中文"` 比较）不在清单内。**用户 2026-08-08 已回复"全翻"并实施（428 处替换完成，见 22.7）**——跨会话接续先看 22.7 的完成状态（翻译插键/部署是否收尾），勿再问"全翻还是按类型"

### 22.7 清单"全翻"实施：三元/对象值/模板串/??兜底批量 getTranslation 化（2026-08-08 用户选"全翻"，428 处 104 文件）
用户对 22.6 清单回复"全翻"→ 实施（428 处替换完成：三元 157/对象值 118/模板串 93/??兜底 60；翻译 496 键×6 语言后台跑，30 键/批 + max_tokens 4000）。可复用流程与坑：
1. **读清单只取"待处理"行**（正则 `\[类型\] 路径:行号 | 内容`，跳过"已有翻译键"标注）→ 按文件分组 → 逐行按类型替换：`?? "中文"` → `?? getTranslation(...)`；三元/对象值 `[?:]\s*"中文"` → getTranslation；模板串 `` `静态${var}静态` `` → `getTranslation(...) + ${var} + getTranslation(...)`
2. **【新坑·类型声明误伤】`: "中文"` 替换会命中 TS 类型声明**（`Array<{ label: string; value: "已上架" | Product["status"] }>`）→ 类型位置出现 getTranslation 调用（TS1131/TS1005）——**修复**：`([|:(])\s*getTranslation\(currentClientLanguage\(\),\s*"(ui\.sel\.\d+)"\)` 按 ui_sel_map 反查原文案改回字符串字面量（70 文件命中，优先用 `|` 前缀模式只改类型联合位，别误伤运行时对象值）
3. **【新坑·JSX 表达式内 `${}` 非法】模板串拆分后 `${x}` 留在 JSX 表达式/字符串拼接里**（TS1381/TS1127，`${}` 只在反引号模板串内合法）——修复三连正则（批量跑含 getTranslation 的文件）：`\+\s*\$\{([^}]+)\}\s*\+` → `+ ($1) +`；行尾 `\+\s*\$\{([^}]+)\}` → `+ ($1)`；行首 `\$\{([^}]+)\}\s*\+` → `($1) +`
4. **【新坑·复杂嵌套模板串自动拆必坏，必须手动重写】**：嵌套模板+三元+转义引号（`` `已为 ${n} 家${x ? `；跳过：${join("、")}` : ""}。` ``）正则拆必乱码（TS1127/TS1002）——本轮 6 处手动重写（静态段逐个 getTranslation 键 + 变量 `(x)` + 三元展开）：AdminTestOrdersClient setMessage、SellerAfterSalesList setNotice、SellerBatchShipList setNotice、SellerFulfillmentForm parcelNote+composedNote、SellerOrderCancelButton alert、SellerProductManager bulkDelete/bulk；**手动新键（ui.sel.469+）要显式写进映射文件**（uniq/manual 字典），翻译脚本才能带出
5. **【判断逻辑/类型值保护】状态赋值不能翻**：`submit(product!.status === "已上架" ? "已下架" : "已上架")` 返回类型 `"已驳回" | "已上架" | "已下架" | "待审核" | "草稿"`（TS2345 string not assignable 兜底抓出）——**状态值三元/比较一律改回中文原值**；同行的按钮**显示文案**（`{cond ? getTranslation(...) : "重新上架"}`）可留翻译
6. **import 补齐**：getTranslation 化文件缺 import → tsc `Cannot find name` 逐文件补（OrderProgressSteps 这类无 import 的文件，插在 "use client" 后或文件首 import 处）
7. **验证与部署**：tsc 0 → 翻译结果插键（7 语言包，`const xx: TranslationMap = {` 锚点，值转义）→ git archive 部署 → 服务器源码 grep 新键（编译产物 grep 会落空勿依赖）→ home 200
- **通用教训：批量文案替换（值中文对象/三元/模板串）比文本节点替换（22 节）风险高一个量级**——类型声明、状态类型联合、嵌套模板、JSX 表达式内 `${}` 四类语法面都会被正则踩到；流程 = 替换 → tsc 报错逐个修（类型位改回/模板手动重写/import 补齐）→ 翻译 → 插键

### 22.8 deepseek 批量翻译：12 路并发 + 401 风控（2026-08-08 全翻批次实录，用户纠正"之前不是12路并发吗"）
- **用户偏好（明确纠正过）**：翻译任务默认 **12 路并发**（ThreadPoolExecutor max_workers=12）——串行跑被用户点名批评慢。实测：**496 键 × 6 语言 = 102 批（30 键/批），12 并发 57s 完成**（串行估算 10-12 分钟）；8 并发 ~2-4 分钟
- **【新坑·deepseek 并发 401 风控】短时间大量并发请求触发 key 风控 → HTTP 401 Authorization Required**：症状 = 单请求正常（连续 3 次 OK）、一上并发（8/12 路）全部 401、重试退避 6 次仍 401；**第一次 12 并发跑成功（57s），紧接着快速重跑就触发**（burst 检测，非额度问题——单请求验证立刻恢复）。处理：① 先单请求测试确认 key 本身没挂 ② 等 60s+ 风控窗口再跑 ③ 并发脚本必须带**退避重试**（sleep 8+attempt*8）+ **中间结果落盘**（每 N 批 json.dump 到临时文件，脚本重启时恢复未完成批次——`if f"{lang}|{key0}" in raw: return`）④ 极端情况降并发（12→8→6→串行）或等更久
- **【坑·长流水线别用 pkl 中转，翻译+插键一个内存脚本完成】**：本次两次把翻译结果 pickle 存盘再读，读出来 en/es 等包是**空 dict**（zh 有值、打印时 OK 保存后变空，原因未明——疑似大 pickle 写入/读取不一致）——**浪费两次 57s 全量重翻**。**教训：翻译结果直接在内存里合并 → 立即插键写 translations.ts → 最后才落盘备份**；如必须中途保存，用 json 存**原始 (lang, batch首键) → 翻译dict** 的并发结果（可增量恢复），不要存合并后的 dict
- **【坑·execute_code 5 分钟超时】**：长翻译（>5 分钟）放 execute_code 会被 kill（300s 超时，进程杀后 translations.ts 可能半写）——**必须 `terminal(background=true)` + `notify_on_complete=true` 跑脚本文件**（脚本内 `print(..., flush=True)` + 独立日志文件 `> log 2>&1`），完成后 process wait/log 看进度
- **【坑·并发收集后合并**：as_completed 拿不到任务参数 → `fut_map = {ex.submit(fn, t): t for t in tasks}` 反查；合并时按 (lang, batch首键) 字典逐个 update，别把并发收集 dict 和合并 dict 搞混（曾出现合并循环变量遮蔽导致 6 语言全空——直接在内存 `raw[lang].update(r)` 最简）
- 翻译批次大小不变：**30 键/批 + max_tokens 4000**（70 键/批必截断，22.5 节）；prompt 强调 "Keep leading/trailing spaces and punctuation"（手工键 469+ 带前后空格，漏了会丢空格）
- **手动新增键必须写进翻译脚本的 manual 字典**（22.7 第 4 条），且排序 key 用 `int(x[0].split(".")[-1])`（ui.sel.N 数字序）
- **【最终结论·IP 级间歇风控，换 key 无效】**：用户提供**新 deepseek key** 后单请求秒过、一上并发（12/8/6/1 路全试）仍全 401、串行第一个请求也 401 → **风控绑定出口 IP/服务端动态窗口**（本机 TUN 出口伦敦节点被标记），换 key 无济于事；窗口期（几十秒~几分钟）自动恢复（单请求测试随时可能过——先测再跑）
- **【最终可用模式（本轮 496 键 6 语言实测收尾方案）】**：等 10 分钟冷却（IP 标记完全过期）→ 2 并发 + 每任务 1.2s 间隔 + **401 时 sleep 60s 再重试（最多 10 次）** → 中间结果 json 落盘（`{lang}|{batch首键}` → 翻译 dict，重启恢复跳过已完成）→ 全部完成后内存合并 → 直接插键写 translations.ts。慢（25-35 分钟）但必成；嫌慢时换非 deepseek 通道（OpenAI/中转）才是根治
- **【给用户解释\\\"为什么之前高并发没事\\\"的话术（用户明确问过）】**：deepseek 风控基于请求频率动态——首次大规模跑一次跑完频率均匀未触发；本次**短时间反复满并发重跑**（每轮 100+ 请求、3-4 轮连撞）→ burst 触发 IP 标记 → 窗口内全 401。**教训：翻译重试必须等窗口过（60s-10min）再降并发慢跑，绝不在窗口期内满并发反复打（每次重跑都把窗口拖长）**
- **【fkcodex newapi 通道验证（用户 2026-08-08 提供）】**：`https://www.fkcodex.com` + `sk-` key，`/v1/models` 403、chat/completions 换 8 个模型名全 403、加浏览器 UA 后变 503 = **服务端渠道不可用（非 key 问题），已弃用**。newapi 中转验证法：models 403 是 newapi 常见（默认关闭）→ 直接试 chat/completions 逐个探测模型名 → 全 403 加浏览器 UA 再试（403→503 = 服务停/渠道挂）→ 换通道
- **【翻译备选通道推荐（用户问\"有没有靠谱中转站\"，推荐口径）】**：① **SiliconFlow 硅基流动**（https://siliconflow.cn，手机号注册+支付宝充值+送额度，API `https://api.siliconflow.cn/v1/chat/completions`，模型 `deepseek-ai/DeepSeek-V3`，国内直连+并发宽松——**deepseek 官方 IP 风控的根治方案**，注册好给 key 直接配）② **OpenRouter**（https://openrouter.ai，API `https://openrouter.ai/api/v1/chat/completions`，有免费模型 `deepseek/deepseek-chat:free`、`openai/gpt-4o-mini:free`——不充值可用，需国际支付才付费）
- **【SiliconFlow 已实测配置成功（2026-08-08 用户提供 key）】**：`.env.local` 写入 `SILICONFLOW_API_KEY=sk-vaan...` + `SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1`（**用户给 key 后第一步先单请求测试连通再配置**）；`/v1/models` 可用（91 模型，含 `deepseek-ai/DeepSeek-V4-Pro/V4-Flash/V3.2`、`zai-org/GLM-5.2`、`moonshotai/Kimi-K2.7-Code` 等）；**翻译用 `deepseek-ai/DeepSeek-V4-Flash`**（便宜快，实测 10 并发 10/10 成功 25.7s、无 401 风控——vs deepseek 官方 2 路都挂）。**并发上限实测（2026-08-08）：15/25/40/60/100 并发全部 100% 成功（18-21s），上限未测到——60 并发即有 20-30 req/s 吞吐，6997 商品全量翻译约 5-8 分钟；批量翻译脚本并发直接给 60（backfill 脚本 CONCURRENCY 12 可调高），无需像 deepseek 官方那样冷却/退避**。**deepseek 官方通道最后成功模式（496 键 6 语言 165s 实测收尾）**：等 10 分钟冷却 → 2 并发 + 401 sleep 60s 重试（最多 10 次）→ 全部完成自动插键——此模式已验证可跑通；以后批量翻译**优先 SiliconFlow**（无需冷却直接 12 并发）

### 22.9 中文原值判断逻辑清单（2026-08-08 全翻收官，用户\"不动底层走渲染层\"决策）
- **交付物**：`C:\Users\Administrator\Desktop\Qavlixor中文原值清单.txt`（107 处 = 比较 105 + 赋值 2，27 文件，买家端 ~55 / 卖家端 ~52，按 30 个状态词分组：已上架 16 / 待发货 15 / 商家处理中 7 / 平台介入 7 / 已拒绝 6 / 售后中 6 / 已退款 5 等——**全是 DB 中文存储值的判断逻辑，必须保持中文原值，翻译会破坏比较**）
- **缺翻译键状态词 8 个（渲染会露中文，判断不受影响）**：商家已拒绝 / 已删除 / 已退款 / 提现冻结 / 提现打款 / 订单结算 / 钱包充值 + 确认规则长句\"签收后可在售后期内提交服务申请…\"——其余 23 个状态词已有翻译键（account.status.* 等，渲染层正常）
- **用户决策（问\"底层改英文要多久\"→ 答 1.5-2 天含测试部署、风险高收益≈0 后）**：**\"不动页面底层，增加渲染层\"**——底层 DB 中文值 + 判断逻辑零改动，只补渲染层翻译：① 统一渲染函数（英文值查 30 状态词翻译键，查不到原样返回）替换直接渲染处 ② 补 8 个缺键 ③ JS 字符串残留补齐——评估 4-6 小时；**【2026-08-08 已实施完成，见 22.11】用户回复\"全部修复\"后按 22.10 报告逐项落地（78 键×7 语言，builds 42/43/44），复扫全清；8 个缺键状态词与渲染函数统一方案按需补**
- **用户最后加码**："商品标题/用户输入的中文内容也翻译，根据用户语言"——**先查现状再动手（用户强调的流程）**：① **商品标题 7 语言翻译数据早已全量存在**（生产 6997 商品中 6988 有完整 7 语言 i18nJson.title，各语言缺失 0；498 个中文标题全部已有 en 等翻译；仅 9 个完全无）——本段早前写的"i18nJson 基本空"是**错的**（发品时/历史回填早已翻完）② **真正缺的是渲染接入**：`productTitleI18n(i18nJson)` 解析函数（lib/product-i18n.ts）目前只有售后申请页在用（app/account/orders/[id]/aftersale/page.tsx 49-52 行），产品卡/详情/订单/购物车/搜索 ~20 处显示标题原文、未按当前语言读 i18nJson ③ 店铺名 76 店（4 个中文店名：星桥优选店/小飞的百货店铺/南星/QA测试店铺），Store.i18nJson 字段 schema 有但翻译数据状态未查清（生产 client 查询 i18nJson 报 library.js 错待查）④ 用户输入（留言/售后描述）无机制，需按需翻译+缓存
- **用户需求澄清（2026-08-08 末）**："我要的不止是能切换英文，而是那几个国家的都能切换"——**7 语言（zh/en/es/fr/pt/ru/ar）切换时动态内容（标题/店名）都要跟着变**（不是只英文）；先确认需求再提方案
- **回填脚本已改造待跑（commit d996f6b，用户喊停未跑）**：`scripts/backfill-product-translations.mjs` 支持 `SILICONFLOW_API_KEY` 优先（deepseek 官方并发 401 风控，见 22.8）+ 12 路并发池（原串行 8 小时→预计 40 分钟，BATCH 15 不变）；新增 `scripts/backfill-store-translations.mjs`（76 店×7 语言写 Store.i18nJson.name，8 并发）——**store 脚本有 bug 未修**：`import { resolve } from "node:fs"` 应为 `node:path`（Node 22 直接 SyntaxError，已实测）；服务器 .env.local 已追加 SILICONFLOW_API_KEY/BASE_URL（ssh echo 追加，注意 .env.local 里现在同时有 TRANSLATE_API_KEY 和 SILICONFLOW_API_KEY，脚本优先读 SILICONFLOW）
- **【用户工作方式指令（2026-08-08 末，最高优先级）】"所有的任务，问清楚我的需要，方案经过我确认之后再去做，不要自己猜我的想法"**——数据类任务先查现状（已有多少/缺多少）再提方案；方案必须用户确认后才动手；用户说"先配置进去，然后我再决定做哪个方案"= 配置（env/key）可以直接做，执行等确认
- **通用模式：判断逻辑值（状态比较/赋值/类型联合字符串字面量）与渲染文案是两层**——改显示语言永远走渲染层（翻译键/DynamicText/渲染函数），底层枚举值与比较逻辑保持稳定；\\\"把 X 改成英文\\\"先问\\\"改展示还是改底层\\\"，展示层改造成本是底层的 1/5 且零风险

### 22.10 英文状态中文残留多并发扫描（2026-08-08 用户\\\"多并发去探测，一个窗口太慢\\\"）
用户要知道\\\"买家端/卖家端英文状态下哪些地方会漏中文\\\"——**别用浏览器逐页看（慢），写服务器 Node 脚本并发 fetch 扫 SSR HTML**：
1. **登录拿 cookie**（qa-buyer-2/qa-seller-1，密码 QaTest!2026；**qa-buyer-1 生产登录 401——可能已禁用/密码被改，扫描登录用 2/3**；demo-view 密码未知）；cookie = `r.headers.get('set-cookie').split(';')[0]`
2. **页面清单**（买家 14 页：首页/列表/搜索/购物车/账户/订单/售后/地址/资料/收藏/联系/登录 + 商品详情/店铺页（商品 id 与店铺 slug 从 /products HTML 正则提取 `\\/products\\/(PD\\d+)`、`\\/stores\\/([a-z0-9]+)`）；卖家 12 页：首页/订单/售后/商品/资金/保证金/提现/划转/物流/消息/账户/批量发货）——**并发 12-15 路 `Promise.all` 切片**（首页/详情/列表类页面全走 127.0.0.1:3000 内网快）
3. **findCn 提取（两个坑，第一版全假阴性）**：
   - **SSR HTML 是压缩单行——绝不能按行 `if line.includes('data-i18n') continue`（整行跳过 = 全部漏报 \\\"✅ 无\\\"）**；要对整个 HTML 用正则剔除 data-i18n 节点后再 match 中文文本
   - 剔除正则 `<[^>]*data-i18n[^>]*>[\\s\\S]*?<\\/[a-zA-Z][^>]*>` **非贪婪跨节点会误剔 data-i18n 容器内文本、也可能剔不干净**（检出的大半可能已带 data-i18n、会被 LanguageSync 翻译 = 误报）——**SSR 扫描结果必须分两档：\\\"真残留（无任何翻译标记）\\\" vs \\\"疑似（可能已有 data-i18n，需浏览器实测确认）\\\"**，别把疑似档当确认残留报给用户
4. **SSR 盲区**：客户端渲染文本（首页库存\\\"6989 件\\\"在 next 内联 JSON `<script>` 里）SSR 扫不到（script 被剔除）——**浏览器实测兜底**（browser_console 跑 TreeWalker：`document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)` 收集含中文文本，1 页 1 次即可，只用于确认 SSR 盲区项）
5. **键名裸露检测**：正则 `>([a-z]+\\.[a-z]+(?:\\.[a-zA-Z0-9]+)+)<`（登录页 `auth.buyer.brandSub` 等 5 键显示键名 = translations.ts 缺键）
6. **无数据页面扫不了**（qa-seller-1 无订单→卖家订单详情无数据；弹窗/JS 提示只有交互触发才显示）——报告注明覆盖盲区
**2026-08-08 扫描结果（已交付用户，修复范围待用户确认，勿重复扫描）**：
- ✅ 确认残留（浏览器实测）：首页商品卡库存\\\"6989 件\\\"（\\\"件\\\"未翻译应为 pcs，SSR 盲区）；登录页 5 个 auth.buyer.* 键名裸露（brandSub/slogan/point.ordersSub/logisticsSub/serviceSub 翻译表缺键）+ 密码框\\\"显示密码\\\"按钮中文
- ⚠️ SSR 真残留（无翻译标记）：卖家资金中心保证金阶梯规则长文案 ~15 处（天支付 GMV/未触发阶梯/高风险/中风险/普通/多类目按最高档缴一次;GMV 阶梯与类目档就高执行,封顶/GMV 差额有 N 天宽限。取消/强制退款按 5% 罚扣(最低 1 最高 100)/累计订单/处理中提现）；卖家首页\\\"昨日无数据\\\"；买家我的账户\\\"最近记录/消费记录\\\"；买家个人资料\\\"简体中文\\\"
- ⚠️ SSR 疑似（可能已有 data-i18n，需浏览器确认）：买家订单详情 25+ 处（订单号/下单时间/剩余/未付款订单将自动关闭/取消订单/确认收货/联系商家/拍下商品/买家付款/商家发货/交易成功/商品总价/运费/包邮/实付款/物流信息/承运商/运单号/待填写/收货人/联系电话/收货地址/付款状态/支付方式 + 前往收银台完成付款…长句）
- 用户数据类（店名\\\"北线好物店\\\"全卖家页、昵称 QA买家2/3）——显示中文属正常（用户输入内容，翻不翻用户定）
- **通用模式：\"哪些页面有 X 残留\"类问题 = 服务器并发 SSR 扫描（快、全）+ 浏览器实测兜底（准、补盲区）**；SSR 扫描结果分档交付，别把疑似当确认

### 22.11 残留\"全部修复\"实施完成（2026-08-08 用户拍板，commits c21080f+3f5bf12+71c5ede，builds 42/43/44）
用户对 22.10 扫描报告回复\"全部修复\"→ 已全部实施并部署（复扫资金中心/卖家首页/首页/账户/登录页=无残留 ✅，tsc 0）。修复清单与可复用手法：
1. **订单详情 25+ 处\"疑似\"档实为真残留**（判定：源码 grep `grep -c data-i18n app/account/orders/[id]/page.tsx` 只有 6 处）——**根因：22 节首轮脚本\"含 { 的行整行跳过\"，订单详情每行都含 `{order.orderNo}` 等变量 → 全漏网**。含 { 行拆分安全版（本轮成功）：`text_pattern = >([^<]{0,80}中文[^<]{0,80})<` + **跳过复杂表达式行**（`? :`/`` ` ``/`||`/`&&`/`=>`/`.map(`/DynamicText/kind= 一行跳过）+ 简单形态 `>文本 {var}<` 才拆（`split_static_var` 按 `(\{[^}]+\})` 切，**parts>3 跳过**）+ 从后往前应用 reps——`>{shipping > 0 ? ... : \"包邮\"}<` 这类三元行拆必坏（TS1381/TS17002 实录），跳过后再手动改（`\"包邮\"` → `getTranslation(currentClientLanguage(), \"ui.cn.44\")`）
2. **资金中心保证金阶梯渲染翻译（TIER_NAMES/类目名是模块级常量，别改常量值）**：渲染处（SellerFundsCenter:161）`getTranslation(currentClientLanguage(), \"ui.cn.tier.\" + TIER_NAMES[tier])` + `\"ui.cn.cat.\" + name`（**键名含中文可作翻译键**，`ui.cn.cat.珠宝配饰`）——常量（lib/deposit-constants.ts）保持中文原值，渲染层翻译
3. **语言名 labelKey 体系（\"简体中文\"残留根因+方案）**：translations.ts `languages` 数组元素加 `labelKey?/shortKey?`（**接口化 `LanguageInfo`**：`code: \"en\"|\"es\"|...|\"ar\"` 联合类型 + labelKey/shortKey——原来 `as const` 推断类型缺字段，TS2339；`LanguageCode = LanguageInfo[\"code\"]`）→ zh-CN 项 `labelKey: \"lang.zhCn\", shortKey: \"lang.zhShort\"` → **两处渲染**都要按 labelKey 走：LanguageSwitcher（strong/small + 下拉 menu 两项）+ **BuyerAccountForms:114 原生 select 的 option**（`data-i18n={item.labelKey ?? undefined} data-i18n-raw={item.labelKey ? undefined : item.label}`——原生 `<option>` 文本节点 data-i18n 有效）——SSR 扫描\"简体中文\"在 `<option value=\"zh-CN\">` 上下文，就是这处
4. **手动项批量**（JS 字符串/三元/单节点）：seller/page.tsx:100 `return \"昨日无数据\"`→getTranslation；BuyerBalancePanel `最近记录` span 加 data-i18n + 三元 `\"消费记录\"` 复用已有键 `ui.sel.301`；PasswordInput `\"显示密码\"`；ProductCard `${inventory} 件库存`→`${inventory}${getTranslation(...)}`（DynamicText kind=operation 拼翻译值）
5. **登录页 auth.buyer.* 5 键补键**（brandSub/slogan/point.ordersSub/logisticsSub/serviceSub——SSR 显示键名=翻译表缺键，zh 值写文案 + 其他 6 语言 SiliconFlow 翻）
6. **新键翻译批次**：51 键（ui.cn.1-44+auth.buyer.*+lang.*）SiliconFlow 12 并发 148s + 27 键（tier/cat/补充）238s——**SiliconFlow 无 401 风控，批次 12-15 键/批即可，无需 deepseek 的 30 键/批限制**；插键同 22 节锚点法
- **遗留（等用户拍板）**：用户数据类（4 个中文店名：星桥优选店/小飞的百货店铺/南星/QA测试店铺 + 买家昵称）按语言翻译——方案=Store.i18nJson.name 预翻译 + DynamicText kind=\"store-name\" 接入；昵称需按需翻译。**用户已确认的优先级**：数据类先查现状（商品标题 7 语言数据早已全量存在，缺的是渲染接入 productTitleI18n 只 4 处页面在用）——**→ 已拍板\"123 全做\"（2026-08-08 末），最终落地不是 i18nJson 预翻译，而是复用 UiTranslation 动态词典（cron 补店名/昵称源 + 缺条人工 upsert）+ DynamicText 渲染接入，完整闭环见 22.12**
- **通用教训：\"扫描一次修完全部残留\"的漏网重灾区 = 含 { 变量行 + JS 字符串 + 模块级常量渲染**——三类都不在纯文本节点扫描覆盖内，用户报残留时先按这三类 grep 再报方案

### 22.12 动态内容翻译闭环（店名/昵称/用户输入按语言翻译，2026-08-08 用户\"123全做\"）
用户拍板：① 中文店名 ② 买家/卖家昵称 ③ 用户输入（售后描述/留言/评价）全做，并发拉 40-60。**先查现状发现机制早已存在且大部分已工作**——不要新建表/新字段，复用：
```
sync-content-i18n.mjs（每小时 cron 机翻）
  → UiTranslation 表（scope=dynamic，生产已 8800+ 条）
  → /api/i18n/extra（LanguageSync 启动时全量拉取动态词典）
  → DynamicText（data-i18n-dynamic + kind）客户端词级翻译
  → LanguageSync 漏翻上报 translationMiss → cron 消化（自动闭环）
```
- **cron 已覆盖源**：售后 reason（parseAfterSaleReason 逐段 type/description/history/evidence）、消息 body、会话 subject、通知 title/body、保证金 reason/reviewNote、提现 reviewNote、商品/店铺 reviewNote、工单 subject/summary、translationMiss 队列——**2026-08-08 补：store.name + user.displayName**（两行 collect 进词典）
- **词典实测（生产）**：星桥优选店→\"Starbridge Select Store\"、南星→\"Nanxing\"、QA买家2→\"QA Buyer 2\"、员工买家一→\"Employee Buyer 1\"、昨日无数据→\"No data for yesterday\" 全已在（cron 自动闭环）；缺的（北线好物店/小飞的百货店铺）**人工 upsert**（prisma.uiTranslation.upsert where source + i18nJson 7 语言 + scope: \"dynamic\"）
- **DynamicTranslationKind**（lib/dynamic-translations.ts）：generic / product-title / store-name / category / status / operation / logistics / settlement / note——通用动态文本用 `kind=\"generic\"`（或 note）；DynamicText 可 `as=\"strong\"` 透传 props/style（客户端组件才需要 import；服务端组件里也能渲染成 data-i18n-dynamic 属性，翻译由客户端 LanguageSync 完成）
- **渲染接入点清单（英文态动态内容显示原文 = 没接）**：已接 ✅ SellerFundsCenter 店名（store-name）、ChatWindow 消息 body（note，134/151 行）、ChatContextPanel 商品标题（product-title + data-i18n-map titleI18n）、rma 售后（note）、卖家售后详情（status/note/product-title）；本轮补 ✅ BuyerAccountCenter:57 displayName → DynamicText generic、卖家订单详情 buyer/游客/收货人/留言/备注（generic/note + \"· 游客\"键 ui.cn.61）
- **sync 脚本并发**：`SYNC_CONCURRENCY`（默认 20——原 40 大文本批次超时）+ `SYNC_MAX_NEW`（默认 300；手动跑大存量 `env SYNC_MAX_NEW=3000`）；主循环 Promise.allSettled 并发池（**BATCH 5/批**——15 太大 SiliconFlow 翻译慢 115s 超时，2026-08-09 已调 5 + 超时放宽 180s）；**i18n-scan-lib.mjs 的 makeTranslator 已 SiliconFlow 化**（SILICONFLOW_API_KEY 优先 → chat/completions + response_format json_object，原 OpenAI /responses 分支保留）——与 backfill 脚本同模式（22.8）
- **生产数据查询坑（Prisma 模型名，首次查全报错）**：昵称在 `User.displayName`（不是 userProfile 模型）；`AfterSaleCase` 只有 reason 无 description；`Message.body` 不是 content；raw SQL 查表报 \"relation store does not exist\"（Prisma 模型映射表名不同——用 `prisma.store` 客户端 API 而非 raw）；生产 client select 新字段（如 Store.i18nJson）报 library.js 大段错误 = client 未重新生成（schema 改动后 db push 必须 prisma generate，见 21.5）
- **验证**：`prisma.uiTranslation.findUnique({ where: { source } })` 查词典命中 → 渲染处 SSR HTML 含 data-i18n-dynamic → 英文态浏览器实测无中文
- **【2026-08-09 商品参数表残留\\\"无\\\"等——静态兜底文案不在 cron 收集源，手动 upsert 入词典】**：商品详情页参数表（app/products/[id]/page.tsx params_ = `product.specs ?? {类目/发货/库存/SKU}` 兜底 + fallbackBullets）渲染已接 DynamicText（generic/note），但\\\"无/商家发货/现货发售/支持订单物流跟踪/售后期内可提交服务申请/标准款\\\"这类**代码内静态兜底文案 cron 收不到**（cron 只收 DB 自由文本）→ 英文/阿拉伯态显示原文。**修复模式：`prisma.uiTranslation.upsert({ where: { source: 文案 }, update: { i18nJson: { 'zh-CN': 文案, en, es, fr, pt, ru, ar }, scope: 'dynamic' } })` 手动补**（6 条实测 3s 完成，无代码改动无需部署——/api/i18n/extra 全量拉取即时生效）。**代码内静态兜底文案（fallback/默认值/占位）要单独 grep 出来手动补词典，cron 自动收集覆盖不到**；\\\"用户输入/数据按语言显示\\\"先查有无现成动态翻译机制（本项目 = UiTranslation + cron + DynamicText），别新建并行机制
- **【生产表缺 schema 列坑（2026-08-09 实测）】**：schema.prisma 有 `Product.specs`/`Product.detailBullets`（Json?）但**生产表没有这些列**（raw SQL 42703 / Prisma library.js 大段报错）——schema 与生产 DB 不同步（历史遗留，页面走 fallback 不报错）。**凡脚本要查 schema 新字段：先 raw SQL `SELECT 1 FROM "表" LIMIT 0` 或 `information_schema.columns` 验证列存在**，别假设 schema=生产表结构；specs 收集路径直接回滚，兜底文案走手动 upsert 词典

### 22.15 发品翻译秒级化（2026-08-09 用户\"新上架商品翻译做到秒级，切换语言不要迟钝\"）
用户场景：商家新上架商品 → 用户看到商品 → 切换语言要**秒级生效**（不等每小时 cron）。排查与修复实录（commit 2d5d6cf，build51）：
1. **发品翻译链路早已存在但实际是失败的**：`lib/product-i18n.ts` 的 `buildProductI18n`（标题/描述/SKU → 7 语言写 i18nJson）被创建/更新 API 调用（app/api/seller/products/route.ts:134 + [id]/route.ts:98），但 **`lib/machine-translator.ts` 的 `translateToAllLanguages` 只认 `TRANSLATE_API_KEY` + OpenAI `/responses` 协议**（`payload.output[].content[]` 解析）——SiliconFlow/DeepSeek 都是 chat/completions 协议，发品翻译必然失败（catch → undefined → i18n 空）。**改 machine-translator 与 i18n-scan-lib.mjs 的 makeTranslator 同款 SiliconFlow 化**（`SILICONFLOW_API_KEY` 优先 → `chat/completions` + `response_format: json_object` + `payload.choices[0].message.content` 解析，OpenAI/Anthropic 分支保留）——**全项目翻译入口清单：makeTranslator（i18n-scan-lib.mjs）/ translateToAllLanguages（machine-translator.ts）/ backfill 脚本各自独立实现，改了 22.8 的 makeTranslator 不等于改了发品翻译**，用户报\"翻译没生效\"先 grep 每个入口的 baseUrl/endpoint 协议
2. **翻译结果同步写 UiTranslation 词典（秒级切换的关键）**：buildProductI18n 成功时（`Object.keys(result).length`）遍历 title/detail/SKU 名 → `prisma.uiTranslation.upsert({ where: { source: 原文 }, update/create: { i18nJson: { \"zh-CN\": zh, ...map }, scope: \"dynamic\", note: \"product-live\" } })`——DynamicText 动态内容（描述/参数/SKU 名）切换语言即时生效，无需等 cron；`await import(\"@/lib/prisma\")` 动态引入避免顶层依赖；失败 catch 不阻断发品
3. **耗时实测**：SiliconFlow V4-Flash 单请求翻译约 7-30s（服务器侧 29s 实测）——发品 API 同步等翻译为一次性成本（商家上架时等待，之后所有用户秒级切换）；如需发品更快可改异步，但用户优先要\"看到商品时翻译已好\"
4. **验证**：服务器 node 脚本直接 POST SiliconFlow chat/completions 200 + 文案正确；发品 API 产物存在性检查别用 .next/server/app/... 路径（Next 15 chunk 结构不同，ENOENT 是预期）；tsc 0 + home 200
5. **通用模式：\"秒级翻译\"需求 = 数据产生时（发品/创建/提交）同步翻译入词典 + 渲染层读词典**——翻译提前到数据写入路径，用户看到数据时词典已就绪；cron 只兜底存量/遗漏（每小时）；机器翻译入口协议必须统一（SiliconFlow chat/completions），各入口（发品/回填/cron/UI键）独立实现容易漏改

### 22.16 全动态内容秒级翻译拓展：lib/live-dict.ts（2026-08-09 用户\"全部秒级，帮我拓展吧\"，commit 630e200 build52）
发品秒级（22.15）做完后用户要求**所有动态内容**（消息/售后/会话/昵称/审核备注）都秒级。核心 = 通用工具 + 各业务写入点接入：
1. **lib/live-dict.ts 设计**：`ensureDynamicTranslated(source: string | null | undefined)`——非中文跳过（`/[\u4e00-\u9fff]/` 正则）、`inflight Map` 并发去重、词典已有且 **30 分钟内**处理过跳过（**UiTranslation 模型没有 updatedAt 字段，只有 createdAt**——用 createdAt 判断 freshness，写 updatedAt 会 TS2353）、后台 fire-and-forget（**不阻塞业务响应**，调用方 `await import(\"@/lib/live-dict\")` 动态引入避免顶层依赖）、翻译失败静默（cron 兜底）；`ensureDynamicTranslatedAll(sources[])` 批量版
2. **接入点清单（写入即翻译）**：消息 body（`appendConversationMessage`，≤500 字符才翻——聊天长文本限长）、会话 subject（`ensureBuyerStoreThread` 的 `店铺 ${store.name} 咨询` 模板）、售后 reason/description（`orders/[id]/aftersale` 买家申请 + `messages/[id]/actions` 会话退款）、昵称（`auth/register` + `account/profile` 更新）、审核备注（`admin/products/[id]/review` / `admin/deposits/[id]` / `aftersales/[id]` 的 reviewNote）
3. **【本会话最大坑·批量代码注入语法破坏（5 处手动重排实录）】**用 execute_code 脚本往多个文件插入 try/import 块时：
   - **`.replace()` 不做 format 转义**：模板串里写 `{{ ensureDynamicTranslated }}` 想表达单花括号——`.format()` 才转义，`.replace()` 原样保留 → 代码里出现 `{{ }}` JS 语法错误（TS1005）。**模板占位用无歧义 token（如 `__LABEL__`）再 replace，或直接 .format()**
   - **锚点必须精确到完整语句级（含结尾逗号/闭合括号）**：`displayName: name` 这种字段锚点会命中**对象字面量内部**——注入块插进 data 对象里语法炸（TS1136）；`reviewNote:`（值在下一行）同样中招。**锚点用整行完整语句**（`const x = await prisma.xxx.update({...});` 或 `字段: 值,` 含逗号），注入块放语句**之后**（对象外）
   - **全文件 `{{`→`{` 批量修复危险**：只对无 JSX 的 lib 文件安全（JSX 的 `style={{...}}` 对象字面量会被破坏）——本轮 message-repository 是 lib 才侥幸；**修复后必须 tsc 全量 + read_file 检查每个注入点上下文**（本会话 5 处：profile/deposits/products-review/aftersales/message-repository 全部需要手动重排对象结构）
   - **通用模式：多文件批量注入代码 = 锚点用完整语句 + 注入块永远放语句后（对象/参数外）+ 注入后逐文件 read_file 验证 + tsc**；宁可每处手工 patch 也不批量 replace 高风险锚点

### 22.17 资金流水描述翻译 + 翻译通道被 TRANSLATE_PROVIDER 劫持（2026-08-09 用户\"资金记录还是中文\"，commits 605ba7f/2ddcf4e/3f4227c build53+）
用户截图资金记录（余额支付：订单XXX / 买家充值：USDT TRC20 / 上级前端测试充值）英文/阿拉伯态仍中文。三层根因与修复：
1. **渲染层 `data-i18n-raw` = 刻意跳过翻译（首查！）**：BuyerBalancePanel:112 资金记录描述列 `<strong data-i18n-raw>{record.note}</strong>`——**data-i18n-raw 是 LanguageSync 的\"原样输出\"标记**（数据值豁免，见第 3 节），带它的节点永不翻译。**用户报\"某处还是中文\"先 grep 该处有没有 data-i18n-raw**（全局清单：LanguageSwitcher 4/AppleSelect 2/BuyerAccountForms/SellerShippingSettings 4/SellerFundsCenter 2/Admin 若干——多数是数据值豁免正常，资金记录这类要翻的改成 `<DynamicText as=\"span\" value={record.note} kind=\"note\" />` 并补 import）
2. **写入时不入词典**：`appendBusinessEvent`（lib/local-db.ts，资金流水唯一写入点）create 后补 `ensureDynamicTranslated(event.detail)`（live-dict，22.16）；sync 脚本加 businessEvent 收集源（`findMany({ select: { detail: true }, take: 2000 })`）
3. **【最大坑·翻译通道被 .env.local 旧配置劫持】**：症状 = **curl 直测 SiliconFlow 200 但 makeTranslator/机器翻译脚本全 401**（错误 \"Authentication Fails, Your api key: ****aoww is invalid\" 却是 SiliconFlow 文案）。根因：服务器 .env.local 有历史遗留 `TRANSLATE_PROVIDER=deepseek` + `TRANSLATE_BASE_URL=https://api.deepseek.com` + `TRANSLATE_MODEL=deepseek-chat`——`isSiliconflow = !!SILICONFLOW_API_KEY && !TRANSLATE_PROVIDER` 被 PROVIDER 挡掉 → 走 deepseek base + SiliconFlow key = 401。**修复：isSiliconflow 判断去掉 `!TRANSLATE_PROVIDER` 条件（SiliconFlow key 存在即优先），baseUrl/model 同样 SiliconFlow 优先**（i18n-scan-lib.mjs + machine-translator.ts 两处都要改，22.15 说过各翻译入口独立实现）。**调试顺序：curl 直测 200 ≠ 脚本通——先打印 `process.env.TRANSLATE_PROVIDER/BASE_URL/MODEL` 三个变量查劫持**（test-mt2 打印实录）
4. **sync 批次调优（大文本流水全超时）**：资金流水 detail 带唯一单号（每条独立翻译）+ 长文本 → BATCH 15 批 115s 超时（20 批全挂）。**BATCH 15→5 + 并发 40→20 + AbortSignal.timeout 115s→180s**（i18n-scan-lib.mjs）——单轮成功率从 0-15% 提到 40-60%，剩余失败下轮 cron 自动重试
5. **【Prisma 6 坑·String 字段 not:null 过滤不合法】**：`businessEvent.findMany({ where: { detail: { not: null } } })` 报 PrismaClientValidationError（+ 标记期望 String）——Prisma 6 String 标量过滤不接受 null；**改全量 `findMany({ select })` + JS 过滤空值**（与 specs Json 列坑同模式 22.12）
- **验证**：`prisma.uiTranslation.findUnique({ where: { source: detail } })` 命中才翻译；存量流水 67 条只翻 1 条 = sync 还在补（带单号流水量大，多轮 cron 或调大 SYNC_MAX_NEW 续跑）
- **通用模式：\"某类数据不翻译\"排查链 = ① 渲染处有无 data-i18n-raw（跳过标记）② 写入点是否入词典（live-dict/cron 源）③ 翻译通道是否真通（curl 200 但脚本 401 → 查 env 劫持）**——三层缺一层都表现为\"显示中文\"；批量翻译大面积超时先查批次大小/超时时间，别怀疑 key

### 22.18 混合翻译 HybridDynamicText + 语言名不走翻译（2026-08-09 用户\"只翻译中文，数字不用动\"，commit 43f0ebd build54 + b634e37 build55）
用户对资金流水翻译的最后澄清（打断我提速方案时补充）：\"余额支付：订单XXX / 买家充值：USDT TRC20 / 上级前端测试充值 这些只翻译中文啊，后面的数字不用动\"——**不要把带唯一单号/哈希的流水逐条完整翻译（慢且浪费），要模板化：只翻中文段，数字/单号/地址/符号原样**。两件事：
1. **新组件 `components/HybridDynamicText.tsx`**：`CJK_RUN` 正则（`[\u4e00-\u9fff]+(?:[：:、·，,。.!！？?（）()\s-]*[\u4e00-\u9fff]+)*`）把文本拆成 [中文段 | 非中文段] 交替——中文段走 `<DynamicText kind=\"note\">` 词典翻译，非中文段（单号/TRC20 哈希/数字）原样 `<span>`；全英文文本直接返回原样（`!/[\u4e00-\u9fff]/.test(source)` 短路）。**资金流水（BuyerBalancePanel note 列）等模板类动态文本一律用 HybridDynamicText，别用整条 DynamicText**——整条匹配词典要求每条带单号流水都有独立翻译（量大有且慢）；拆段后命中模板词典（如\"余额支付：订单\"）秒级生效
2. **模板词典补 9 条 × 7 语言（手动 upsert UiTranslation，3s 完成无需部署）**：余额支付：订单 / 买家充值：USDT TRC20 / 上级前端测试充值 / 买家充值 / 提现申请 / 订单结算 / 平台后台充值 / 确认收货后结算 / 已删除（原状态：已上架）——**凡是\"中文模板前缀 + 动态后缀\"的流水/通知文案，把纯中文前缀部分手动补进词典即可全覆盖**，这是 22.12「代码内静态兜底文案手动补词典」模式在流水场景的变体
3. **【22.11 反转·语言切换列表语言名不走翻译（commit b634e37）】**：用户要求\"切换语言列表里面的语言保持不要走翻译机制\"——LanguageSwitcher（触发按钮 strong/small + 下拉 menu）和 BuyerAccountForms:114 默认语言下拉的 option，**去掉 labelKey/shortKey 的 data-i18n 引用，改 `data-i18n-raw` 显示 item.label/item.short 原文**（各语言显示自己的母语名：中文/English/Español...，不随当前语言翻译）。22.11 加的 labelKey/shortKey 体系**被用户反转**——语言名在切换器里是\"数据值豁免\"（第 3 节 AppleSelect 同款），语言名翻译键留在 translations.ts 不引用即可。**教训：\"语言名翻译\"这种方案用户试用后可能反转——语言切换器的语言名永远显示母语原文是国际惯例，直接按原文做**
4. **sync 最终调优（BATCH=1 单条并行）**：大文本流水批次翻译链路 = BATCH 15（40 并发 115s 超时全挂）→ 5（成功率 40-60%）→ **1（单条并行 20 并发，每条独立请求 7-30s，不再批次等待放大延迟）**。**通用模式：翻译慢的瓶颈常是\"批次内最慢一条拖全批\"（5 条 × 6 语言输出 = 大响应），单条并行 + 高并发吞吐反而更高**；SiliconFlow 无并发风控（100 实测全过），单条并行是安全选择
5. **模型速度实测（服务器侧 2026-08-09）**：`deepseek-ai/DeepSeek-V4-Flash` 单请求 ~16s（翻译含 6 语言输出）；`Qwen/Qwen3-30B-A3B-Instruct-2508` / `Qwen3-235B-A22B` 请求 400（模型名/配额不可用）——**换快模型前先服务器单请求实测，别假设模型名可用**（SiliconFlow /v1/models 列表里有 ≠ 可调用）
6. **SSH 断连重试模式**：paramiko 上传偶发 `10054 连接被强制关闭`/`Error reading SSH protocol banner`（服务器/网络抖动）——**重试 3 次 + sleep 10 通常成功**，不要一次失败就放弃部署；长会话中途 SSH 失败属正常抖动不是配置问题

### 22.19 翻译"慢"的真相 + crontab 编辑坑 + 翻译体系全景图（2026-08-09 用户"为什么翻译这么慢"/"捋一遍全部翻译机制"）
用户两个问题：① 为什么翻译这么慢 ② 捋一遍现在已经有的全部的翻译机制和逻辑脚本。回答要点（完整图见 `references/translation-system-map.md`）：
- **翻译慢的根因 = 调度频率不是 API 速度**：动态内容（消息/售后/店名/昵称）靠 cron 周期批量翻译，新内容最长等一个周期；静态 UI 键和商品标题 i18nJson 是预翻译秒切。**秒级需求必须走"写入即翻译"（22.15 发品 + 22.16 live-dict），cron 只兜底**。用户感知"切换语言没反应"先查数据产生时刻到 cron 运行时刻的窗口
- **cron 频率已优化**：sync-content-i18n 10 分钟 → 2 分钟（`crontab` 改 `*/2 * * * *` + flock 防重入已就位；SiliconFlow 便宜无需担心频率）
- **【crontab 编辑事故·sed 行内替换必炸】**：`sed 's|*/10 * * * * cd ...|*/2 ...|'` 的 `*` 被 sed 当通配 → 匹配错乱 → crontab 变垃圾行。**安全做法：完整 crontab 内容写文件 sftp 上传 → `crontab /tmp/xxx.txt` → 验证 `crontab -l | grep -c '^\\*/'` 计数**。改生产 crontab 别用 sed 单行替换
- **翻译体系全景（盘点定稿）**：① 静态 UI 键（translations.ts ~800 键 × 7 语言，data-i18n + getTranslation）② 发品即翻（buildProductI18n：标题/描述≤300字/SKU名 → i18nJson + UiTranslation，挂创建/编辑 API）③ 动态内容写入即翻（live-dict ensureDynamicTranslated，挂 8+ 处 API）④ cron sync 兜底（sync-content 2 分钟 + backfill 10 分钟 + sync-i18n 每日）。渲染：LanguageSync（/api/i18n/extra 全量词典 + 漏翻上报）+ DynamicText（9 kinds）+ HybridDynamicText（中文段/非中文段混合）。通道：machine-translator.ts + i18n-scan-lib makeTranslator + backfill 各自独立实现（SiliconFlow 优先）
- **【唯一真缺口·Product.specs 产品参数翻译数据缺失】渲染已接 DynamicText（详情页 params_）但发品/backfill/sync 都没收集 specs（发品只翻 title/detail/skuItems）——用户原始痛点"产品参数部分文字翻译转化不了"的根因。修复 = 三处各加几行（发品 API + sync 收集 + backfill）。⚠️ **生产表无 Product.specs/detailBullets 列**（schema 有但生产 DB 没有，raw SQL 42703）——写收集逻辑前先验证列存在（22.12 同坑）
- **通用模式：用户问"为什么 X 慢"先分环节定位（哪个阶段耗时/等多久），别只归因 API 速度；用户问"捋一遍已有机制"先查代码事实（grep 引用/读源码）再给全景，别凭记忆——本会话"方案 A 写入即翻译已做过了"就是用户纠正我"我记得不是已经做过了吗"（live-dict 22.16 确实早已挂钩）**

### 22.20 前端全内容秒级翻译闭环收尾（2026-08-09 用户"全部并发去做+速度最快"，commits ff97289/09344cb builds 46/47）
用户目标：买家端+卖家端前端**所有显示内容**秒级同步翻译、切语言零卡顿、零遗漏（不管原文中文/英文/其他语言）。并发并行策略：**先把回填/清理脚本部署到服务器后台跑（最耗时），同时本地改其余代码**。本轮新增三件事 + 存量盘点定稿：
1. **按需实时翻译兜底（report-miss 路由升级，最后防线）**：原 report-miss 只写 TranslationMiss 表等 cron；**升级为"写队列 + 实时 SiliconFlow 翻译入 UiTranslation + 返回结果给客户端立即生效"**——`app/api/i18n/report-miss/route.ts`：`translated`（已入库集合）之外 `need` 数组 `Promise.all` 并发 `translateToAllLanguages({ text: source })`（单次 `MAX_LIVE=8` 条防 POST 超时），upsert 后返回 `{ ok, translations }`。**LanguageSync.tsx 的 miss flush fetch 从 `.catch(() => {})` 改为读响应**：`.then(data => data?.translations && registerDynamicEntries(data.translations) + applyDynamicElements(currentLanguage(), true))`——**页面无需刷新/等 cron，漏翻中文秒级补上**。注意：`applyDynamicElements(normalizedLanguage, onlyNonChinese)` 是重翻动态元素的主函数名；当前语言函数叫 `currentLanguage()`（不是 getCurrentLanguage——TS2304）；`registerDynamicEntries` 在 lib/dynamic-translations.ts（合并本地词典 + 重建 sourceTerms）
2. **词典 localStorage 缓存（切语言零卡顿）**：extra 词典 ~1.5MB（9269+ 条 × 7 语言）每次加载全量拉取 → LanguageSync 加 `DICT_CACHE_KEY = "qav-dynamic-dict-v1"`：**先读 localStorage 缓存注册 + scheduleApply（首屏秒读），后台再 fetch /api/i18n/extra 增量刷新 + 写缓存**（缓存损坏 try/catch 忽略走网络）。静态键翻译不受影响（内存中）
3. **商品翻译存量覆盖实测定稿（数据查清，缺口比预期小很多）**：title 6997/6997 七语言 ✅、detail 6956 ✅、**SKU 规格名 ProductVariant.i18nJson 74305/74305 全翻 ✅**（`Product.i18nJson->skuNames` 是 0 但那是查错位置——SKU 翻译存在变体表）、subtitle 0 数据（无内容不用翻）、specs 仅演示数据（生产走 fallback 参数 `{类目/发货/库存/SKU}`）→ **真实缺口 = 3 个 fallback 词（类目/发货/SKU）缺词典**（库存/商家发货已有）→ 手动 upsert 7 语言 3s 完成；TranslationMiss 2553 条 `SYNC_MAX_NEW=4000` 手动跑一次 + cron 2 分钟清空（pending=0）
4. **【新坑·全翻批次 data-i18n 属性错位】**：卖家订单筛选 `<option value="all"> data-i18n="ui.fix.71"全部字段</option>`——**data-i18n 被插到 `>` 外面成了文本节点内容（属性失效，SSR 露中文）**。修复：属性移回标签内 `<option value="all" data-i18n="ui.fix.71">全部字段</option>`；**全库排查同类误伤：`grep -rn '"> data-i18n=' app/ components/`**（本轮只此 4 处）。**批量脚本插属性后必须 grep 校验属性位置（`<tag data-i18n=` 而非 `> data-i18n=`）**
5. **零遗漏验证闭环**：SSR 全页复扫（买家 7 页 + 卖家 6 页，剔除 data-i18n 节点）全清；店名"北线好物店"SSR 露原文属正常（DynamicText 客户端翻译 Northline Goods Store）——**复扫排除已知动态内容**；TranslationMiss pending=0 是"无遗漏"的量化证据
- **通用模式："全部并发去做"的并行执行 = 数据回填/清理类任务先后台启动（nohup + 日志），同时改代码/翻译/插键，最后统一 tsc+提交+部署**；"零遗漏"的量化标准 = ① SSR 复扫 0 残留（分静态/动态两档）② miss 队列 pending=0 ③ 存量数据覆盖表（各字段计数）——三样都过才算闭环

### 22.21 非中文源翻译漏洞修复（2026-08-09 用户贴 PDP store card 指出店名/店铺介绍切语言不翻译）
用户贴出 PDP 店铺卡 HTML：`<h3 data-i18n-dynamic="Etoile Wear" kind="store-name">` + 英文店铺介绍 `<p data-i18n-dynamic="The platform has completed..." kind="note">`——**切西语/法语时都不翻译**。这是"任何语言原文都可切换"（用户 22.9 明确要求）的漏洞：
- **根因①：三处过滤全部只认中文源**——`components/LanguageSync.tsx` reportTranslationMiss 的 `chineseTextPattern.test(value)`、`scripts/sync-content-i18n.mjs` collect 的 `CJK.test(value)`、`app/api/i18n/report-miss/route.ts` 的 `CJK.test(item)`——**非中文原文（英文店名/英文介绍/西语消息）一律不进翻译体系**（词典只有中文源条目）。之前的 SSR 复扫只查"英文状态下的中文残留"，英文原文在英文态本来就显示英文，所以从没暴露；用户实际切西语才发现。**修复：三处统一放开为 `/[A-Za-z\u4e00-\u9fff]/`（任意字母/中文源）+ 排除数据行（`\d{6,}|@|https?:\/\/`），源长 2-190（sync collect 上限 400）**
- **根因②：静态键值被 DynamicText 包住绕过翻译**——PDP 原 `note: product.storeNote ?? getTranslation(currentClientLanguage(), "ui.sel.101")`（27 行把静态键翻译值算进 store.note）再 `<DynamicText value={store.note} kind="note" />` → 静态键翻译机制被架空（客户端切语言查词典"英文原文"未命中 → 永不翻）。**修复：`note: product.storeNote ?? null` + 渲染 `store.note ? <DynamicText as="p" value={store.note} kind="note" /> : <p data-i18n="ui.sel.101">...原文...</p>`——静态键 fallback 直接 data-i18n 标记，不进 DynamicText**
- **【Prisma 6 严格校验坑·.mjs 脚本无类型检查】给 sync 补 storeNote 收集时 `prisma.product.findMany({ where: { storeNote: ... } })` 运行时崩溃（library.js 大段错误）——schema 的 Product 根本没有 storeNote 字段**（PDP 的 product.storeNote 是 repository 扩展对象，非 DB 列）。**写查询前先 `grep -n "storeNote" prisma/schema.prisma` 验证字段存在**（.mjs 编译期不报，只有运行时炸）；删该行即恢复
- **英文店名批量回填（73 个 × 7 语言）**：store.name 收集放开后 collect 有遗漏（existing/coverage 判断），直接手动脚本：`store.findMany({ select: { name } })` → 非全中文名（`!/^[\u4e00-\u9fff]+$/`）→ `uiTranslation.findUnique` 缺则 SiliconFlow 翻译（prompt 同 22.8 店名模式：7 语言 + 拼音化中文品牌 + 品牌可识别）→ upsert scope=dynamic。实测模型按规则处理：**Etoile Wear → es "Estrella Wear" / fr "Étoile Wear" / ru "Звезда Wear" / zh "星装"；纯品牌 Bloom & Bear → 保持原文**（合理，勿强制全翻）
- **【用户点名纠正·临时翻译脚本串行 for-await 太慢】**：73 个店名第一批 8 并发、后续临时脚本写成 `for...of + await` 串行 → 10+ 分钟。用户问"SiliconFlow API 不是可以多线程并发跑吗"——**批量翻译一律用 40 并发池（sync 标准配置），临时脚本禁止手写串行循环**；SiliconFlow 100 并发实测全过（22.8）
- **【node 临时脚本不加载 .env 坑】**：服务器 `node _script.js` 直接跑**不读 .env.local** → `process.env.SILICONFLOW_API_KEY` 为空 → 401 "Invalid token"（第一个脚本因硬编码 key fallback 成功、第二个脚本只读 env 全 401，调试才发现）。**临时脚本要么硬编码 key fallback、要么复用 sync 的 loadEnvFiles 逻辑**；`curl 直测 200 ≠ 脚本通` 先打印 `!!process.env.SILICONFLOW_API_KEY`
- **词典缓存注意**：客户端 localStorage 缓存旧词典（DICT_CACHE_KEY），新翻译入库后**刷新页面（extra 拉取覆盖缓存）才生效**——验证/向用户说明时提醒硬刷新
- **验证**：`uiTranslation.findUnique({ where: { source: 'Etoile Wear' } })` 命中（es=Estrella Wear）✅ + 词典总量增长 + 复扫（排除已知动态内容）
- **通用模式："全部语言内容都可切换翻译"的审计口径**——翻译体系三入口（客户端上报/服务端接收/sync 收集）的**语言过滤条件要统一**（本项目三处独立实现，只放开一处必留洞）；"某内容不翻译"排查链 = ① 渲染处 data-i18n-raw/DynamicText 包静态键 ② 上报/收集过滤是否吞了源语言 ③ 词典是否命中 ④ 翻译通道是否通（22.17）

### 22.22 物流 lastEvent 嵌入 17TRACK 原始 JSON"乱码" + 部署包 git 自我包含事故（2026-08-09）
用户截图总后台物流监管页：商家发货备注（lastEvent）显示 17TRACK 原始 JSON 响应（`{"code":0,"data":{"rejected":[{"error":{"message":"No tracking information at this time."}}]}}`），但商家端没有。两个独立问题：
1. **lastEvent JSON 乱码根因（lib/logistics-provider.ts parse17Track:129）**：`readNestedText(latest) || readNestedText(trackInfo) || readNestedText(rejected) || JSON.stringify(payload).slice(0, 260)`——**readNestedText(rejected) 读不到 error.message 时兜底把整个 17TRACK 失败响应截 260 字符拼进 lastEvent**。商家端显示的是发货时表单快照（SellerFulfillmentForm:56 note = 发货时 lastEvent，干净），总后台读最新查询结果（含 JSON）→ 两端差异。**修复**：rejected 时显式读 `error.message`（`rejected.error?.message`）作可读文案，兜底"17TRACK 暂未查询到物流轨迹"——**外接 API 的原始响应（JSON/英文报文）绝不能当展示文案入库**，必须映射成可读文案或读错误消息字段。**存量清理模式**：`shipment.rawTrackingPayload` 里 `lastEvent.indexOf('{"code"') !== -1` 的行 → 截 JSON 前段 + 拼 `"message":"..."` 可读文案（22 条 3s 清完，纯数据修复无需部署）
2. **部署包 git 跟踪自我包含事故（连续 3 次 tar 解压 EOF 的根因）**：`qav-deploy.tar`/`qav-deploy.tar.gz` 被 `git add -A` 误提交进仓库 → `git archive` 打包时**把 tar.gz 本身打进了包里**（25MB 的 tar 里装着 25MB 的 gz）→ 服务器 `tar xzf` 解压时**把包里的同名 gz 解出覆盖了正在读取的 gz 文件** → `gzip: stdin: unexpected end of file`。**排查信号**：本地 `gzip -t` 通过 + md5sum 一致 + 服务器仍 EOF；tar 包大小异常膨胀（15MB→45MB）。**修复**：`git rm --cached qav-deploy.tar qav-deploy.tar.gz` + .gitignore 加 `qav-deploy.tar*` → 重新打包（25MB→3.6MB）。**通用教训：git archive 打包前 `git ls-files | grep -E 'qav-deploy'` 确认部署包没进 git；SFTP 大文件传输用 1MB 分块写入（`while chunk: f.write(chunk)`）替代单次 put + 服务器 md5sum 比对 + `tar xzf` 验证三步走**（22.13 的 gzip 流程补充）

### 22.23 售后证据 CDN 白名单过滤——证据存不进库（2026-08-09 用户"买家二次售后证据卖家端看不到"）
用户报告：买家申请售后上传的证据材料，卖家端详情页看不到（"点进去没有详情页面，看不到上传证据材料"）。
**排查链（先查数据再下结论）**：① 卖家售后详情页证据卡片渲染存在（`evidenceList(row.evidenceJson) + parsed.evidence`，[id]/page.tsx:46，img src 渲染），qa-seller-1 curl 实测详情页 200 正常 → 不是页面问题 ② 全库 10+ 售后单 `evidenceJson` 几乎全空（仅 2 单有，且是旧格式）→ **证据根本没存进库** ③ 查上传链路：`app/api/uploads/route.ts:65-74`——对象存储就绪时 url = `https://cdn.qavlixor.com/...`（CDN），否则本地 `/api/upload-files/...` ④ **根因：2026-08-07 安全扫描 L3 加的证据白名单只认 `/^\/(?:api\/upload-files\/|uploads\/)/`（本地路径）——CDN URL 全被过滤 → evidence 数组为空 → evidenceJson 存空 → 两端显示"买家未上传证据材料"**
- **修复（commit 2f49e28，两处白名单正则放行自有 CDN 域名）**：`app/api/orders/[id]/aftersale/route.ts:40`（售后申请）+ `app/api/aftersales/[id]/evidence/route.ts:33`（补充证据）→ `|^https:\/\/cdn\.qavlixor\.com\//`。外链（evil.com/裸 IP）仍拒绝——**安全扫描初衷（防外链追踪像素）不变，自有域名放行不算开洞**
- **验证模式**：正则测试清单（CDN 放行 ✅ / 本地路径放行 ✅ / `https://evil.com/pixel.png` 拒绝 ✅ / `http://IP/uploads/x.png` 拒绝 ✅）
- **通用模式：URL 白名单（安全过滤）必须与当前存储架构同步演进**——引入对象存储/CDN 后，凡是"上传文件 → 存 URL → 白名单校验"的链路（售后证据/审核材料/头像/物流面单）都要 grep 白名单正则补自有 CDN 域名；**"某端看不到上传的材料"排查 = ① 渲染处存在性 ② 库里有没有（全库计数）③ 写入时 URL 被什么过滤了**——多数情况数据压根没存进去，不是渲染 bug
- **已核实的渲染链路（勿重复排查）**：卖家售后详情页（evidence 数组 + `/^(\/|https?:)/` → img）+ 买家 rma 页（app/account/rma/page.tsx:73 同款读法）都能显示 CDN URL；补充证据 API（evidence route）把新证据 merge 进 evidenceJson + reason 追加 history（appendAfterSaleHistory），ACTIVE_STATUSES = 商家处理中/seller_reviewing/已拒绝/平台介入 才可补

### 22.24 买家订单详情页中文残留（2026-08-09 用户截图英文态订单详情，14 键 × 7 语言）
用户截图 https://qavlixor.com/account/orders/XXX 英文状态下仍有中文：确认收货（黑按钮）/联系商家/申请售后/查看售后/物流信息/收货人/联系电话/收货地址/付款状态/交易凭证 + 订单时间线（拍下商品/买家付款/商家发货/确认收货/交易成功/已完成）。这类"每行都含 {order.xxx} 变量"的页面是 22 节首轮脚本"含 { 行整行跳过"的漏网重灾区（22.11 修过一轮但按钮层/组件层/时间线又漏）。
- **修复（commit a6cff16）**：补 14 键 × 7 语言（ui.cn.80-88 文案 + ui.cn.89-93 时间线；确认收货复用已有 ui.sel.320，SiliconFlow 翻译 9+5 键）→ 渲染接入三处：
  - `app/account/orders/[id]/page.tsx`（服务端组件）9 处 `<span>中文</span>` → `{getTranslation(currentClientLanguage(), "ui.cn.N")}`——**⚠️ 2026-08-09 用户反馈该方案切语言需二次刷新（getTranslation SSR 固化，客户端 LanguageSync 不更新），已按 22.26 改回 data-i18n——服务端组件文案一律 data-i18n，勿再用 getTranslation SSR 直译**（22.24 当时的判断被用户实测反转）
  - `ConfirmReceiptButton.tsx`（客户端）：硬编码 `"确认收货"` → `getTranslation(..., "ui.sel.320")`（saving 态 ui.sel.319 已有）
  - `OrderProgressSteps.tsx`（客户端）：steps **数组里的 label** 全部 getTranslation（拍下商品/买家付款/商家发货/确认收货 ui.sel.320/交易成功）+ closed 态 24 行 `<strong>拍下商品</strong>` + 46 行 `"已完成"` fallback——**数组/对象里的 label 也要翻，别只翻 JSX 文本节点**
- **【插键锚点法·多语言包批量插入】**：zh 插 ui.cn.80-93 后，其他 6 语言逐个语言包定位——**锚点 = 该语言块特有的 ui.sel.320 值行**（en "Confirm Receipt" / es "Confirmar recepción" / ru "Подтвердить получение" / **ar " تأكيد الاستلام" 带前导空格**，锚点字符串必须带空格否则匹配不到），从锚点行**往回**找最近的 `"ui.cn.79"` 行在其后插入（找不到插锚点行前）。插入后 `grep -c '"ui.cn.80"'` 必须 == 7
- **验证受限场景**：qa-buyer-1 生产登录 401（QaTest!2026/QavTest@2026 都失败——QA 账号已禁用/改密，与 22.10 记录一致），无法自动化验证登录态订单详情 → 以 tsc 0 + 键 7 语言齐全 + SSR 直译逻辑为准，**告知用户硬刷新（Ctrl+Shift+R）验证**；查订单归属买家：`prisma.order.findFirst({ where: { orderNo }, select: { buyer } })`（本轮该订单买家是 qa-buyer-1 而非 2/3）
- **通用模式：订单详情类页面（每行含变量）残留 = 文本节点扫描永远漏**——补翻覆盖三处：JSX 文本节点（含 { 行）→ JS 字符串/数组 label → 客户端子组件（按钮/时间线/进度条），子组件独立 grep 才能兜住；~~服务端页面已有 getTranslation 用法时可继续用（SSR 直出）~~ **已被 22.26 反转：服务端组件文案一律 data-i18n（切语言即时），勿再用 getTranslation SSR 直译**
- **【插键前查键占用坑】给\"已确认收货\"找键时误用 `ui.sel.321`（已被占用 = \"取消失败，请稍后重试。\"）** → 每个语言包出现 2 个 ui.sel.321，JS 对象重复键后面覆盖前面（翻译表被污染）——**补新键前必须 `grep -n '\"新键名\"' lib/translations.ts` 确认键号未被占用**（本轮改 `ui.cn.94`）；清理重复键 = 删误插的 7 处 + 用新键号重插
- **【确认收货按钮状态简化（用户\"已确认收货 5 个字冗杂\"）】**：确认后按钮本身直接变\"已确认收货\"（disabled），不再弹\"已确认收货。\"消息（ui.msg.37）——`ConfirmReceiptButton` 加 `confirmed` prop（页面传 `Boolean(order.receiptConfirmedAt)`），按钮文字三态：confirmed ? ui.cn.94 : saving ? ui.sel.319 : ui.sel.320；确认成功 `setMessage(\"\")` 不弹消息。**通用模式：状态性按钮的\"完成态\"直接由按钮文字表达（按钮变体），别在按钮旁再挂消息/标签重复**

### 22.25 卖家售后列表"买家补充材料"徽标 + 订单详情顶栏居中（2026-08-09 用户两次小需求）
1. **二次售后列表提示（commit b6c7326）**：用户反馈\\\"买家二次申请售后（补充材料），卖家端列表无提示，只有点进详情（时间线）才能看到，易遗忘\\\"。实现：
   - **判定（零新字段）**：`app/seller/aftersales/page.tsx` rows 构造里 `parseAfterSaleReason(item.reason).history.filter(h => h.actor === \"买家\")`——reason 串的时间线（`｜处理：[买家 时间] ...`）有买家 actor = 买家补充过材料（appendAfterSaleHistory 写入的）
   - **【2026-08-09 重大坑·actor 是中文标签不是英文码】`parseHistoryEntry`（lib/aftersale-reason.ts:47-50）解析 HISTORY_PREFIX（`/^\\[(商家|平台|买家)\\s+.../`）的 `match[1]` 是**中文标签**（\\\"商家\\\"/\\\"平台\\\"/\\\"买家\\\"）——写成 `h.actor === \"buyer\"`（英文）**永不匹配**，徽标/文案全不显示（用户反馈\\\"这个没改动\\\"）。**判定/比较必须用中文标签**（与 appendAfterSaleHistory 的 ACTOR_LABELS 一致）；同一 session 该 bug 在 page.tsx 部署后仍\\\"没生效\\\"，生产验证：`afterSaleCase.findMany({ where: { reason: { contains: '｜处理：[买家' } } })` 确认数据含买家 actor
   - **类型**：`AfterSaleCardRow` 加 `supplemented: boolean` + `supplementCount: number`
   - **渲染**：SellerAfterSalesList as-top 区（状态标签后）`{row.supplemented ? <span className="as-supp" data-i18n="seller.aftersalesList.supplemented">买家补充材料</span> : null}`——**data-i18n 键补 7 语言**（锚点法：找各语言块的 `seller.aftersalesList.empty` 行——每语言块恰好出现 1 次共 7 次，第 2-7 个位置按 en/es/fr/pt/ru/ar 顺序插）
   - **CSS**：`.as-supp` 橙色警示胶囊（`background:#FFF7E6; border:1px solid #FFD591; color:#D46B08; border-radius:999px; font-size:11.5px`）
   - **通用模式：\"列表看不到 X 的二次状态\"= 从现有数据推导状态标记（本项目 = reason 时间线 actor），不加字段不加表**；售后/工单/审核类列表都可以复用\"时间线里有某角色新记录 → 列表行加警示徽标\"模式（用户明确说\"卖家处理售后会遗忘\"——列表页是所有待办信息的默认入口，二次动态必须上列表）
2. **订单详情顶栏（两次调整，最终版 space-between+padding，commit 4b39b62 + ba46eff）**：用户先截图圈\"订单号/下单时间（左）\"和\"返回订单列表（右）\"太靠两侧 → 改 `justify-content: center`（居中靠拢）→ **部署后用户反转：\"订单号和下单时间，靠左，返回订单列表靠右，但是不要贴边，与表格白边保持适当距离，上下也要居中\"** → 最终版 `.buyer-portal .bod-topbar` = `justify-content: space-between` + `padding: 2px 8px`（不贴边留白距）+ `align-items: center`（上下居中）+ `flex-wrap: wrap`。**通用模式：页面顶部信息条用户嫌\"靠两侧\"先试 center，但\"靠左+靠右但不要贴边\"= space-between + 左右 padding——用户描述\"不要贴边\"就是要有内边距，别只改 justify-content**；顶栏类布局小改动直接改部署让用户确认，可能一轮反转（center 方案被否）
3. **"已拒绝+买家补充"提示升级（commit e3f1c7e，用户"已拒绝-买家可申诉 买家提交补充材料后，改为买家已补充证据材料 提醒商家去跟进"）**：`app/seller/aftersales/page.tsx` 的 `timeoutText` 三元链加档——`item.status === "已拒绝"` 且 `supplemented`（第 1 条的 buyerSupplements）→ 显示"买家已补充证据材料 · 请跟进处理"（替代"已拒绝 · 买家可申诉"）+ `timeoutRed: item.status === "商家处理中" || ("已拒绝" && supplemented)` 标红。**const supplemented 必须定义在 return 语句前（对象字面量属性位置不能放 const 声明，TS 语法错，本会话先写错再修正）**——**通用模式：列表状态文案是"状态 × 附加条件"二维组合时，条件布尔提前到 return 前，三元链只引用布尔**

### 22.26 切语言需二次刷新 = getTranslation SSR 固化坑（2026-08-09 用户反馈黄圈按钮 + 服务端直译方案反转）
用户反馈买家订单详情页：**切语言后只有 ConfirmReceiptButton 变了（且要二次刷新），联系商家/申请售后/查看售后等按钮切换不过来**。根因与最终修复（commit ba46eff，build 已部署）：
- **根因：`getTranslation(currentClientLanguage(), key)` 在服务端组件里是 SSR 固化值**——页面 HTML 渲染时按当时语言算好，客户端 LanguageSync 切语言只处理 `data-i18n` 元素，**SSR 固化的文本不更新 → 必须刷新（SSR 重跑）才变**。\"二次刷新\"= 第一次刷新更新 localStorage 触发的重渲染链路延迟。**22.24 教的\"服务端页面已有 getTranslation 用法时照用 SSR 直译\"是错的——直译首屏对，但切语言不即时，用户要的是秒级切换**（22.9 用户原话\"切换语言不要卡顿不要迟钝\"）
- **最终修复方案（三处）**：
  1. **服务端组件文案一律 `data-i18n`**（不是 getTranslation）：`<Link data-i18n=\"ui.cn.80\">联系商家</Link>`、`<h2 data-i18n=\"ui.cn.83\">物流信息</h2>`、`<span data-i18n=\"ui.cn.84\">收货人</span>`——**data-i18n 直接挂在 Link/button/h2/span 上即可**（LanguageSync 替换 textContent），无需再包 span；SSR 首屏显示中文原文，LanguageSync mount 后 ~100ms 翻成当前语言（可接受），切语言即时生效零刷新
  2. **客户端组件（ConfirmReceiptButton 等用 getTranslation 的）加语言切换监听**：`const [, setLangTick] = useState(0); useEffect(() => { const h = () => setLangTick(v => v + 1); window.addEventListener(\"qavlixor-language-change\", h); return () => window.removeEventListener(...); }, [])`——**`qavlixor-language-change` 事件是 LanguageSwitcher 切换时 dispatch 的全局信号，所有依赖 currentClientLanguage 渲染的客户端组件都要监听它强制重渲染**（LanguageSync 本身不触发 React 重渲染）
  3. **OrderProgressSteps 时间线 steps 数组**：label 用中文原文 + 额外 `i18nKey` 字段，渲染 `<strong data-i18n={step.i18nKey}>{step.label}</strong>`（data-i18n 键实时翻译）；\"已完成\" fallback 同样 `<span data-i18n=\"ui.cn.93\">已完成</span>`——**数组/对象里的 label 别用 getTranslation（不会随语言重算），用 原文+i18nKey 双字段**
- **验证信号**：用户说\"切换到英文/其他语言需要二次刷新才能切换过来\"= 该页文案是 SSR 固化（getTranslation），按 22.26 三处改 data-i18n/监听
- **通用模式：切语言即时生效的硬性要求下，服务端组件文案一律 data-i18n（客户端实时），客户端组件用 getTranslation 必须配 qavlixor-language-change 监听**；getTranslation SSR 直译只适合\"首屏正确性 > 切语言即时性\"的场景，本项目用户明确要秒级切换所以禁用
- **【最终全局根治 commit 162d893】用户再报"老是点击之后不能一步到位，需要自己手动刷新"**：data-i18n 改造只能覆盖标记过的元素，**全站仍有大量 getTranslation SSR 固化文本（无标记）切语言不更新**。根治 = LanguageSync（挂根布局 app/layout.tsx，全站生效）在 `handleLanguageChange`（LanguageSwitcher dispatch 的 `qavlixor-language-change` 事件）**和 `handleStorage`（跨标签页）里：`scheduleApply(next)`（data-i18n 元素即时翻译）后 `window.clearTimeout(refreshTimer); refreshTimer = window.setTimeout(() => router.refresh(), 400)`（防抖 400ms 自动 refresh）——Next.js 流式刷新保留滚动/表单状态，SSR 固化文本自动重渲染，**用户零操作一步到位**。实现：`import { useRouter } from "next/navigation"` + `const router = useRouter()`（组件内）+ 模块级 `let refreshTimer = 0`（LanguageSync 单例）。链路确认：LanguageSwitcher:52 dispatch 事件 ✅ / LanguageSync 挂 layout.tsx ✅
- **通用模式（全站级兜底）**：根治"切语言要刷新"类问题 = ① 文案层 data-i18n 化（覆盖标记元素）② 客户端 getTranslation 组件配语言监听（覆盖组件）③ **LanguageSync 事件后自动 router.refresh 兜底（覆盖一切 SSR 固化文本，最后防线）**——三层组合才真正"一步到位"，单做①②仍会被无标记的 getTranslation 残留打回原形

### 22.27 test-orders 90 天回填限制已取消（2026-08-09 用户拍板，commit 1f49f18）
用户问\"批量生成订单开始时间需在最近90天内 这个意图在哪里\"→ 告知是 2026-08-07 安全扫描 L4 加的（防污染统计/报表）后，用户拍板**取消**：\"让统计和售后顺应数据，把这个限制取消了，可以随意生成\"。
- **改动（两轮）**：第一轮 `app/api/test-orders/route.ts` 删除 `MAX_BACK_MS = 90天` 校验块（startTime 任意历史时间均可），保留\\\"结束时间不晚于当前+60s\\\"；**第二轮（commit 605269c）用户仍报\\\"不能直接生成订单，提示结束时间不能晚于当前时间\\\"（填了未来 endTime 被拦）→ 连 endTime 限制也去掉**——只剩：① 结束必须晚于开始（顺序校验，填反才报）② 时间格式有效（`Number.isNaN(getTime())` 报\\\"格式无效\\\"）。任意历史/未来时间均可批量生成
- **勿再重新加回任何时间范围限制**（90 天与 endTime 上限都已被用户拍板取消）；未来若用户再问\\\"为什么能生成很久以前/未来时间的订单\\\"按此解释
- **【2026-08-09 时区偏移 9 小时坑·前端 toISOString 依赖浏览器时区 vs 服务器 UTC】**：用户设 23:15-23:20 生成，订单 createdAt 却落 14:15-14:18（早 9 小时）——前端 `new Date(\"2026-08-09T23:15\").toISOString()` 的解析依赖**浏览器时区**，服务器 UTC 环境下解析不一致。**修复（commit b58ffb3）**：前端改传 **Unix 毫秒时间戳**（`String(new Date(startTime).getTime())`，时区无关）→ 服务器 `parseTime` 兼容解析（number / 纯数字串 / ISO 字符串）。**通用模式：跨时区的时间传输一律用毫秒时间戳（epoch ms），ISO 字符串的解析结果取决于解析端时区**——datetime-local 值 + toISOString 的组合在浏览器时区≠服务器时区时必偏移
- **通用模式：安全扫描加的\\\"防污染\\\"类校验用户可能拍板取消（测试数据场景）——用户说\\\"顺应数据\\\"= 接受数据侧代价，只留防逻辑错乱的硬约束（顺序/格式）；同批 L4 的其他限制（售后证据白名单等）未动**
- `references/scheduled-orders-2026-08.md` — **校验订单定时创建逻辑**（2026-08-09）：ScheduledOrderJob/Item 表 + cron 执行器 + 生成核心 lib 提取 + 管理端计划 UI + 四坑（同店分组/CRON_SECRET env/db push generate/按店分组）+ 端到端验证模式
- `references/qa-test-cases-2026-08.md` — **504 条逐项测试用例体系**（C-01~C-200/S-01~S-167/A-01~A-137，docs/qa/ 四文件）：编制方法论（子代理提取交互清单→逐按钮转用例）、用例编号/表格格式、跨端联动章节、三端关键交互事实、QA 账号体系
- `references/seller-pages-map.md` — **卖家端 34 页 + 34 组件全景映射**（路由→组件→交互要点/校验/待接清单 + 交互清单交付格式）
- `references/real-launch-2026-08.md` — **真实上线收尾全记录**（2026-08-07）：pm2 DATABASE_URL 覆盖坑（BOM/sed/症状）、build 缓存坑、AdminUser 密码迁移脚本、买家充值核验化 + 端到端实测模式（DB 直插测试账号）、生产清理（校验单级联删/demo 禁用/nginx）、商品盘点结论、**Cloudflare 源站保护已执行（iptables CF 白名单 + 访问入口变化）**
- `references/security-audit-fixes-2026-08.md` — **三端 26 项缺陷修复状态**（16 已修 / 10 待修 / 2 设计使然 + 通用修复模式 + 接续步骤）
- `references/admin-security-audit.md` — 管理端安全审计完整缺陷清单（2026-08-07，21 项：严重度/位置/场景/修复 + 已确认安全项）
- `references/seller-security-audit.md` — 卖家端安全审计完整缺陷清单（2026-08-07，17 项：严重度/位置/场景/修复 + 已确认安全项）
- `references/security-audit-buyer-2026-08.md` — 买家端安全审计完整缺陷清单（严重度/位置/场景/修复）
- `references/pitfalls.md` — 坑库：@url 链接 404、datetime-local 时区、admin 铃铛 API、dev 崩溃恢复、AdminUser/权限表、买家余额闭环（BuyerWallet/充值/提现/管理端审核）、货币 USDT 化根因、**$transaction catch 陷阱**、新表接入后 KPI 漏计扫描、逻辑缺陷检查清单
- `references/translation-system-map.md` — **翻译体系全景图**（2026-08-09 盘点定稿）：四层翻译机制（静态键/发品即翻/live-dict 写入即翻/cron sync）清单与挂钩点、翻译通道入口表、UiTranslation 词典手动补条模式、**Product.specs 产品参数翻译缺口**（唯一真缺口，修复三处）、生产 crontab 全貌 + sed 编辑坑
- `references/production-deploy.md` — **生产部署全流程**（2026-08 首次实战）：SSH root@202.95.1.135:**12125**（标准 22 全拒，别试）、密码在 `~/.ssh/deploy_pw`、paramiko 连接、备份→git archive→sftp→解压→db push→build→pm2 restart；**cssnano "Unexpected '/'" 构建失败排障**（dev 永不报、二分定位、根因=CSS 注释块长中文+括号→改写纯 ASCII 修）

### 22.13 部署提速：为什么慢 + fast-deploy.sh（2026-08-08 用户"怎么感觉部署生产变慢了"）
- **慢的根因（实测一轮部署 ~3 分钟，构建只占 14s）**：① 构建轮询写死 `sleep 60 + 每 20s 查一次`（构建 14s 却等 ~1 分钟）② 二次 restart 固定 `sleep 20 + 15`（不管服务是否就绪）③ tar 未压缩上传 15MB ④ 多步 SSH 往返（上传/轮询/restart 各 1 个会话）
- **优化（commit bfe9224 `scripts/fast-deploy.sh`）**：① `git archive | gzip` → tar.gz（15MB→4MB，上传快 3 倍）② 构建轮询 5s（`grep -qE "Compiled successfully|Failed to compile|ELIFECYCLE"` 就停）③ restart 后 **curl 200 就绪探测循环**（10s 间隔，就绪即停；二次 restart 同法，不等固定 sleep）④ 服务器端一个 SSH 命令串完
- **本机无 sshpass**（scp/ssh 密码交互不可用）→ 实际操作仍走 paramiko 执行同样逻辑（gzip 上传 + 5s 轮询 + 就绪探测）；脚本留作以后配 ssh-key 手动用
- **【2026-08-09 部署传输坑·SFTP put 大文件偶发截断】**：25MB 裸 tar 经 paramiko `sftp.put` 后 `tar xf` 报 `Unexpected EOF in archive`（残留 512 字节假 tar）；`sftp.stat` 大小校验显示一致却仍失败（put 缓冲/覆盖竞态）。**稳妥流程：`gzip -c qav-deploy.tar > qav-deploy.tar.gz`（15MB→10MB）→ sftp.put → 服务器 `md5sum` 与本地比对一致 → `tar xzf` → rm**；解压失败就重传，别在坏 tar 上反复试。服务器端 tar 解压失败时先 `df -h`（空间不足也报 EOF 类错误）+ `ls -la` 看残留文件大小
- **通用模式：等待型步骤（构建/重启）一律用"就绪探测循环"（轮询日志关键词/curl 200 就绪即停）而非固定 sleep**；传输用压缩包；连续多步部署合并成单 SSH 命令减少往返
- **【服务端组件坑】app/ 下非 "use client" 的服务端页面不能用 `currentClientLanguage()`/`getTranslation(currentClientLanguage(), ...)`**（读 localStorage，服务端无 window → tsc TS2304 或运行时 undefined）——服务端页面的动态文案翻译用 **`data-i18n` 静态标记**（`<span data-i18n="key">原文</span>`，LanguageSync 客户端处理）或 DynamicText（data-i18n-dynamic，客户端翻译）；只有客户端组件才能用 getTranslation(currentClientLanguage(), ...)（本轮 seller/orders/[id] 的"游客"键从 getTranslation 改回 data-i18n span 实录）

### 22.14 购物车下架商品 5 秒内仍可结算 + 列头按钮重叠（2026-08-08 用户反馈+截图）
用户报：已下架商品从购物车结算，**5 秒内仍可下单成功**；购物车列头"金额 (USDT)"与"清除失效商品"按钮文字重叠（截图红圈）。两个独立问题：
1. **下架结算漏洞根因 = 商品目录 60s 缓存**：`getProductCatalog()` → `loadPrismaCatalogCached()`（CATALOG_TTL_MS=60_000）——**商品下架后 60 秒内 checkout/orders 仍用旧缓存放行**；下架/删除操作也没有 invalidateCatalogCache（grep 无调用方）。**修复（commit 5f391a2）**：checkout/orders 在 catalog 校验后，对每个商品**实时 prisma 复查**（`prisma.product.findMany({ where: { id: { in: ids } }, select: { id, status, title } })` + `live.status !== "published"` 拦截）。实测：delisted 商品下单 → 400"商品不可购买：<标题>" ✅
   - **【双层状态映射坑】catalog 的 `product.status` 是中文（"已上架"，转换层），DB 是 Prisma 枚举 ProductStatus（draft/published/delisted）**——实时复查必须用枚举比较（`live.status !== "published"`），用"已上架"比较 tsc 直接报 TS2367（类型无重叠）
   - **【Prisma 字段坑】Product 模型没有 `inventory` 字段**（select 写 inventory → TS2353 Object literal may only specify known properties）——库存校验仍走 catalog（`product.inventory` 是转换层合成字段），实时复查只查 status/title
   - **通用模式：一切"缓存 + 校验"链路（目录缓存/会话缓存/配置缓存）都有窗口期**——资金/订单/状态类校验不能只信任缓存层，关键下单/提现/退款入口对核心字段（状态/库存/余额）实时复查 DB；缓存 TTL 越长窗口越大（本项目 60s 已实测可复现）
2. **列头按钮重叠根因 = absolute 定位覆盖**：`.bct-clear-invalid`（清除失效商品）`position: absolute; right: 16px` 悬在 grid 列头（金额列）上方 → 有失效商品时与"金额 (USDT)"文字重叠。**修复（commit ca9ed8f）**：按钮从 `.bct-cols`（grid 6 列）移到 `.bct-head` 标题行（`{invalidItems.length ? <button...> : null}`），CSS 改 `position: static; margin-top: 8px; border-radius: 999px; color: var(--danger)` 胶囊样式
   - **通用模式：表头/列头里的"条件按钮"（如清除/批量操作）别用 absolute 悬在 grid 上方——放标题行或工具栏**；CSS 改动后要清理 patch 残留（本次 replacement 尾部遗留旧属性块，需二次 patch 删净）

## 生产部署速查（详见 references/production-deploy.md）
- 连接：python paramiko，`root@202.95.1.135:12125`，密码 `~/.ssh/deploy_pw`（22 端口连接级拒绝是常态，直接上 12125）
- 顺序：备份(dev.db+.env*)→ `git archive` 打包 → SFTP 上传 → `tar xf` 覆盖（保留 .env*/node_modules/.next-build）→ `pnpm install` → `prisma generate && db push`（PG，新表纯新增）→ `pnpm run build` → `pm2 restart tiktok-marketplace` → 健康检查 → 操作日志
- **cssnano 构建失败坑**：`Unexpected '/'` 只出现在生产 build（dev 不压缩 CSS），postcss.parse 全过但 cssnano 挂 = 某 CSS 注释块含长中文/括号/`*` 连写触发老解析器把 `/` 当选择器组合符；用 `node_modules/.pnpm/postcss@8.4.31` + `next/dist/compiled/cssnano-simple` 对 CSS 二分定位，修复=注释改纯 ASCII
- **服务器脚本要放项目目录跑**（/tmp 下 require 不到 node_modules）；paramiko 复杂命令写文件传上去执行
- **本地 bash 后台跑 node 用绝对路径**：Hermes terminal 的 background 模式下 `node` shim（/d/node）后台执行必崩（exit 1 无输出，前台正常）；`/d/node22/node.exe` 后台正常。长翻译/脚本任务 = `terminal(background=true)` + `/d/node22/node.exe scripts/xxx.mjs`
- **【2026-08-07 重大坑】生产 pm2 进程 DATABASE_URL 被 .env.local 覆盖 → 全部 Prisma 查询静默失败**：Next.js 加载 .env.local 优先于 .env；生产 .env.local 第 1 行（**带 UTF-8 BOM**）历史遗留 `DATABASE_URL="file:./dev.db"`（sqlite）→ pm2 的 next start 进程 DATABASE_URL=sqlite → provider=postgresql 的 Prisma **所有查询初始化失败**。**症状**：界面/页面看起来正常（API 的 prisma 调用全被 `.catch(() => null)` 静默降级——如登录 staff findUnique 失败 fallthrough 硬编码分支），但 `pm2 logs` 有 `prisma:error ... the URL must start with the protocol postgresql://`；改动登录逻辑后行为不变 = 大概率 DB 全挂。**修复**：删 .env.local 的 DATABASE_URL 行（生产 DB 配置只留 .env）→ pm2 restart。**BOM 陷阱**：`sed -i '/^DATABASE_URL=/d'` 匹配不到 BOM 行（grep -c 仍 1）——先 `sed -i '1s/^\xEF\xBB\xBF//'` 去 BOM 再删行。同根因两面：脚本层已修 loadEnvFiles（.env 覆盖），Next 进程层靠删行
- **【2026-08-07】服务器 build 缓存坑**：tar 解压更新代码后 build，产物可能仍含旧逻辑（Next webpack 增量缓存误判文件未变——曾出现 login 改动在源码/产物 grep 都在但运行时行为旧）。**排障顺序**：grep 服务器源码（tar 是否覆盖）→ grep .next-build 产物（编译是否含新分支）→ 仍不对就 `rm -rf .next-build` 全量重建（29.7s）+ pm2 restart。用 `ls -la` 看产物/BUILD_ID 时间戳与进程启动时间对得上才可信。**【2026-08-08 补充】进程跑旧产物/UI 没上线的完整验证法见 references/production-deploy.md「验证 UI 中文文案（SSR HTML 抓取法）」+「部署后进程跑旧产物（时间戳对照法）」**：组件中文文案 grep chunk 会落空（压缩/转义）——用登录态 node 脚本抓 SSR HTML 验证；`ps next-server 启动时间` vs `BUILD_ID 时间戳`（产物时间 > 进程时间 = 旧产物，再 restart）；同一 build 内 API 新但前端 chunk 旧 = 增量缓存 bug，UI 必须 SSR/浏览器实测
- **【2026-08-08 重大坑】gitignore 误伤 app/api/ 路由 → 生产永远旧版**：`.gitignore` 的 `uploads/` 误匹配 `app/api/uploads/` 目录 → 上传路由**从不进 git → 不进 archive → 生产一直是旧文件**（豁免修复只存在本地 git，生产永远拿不到——症状：豁免"已修+部署"后生产仍 403「商户入驻尚未审核通过」）。**修复**：gitignore 精确化（`uploads/` → `/uploads/`，只挡根目录存储）+ `git add -f app/api/uploads/route.ts`。**通用教训：改完 API 部署前必须验证 tar 包内容**：`tar tf qav-deploy.tar | grep <目标文件>`；排查信号：服务器源码时间戳很旧 + `git ls-files` 无该文件 = gitignore 误伤。详见 references/production-deploy.md「gitignore 误伤 API 路由」
- **真实上线收尾清单（2026-08-07 已全部执行，详见 references/real-launch-2026-08.md）**：①买家充值接真实核验（原"提交即到账"= 无限套现后门，见第 11 节，端到端实测通过）②AdminUser 密码迁移（7 角色随机强密码哈希入库，登录表优先 + 硬编码迁移期回退；密码已交付桌面 txt）③生产清理（30 校验单级联删 Shipment→OrderItem→PaymentTransaction→Order；4 个 demo 账号 updateMany status=disabled；nginx server_name 清旧 IP 后 `nginx -s reload`）④商品盘点（6995 全审核通过 0 占位 0 零价 = 健康）⑤Cloudflare 源站保护**已执行**（iptables 仅 CF IP 段放行 80/443 + 持久化）——**IP 直连 202.95.1.135 已断，访问一律走 https://qavlixor.com/**（买家端）/ seller.qavlixor.com / admin.qavlixor.com；SSH 12125 不受影响
