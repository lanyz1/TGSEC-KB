# 2026-08-14: 订单生成真实化 + 时区三件套 + 扣库存 + 通知补发

用户拍板链: 定时生成订单时间全挤一起 → 时区不一致质疑(北京时间 vs UTC) → 通知中心要真实文案 → 生成订单也要扣卖家库存 → 待结算明细页+预计到账时间 → 翻译铁律。

## 1. 时区一致性(三件套原则)
- **生产服务器/DB 统一 UTC**(`now()`=UTC, 与北京差 8h)。三层原则:
  1. 存储统一 UTC(timestamp 无时区后缀 = UTC 约定)
  2. 调度执行按 UTC 绝对时刻(plannedAt 到点即执行, 与谁看无关)
  3. 展示按查看者浏览器时区: 前端 `new Date(iso).toLocaleString()`
- **订单号 = UTC 时间戳**: `generateOrderNo(buyerKey, date?)` 首 12 位 yyMMddHHmmss。**定时生成必须传计划时间**(第 2 参), 否则列表页时间全挤在 cron 执行时刻(30s/分钟粒度)。
- **卖家端 orderTimeOf 解析订单号**: 必须 `new Date(Date.UTC(2000+yy, mo-1, dd, hh, mm, ss))` 再 `toLocaleString()`。直接拼字符串 = 把 UTC 当本地显示, 差 8 小时 bug(已修 `app/seller/orders/page.tsx` + `orders/[id]/page.tsx`)。买家/管理端用 createdAt ISO → toLocaleString 正确。
- 定时生成前端提交: datetime-local 传 `{ raw, offset }`, 后端 `Date.UTC(y, mo-1, d, h, mi) + offset*60_000` 转 UTC 存储。
- 排查口径: 跟用户说时间必须换算成用户时区, 否则"时间搞错了"误解(上轮我用 UTC 报"现在 16:35"被质疑)。

## 2. 定时生成 cron 链路(任务不执行排查)
- 执行器: crontab `* * * * * cd /www/tiktok && CRON_SECRET=... flock -n /tmp/qav-sched.lock node scripts/process-scheduled-orders.mjs >> /var/log/tiktok-scheduled-orders.log`(每分钟, x-cron-secret 头调 `/api/cron/scheduled-orders`)。
- 坑1: **process-scheduled-orders.mjs 生产可能缺失**(scripts/ 目录靠部署同步, 没部署过就 fetch failed 静默)→ 所有定时任务不落库。查日志 /var/log/tiktok-scheduled-orders.log。
- 坑2: `scripts/run-scheduled-tasks.mjs`(结算 cron */10)默认只调 `/api/cron/settlement`, 须补 `/api/cron/scheduled-orders`(鉴权是 **x-cron-secret 头**, 不是 Bearer)。改完同步生产该文件即生效(独立脚本, 无需重启)。
- 坑3: 管理端"待执行 0/N"可能**正常**: plannedAt 在未来未到点; 到点后 1 分钟内 cron 自动落库。processed=0 无日志输出属正常。
- 执行器状态机: ScheduledOrderItem pending→done; job pending→processing→done(全部 done 后)。due = `status=pending AND plannedAt<=now AND job.status<>'cancelled'`, take 60。多任务积压时先处理更早 plannedAt 的。
- 验证: psql 模拟 `SELECT count(*) ... WHERE status='pending' AND "plannedAt"<=now() AND job.status<>'cancelled'` — 若 0 而接口返回 processed 0, 先怀疑进程时区/锁。

## 3. 校验订单 → 真实订单生成(对外全真实, 内部保留标记)
- 用户拍板: 管理端"生成校验订单"功能**对外文案全部真实化**, 但 **orderChannel='validation' 内部保留**(库存安全: 生成单曾不扣库存→取消/退款不回补, 见 §4)。
- 改点清单: admin 工作台 hero/焦点卡片、订单监管页按钮、商户列表+详情页按钮、订单列表"校验订单"标签(删)、详情 eyebrow(删)、权限描述、API message、操作日志/业务事件("生成订单")、买家邮箱 `@validation.local`→`{name}@gmail.com` 风格。
- 翻译键(6 语言): `admin.merchants.genTestOrder` / `admin.dash.genOrderBtn` / `admin.dash.focus3Title` / `admin.dash.focus3Detail` / `admin.orders.genTestOrder` / `admin.nav.testOrders` / `ui.sel.241`。

## 4. 生成订单扣库存(2026-08-14 拍板)
- 落库前逐商品 `reserveProductStock(productId, qty, sku)`(条件原子扣减, 并发安全); **任一商品库存不足 → 整单跳过不落库**(返回 skippedByStock, API message 提示"因库存不足跳过")。
- `Order.inventoryDeducted Boolean @default(false)`: 落库成功后置 true。
- **取消/退款回补条件**(3 处: `app/api/orders/[id]/cancel`、`app/api/seller/orders/[id]/cancel`、`app/api/aftersales/[id]`):
  `if (order.orderChannel !== "validation" || order.inventoryDeducted === true) releaseProductStock(...)`
  存量校验单(false)不回补 → 防"库存不减反增"复现; 新生成单(true)回补 → 闭环。
- **schema 改后本地必须 `npx prisma generate`**, 否则本地 tsc 报 TS2339(产物类型旧)。生产加列用 SQL 文件 `psql -f`(`psql -c` 双引号会被 bash 吃, `"Order"`→`Order` 语法错)。

## 5. 生成订单通知(按店合并 + 真实文案 + 存量补发)
- 生成器落库后 `notify`: role=seller, recipientEmail=店铺 owner(User.email), templateKey=`order_created`, title="新订单", body=`{store} 有 N 个新订单待处理，请及时查看并安排发货。`
- **按店合并一条**(created.filter(store).length), 防批量刷屏(142 单=1 条)。文案禁"校验/测试/生成"字样。metadata source='validation' 仅内部。
- 店铺→卖家: `Store.sellerAccountId → SellerAccount.userId → User.email`。
- **存量补发**(改文案/补通知): 删旧(metadataJson LIKE '%validation%')→ 按店 INSERT 合并 1 条。NotificationMessage id 可用 `gen_random_uuid()::text`; 字段: recipientEmail/role='seller'/channel='in_app'/templateKey/title/body/status='sent'/provider='in-app'/metadataJson/sentAt/createdAt/updatedAt。
- 卖家通知中心口径(nav-counts): recipientEmail=卖家邮箱, channel=in_app, readAt null, createdAt 7 天窗口。

## 6. 资金中心"待结算明细"页 + 预计到账时间
- `FundsSnapshot.pendingSettlementItems` = paymentStatus=paid 且 orderStatus in [delivered, shipped, awaiting_shipment, paid] 逐单(orderNo/status/amount/time/etaAt)。
- **预计到账 = autoConfirmAt**(物流签收时写 `now + 7d`; 结算 cron 按 `autoConfirmAt<=now OR deliveredAt<=cutoff` 自动确认收货 → 货款进可提现)。
- **服务端返结构化 etaAt**(有 autoConfirmAt 返时间串, 否则 null), **前端 null 时渲染翻译键** `seller.funds.settle.etaPending`(6 语言) — 禁服务端直返中文串(翻译铁律)。
- 翻译键: `seller.funds.tab.settle` + `settle.colOrder/colStatus/colTime/colEta/colAmount/empty/etaPending` ×6。

## 7. 生成订单状态时间线(物流间隔, 用户纠正: 不能"下单即签收")
- 已签收单: `shippedAt = createdAt + randInt(1,48)h`(发货间隔) → `deliveredAt = shippedAt + randInt(2,7)d`(运输) → `autoConfirmAt = deliveredAt + 7d`(自动确认)。三者依次递增。
- 运输中单: 只写 `shippedAt = createdAt + randInt(1,48)h`(隐含已发货 → 售后全额退款不回补库存)。待发货: 不写。
- 定时生成的历史单(createdAt 几天前)时间线全落过去, 自洽; 立即生成单内部相对关系正确(状态快进是造数工具固有特性)。
- 待结算明细「预计到账时间」= autoConfirmAt 具体日期(已签收单), 未签收显示翻译键文案。

## 8. 生成订单 vs 真实购买订单差异清单(用户问答过, 保留要点)
- **相同**: 订单号 19 位 / 同一张 Order 表 / PaymentTransaction paid / 结算链路(待结算→7天确认→可提现) / 扣库存+取消回补 / 销量"付款即售出" / 卖家通知 / 物流单号 / 美国收货信息。
- **差异**: 买家=虚构 gmail 账号(无 buyerUserId, 买家端看不到订单, 无买家通知/会话) / 直接 paid 跳过收银台(无 pending_payment 阶段, 不动买家钱包) / 状态直接随机分布(无真实流转事件) / "已签收"是状态伪装(补了时间字段但无真实物流事件) / "售后中"无真实 AfterSaleCase 工单 / 内部标记 orderChannel=validation + inventoryDeducted=true。

## 9. 翻译铁律(2026-08-14 用户明令, 永久)
- **每完成一个任务, 自动把所有新增内容纳入翻译体系**: 内置键 lib/translations.ts(6 语言 zh/en/es/fr/pt/ru) + 生产 UiTranslation 表(scope=console/dynamic, 覆盖模型 i18nJson)。
- 服务端返回结构化数据(null/时间/枚举), 中文文案一律前端 `data-i18n` 键渲染; 禁服务端直返中文串(eta 案例)。
- 改键值用脚本按语言区锚点行插入, 插后 `grep -c 每键=6` 验证。

## 10. 操作备忘
- 生产 .next 实际在 `/www/tiktok/.next-build`(不是 .next); BUILD_ID 时间戳验证部署版本。
- 验证部署产物: `grep -rl "中文原文" /www/tiktok/.next-build/server/chunks/*.js`(中文/键名在压缩产物里保留)。
- 卖家登录 API: `/api/auth/login` body 须带 `"role":"seller"`(默认 buyer 报"请从商户端登录")。管理端 <EMAIL-REDACTED> 生产密码未知(种子 401, 勿试)。
- QA 卖家: <EMAIL-REDACTED> / QaTest!2026, 店=EchoSaila(99 校验单)。
- 4 校验店店主: Livvy Home=<EMAIL-REDACTED>(173) / FlyGlobal=<EMAIL-REDACTED>(420) / EchoSaila=qa-seller-1(99) / Nestwell Home=<EMAIL-REDACTED>(1)。
- KPI "昨天"= 独立单日窗口(today0-1d → today0, 环比前天), RangeKey="today"|"yesterday"|7|14|30; 折线图不支持单日, 昨天时图表显示近 7 天。KPI 5 个日期筛选按钮翻译键 `seller.dashboard.range{Today,Yesterday,7,14,30}` ×6 语言(data-i18n 挂按钮)。
