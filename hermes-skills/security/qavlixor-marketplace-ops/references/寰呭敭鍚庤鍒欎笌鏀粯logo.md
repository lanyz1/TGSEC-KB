# 待售后状态规则 / 已发货锁定 / 支付官方 logo(2026-08-13)

## 待售后状态机(用户质疑"待售后不应自动出现"→ 修复闭环)

**铁律:订单只有买家发起售后申请才进入"售后中/待售后";任何系统事件(物流异常等)不得自动置售后中。**

### 历史 bug:物流异常自动置售后中
物流状态更新为"异常"(退件/派送失败)时订单被自动翻成 `after_sales_pending` → 卖家端出现大量无售后单的"待售后"订单(生产实测 135 个假售后)。
异常映射散落在 **4 处**,全部要同步改(漏一处就复发):
- `app/api/logistics/[id]/route.ts` — `toOrderStatus()`(local 分支)与 `prismaOrderStatus()`(prisma 分支):异常 → 改 `"运输中"`/`shipped`(shipment.status=exception 单独体现异常)
- `app/api/orders/[id]/fulfillment/route.ts` — `orderStatusFromLogistics()`:异常 → `"运输中"`
- `lib/order-repository.ts` `syncLogisticsToPrisma()` 兜底三元:异常 → `"运输中"`

### 展示层双保险
- `app/seller/orders/page.tsx` `displayStatusOf(order, fulfillment, afterSale)`:待售后条件必须 `afterSale &&`(存在 AfterSaleCase),不能只看订单状态/afterSaleStatus
- `matchesOrderFilter(status, filter, hasAfterSale)`:退款·售后 tab 同样要求 hasAfterSale,filterCounts 与 visibleOrders 调用处都要传

### 售后单归属查询坑
`afterSaleCase.storeName` 可能存**截断/旧值**(如 "EchoSail" ≠ 店铺名 "EchoSaila")→ 卖家订单页 `prismaOrderData` 的 cases 查询必须按订单号兜底:
`where: { OR: [{ storeName }, { orderId: { in: rows.map(r => r.orderNo) } }] }`
(注意 Promise.all 里引用自身 rows 会 TS7022/TS2448,先查 rows 再查 cases)

### 数据修复脚本模式(生产假售后清理)
查 `orderStatus='after_sales_pending'` 且无对应 AfterSaleCase 的订单 → 按 shipment 有无真实单号还原:
- 有单号 → `shipped`(运输中)
- 无单号 → `awaiting_shipment`(待发货)
- 同时 `afterSalesStatus='none'`;shipment.orderId 存的是**内部 uuid 不是 orderNo**,按 orderNo 查 shipment 查不到(别被误导)

### 状态值规范
- 买家发起售后 API(`app/api/orders/[id]/aftersale`)写入 `status: "商家处理中"`(中文),**禁止写英文码 seller_reviewing**
- 历史数据混用英文码 → 读取端统一走 `cnAfterSaleStatus()`(lib/aftersale-status.ts,已建)
- 商家/平台动作 API 写中文("已退款"/"已拒绝"/"平台介入"/"已关闭")✅ 勿动

## 已签收订单锁死 + 自动签收倒计时

**需求**:已签收订单操作列全部锁死(只剩查看订单),并显示自动确认收货倒计时(每秒跳动)。

- **数据链路**:prisma `Order.autoConfirmAt`(物流更新为已签收时写入 = 签收时间 + 7 天,见 `app/api/logistics/[id]/route.ts`);内存 `Order` 类型补 `autoConfirmAt?: string | null`,`orderFromPrisma` 带出 `row.autoConfirmAt?.toISOString() ?? null`;orders/page.tsx 行数据传 `autoConfirmAt`
- **展示**:`components/seller/AutoConfirmCountdown.tsx`(client,每秒 `setInterval` 算剩余,`max(0, target-now)`,显示 `自动签收 · X天 HH:MM:SS`,无 deadline 优雅返回 null)
- **操作列锁死**:`SellerOrdersTable` 已签收(status==="已签收")订单 → 只显示 🔒已锁定 + 倒计时 + 查看订单,去掉物流详情按钮(详情页可看)
- 翻译键:seller.orders.locked / autoConfirm / countdownDay / autoConfirmHint × 6 语言(锚点 seller.orders.logisticsDetail)
- **验证注意**:生产无已签收订单时,可临时把订单改为 `receipt_confirmed` + autoConfirmAt 验证后还原;页面经 CF 缓存会显示旧版本,服务器本地 node fetch localhost:3000 + Host 头才是真相

## 已发货订单锁定(重复发货/无限改单号 bug 修复)

- **后端权威守卫**(`app/api/orders/[id]/fulfillment/route.ts`):`mode=ship` 仅 `"待发货"` 可发货;`mode=draft` 同样锁(已发货/已完结不能存草稿防绕过)。原允许"运输中"补录是 bug 根源
- **前端**:`SellerFulfillmentForm` 加 `orderStatus` prop;非"待发货"整个表单替换为只读锁定卡(🔒 + 当前状态 + 承运商/单号/仓库/发货时限 kv),无输入框无按钮
- 镜像补插行状态映射(fulfillment route 47-52):`delivered/receipt_confirmed → 已签收`(原落 else 显示"已完成"是错的)
- 详情页时间线 shipped 判断:结合物流单号事实(trackingShipped 参数),不看状态——售后中/已退款订单(发过货)时间线才显示"已发货";`Boolean(单号 && 单号 !== "待填写")` 防 TS2345

## 支付方式官方品牌 logo(用户两次纠正后的最终方案)

**用户偏好:不要手绘 simple-icons SVG,要官方品牌 logo 图。** 本地化到 `public/payment-logos/` 防外链失效(大厂 CDN 挡 curl 时用 Wikimedia Commons `Special:FilePath/<文件名>`)。

### 大坑:无内在尺寸 SVG 渲染 0×0
cryptologos 类 SVG 只有 viewBox、**无 width/height** → `img { height:auto }` 时浏览器渲染成 0×0(USDT/Visa 曾全部消失)。
**方案**:`height: size` 固定 + `maxWidth: 34` + `objectFit: contain` + `width: auto`:
- 固定高度 → 无尺寸 SVG 按 viewBox 比例正常渲染
- maxWidth → 横向长 logo(Wise 512×124)不会撑爆被裁切
- 图标盒 `.pm-logo2`:`min-width:38px;max-width:118px` 自适应 + **去掉 overflow:hidden**(38px 固定盒裁切 PayPal/Wise/GooglePay)

### 三端统一
- `components/PaymentLogos.tsx` 组件 API 不变(PmLogoUsdt/PmLogoPaypal/PmLogoWise/PmLogoCard 等),内部改 `<img src="/payment-logos/...">`
- 买家端 BuyerBalancePanel:select 改图标列表(USDT×3/PayPal/Wise),method 提交值不变
- 卖家充值 6 方式 / 卖家提现 4 方式共用组件
- 卡组(visa/mc/amex)缩小横排(高 ≈ size×0.55)适配图标盒

### 验证注意
- 无头浏览器默认俄语(SSR 默认语言,localStorage 键 `globalmart-language`),中英文验证直接读 translations.ts 与 SSR HTML 更可靠
- 服务器本地 `curl http://localhost:3000/... -H "Host: seller.qavlixor.com"` 带登录 cookie 可绕过 Cloudflare 缓存看真实渲染
