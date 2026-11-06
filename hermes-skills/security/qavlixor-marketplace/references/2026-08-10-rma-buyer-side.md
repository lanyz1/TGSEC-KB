# 2026-08-10 买家端售后对标修复 + 拆段混合翻译根治循环 (#147-148)

## #147 买家端售后页(/account/rma)对标卖家端修复

### 商品行不显示的真根因（历史数据双格式）
- `AfterSaleCase.orderId` **历史数据存的是 orderNo（20位数字）**，代码注释声称存 Order.id（cuid）→ 按 id 查永远空 → 商品行/关联订单查不到。
- 修复：查询 `OR: [{ id: { in: ids } }, { orderNo: { in: ids } }]`；map 双键（order.id + order.orderNo 都 set）；titleI18nByOrderTitle 同理双键 `${orderId}::${title}`。
- 详情页 findUnique(id) 改 findFirst(OR)。
- 排查方法：服务器脚本打 `case.orderId` → `order.findUnique({where:{id}})` vs `{where:{orderNo}}` 对照，一眼确认格式。

### 状态标签对标（.status 基础已是胶囊 999px）
- statusClass 扩展：已退款→`status ok`（绿 #e5f7ec/#1a7f37）、已关闭→`status done`（灰 #f0f0f2/#6e6e73）、拒绝→danger、处理中/平台介入→warning。CSS 加 `.status.ok/.status.done`。

### 按钮胶囊化
- `.buyer-portal .bac-rma-card .btn.sm, .buyer-portal .bac-rma-back .btn.sm { border-radius:999px; border-color:#E8E8ED; background:#fff; color:#1D1D1F; font-weight:600; padding:8px 18px }`（对标卖家端 op-btn）。

### 语言切换器
- LanguageSwitcher 的 `<span className="language-switcher-globe">文</span>` 改 🌐（"文"在英文界面突兀）。

### 脏数据清理（售后 reason 结构化文本）
- reason 是 `类型 · 商品 · SKU · Requested X USDT｜处理：[角色 时间] 文案｜处理：...` 拼接串。
- QA 测试乱回复产生尾部脏词：`同样`/`看`/`cnm`/`7`/`1` → 统一替换：`\n同样`/`\n看`/`\n数字` → `\n同意退款`；`] cnm` → `] 已介入处理`。共 6 条。
- 正则清理：`/\\n[0-9]{1,3}$/` → 同意退款。

## #148 拆段混合翻译根治循环（★反复出现，用户要求"全扫不要漏"）

### 现象
裸中文短词 miss 词典 → 拆段翻译 → 拼接残留：`已Agree退还`(已同意退还)、`Refund原因：Quality issue 同样`、`Paid in fullAmount Due额`(已缴足应缴额)、`Balance Transfer保证Gold`(余额划转保证金)、`26orders`。

### 治标：整句预置 UiTranslation（词典命中优先于拆段）
- UiTranslation **唯一键 = `source`**（不是 sourceText/id；findUnique({where:{source}})/findFirst 均可）。
- 本会话预置词单（7语言全）：已同意退还/同意退还/确认到账/已扣罚/已确认/差额退/全额退/已转回余额/正常/已同意/退还/已缴足应缴额/余额划转保证金/占用可提现/申请退还后释放/保证金/退款原因/同样/处理记录/问题描述/证据材料/同意退款/已介入处理。

### 治本：运行时混合扫描（比代码 grep 准）
1. 切英文（localStorage + dispatchEvent qavlixor-language-change）→ 等 10-13s（等兜底/补译回填）
2. TreeWalker SHOW_TEXT 扫：`/[\u4e00-\u9fff]/.test(t) && /[A-Za-z]/.test(t) && !/\d{6,}/.test(t)` 收集 ≤60 字文本
3. 定位源（grep 文案 / 查 DB reason）→ 预置整句 + 清脏数据
- 代码层 grep 拼接型（`已{` `共{` 等）实测抓不到（JSX 写法多样）——以运行时扫描为准。
- 用户拍板：扫描可 delegate_task 挂后台（子代理只读 grep 代码层，列文件:行号:原文），主线程继续其他任务。

### 注意：中文 placeholder 会被 LanguageSync 拆翻成混合（如"已缴足应缴额"→"已缴足Amount Due额"）——不用中文 placeholder，改行内条件渲染文本（裸中文 div + 词典预置）。

## 服务器脚本执行 Prisma 备忘（多次踩坑）
- node 直接跑静态 `import { PrismaClient } from '@prisma/client'` → `ERR_AMBIGUOUS_MODULE_SYNTAX`（@prisma/client 双模式入口与 node22 ESM 冲突）→ **用动态 import**：`const { PrismaClient } = await import('@prisma/client')`，文件存 `.mjs` 用 `node` 跑。
- 模型属性名是 **`p.uiTranslation`**（不是 uITranslation，报 undefined 时先 `Object.keys(p)` 查）。
- `.env.local` 无 DATABASE_URL 时进程 env 已注入（PM2），count 可通；连接失败先看 env 是否读到。
- tsx 跑 .mts 静态 import 也可能歧义——统一 .mjs + 动态 import + node。

## 保证金差额退脚本（绕过 hasOpenOrders，用户"超额直接退回"）
- refund API 有 `hasOpenOrders` 拦截（未完结订单不能退），但超额部分与订单无关——一次性脚本直接：
  1. `sellerDeposit.create({ kind:'refund', paidAmount: refundableDifference, status:'approved', reason:'差额退' })`
  2. 复检 `getDepositOverview` net 不为负（并发防重）
  3. `refreshSellerWallet(store.id)`（余额自动 +209）
  4. `appendOperationLog/appendBusinessEvent` 留痕
- 验证：net 归位 = requiredAmount、refundableDifference=0、钱包可用增加。

## 保证金划转上限规则（08-10 用户拍板）
- **最高只能缴到档位应缴额**：`maxTransfer = requiredAmount > 0 ? round2(max(0, required - net)) : 100`（应缴 0 时允许基础档 100）。
- 旧 bug：gap=0（已缴足）仍放行 100 → 可无限超缴；修复前后端同规则 + 已缴足时输入框 disabled + 行内提示"已缴足应缴额"（勿用 placeholder）。
