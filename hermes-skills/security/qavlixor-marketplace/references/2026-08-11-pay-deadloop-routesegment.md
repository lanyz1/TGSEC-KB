# 2026-08-11 支付链路 + 部署事故（#177-185 知识库）

## ★#185 Next.js 动态段冲突 → 全站 500（最危险，先记）

**症状**：部署后首页/登录页全部 500；PM2 日志刷 `Error: You cannot use different slug names for the same dynamic path ('id' !== 'orderNo')`。

**根因**：同一路径层级不能混用动态参数名。`app/api/orders/[id]/...` 已存在，新建 `app/api/orders/[orderNo]/pay-balance/route.ts` 即触发，**构建期全站崩**。

**恢复三连（缺一不可）**：
1. 本地改名目录（git mv 到 `[id]`，params 解构改 `{ id: orderNo }`）
2. **删服务器残留目录**：deploy.py 是 archive|tar 解压，**不清理多余目录**——旧 `[orderNo]` 目录会留在服务器上继续报错（`rm -rf '/www/tiktok/app/api/orders/[orderNo]'`）
3. **清服务器 .next 缓存**：`rm -rf /www/tiktok/.next`——增量构建保留旧路由 manifest，只删目录不重建还是 500。之后重跑 deploy（全量 build 慢，用 background=true + notify_on_complete）

**预防**：新建动态路由前先 `find app -path "*[xxx]*"` 查同名段；报 slug 冲突先查服务器残留再查 .next。

## #184 支付死循环 + 通道切换

**死循环**：收银台(/pay/[intentNo]，USDT 锁定) 返回 → 订单列表(去支付=PayNowButton 固定 USDT) → 回收银台 → 循环。根因：①intents API 无 method 参数（固定 USDT）②收银台返回写死 `/account/orders`。

**修复链**：
- 收银台底部加「更换支付方式」按钮（order kind + refs 存在时）→ `/account/orders/{orderNo}?changePay=1`
- 买家订单详情 `changePay=1` 时 PayNowButton 渲染 channels 模式（radio 通道选择：USDT/余额/其他-风控提示，复用 checkout/payment-restricted 页）
- 新增余额补付 API `app/api/orders/[id]/pay-balance`：buyerOwnsOrder 校验 → 原子扣减 BuyerWallet（updateMany availableAmount>=total）→ 订单转 paid+awaiting_shipment → syncPaymentForOrder(balance) → 销量+ → 通知（order_paid）→ 运营日志
- 收银台「返回」改跳订单详情（refs[0].ref），refs 空才落列表

## #182 checkout 兜底商品（金额恒 39.9 的另一半）

`app/checkout/page.tsx` 曾有 `fallbackProduct = 第一个有库存商品`（=水豚 39.9）——**无 product 参数时静默塞入 39.9 商品**。修复：无 product 参数直接渲染"暂无可结算商品"提示，不再兜底。

**checkout 取价顺序（已修）**：按 `params.sku` 在 operation.skuItems 中匹配价格；不匹配回落本商品 skuItems[0]；绝不用 product.price（=首变体价，多 SKU 商品会算错成首规格价）。

## #177 提交审核慢到极致

PATCH 主链路同步 `buildProductI18n`（SiliconFlow 单条 11.7s，整品 20-60s）→ 全异步化：`const i18n = product.i18n` 保留旧值，翻译由 `scripts/sync-content-i18n.mjs` cron（2 分钟）后台补，与 POST 同策略。**新增内容字段后 i18n 旧是预期行为，勿加回同步翻译。**

## #178 草稿回填产品参数跑卖点

`parseDescriptionPairs` 原 `pairCount < 3` 整体降级为纯文本（全进卖点框）。放宽为 `pairCount < 2`（≥2 对即启用参数表）。SellerProductForm 的卖点首行拦截校验同步 3→2。注：参数行 label 含冒号/括号等非 `LABEL_PATTERN` 字符仍会全进卖点（isLabelLine 未放宽，保守处理）。

## #179 主页只轮换直营店商品

Product 结构加 `storeKind`（PrismaProductRow.store + include select + productFromPrisma），app/page.tsx 过滤 `storeKind === "self_operated"`。直营店识别：`Store.storeKind === "self_operated"`（lib/direct-stores.ts）。普通商家商品仍出现在 /products 列表/搜索/店铺页。

## #180 草稿品牌/运费模板丢失

- **品牌**：原只拼进标题（composedTitle），回填拆不回 → Product 表加 `brand` 字段独立存储（schema + syncProductToPrisma upsert update/create + POST/PATCH 路由 + productFromPrisma + 编辑页构建 + 表单 useState 初始化 + payload 传 brand）。schema 变更后**本地必须 `pnpm prisma:generate` 再 tsc**（否则 TS2339 brand 不存在）。
- **运费模板**：发布页下拉原硬编码 3 个模板 → 改读 `listShippingTemplates(storeName)`（Store.shippingTemplatesJson），新建/编辑页传 `shippingTemplates` prop；回填从 shippingNote 拆 `运费模板：(.+)`；无模板时兜底内置标准模板。

## #181 保存草稿"点击无反应"

- fetch 无超时无 catch → 网络异常时 saving 卡 true → 按钮永久 disabled。修复：`AbortSignal.timeout(30000)` + `.catch(() => null)` + 失败分支 setSaving(false)。
- 校验失败 notice 原只显示在侧栏完成度区（右下按钮处看不到=像没反应）→ 按钮行正上方红色提示。

## #183 商品审核页图片 tab

原 4 个 span 静态文字（点不动）+ 只显示主图 → 新建 `components/admin/AdminProductGallery.tsx`（client）：按 sortOrder 分组（0=主图 / 1-19=详情 / 20-39=包装 / 40+=资质），带数量、选中高亮、空组隐藏。DB 实测分布：0 约 7001 张、1-19 约 35807、20-39 仅 53。

## 同会话其他修复（简记）

- **卖家订单详情金额**：orderFromPrisma 漏映射 shippingAmount → 详情运费恒 0、商品金额=含运费 total。修复：映射 shippingAmount，商品金额=total-shipping，买家端详情同源同步修复。DB 实测 subtotal+shipping=total（9.99+5=14.99）。
- **卖家订单单价恒 39.9**：fulfillment 映射漏 unitPrice/totalPrice → 详情回落 product.price。补映射（orderItem 有真实单价：39.9/69.9/9.99 各异）。
- **商品审核通过无通知**：review/route.ts 完全无 notify → 通过/驳回发 product_reviewed（卖家），跳转 targetUrlOf 加 product_ → /seller/products，categoryOf 归 system，8 句整句预置词典。
- **三端切页卡顿**：LanguageSync applyLanguage 写 DOM → MutationObserver 再全页重扫 → 自循环 2-3 轮。修复：applyingSilence 静默期 flag（applyLanguage 首行置 true，300ms 后释放；observer 回调开头 if (applyingSilence) return）。★同类组件写入型 observer 都要防自循环。
- **通知提示音**：Web Audio 合成叮咚（E6+B5）；**浏览器自动播放策略=AudioContext 需用户手势** → pointerdown/keydown 一次性预热（ensureAudio+resume）；已读清零时 prevCountRef 同步 0 否则漏响；轮询 60s→30s。
- **运费模板/商品详情等显示一致性**：列表价优先 operation.skuItemsJson[0]（displayPrice），勿用 variants[0]。

## #186 反馈页空提交提示文案张冠李戴（翻译键语义核对）

SellerFeedbackPanel 空提交校验用了 `ui.msg.13`（值="请输入有效的新价格"，商品编辑页的键）→ 提示完全错位。修复：新增 `seller.feedback.contentRequired`（请输入有效的反馈内容）×6 语言。**教训：写校验提示前先 grep 键值确认语义，勿随手复制他页键名；键名相似（msg.13 vs msg.14）不代表语义相近。**

## #187 管理端客服工作台（用户拍板"建"）

- **现状**：卖家消息中心客服会话（seller_support，5 类主题）API 层 admin 早可读可回（conversations/messages requireRole 含 admin，message-repository 将 admin/support 统一映射为 support 客服视角），但管理端无 UI，卖家消息无人可见可回。
- **落地**：`/admin/contacts` 改为双 tab（URL 参数）：默认 `?tab=chat`=客服工作台（**直接复用 ChatWorkspace 传 `role="support"`，零后端改动**），`?tab=forms`=原官网联系表单记录。权限点 service 不变。翻译键 `admin.contacts.tabChat/tabForms` ×6。
- **可复用模式**：管理端要聊天/客服能力时直接复用 `components/chat/ChatWorkspace`（baseHref 传当前页 + role="support"），聊天/发送/已读/快捷回复全走现有 API。

## 补键脚本定稿（防 TS1117 重复键事故）

本次事故：`src.find(anchor)` 从头找 → 6 个语言键**全部插进第一个语言区（zh）** → `error TS1117: duplicate property`。定稿法：`occ = [m.start() for m in re.finditer(r'"键名":', src)]` 收集**所有**出现位置（文件内语言区顺序固定 zh-CN→en→es→fr→pt→ru），按序逐区插入；插后必跑 tsc。失败恢复：`git checkout lib/translations.ts` 后重插。

## SSH 弹窗教训（勿打扰用户）

terminal 工具里直接跑 `ssh root@202.95.1.135 -p 12125 ...` 会触发系统 SSH 密码提示框（用户会被打扰并追问）。**服务器连接一律用 execute_code + paramiko**（密码硬编码进脚本，无弹窗）；需要交互式 SSH 前先告知用户。顺带：terminal 里 ssh 无密钥交互时命令会挂起超时（timeout 120 也救不回），paramiko 是唯一顺滑路径。

## #188 买家余额浮点精度（Decimal→Number 丢精度）

**症状**：余额显示 `196.39999999999998`（应最多两位小数）。
**根因**：API 层 `Number(wallet.availableAmount)`——Prisma Decimal 直接转 JS number 产生浮点噪声（196.4 → 196.39999999999998），前端原样显示。
**修复三层**：
1. **API 边界**：`Number(Number(x).toFixed(2))`（/api/buyer/wallet 返回、提现"余额不足"错误消息里的余额显示等所有 Decimal→Number 展示点）
2. **显示层兜底**：`toFixed(2)`（BuyerBalancePanel 余额、CheckoutSubmitForm 余额通道可用余额——防其他来源的浮点值）
3. 比较/扣款逻辑本身走 Decimal（DB 侧精确），**只修显示与 API 返回，勿动运算**
**同类排查**：`grep -rn "Number(.*availableAmount" app/api/ lib/ --include="*.ts"` 扫全部 Decimal→Number 展示点。

## #189 工单功能删除（用户拍板：半成品无触发入口）

**背景**：对话框"工单"tab 永远空——创建逻辑存在（发消息带 dispute 标记时自动建 supportTicket + system 消息"系统已自动创建客服工单 SV…"），但**全站没有任何入口传 dispute**（消息 API 无该参数；售后升级 escalate 只发 after_sale_escalated 通知、不建工单）→ 死代码。用户问"工单什么时候会有"→ 如实说明半成品 → 拍板"直接给这个工单删了吧"。
**删除范围**：ChatList TabKey 去 ticket、ticket 过滤、工单 tab 数组项、列表工单 badge；message-repository 的 dispute 自动建工单块 + ticketNo() 函数。**保留**：supportTicket 模型/表、disputeFlag 纠纷红标（还在用）、chat.tab.ticket 翻译键（无引用无害）。
**教训**：半成品功能（有逻辑无入口）先如实告知"永远不会出现"，用户倾向直接删（"拍板即删不留占位"）。UI 删除为主、后端死代码同删、DB 模型保守保留。

## #180 补记（第二轮修复：shipFeeMode 回填 + 存量品牌启发式）

- **shipFeeMode 不回填**（首轮漏掉）：useState 固定 `"free"` → 即使用户保存时选了"运费模板"，重新进入显示"免运费"、模板下拉不显示 = 看起来"运费模板消失"。修复：useState 初始化器从 shippingNote 正则拆（`运费模板：`→tpl / `自定义运费`→custom / 否则 free）。**表单里所有 radio 态都要从持久化文本拆回，勿只修下拉数据源。**
- **存量草稿品牌**（brand 列上线前保存的旧数据 brand=null）：启发式从标题拆首词（首词 ≤20 字符、无中文标点、标题含空格才拆）；新草稿走 brand 字段不受影响。
- 验证受限：草稿归属店铺 ≠ 登录会话店铺时编辑页 404（权限隔离正常）——只能 DB 验证 brand 落库 + 代码级确认回填逻辑，向用户说明验证方式。

## #190 购物车账号隔离（同一浏览器多买家账号串车）

**症状**：浏览器 A 账号加购 → 退出 → B 账号登录 → 仍看到 A 的购物车商品。
**根因**：购物车存 localStorage，key 固定 `qx_cart`（跨账号共享）。
**修复（三件套）**：
1. `lib/cart-storage.ts`：key 动态化 `qx_cart:{accountKey()}`（`qx_account` 标识 + 邮箱格式校验，未登录=guest）；结算勾选 `qx_cart_sel:{account}` 同步隔离。所有 `CART_KEY/SELECTION_KEY` 常量引用改函数调用。
2. 登录成功写标识（`components/seller/LoginSubmitForm.tsx` submit 里 `window.location.assign` 前）：写 `qx_account` + **存量旧 key（qx_cart）迁移到本账号 key**（防升级后购物车"消失"）。
3. 登出清除：买家端退出登录链接（BuyerAccountCenter）onClick `removeItem("qx_account")`。
**注意**：前端拿不到 httpOnly cookie 里的邮箱 → 只能靠登录表单的 email 写标识；游客期加购不丢（guest key）。

## #191 购物车数量按"加购数量"而非"购买数量"

**根因**：结账页"返回购物车"链接带 `qty={下单数量}` → 购物车页把该 qty 叠加/写入购物车（/cart?product&qty 会触发 addCartItem），购物车数量被"购买数量"污染。
**修复**：checkout 返回链接改纯 `/cart`（只看不改）。详情页"加入购物车"（addCartItem 叠加）本就正确，勿动。
**同类排查**：`grep -rn "cart?product" app/ components/` 找所有带参进购物车入口，逐个确认 qty 语义。

## 运费模板"消失"类问题排查顺序（用户报数据丢失时）

1. 先浏览器实测完整链路（新建→列表→切页→回来）——本次实测 API 层完全正常（POST 创建 → GET 立即可见 → 切页后仍在）
2. 链路正常 → 提示用户强刷（Ctrl+Shift+R）排除旧 JS 缓存（列表刷新逻辑是近期加的，旧脚本渲染会"消失"）
3. 用户说"发货模板"可能是**两个不同页面**：运费模板（/seller/shipping-templates）vs 发货默认设置（Shipping defaults）——先确认用户指哪个再排查
4. 仍复现才查 DB（shippingTemplatesJson 有没有那条）区分"没保存"vs"渲染问题"

## #192 运费模板结算计算修复（用户反馈：自定义运费只应用包邮门槛 / 按重量默认模板不启用）

**三个根因**（/api/checkout/orders/route.ts）：
1. **取模板取"第一个启用模板"（`tpls.find(enabled !== false) ?? tpls[0]`），不是 isDefault** → 按重量默认模板被其他模板挤掉，完全不生效
2. **只算 `firstFee`（首件）**，没有续件（addFee × (qty-1)）
3. **商品"自定义运费"（编辑商品时设置）完全没被读取**——结算只认店铺模板

**修复**：
- `parseCustomShipping(note)`：正则 `/自定义运费：首件\s*([\d.]+)\s*\+\s*续件\s*([\d.]+).*?满\s*([\d.]+)\s*包邮/` 解析商品 shippingNote（subtitle）
- `calcShipping(subtotal, qty, rule)`：满门槛（freeOver>0 且 subtotal>=freeOver）→ 0；否则 `first + add × max(0, qty-1)`
- 结算循环：**商品自定义运费优先**（同店取第一个带自定义的商品规则）→ 无则店铺模板（isDefault 优先：`tpls.find(isDefault && enabled) ?? tpls.find(enabled) ?? tpls[0]`）
- **productFromPrisma 必须补 `shippingNote: row.subtitle ?? undefined` 映射**——漏了则解析永远 null（catalog 的 Product 之前没这个字段！）
- SellerProductForm 编辑回填：feeFirst/feeAdd/feeFree 用 initialCustomFee 正则从备注拆（此前固定默认值 5/2/50，编辑一次就覆盖用户设置）

**实测验证**：商品设"自定义运费：首件 5 + 续件 2 USDT，满 100 包邮"→ 下单 1 件 → 订单 subtotal 9.90 + shipping 5.00 = 14.90 ✅（此前运费 0）。收银台金额含 0.10 唯一后缀（15.00 显示 = 14.90 实付），核对以 DB 订单为准。

**清理测试数据踩坑**：服务器 prisma client 的 `orderItem/orderPayment` client 属性 undefined（deleteMany 直接报错；$queryRawUnsafe 表名也拿不准）→ **测试订单别强删，留待支付 30 分钟超时自动关闭**；商品字段回改用老模型 `product.updateMany` 恢复。
