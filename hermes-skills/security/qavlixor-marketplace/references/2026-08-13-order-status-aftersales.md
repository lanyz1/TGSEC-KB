# 2026-08-13 订单状态机 / 售后体系 / 侧边栏红点 / 翻译拼接键 / HTML预览(本批交付:已签收锁死+自动签收倒计时、发货重复发货修复、售后0显示修复、待售后合理化、支付受限页文案+双层白、保证金翻译、侧边栏红点、厂家报价单)

## 1. 待售后状态语义(用户质疑"没有买家提售后不该有售后"后重构)
- **待售后必须存在售后单**:`app/seller/orders/page.tsx` 的 `displayStatusOf(order, fulfillment, afterSale?)` 与 `matchesOrderFilter(afterSales)` 都要求 `afterSale`(AfterSaleCase 存在)才显示"待售后"/进"退款·售后"tab;状态售后中但无售后单的历史脏数据不再混入。
- **物流异常不再自动置"售后中"**:原 logistics/fulfillment 的 `异常 → 售后中/after_sales_pending` 映射全部改为保持 `运输中/shipped`(异常属运输环节,体现在 shipment.status=exception):
  - `app/api/logistics/[id]/route.ts` toOrderStatus(12行)/prismaOrderStatus(27行)
  - `app/api/orders/[id]/fulfillment/route.ts` orderStatusFromLogistics(25行)
  - `lib/order-repository.ts` syncLogisticsToPrisma 兜底(235行)
- **买家发起售后 API**(`app/api/orders/[id]/aftersale/route.ts` 49行)是唯一入口:订单原子翻转 after_sales_pending + 创建 AfterSaleCase,并发双提交由 updateMany count===1 锁住(409)。

## 2. 售后状态英文码/中文混用(售后工单"全部显示0"根因)
- AfterSaleCase.status 历史混用英文码(`seller_reviewing` 等,买家发起时写入)与中文(`已退款/已拒绝/平台介入/已关闭`,商家/平台动作写入)。
- 卖家端/管理端直接 `=== "商家处理中"` 匹配 → 英文码单永远匹配不上 → 统计 0、详情页英文码裸奔。
- 修复:`lib/aftersale-status.ts` 统一 `cnAfterSaleStatus(status)` 映射(seller_reviewing/seller_processing/pending→商家处理中;platform_reviewing→平台介入;rejected→已拒绝;refunded→已退款;closed→已关闭),卖家列表/详情/管理端统计全走映射;**写入端归一**:买家发起售后直接写中文"商家处理中"。
- 同类兜底:`AfterSaleCase.storeName` 可能存截断/旧值(如 `EchoSail` 而非 `EchoSaila`),卖家侧查询必须 `OR: [{storeName}, {orderId: {in: 本店订单号}}]`(`lib/order-repository.ts` prismaOrderData;注意 Promise.all 内引用 rows 会 TS7022 循环初始化报错 → 拆顺序查询)。

## 3. 订单详情时间线"缺已发货"(售后/退款订单)
- `app/seller/orders/[id]/page.tsx` orderTimeline 原 `shipped = 状态 in [运输中,已签收,已完成,已关闭]` ——不含"售后中/已退款",已发货过的售后订单时间线显示"—"。
- 修复:shipped 判断结合实际物流单号 `trackingShipped = Boolean(fulfillment.trackingNo && !== "待填写")`,`orderTimeline(order, trackingShipped)`;没发货的售后订单仍显示"—"。

## 4. 已签收订单锁死 + 自动签收倒计时
- `autoConfirmAt` 链路:物流更新为已签收时设置 `now + 7天`(logistics route 72行);Order 类型加 `autoConfirmAt?: string | null`,`orderFromPrisma` 带出。
- `components/seller/AutoConfirmCountdown.tsx`(client,每秒 tick,显示"自动签收 · X天 XX:XX:XX";注意 currentClientLanguage 在 SSR 安全,window 判断已内置)。
- 表格:已签收订单操作列 = 锁定标签 + 倒计时 + 查看订单,无发货/物流/取消按钮。

## 5. 已发货订单重复发货/无限改物流单号 bug(双层守卫)
- 后端:`fulfillment` route 状态守卫原来允许 `["待发货","运输中"]`(运输中=补录场景)→ 收紧为**仅"待发货"**可 ship 且 draft 也拒绝;报错文案区分"仅待发货可发货;已发货订单物流信息已锁定"。
- 前端:`SellerFulfillmentForm` 原本**不知道订单状态**(bug 根因)→ 新增 `orderStatus` prop,非"待发货"渲染**只读锁定卡**(承运商/单号/仓库只读展示),无任何输入/按钮。
- 顺手:syncOrderToPrisma 镜像补插状态映射补 `delivered/receipt_confirmed → 已签收`(原来落 else 显示"已完成")。

## 6. 卖家侧边栏红点(badgeKey 体系)
- `components/PortalShell.tsx` NavItem.badgeKey → `navCounts[badgeKey]`,`count > 0 ? <em>{count>99?"99+":count}</em>`;买家端顶部导航仍用 ChatUnreadBadge(保留)。
- 数据源 `app/api/seller/nav-counts/route.ts` 返回 5 计数:
  - orders=待发货数 / aftersales=未完结售后单(status notIn [已退款,已关闭,refunded,closed],storeName+orderId 双口径)
  - notifications=7天内未读站内通知(NotificationMessage readAt null)
  - messages=与**买家**会话未读(buyerEmail 非空) / support=与**平台客服**会话未读(无 buyerEmail)
  - 均排除 `sellerDeletedAt` 软删会话;60 秒轮询。
- 验证法:直接造数(NotificationMessage create + Conversation/Message create)→ 无头查 nav-counts 与侧边栏 em → 标记 readAt/删测试数据清理。Message 表字段是 `body`(不是 content),ConversationType 枚举 buyer_seller/buyer_support/seller_support。

## 7. 翻译拼接键词序坑(阶梯保证金文案"没纳入翻译系统")
- ui.sel.404/405/406 是拼接键(`404 + num + 405 + date + 406`),旧值各语言乱序(英文 "difference1,700USDT, please pay..." 缺空格断句错)。
- **拼接键纪律:每语言拼接后必须通顺**(空格/断句/词序),6 语言逐语言重写;组件内别漏硬编码中文(251行 `"当前保证金差额"` 改 ui.sel.407 键)。
- 生产三件套:translations.ts 6语言 + 组件 getTranslation + **生产 UiTranslation upsert**(`{source, i18nJson, scope:"console"}`),用户说"没纳入翻译系统"时先查生产表命中(scope 分布 console≈245/dynamic≈10k)。

## 8. 生产数据修复模式(135 个假售后订单)
- 排查链:卖家订单管理"售后中"订单 > DB 查 `orderStatus=after_sales_pending` 无售后单(135/136) > afterSalesStatus 分布 pending(非 logistics_exception,排除物流异常源) > 还原脚本:按 shipment 有无单号还原 `shipped`/`awaiting_shipment`,afterSalesStatus→"none"(注意 shipment.orderId 存内部 id 非 orderNo,按 orderNo 查会全空 → 全部落 awaiting_shipment 也合理:发货草稿状态)。

## 9. 本地 HTML 预览 file:// 中文路径打不开 → HTTP server
- `start chrome file:///D:/跨境商城/会话产物/xxx.html`(中文路径)经常打不开/白屏;且 file:// 页面内 file:// 图片被拦。
- 可靠方案:`python -m http.server 8766 --bind 127.0.0.1 --directory <素材根>`(后台),HTML 放根目录、img 用相对路径,`start chrome "http://127.0.0.1:8766/<页面>"`;验证用 python urllib(避免 bash 管道中文 URL 转义坑)。

## 10. 厂家报价单(桌面素材,非商城代码)
- 输入:`C:\Users\Administrator\Desktop\素材商品批量上架.xlsx`(47 品,15 列含运费字段,全部免运费)。
- 规则:拿货价=售价/2 **取整**(int 截断);运费与价格分开:整机/套装 60 USDT、耗材/配件 8 USDT;合计=拿货+运费。
- 品类统计:整机 12 款=12 型号(A/P/H/X 系列,3 套装);耗材 35 款=9 大类(PLA 17/PETG 5/TPU 3/ABS 2/PC 2/PA 2/Support 2/ASA 1/PVA 1)。
- 生成脚本:临时 make_factory_quote.py 输出桌面 `厂家报价单_拓竹47品.xlsx`(序号/标题/品牌/分类/SKU数/售价/拿货/运费/合计+汇总+规则说明)。
- 报价图模板预览:`D:\跨境商城\会话产物\厂家报价图模板预览.html`(A 白底商务/B 深色品牌/C 电商海报),走 http.server 预览;最终批量生成待用户选模板后做(截图或 PDF)。
