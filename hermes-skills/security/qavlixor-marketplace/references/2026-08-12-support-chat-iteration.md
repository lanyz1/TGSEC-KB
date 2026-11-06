# 2026-08-12 客服系统第二波迭代 + 翻译批量插入坑 + 工作台筛选 + 钱包口径终态

## 客服系统最终架构(承接 #203 独立客服页第一波)

### 页面矩阵
| 端 | 客服入口 | 说明 |
|---|---|---|
| 买家 | `/account/support`(+`[id]`) | 独立客服页,supportOnly 模式;个人中心右下角悬浮按钮直达 |
| 卖家 | `/seller/support`(+`[id]`) | 独立客服页;侧边栏"客户服务→联系客服"+ 反馈页"进入客服对话"按钮 |
| 管理端 | `/agent`(+`[id]`) | **独立客服网页**(全屏,无管理端侧边栏),admin 登录即客服工作台 |

### 关键实现
- **ChatWorkspace** 新增 `supportOnly`(独立客服页:两栏布局去 ctx 面板、顶部条+退出按钮)+ `agentName`(客服端顶部显示"当前客服:昵称")
- **exitHref 按角色**:`role==="support" ? "/admin" : baseHref.replace(/\/support(?:\/.*)?$/, "")`(客服端 baseHref=/agent 无 /support 后缀,直接 replace 会退到自己,必须按角色分支)
- **ChatList supportOnly**:买家/卖家显示客服类型发起网格(图标+描述纵向列表);`role==="support"` **不显示发起网格**(客服是回复不是发起),只显示"全部客服会话"+ 会话列表
- **消息中心(ChatList 普通模式)去掉 support tab**:只剩 All/Unread;客服不再混入消息中心
- **买家端开放官方客服**:`/api/chat/support` requireRole 含 buyer,创建 buyer_support 会话(管理端可见)
- **客服身份**:AdminUser 加 `supportNickname`(需 db push);客服发消息 senderName = `supportNickname || displayName`(买家/卖家看到"客服-昵称",之前是匿名);管理端 `/admin/roles` 每行加"客服昵称"输入框(超管可改,存 `/api/admin/permissions` 的 supportNickname 字段);`/agent` 顶部条显示当前客服身份
- **卖家端会话管理(消息中心 ⋯ 菜单,仅卖家角色显示)**:
  - 置顶:`Conversation.pinned` Boolean 默认 false,列表 `orderBy: [{pinned:"desc"},{lastMessageAt:"desc"}]`,ChatSummary 加 pinned
  - 标未读:`markConversationUnread` = 清空该会话**对方已读消息的 readAt**(未读计数自然恢复,勿另加 flag)
  - 删除:`sellerDeletedAt` **卖家视角软删除**(买家/客服不受影响);`visibleWhere` 卖家分支 **OR 两个分支都要加 `sellerDeletedAt: null`**(只加一个会漏)
  - 前端操作后 `onUpdate` 回调本地更新+重排(ChatWorkspace 传 updateConversation)
- **卖家反馈页(SellerFeedbackPanel)**:内嵌的客服类型下拉+发起按钮已删,改为蓝色按钮链接 → `/seller/support`(不再跳 `/seller/messages/{id}` 与买家消息混用;顺带消除该路径 404 争议)

### 样式双写坑
买家外壳 = `.buyer-portal`(PortalShell),卖家外壳 = `.seller-portal`(ConsolePortalShell),但 **ChatWorkspace 根节点恒为 `.sap`** → 新样式要 `.buyer-portal` 和 `.sap` 各写一份,否则卖家端不命中。

## 翻译键 6 语言批量插入脚本坑(重要)

用 python heredoc 批量往 `lib/translations.ts` 的 6 语言区插键时:
1. **锚点值必须各语言唯一**:fr 和 en 的 `"chat.tab.support"` 值都是 "Support" → `src.replace(anchor)` 把 en 的键插进 fr 区,造成同对象重复键(TS1117: An object literal cannot have multiple properties with the same name)。先 `grep -n '"键名"'` 看各语言实际值分布,有同值语言用**带相邻键的上下文锚点**定位,或按语言区特征(如 en 区后面跟着英文的 chat.tab.ticket)循环跳过已插入位置。
2. **LanguageSync 会机翻改写锚点值**:JSX fallback 文本曾被机翻生成 UiTranslation 覆盖,`translations.ts` 里的值可能已不是最初写的(如"选择客服类型发起对话"→"选择客服类型")。脚本前 grep 实际值,别按记忆写锚点。
3. **插入后必须验证**:每个键 `grep -c` 应为 6,且检查是否有相邻重复行(`grep -n` 相邻两个相同键值 = 插错语言区)。修复用 python 按 `dup\n dup` 精确串删除,保留第一个。
4. 新文案要**同步加 data-i18n**,否则 LanguageSync 把纯文本机翻(半中半英如 "Top Up、Withdraw与Deposit相关")污染显示。

## 工作台 KPI 日期筛选(今日/7/14/30 天)

- 服务端(page.tsx)只查一次近 60 天已付款订单明细(`{t,c,u,g}` 序列化数组),`DashboardRangeHost`(客户端)本地聚合 今日/7/14/30 天销售额/订单数/客户数+环比
- SalesLineChart 改**受控组件**(range + onRangeChange 从父级传),与 KPI 共用 range 联动
- 本地 dev.db schema 过期会导致 TransformError → 测试前 `npx prisma db push`;本地无测试账号时直接生产验证(<EMAIL-REDACTED> / QaTest!2026)

## 钱包口径终态(校验单计入资金)

- `refreshSellerWallet(storeId)` 是**聚合重算**(从订单全量算 pending/frozen/available),不是增量;校验单生成后**必须调用**(generateValidationOrders 落库后对涉及店铺刷新),否则余额不同步
- 用户拍板:**校验订单(validation)计入资金**(撤销 2026-08-07 安全扫描 S2 的排除);资金页 prismaSnapshot 与钱包 refreshSellerWallet **同一口径**(都含 validation,都不重复 parse)
- 修复路径教训:先按含校验单重算(待结算飙到 6 万虚高)→ 用户明确要求"校验单走正规流程" → 恢复含校验单并统一两处口径。**改资金口径前先问用户要不要含校验单**,别自己拍板排除
- 全库重刷:遍历有订单的 store 调 refreshSellerWallet(settlement cron 只刷到期待确认的店,不会刷全部)
- Json 类型字段 Prisma 返回已是对象,**勿再 JSON.parse**(曾致误判)

## 商品详情 SKU 下方主副图

- `app/products/[id]/page.tsx` pdp-spec 区 SKU 明细表后加 `.pdp-sku-images` 网格,展示 `galleryImages`(排除 role=detail 的详情图,与左栏轮播同口径),按 sortOrder 顺序
- 勿用 ui.sel.106/107 做"主图/副图"alt(那是"商家处理中/证据"的其他含义),用 `${title} ${index+1}`

## 批量订单生成(上限删除)

- 数量上限 20 已删:**两处**都要改——`app/api/test-orders/route.ts`(Math.min(count,20)→100000)和 `lib/test-order-generator.ts`(同款上限,立即生成/定时 cron 共用此函数,漏改则定时模式仍截断)
- 完整逻辑文档:`docs/批量生成订单-逻辑与规则.md`
- SKU 上限 20(商品变体数,平台 API 硬限制)与批量订单数量上限是**两个不同限制**
