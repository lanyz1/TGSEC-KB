# 2026-08-10 通知提示音 + 多类型客服体系 + 消息中心改名

## 1. 通知提示音（Web Audio"叮咚"，无音频文件）

实现位置：`components/NotificationBell.tsx`（卖家/管理端右上角铃铛，全站唯一轮询点）。

- 轮询 `/api/{portal}/notifications-recent`，**30s**（原来 60s，响铃更及时）
- **首轮建立基线不响**（`prevCountRef` 初始 null；页面加载不响旧通知）
- 后续 `newCount > prevCount` 且 `!document.hidden` → 每多一条响一声，间隔 700ms，**cap 5 声**防轰炸
- 音效：Web Audio 合成双音（正弦波）——"丁"=E6 1318.5Hz 0.18s + "当"=B5 987.8Hz 0.38s，gain 用 exponentialRamp 包络防爆音；`osc.connect(gain).connect(ctx.destination)`
- 兜底 try/catch，音频不可用不影响功能

### ★无声 bug 两个根因（用户实测"没声音"后修复，必读）

1. **AudioContext 手势预热（最常见根因）**：浏览器自动播放策略——在 `setTimeout` 回调（非用户手势上下文）里 `new AudioContext()` → ctx 处于 `suspended`，此时 `resume()` 无手势可能被浏览器拒绝 → 永远无声。
   **修复**：`useEffect` 挂一次性 `pointerdown`/`keydown` 监听 → `ensureAudio()`（创建 + resume）预热；用户首次点击页面后 ctx 就绪，之后 `playDingDong` 直接可用。`ensureAudio()` 返回 ctx，`playDingDong` 里先取 ctx 再排音符。
2. **已读清零不同步基线**：打开面板时 `setCount(0)` + 调已读 API，但 `prevCountRef` 保持旧值 → 新通知 `newCount(1) > prevCount(5)` 为 false → 漏响。
   **修复**：打开面板清零处同步 `prevCountRef.current = 0`。

**验证法**（Browserbase 无扬声器也能验证链路）：DB 插一条 notificationMessage → 页面首轮基线 = 旧 count → 再造第二条 → 等 30s 轮询 → 铃铛角标从 1 变 2 即证明"增量检测 → 响铃逻辑"链路工作。测完删测试数据。

## 2. 多类型客服体系（一个客服一类职能）★最终版=独立tab（用户两次纠正后定稿）

> ⚠️ 用户原话："客服是一个单独的选项，他里面有五个对话，每个对话是一个不同的客服…不要和前面的买卖家会话混在一起"。**不是** tab 行的按钮+弹窗（初版方案已被否）。

### 共享类型清单 `lib/chat-support-topics.ts`（前后端共用）
```ts
SUPPORT_TOPICS = [orders 订单问题, aftersales 售后问题, funds 资金/保证金, onboarding 入驻/开店, other 其他问题]
// 每项 { key, label, labelKey, subject }；supportTopicOf(key) 兜底 other
```

### `/api/chat/support` 按类型创建/复用（app/api/chat/support/route.ts）
- `body.type` → `supportTopicOf()` → **subject 存类型名**（如"订单问题"）
- **复用条件：type=seller_support + sellerEmail + subject=类型名 + status≠closed**——同一类型复用未关闭会话，**不同类型各自独立**（卖家可同时有订单/资金两个客服会话）
- 返回 `{ ok, conversationId, subject }`

### 消息中心"客服"独立 tab（components/chat/ChatList.tsx，最终实现）
- `TabKey = "all" | "unread" | "ticket" | "support"`；tab 行渲染 4 个 tab：全部|未读|工单|客服（`chat.tab.support` 键）
- **过滤**：`supportConversations = conversations.filter(i => i.type === "seller_support")`——客服 tab **只显示客服会话，绝不混入 buyer_seller**
- **空态**：`tab==="support" && role==="seller" && 列表空` → `.cl-support-grid`（2 列网格，5 张类型卡片，点击 `startSupport(topic.key)` → fetch → `router.push(baseHref/会话id)`）；**有会话后网格消失，显示会话列表**（每项带"客服"`st blue` 标签）
- **客服会话显示名按类型**：message-repository.ts 卖家视角 252 行——`row.type==="seller_support"` 时 peerName = `subject.replace("问题","").replace("资金/保证金","资金").replace("入驻/开店","入驻") + "客服"`（订单客服/售后客服/资金客服/入驻客服/其他客服），不再是统一的"平台客服"
- ChatList 必传 props `role` + `baseHref`（ChatWorkspace 调用处同步传）；`startSupport` 里 `supportBusy` 存 `string|null`（当前点击的类型显示"…"防连点）

### 反馈与建议页入口（SellerFeedbackPanel.tsx）
客服卡片加 `AppleSelect` 客服类型下拉（`supportTopic` state）→ contactSupport 带 `{type}` 发 POST。两入口共用同一 API。

### 翻译键（8 键 × 6 语言）
`chat.tab.support / chat.supportChoose / support.topic.label / support.topic.orders|aftersales|funds|onboarding|other`——按各语言区 `chat.tab.ticket` 行锚点插入（方法见 product-review-notify 的补键脚本定稿法）。

### CSS（globals.css .buyer-portal 区，最终版）
`.cl-support-grid`（白卡阴影、2 列 grid、`margin: 0 12px 10px`）、`.cl-support-title`（grid-column 1/-1）、`.cl-support-item`（hover 蓝边框；disabled opacity .5）。**初版的 `.cl-tabs .cl-support` 蓝色按钮 + `.cl-support-pop` 弹窗样式已删除**。

## 3. 消息中心改名（买家消息 → 消息中心）
- `translations.ts` 改 `seller.nav.messages` 值 ×6 语言（zh 消息中心 / en Message Center / es Centro de mensajes / fr Centre de messages / pt Central de mensagens / ru Центр сообщений）
- 卖家消息页 `app/seller/messages/page.tsx` 加 `page-head` 标题 `<h2 data-i18n="seller.nav.messages">消息中心</h2>`（复用 nav 键，无需新键）
- 全部|未读|工单 tab 原已存在（ChatList 18 行起），本轮只是补第 4 个客服 tab

## 4. 杂项（小）
- **语言切换器白地球图标**：`.language-switcher-globe` 黑底 emoji 🌐 → 白底圆 + 1px 浅灰边 + 蓝色地球线条 SVG（circle + 横线 + 椭圆经线，stroke=currentColor #0071e3，15px）；组件里替换 `<span>🌐</span>` 为 inline SVG
- **风险店铺功能删除**（用户拍板）：管理端店铺管理删 风险筛选下拉/风险列/编辑行风险/详情页风险等级；riskClass/riskLabel 函数同步删（否则 tsc 未用报错）；DB riskLevel 字段保留不动；**patch 时注意删函数块易错位**——用唯一锚点含函数签名，删完立刻 tsc
