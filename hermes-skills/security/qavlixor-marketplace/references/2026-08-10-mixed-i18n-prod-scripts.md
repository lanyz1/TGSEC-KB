# 2026-08-10 尾段沉淀：拆翻混合治标 / 消息卡片补图 / 生产脚本技巧 / 订单详情顶部改版

## 1. 拆翻混合（半中半英）→ 整句预置词典治标

**现象**：裸中文被 LanguageSync 拆段翻后拼接成半中半英——实测案例：
- "已缴足应缴额" → `Paid in fullAmount Due额`（"已缴足"→Paid in full + "应缴额"→Amount Due + 残留"额"）
- "已同意退还" → `已Agree退还`（单字"已"不翻残留 + "同意"→Agree + "退还"未翻完）

**根因**：整串词典 miss → 拆段翻；单字段（如"已"）不翻残留；段拼接无空格。

**修复（双保险）**：整句预置 UiTranslation（命中优先于拆段）+ 拆段词也预置：
```ts
// 服务器脚本（.mjs 动态 import，见 §3）
const dict = { "en": "...", "es": "...", "fr": "...", "pt": "...", "ru": "...", "ar": "...", "zh-CN": "源文本" };
const existing = await p.uiTranslation.findUnique({ where: { source: src } });
if (existing) await p.uiTranslation.update({ where: { source: src }, data: { i18nJson: dict } });
else await p.uiTranslation.create({ data: { source: src, scope: 'dynamic', i18nJson: dict } });
```

**保证金/状态词完整预置清单**（2026-08-10 已全部入库）：已同意退还=Refund approved / 同意退还=Agree to refund / 确认到账=Confirm receipt / 已扣罚=Penalty deducted / 已确认=Confirmed / 差额退=Refund difference / 全额退=Full refund / 已转回余额=Transferred back to balance / 需补缴=Additional payment required / 待财务确认=Pending finance confirmation / 正常=Normal / 已同意=Approved / 退还=Refund / 已缴足应缴额=Paid in full。

**用户会持续发现混合文案**——逐处预置，不修拆翻逻辑本身（拆翻对长句仍必要）。**用户拍板（08-10）：不要等用户截图，主动全扫**。两层扫描法：
1. **代码层**（快速）：`grep -rhoE ">[一-鿿]{1,5}<" app/ components/ --include="*.tsx" | sort | uniq -c | sort -rn`（高频裸中文——多数是 data-i18n fallback 会替换，排除后剩真裸词）；拼接型 `(已|待|未|共|第|剩)[{+\"]` 模式
2. **运行时**（准）：浏览器登录后切英文 → 等 12s（补译回填）→ TreeWalker 扫混合文本节点：
   ```js
   const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
   // 中文+拉丁混合 且 无长数字（排除订单号/金额）→ 收集
   if (/[\u4e00-\u9fff]/.test(t) && /[A-Za-z]/.test(t) && !/\d{6,}/.test(t)) mixed.add(t.slice(0, 45));
   ```
   逐页导航扫描（/seller/funds、orders、aftersales、notifications、account、messages + 买家端订单/商品/消息），命中即整句预置。已知命中：资金页"余额划转保证金 USDT 300.00 占用可提现（申请退还后释放）"→`Balance Transfer保证Gold ... 占用Withdrawable`——拆翻把"保证金"拆成"保证"+"金"(→Gold)。预置：余额划转保证金/占用可提现/申请退还后释放/**保证金=Deposit**（核心词，先查再补）。纯中文长扫描可 delegate_task 挂后台（子代理 grep + 输出文件:行号:原文清单）。

## 2. 订单→联系商家会话商品卡片缺图

**根因**：`ensureBuyerOrderThread`（lib/message-repository.ts）创建会话时 system 消息 cardPayload 只有 `itemTitle`；商品详情入口（createOrRouteConversation）有 `imageUrl: product.images[0]?.url`。**OrderItem 快照无图字段**（只有 productTitleSnapshot/skuSnapshot）。

**修复（两层）**：
1. 创建时实时查图：`prisma.product.findUnique({ where: { id: firstItem.productId }, select: { images: { take: 1, select: { url: true } } } })` → cardPayload 加 `imageUrl: itemImage`
2. 存量会话脚本：遍历 `conversation where contextType='order'` → system 消息 cardType='order' 且 cardPayload 无 imageUrl → 反查订单 items[0].productId → 查 Product 图 → `message.update` 补进 cardPayload（实测补 4 条）

验证：查该会话 system 消息 cardPayload.imageUrl 非空。ChatWindow 渲染键名 = `payload.imageUrl`（53 行）。

## 3. 生产脚本执行技巧（node22 + prisma）

- **静态 `import { PrismaClient } from '@prisma/client'` 报 `ERR_AMBIGUOUS_MODULE_SYNTAX`**（@prisma/client 双入口歧义，node 22 直接跑或 tsx 某些情况）→ 改用 **.mjs + 动态 import**：
  ```js
  const { PrismaClient } = await import('@prisma/client');
  ```
- **模型属性名是 `uiTranslation`**（不是 uITranslation）；**唯一键是 `source`**（不是 sourceText）——`findUnique({ where: { source } })`，update 同样 `where: { source }`；create 需带 `scope: 'dynamic'`
- SellerDeposit 字段是 `paidAmount`（无 amount 字段）；Prisma 物理表名小写（sellerdeposit），$queryRawUnsafe 用模型名会 42P01
- 进程环境已有 DATABASE_URL（PM2 env），.env.local 不一定有——`console.log('DATABASE_URL set:', !!process.env.DATABASE_URL)` 为 false 但连接正常

## 4. 买家订单详情顶部改版（方案 B，用户选定）

用户流程：**UI 布局改动先出 HTML 多方案预览（D:\跨境商城\会话产物\）→ 系统 Chrome 打开（`"/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window file:///...`）+ Hermes open_preview 双保险 → 用户选方案 → 落代码部署**。

方案 B 结构（app/account/orders/[id]/page.tsx）：
```tsx
<div className="bod-topbar">
  <div className="bod-top-back"><Link className="bod-back-link" href="/account/orders"><span data-i18n="ui.fix.4">返回订单列表</span></Link></div>
  <div className="bod-top-info">
    <div className="field"><span className="lbl" data-i18n="ui.cn.1">订单号</span><strong>{order.orderNo}</strong></div>
    <div className="field"><span className="lbl" data-i18n="ui.cn.2">下单时间</span><span className="val">{formatDateTime(order.createdAt)}</span></div>
  </div>
</div>
```
CSS：bod-topbar flex-column；bod-back-link 蓝色 13px 600 + `::before content: "‹"`；bod-top-info 浅灰 F5F5F7 圆角 12px 内 flex gap 26px；lbl 11.5px #86868B / 值 15px 600。

## 5. 操作入口一律胶囊按钮（用户偏好）

售后工单列表"详情"：`btn sm ghost`（文字感）→ `op-btn`（96×28 白底灰边圆角 999px，与订单操作列一致）。次级操作=op-btn，主操作=黑色胶囊（btn primary）。**用户会主动要求文字链接改胶囊**。
