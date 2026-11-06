# 订单会话商品卡片补图 + 买家端订单详情顶部改版（#128，2026-08-10）

## 一、订单"联系商家"会话商品卡片缺图（根因 + 修复模式）

**现象**：买家从订单详情点"联系商家"→ 对话框商品卡片显示占位图标无图；从商品详情页"联系商家"→ 有图。

**根因**：两个入口的会话创建 cardPayload 数据源不同：
- 商品详情入口（`lib/message-repository.ts` createOrRouteConversation）：`cardPayload: { ..., imageUrl: product.images[0]?.url }` ✅
- 订单入口（`ensureBuyerOrderThread`）：只有 `itemTitle: order.items[0]?.productTitleSnapshot` ❌ **没有图**
- 深层原因：**OrderItem 快照表不存图片字段**（只有 title/sku/option 快照），创建会话时也没实时查商品图

**修复（两层，缺数据快照的通用模式）**：
1. **创建时**：`ensureBuyerOrderThread` 创建会话前实时查 `prisma.product.findUnique({ where: { id: firstItem.productId }, select: { images: { take: 1, select: { url: true } } } })` → `itemImage` 写入 cardPayload 的 `imageUrl` 键（**键名必须 imageUrl**——ChatWindow 商品卡片渲染读 `payload.imageUrl`）
2. **存量会话**：一次性 DB 脚本遍历所有 `contextType: "order"` 会话的 `cardType: "order"` system 消息，`cardPayload` 有 orderNo 无 imageUrl 的 → 查订单 items[0].productId → 查 Product.images[0] → UPDATE 补上（本会话 4 条存量全部补图）

**要点**：
- ChatWindow 商品卡片（53 行）：`payload.imageUrl ? <img> : BOX_SVG 占位`
- 存量会话不重建（`existing` 复用），所以**必须脚本补存量**，否则用户实测永远无图
- 补图验证：查该会话 system 消息 cardPayload 是否含 imageUrl

## 二、买家端订单详情顶部改版（bod-topbar 方案 B）

**用户流程**：UI 布局类修改先出 HTML 多方案预览（`D:\跨境商城\会话产物\`，用系统 Chrome 打开 `cmd //c start chrome "file:///..."`）→ 用户选方案 → 落改部署。用户明确"改完先别部署，放 html 审核"。

**方案 B 落地**（用户选定）：
- `app/account/orders/[id]/page.tsx`：`bod-topbar` 内结构改为 `bod-top-back`（返回链接）+ `bod-top-info`（提示框：两个 `.field`（label 小字 + 值大字））
- `app/globals.css`：`.bod-topbar` flex-column；`.bod-back-link`（蓝字 600 + `::before content "‹"`）；`.bod-top-info`（背景 `#F5F5F7` 圆角 12px，label 11.5px 灰，值 15px 600）
- 翻译键复用 `ui.cn.1`（订单号）/`ui.cn.2`（下单时间）/`ui.fix.4`（返回订单列表）
- 实测：英文界面返回链接/标签均跟随（键机制），提示框 `rgb(245,245,247)` + 12px 圆角

**注意**：买家端登录测试用 <EMAIL-REDACTED>（密码见 QA 记录），订单详情页 URL `/account/orders/{orderNo}`。
