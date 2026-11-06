# 定时生成订单时间戳根因 + 生产 psql 直查与改单号数据修复纪律

(2026-08-13 实战:SO2608121859252057 的 142 单时间修正)

## 1. 根因:订单号带的是"生成时刻",列表页按订单号解析下单时间

- `lib/doc-number.ts` 的 `generateOrderNo(buyerKey?, date = new Date())` — **默认用当前时刻**打订单号(前 12 位 yyMMddHHmmss)
- 卖家端订单列表的"下单时间" = **订单号前 12 位解析**(`app/seller/orders/page.tsx` 的 `orderTimeOf(orderNo)`),**不是 DB createdAt**
- 定时生成模式(cron `/api/cron/scheduled-orders` 每 30s 扫一批落库):若生成订单号时不传计划时间 → 每批订单号 = cron 执行时刻 → 列表时间全部挤在 30s 粒度内,看起来"没随机分布"
- **修复**:`lib/test-order-generator.ts` 定时模式 `generateOrderNo(buyer, spreadTimes.length ? spreadTimes[jobs.length] : undefined)` — 计划时间传入订单号
- 已落库的订单改不了(订单号已生成),只能 DB 修复或删除重生成

## 2. 生产 psql 直查模式(替代 node -e PrismaClient)

- **应用路径 = `/www/tiktok`**(不是 /root/qavlixor;node -e 引 PrismaClient 会打印模块代码,不可用)
- DB:`postgresql://qavlixor:<pw>@127.0.0.1:5432/qavlixor_prod`;密码从 `/www/tiktok/.env` 的 `DATABASE_URL` 正则提取
- **psql 多层引号转义会碎**(`-c "SELECT \"Order\"..."` 远程 shell 解析后列名/表名对不上,静默返回空)→ **把 SQL 写到 /tmp/qN.sql(sftp),再 `psql -f /tmp/qN.sql`** —— 可靠
- 表名/列名 camelCase 必须双引号:`"Order"`、`"createdAt"`、`"orderNo"`
- **账号-店铺关联链**:`Store.sellerAccountId → SellerAccount.id`;`SellerAccount.userId → User.id`;登录邮箱在 `User.email`(**SellerAccount 无 email 列**,有 contactEmail 但勿用)
- 订单/任务表:`Order`(orderNo/createdAt/orderStatus/storeId/totalAmount)、`ScheduledOrderJob`(jobNo/startTime/endTime/count/status)、`ScheduledOrderItem`(jobId/storeId/plannedAt/status/orderNo)

## 3. 改订单号(业务单号)的数据修复纪律

场景:把定时生成订单的订单号/createdAt 改成计划时间(plannedAt),142 单。

1. **先检查唯一性**:新号 = `to_char(plannedAt,'YYMMDDHH24MISS') || substr(oldNo,13)`(保留后 7 位);查( a )新号与现存 Order.orderNo 冲突、( b )job 内新号互撞 — 均须 0
2. **查引用表**:含 orderNo/orderId 列的表(`information_schema.columns` 按列名过滤):Order、ScheduledOrderItem、PaymentTransaction(orderNo+orderId 都有)、AfterSaleCase.orderId、SellerDeposit.orderNo、SupportTicket.orderNo、OrderItem/Shipment 用 Order 内部 id(不受影响)
3. **一个事务内更新**:Order(orderNo+createdAt)→ ScheduledOrderItem.orderNo → PaymentTransaction.orderNo → AfterSaleCase.orderId
4. **⚠️ CTE+UPDATE 顺序坑**:每个 UPDATE 里的 CTE 是按"当时表状态"重新求值的 —— Order/ScheduledOrderItem 的 orderNo 先被改掉后,后续 UPDATE 再读这两个表取 old_no 得到的是**新号**,join 旧号 0 行(实测 PaymentTransaction UPDATE 0)。**改完后用稳定键补同步**:PaymentTransaction 用 `orderId`(→Order.id,不变)join 拿新 orderNo
5. **改后验证**:残留旧前缀(`LIKE '26081219%'`)应为 0;抽查 `substr(orderNo,1,12) = to_char(createdAt,'YYMMDDHH24MISS')` 一致性;按天分布应铺开

## 4. 测试数据识别

- 校验/测试订单号前缀 = 生成时刻(`26081219xxx`),买家邮箱形如 `<name> <name>@guest.local`
- 定时任务 jobNo 前缀 `SO`;判断"那会定的时间范围"查 `ScheduledOrderJob.startTime/endTime`
