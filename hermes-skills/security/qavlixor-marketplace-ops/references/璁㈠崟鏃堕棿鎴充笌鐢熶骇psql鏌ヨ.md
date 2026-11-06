# 定时生成订单时间戳 & 生产数据库查询

## 定时生成订单时间戳 bug(2026-08-13 修复, commit 78a4a3a)

**现象**:管理端"随机生成订单"选了时间范围(如 1 小时/12 天),卖家端订单列表的下单时间却全挤在一起(30 秒粒度)。

**根因链**(四段,缺一不可):
1. 计划时间生成本身正确:`app/api/test-orders/route.ts` `start + Math.random()*span` 均匀随机 + 升序排序
2. cron(`app/api/cron/scheduled-orders/route.ts`)每 30s 扫到点条目批量落库
3. **订单号 bug**:`lib/test-order-generator.ts` 里 `generateOrderNo(buyer)` 不传日期 → 默认 `new Date()` = **执行时刻**;plannedAt 只写进了 DB `createdAt`
4. **显示端**:卖家订单列表"下单时间"从**订单号前 12 位解析**(`app/seller/orders/page.tsx` 的 `orderTimeOf(orderNo)`,yyMMddHHmmss),不看 DB createdAt

→ 结论:**该平台订单展示时间 = 订单号解析,不是 DB createdAt**。改"下单时间"必须改订单号前缀;只改 createdAt 列表页不变。

**修复**:`generateOrderNo(buyer, spreadTimes.length ? spreadTimes[jobs.length] : undefined)` — 定时模式订单号带计划时间,立即模式不传(now)。

## 生产数据修复模式(历史订单号时间重写)

场景:历史 142 单订单号全是执行时刻,需按原 job 计划时间重写(用户: "把那天生成的订单时间按定的时间范围改一下")。

**数据链路**:管理端定时生成登记 `ScheduledOrderJob`(jobNo=SO..., startTime/endTime, count)→ `ScheduledOrderItem`(plannedAt, status, orderNo)。

**重写算法**:`new_orderNo = to_char(plannedAt,'YYMMDDHH24MISS') || substr(old_orderNo,13)`(保留后 7 位随机尾,唯一性检查后安全)。

**必须同步的表**(全查过):
- `Order`:orderNo + createdAt = plannedAt
- `ScheduledOrderItem.orderNo`(same CTE)
- **`PaymentTransaction.orderNo`:用 `orderId → Order.id` join**(Order.orderNo 改后 orderNo join 已失效——本会话踩坑:UPDATE ... FROM ji WHERE t.orderNo=ji.old_no 返回 0,因为 CTE 读的是已改过的 ScheduledOrderItem);检查时用 `orderId` join 命中 142
- `AfterSaleCase.orderId`(如有;测试校验单无售后 = 0)

**流程**:先 check(新号与现存冲突、job 内新号互撞、关联表命中数)→ 事务 UPDATE → 验证(按天分布 count、`substr(orderNo,1,12) = to_char(createdAt,'YYMMDDHH24MISS')` 一致性=0 不一致)。**改前确认该店非 job 订单不能误改**(按 jobNo 精确限定,不动其他订单)。

## 生产 psql 查询(202.95.1.135:12125 root)

- **应用目录 `/www/tiktok`**(不是 /root/qavlixor);node -e 里 require prisma 会炸(输出压缩 JS)——直接用 psql
- DATABASE_URL 在 `/www/tiktok/.env`:`postgresql://qavlixor:PASS@127.0.0.1:5432/qavlixor_prod`
- **psql -c 多层引号转义坑**:SQL 含中文/双引号表名(`"Order"`)/单引号值时,paramiko 拼 -c 会静默失败(输出空)。**用 SFTP 写 SQL 文件到 /tmp → `psql -f` 执行**,稳
- **店铺归属 JOIN 链**:`Store.sellerAccountId → SellerAccount.id;SellerAccount.userId → User.id(email)`。SellerAccount **无 email 列**(只有 contactEmail/contactPhone)
- Order 表:`orderNo` 存 19 位业务订单号,`id` 是内部主键;`PaymentTransaction.orderId = Order.id` 可 join(订单号改后仍稳)
- **卖家登录 API**:`/api/auth/login` body 必须带 `"role":"seller"`(否则 403 "该账号是商户账号,请从商户端登录");qa-seller-1 测试密码 `QaTest!2026`
- 卖家页验证:服务器本地 curl(http://localhost:3003/seller 绕 CF),登录 cookie 后 grep SSR 直出

## 卖家端 KPI 筛选加"昨天"(2026-08-13, commit e249f35)

- `components/seller/DashboardKpis.tsx`:`RangeKey` 加 `"yesterday"`(RANGE_KEYS/LABEL/PREV_DAYS 同步);计算分支:昨天 = `today0-1d → today0`(固定窗口,不是含今天),环比前天(`today0-2d`)。注意 curEnd 不能用 now(会含今天已过时间)
- `components/seller/DashboardRangeHost.tsx`:图表 range 传 7(折线不支持单日,显示近 7 天含昨天)
