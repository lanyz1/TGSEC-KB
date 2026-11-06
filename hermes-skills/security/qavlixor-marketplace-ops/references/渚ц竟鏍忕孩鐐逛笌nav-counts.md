# 卖家端侧边栏红点(badgeKey / nav-counts 体系,2026-08-13)

## 机制(与订单管理红点同源)
- `components/PortalShell.tsx` 的 `NavItem` 有 `badgeKey`;渲染:`count = item.badgeKey ? navCounts[badgeKey] ?? 0 : 0`,count>0 渲染 `<em>{count>99?"99+":count}</em>`,0 不渲染
- `navCounts` 由 `/api/{portal}/nav-counts` 提供,60s 轮询(页面隐藏时跳过)
- 卖家 nav-counts 原有:`orders`(待发货数,按 `store===scope.storeName && status==="待发货"`)、`aftersales`(未完结售后单,storeName+orderId **双口径**取并集,status notIn [已退款,已关闭,refunded,closed])

## 2026-08-13 扩展三个入口(用户:通知中心/买家消息/联系客服加红点)
侧边栏配置:
- 通知中心 `badgeKey:"notifications"`
- 买家消息 `badgeKey:"messages"`(原来用 ChatUnreadBadge 特判 → 统一 badgeKey 渲染同一 `<em>`;ChatUnreadBadge 保留给买家端顶部导航 84 行)
- 联系客服 `badgeKey:"support"`

nav-counts API 数据源(`app/api/seller/nav-counts/route.ts`):
- `notifications` = 7 天内未读站内通知:`prisma.notificationMessage.count({ recipientEmail: email, channel: "in_app", readAt: null, createdAt >= now-7d })`
- 会话未读:`prisma.conversation.findMany({ sellerEmail: email, status: { not: "closed" }, sellerDeletedAt: null }, select: { id, buyerEmail })` → **buyerEmail 非空 = 买家消息**,空 = 平台客服会话(联系客服);分别 count `prisma.message({ conversationId in ids, readAt: null, senderRole: { notIn: ["seller", "system"] } })`
- 软删会话 `sellerDeletedAt` 必须排除(与消息列表口径一致)

## 造数验证模式(红点类功能)
生产插入测试数据 → 无头刷新看红点 → **按标记清理**:
- 通知:`templateKey: 'test_badge'` 标记,清理 `deleteMany({ templateKey: { in: [...] } })`
- 消息:用固定 senderEmail 标记(`<EMAIL-REDACTED>`),清理按 senderEmail;会话可复用已有买家会话(不用新建),删消息即可
- 无头断言:登录 → 抓 `.qx-console-sidebar` 内所有 `a > em` 的文本映射到导航项文本

## 踩坑(prisma 字段)
- Message 表字段是 **`body` 不是 content**(造数报 PrismaClientValidationError)
- ConversationType 枚举:`buyer_seller` / `buyer_support` / `seller_support`
- MessageSenderRole 枚举:`buyer` / `seller` / `support` / `system` / `ai`
- NotificationStatus 枚举:`queued` / `sent` / `skipped` / `failed`
