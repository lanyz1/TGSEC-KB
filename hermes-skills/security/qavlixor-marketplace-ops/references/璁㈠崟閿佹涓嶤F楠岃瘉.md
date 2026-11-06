# 卖家端订单锁死 + 自动签收倒计时 + 生产验证技巧(2026-08-13)

## 已签收订单:全部锁死 + 自动签收倒计时(commit 704777f)
- 需求:卖家端订单管理"已收货"tab 的已签收订单**操作全部锁死**,并显示**自动签收倒计时**(签收后 7 天系统自动确认收货、释放结算——后端机制本就存在 `/api/orders/[id]/confirm` source=system,本次只补展示)。
- 数据链路:`prisma Order.autoConfirmAt`(物流更新为已签收时由 `/api/logistics/[id]/route.ts` 写入 = now+7 天)→ `lib/sample-data.ts` Order 类型加 `autoConfirmAt?: string | null` → `orderFromPrisma` 带出 `row.autoConfirmAt?.toISOString()` → orders/page.tsx 行数据 → OrderRow 类型 → 表格。
- 组件 `components/seller/AutoConfirmCountdown.tsx`(client):`useState(Date.now)` + `setInterval 1000` 每秒刷新;剩余 = target-now,显示 `自动签收 · X天 HH:MM:SS`;deadline 为空返回 null;remain<=0 兜底 `自动签收 · ✓`。文案走翻译键(锁定/自动签收/天/提示 4 键×6 语言)。
- 表格锁死逻辑(SellerOrdersTable ops 列):`order.status === "已签收"` 时渲染 `🔒 已锁定` + `<AutoConfirmCountdown>` + 仅保留"查看订单";发货/取消/物流详情按钮条件排除已签收(物流详情从 `shipped || 运输中 || 已签收` 改为 `shipped || 运输中`)。
- 验证:生产无已签收订单 → 临时把真实订单改 `receipt_confirmed` + `autoConfirmAt`(3 天后),无头验证后**必须还原**(改回 delivered + autoConfirmAt:null)。

## 已发货订单:禁止重复发货 / 无限改物流单号(commit 08006d4 + 18a03d2)
- 需求:用户报告"已发货订单虽然显示已发货,但还能点保存并标记发货,甚至可无限更改物流单号"。
- 根因1(后端):`app/api/orders/[id]/fulfillment/route.ts` 状态守卫原来 `["待发货","运输中"]` 都放行(注释写"运输中(补录)")——已发货(shipped→运输中)订单可反复调 API 改单号/重复发货。
- 修复:①`mode=ship` 守卫收紧为**仅 `待发货`** 可发货;②`mode=draft` 草稿同样锁(仅 待发货/运输中 可存草稿),防绕过;③报错文案明确"仅待发货订单可以发货;已发货订单的物流信息已锁定,不能重复标记发货或修改物流单号"。
- 根因2(前端):`SellerFulfillmentForm` 收不到订单状态,已发货订单照样渲染可编辑表单。修复:发货页(`app/seller/orders/[id]/logistics/page.tsx`)传 `orderStatus={order.status}` prop;组件内 `locked = orderStatus !== undefined && orderStatus !== "待发货"` 时**整个表单替换为只读锁定卡**(🔒 锁定横幅 + 承运商/单号/仓库/时限 kv 只读展示,无输入框无按钮),新键 `seller.fulfillment.locked`/`lockedTip` ×6 语言。
- 顺手:镜像补插行状态映射缺 `delivered`/`receipt_confirmed`(落 else→"已完成",误导文案)→ 补 `delivered/receipt_confirmed → "已签收"`。
- 验证:服务器本地 fetch `http://localhost:3000/api/orders/{id}/fulfillment`(mode=ship 改新单号 + mode=draft)→ 均 **400** 且订单数据未被改动(查 prisma orderStatus/autoConfirmAt 前后一致)。
- 通用教训:**后端状态机守卫是权威**,前端锁定只是体验;守卫名单从宽到严要同步更新报错文案,别让用户看到"状态已完成"这种误导映射。

## ⚠️ Cloudflare 缓存导致验证误判(重要排查手法)
- 症状:代码已部署且逻辑正确,但 **curl / 无头浏览器经 CF 访问看到旧页面**(如:订单已改为已签收,curl 页面查订单号 0 次、无头看不到锁定);SSR HTML 里订单号只出现在 `<script>`(RSC payload)而未在表格 —— 也是缓存/数据源问题信号。
- **可靠验证 = 服务器本地 curl 绕 CF**:paramiko SSH 到生产,node 脚本内 `fetch('http://localhost:3000/api/auth/login', { headers: { Host: 'seller.qavlixor.com' } })` 拿 cookie,再 `fetch('http://localhost:3000/seller/orders?status=received', { headers: { Host, Cookie } })` 看真实 SSR HTML。**必须带 Host header**(否则 Next 路由到错误子应用/404)。
- CF 缓存通常 1-2 分钟自动过期;让用户强刷 Ctrl+Shift+R 或等缓存。
- 判断页面数据源:`getOrderData` 的 `isEnabled()` = `USE_JSON_DB !== "1"`;生产 .env.local **无 USE_JSON_DB** → 走 prisma;但服务器 `/www/tiktok/work/local-db.json` 仍存在(51 个演示订单,含已签收示例 TO-1782325104858-2-2/Blue Ridge Goods)——prisma 失败时 catch 回退 JSON 库。排查"页面为什么没有我改的数据"时先确认走的是哪条路径(直接查 prisma 表 + 查 local-db.json 状态分布)。

## 无头验证其它坑(本会话积累)
- **React 受控输入**:`el.value = x` 后必须用 native setter(`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el, x)`)+ `dispatchEvent(new Event('input',{bubbles:true}))`,否则 React state 不更新、表单提交空值(新增客服弹窗踩过)。
- **语言切换验证**:语言存 `localStorage['globalmart-language']`,SSR 默认语言是 **ru**(未设 localStorage 时页面显示俄语属正常,勿当 bug);验证语言正确性必须显式设 localStorage 后 reload。
- **卖家端默认英文界面**:按钮/页签文本是英文("Recharge"/"Withdraw"),用中文正则(`/充值/`)点不到;tab 切换用 `/recharge/i` 匹配 textContent。
- **买家端验证用 API 登录**:`fetch('/api/auth/login', {role:'buyer',...})` 直接拿 cookie,比走登录表单稳(表单选择器常变)。

## 卖家端订单页结构备忘
- `/seller/orders` 页签 filter:received = `status === "已签收"`(displayStatus 显示"已收货");orders 按 `store === scope.storeName` 过滤。
- 表格行是 Fragment 多行(rowSpan),订单号所在行 ≠ 操作列所在行,无头抓操作列时找 `.ops` 容器而非按 tr 文本定位。
