# 校验订单定时创建逻辑（2026-08-09 用户"到点才出现"）

用户先取消时间限制（22.27）后又要求：管理端选时间范围生成校验订单 → **订单到点才落库出现**
（卖家端 23:15 之前看不到，23:15 开始冒第一单，23:20 前全部出现），不要立即生成。
Commits 5af1260（主体）+ 4bcef8a（按店分组修复），已部署生产。

## 架构

```
管理端选时间范围生成
  → 登记计划（ScheduledOrderJob + ScheduledOrderItem 明细）
  → crontab 每分钟调 scripts/process-scheduled-orders.mjs
  → POST /api/cron/scheduled-orders（CRON_SECRET 鉴权）
  → 扫描到点条目 → 按 job→store 分组 → lib/test-order-generator.ts 落库
  → 卖家端"到点才出现"
不填时间 → 维持立即生成（同 lib）
```

## 实现清单

1. **schema 新表**（追加 schema.prisma 末尾）：
   - `ScheduledOrderJob`：jobNo unique / adminEmail / storeIds Json / count / statusMode / startTime / endTime / status(pending|processing|done|cancelled) / finishedAt
   - `ScheduledOrderItem`：jobId（relation Cascade）/ storeId / plannedAt / status(pending|done|failed) / orderNo（回填），`@@index([plannedAt])` + `@@index([jobId])`
   - 生产 `npx prisma db push` 后用 `information_schema.tables LIKE 'Scheduled%'` 验证

2. **API 双模式**（app/api/test-orders/route.ts）：
   - `startTime && endTime` 都填 → 登记计划：validStores（含已上架商品）→ 每单计划时间区间内均匀随机、升序 → `scheduledOrderJob.create`（`jobNo: generateDocNo("SO")`，DocPrefix 类型要加 "SO"）→ `scheduledOrderItem.createMany` → 返回 `{ scheduled: true, jobId, jobNo, total, startTime, endTime, message }`
   - 不填 → 立即生成（调 lib）
   - 时间解析 `parseTime`：number / 纯数字串（epoch ms）/ ISO 字符串三态兼容

3. **生成核心提取 lib/test-order-generator.ts**：从 route 搬全部辅助（firstNames/lastNames/streetNames/streetTypes/usCities/pick/randInt/sampleBuyerName/sampleReceiver/sampleTracking/statusFor/normalizeStores）+ `generateValidationOrders({ storeIds, stores?, count, statusMode, plannedTimes?: Date[] })`——plannedTimes.length === 订单总数时按序分配 createdAt（否则 now）。含落库（syncOrderToPrisma + paymentTransaction.upsert + incrementProductSold + 操作日志）。**route 重写为纯校验+分发**（比 patch 残留旧代码干净）。

4. **cron 执行器** `/api/cron/scheduled-orders/route.ts`：
   - 鉴权：`x-cron-secret` header 或 ?secret=，比对 `process.env.CRON_SECRET`（否则 401）
   - 查 `scheduledOrderItem.findMany({ where: { status: "pending", plannedAt: { lte: now }, job: { status: { not: "cancelled" } } }, take: 60, include: { job: true } })`
   - **按 jobId 分组 → 每个 job 内再按 storeId 分组**（关键！见坑 8）
   - 每组 `generateValidationOrders({ storeIds: [storeId], count: 组条数, plannedTimes: 组条目时间 })` → 逐条 `scheduledOrderItem.update({ status: done|failed, orderNo })`
   - job 无 pending/failed → `status: done, finishedAt: new Date()`

5. **触发脚本** scripts/process-scheduled-orders.mjs：fetch POST（`x-cron-secret` header），打印 `到点落库 N 单`；crontab 每分钟 `* * * * *`（flock 防重入）——**cron 最小粒度 1 分钟，做不到 30s**

6. **管理端 UI**（AdminTestOrdersClient.tsx）：`result.scheduled` → setMessage(result.message) + loadScheduledJobs()；state `scheduledJobs` + `loadScheduledJobs`（fetch GET /api/scheduled-orders）+ `useEffect` 15s setInterval 轮询；表单下方计划列表区块（as-card：jobNo/状态标签 done|processing|pending|cancelled/进度条 doneCount/totalCount，done 绿 #34C759 否则橙 #FF9F0A）

7. **GET /api/scheduled-orders/route.ts**：管理端 ops 权限，jobs 列表 + 每 job done/total 计数

## 坑（按踩坑顺序）

1. **同店多条计划总数算错（done+failed 各一）**：第一版 `storeIds: items.map(storeId), count: 1`——generateValidationOrders 的 stores 查询**按 id 去重**（同一店多条目 → totalOrders=1 < plannedTimes.length=2 → spreadTimes 空 → createdAt 用 now + 第 2 条 orderNo 拿不到）。**必须按 storeId 分组，count=该店条数**（4bcef8a）
2. **crontab/脚本 401 unauthorized**：① crontab 行没带 `CRON_SECRET=...` 前缀 → 脚本 env 空；② **更隐蔽：服务器 .env.local 没有 CRON_SECRET 行**（`grep -c CRON_SECRET .env.local` = 0）→ Next 进程 `process.env.CRON_SECRET` 空 → curl 带 header 也 401。修复：`.env.local` 追加 `CRON_SECRET=gm-cron-2026` + pm2 restart。**401 排查链：脚本 env → .env.local → API 端 process.env**
3. **db push --skip-generate 后 build 必挂**：`Property 'scheduledOrderItem' does not exist on type 'PrismaClient'`——db push 后必须 `npx prisma generate` 再 build（21.5 同坑）
4. **DocPrefix 类型**：`generateDocNo("SO")` 需先给 `lib/doc-number.ts` 的 `DocPrefix` 联合类型加 "SO"（TS2345）
5. **admin 登录 401**：生产 root.admin 密码常失效（AdminUser 表已迁移，见桌面《Qavlixor管理密码.txt》）——**端到端测试不依赖登录**：DB 直插测试 job

## 端到端验证模式（生产）

```
DB 直插测试 job（jobNo 前缀 SOTEST）+ createMany 2 条 items（60s/100s 后）
→ 等 cron 跑 2 轮（~150s）
→ 断言：job status=done + items 全 done + 订单 createdAt 精确落在计划时间
  （两单差 40s 对应计划差 40s = 按时间顺序出现）
→ 清理测试数据：删 items/job + 级联删订单
  （orderItem → paymentTransaction → shipment → order，外键顺序，22.13）
→ 清理后 `order.count({ where: { orderNo: { in } } }) === 0`
```

测试订单删除若遇 `OrderItem_orderId_fkey` 外键拦截——先删 orderItem/paymentTransaction/shipment 再删 order；**删除失败不能 catch 吞掉**（19.9 铁律）。

## 通用模式

"到点才出现"类需求 = 登记计划（新表）+ cron 到点执行 + 管理端进度 UI；cron 执行器按业务分组（job→store）避免生成函数去重后 plannedTimes 错位；任何新表接入 = db push + prisma generate + information_schema 验证 + crontab env 齐全四步。
