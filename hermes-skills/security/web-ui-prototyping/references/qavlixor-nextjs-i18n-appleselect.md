# Qavlixor Next.js 阶段：i18n 与 AppleSelect 白面板下拉（2026-08-05 实测）

原型单文件 SPA 之后进入 Next.js 实现阶段（App Router + LanguageSync 客户端词翻译 + DynamicText）。本文件是 S3-S6 逐页量测中踩出的通用坑与标准做法。

## 1. 中英混排根因：词级翻译 vs data-i18n 整段替换

页面静态中文文案**必须加 `data-i18n` 键**（translations.ts zh/en 双份）。不加的文案由 LanguageSync 词翻译兜底，词典只覆盖单词 → 产生半译：
- "返回订单详情" → "返回Order Details"（"返回"在词典，"订单详情"不在）
- "批量发货" → "批量Shipping"（"发货"→"Shipping"）
- "超时未发货将触发平台催发提醒" → "超时未Shipping将触发平台催发提醒"

**诊断**：量测时正则抓 `[中文][A-Za-z]` 或 `[A-Za-z][中文]` 相邻混排；每页必须 grep 全部 data-i18n 键对照 translations.ts（键缺失时元素渲染原始键名，如 `seller.products.edit`）。

**批量 i18n 化流程**（S5 物流页 50 处 / S6 批量发货页 42 处，均一次过）：
1. execute_code 读文件，对每个唯一中文文本构造精确 replace（`<h2>订单发货</h2>` → `<h2 data-i18n="seller.logistics.title">订单发货</h2>`），每对断言 `s.count(old)==1` 否则报 FAIL
2. translations.ts 用锚点批量插键：找一对相邻的 zh/en 键（如 `"seller.logistics.orderNo": "订单号",` 与其 en 版），在两处各插入一整块 `"key": "值",` 行
3. `npx tsc --noEmit` EXIT 0 + 浏览器快照验证无键名/无混排

## 2. 金额三件套（USDT 不被 LanguageSync 换算）

LanguageSync 货币换算作用域 = `.buyer-portal, .seller-portal, .admin-portal`（含三端），把 "59.8 USDT" 换算成当地货币（$5/$0 或 价格 (CNY)）。卖家端金额统一：
1. **所有带 USDT 的静态文本加 `data-currency-lock`**（表头/金额行/弹窗罚扣文案）
2. **表头 "(USDT)" 后缀必须写进 translations 值**：`data-i18n` 会整段替换 textContent，JSX 里的 `>单价 (USDT)<` 后缀会被英文翻译值覆盖丢失 → zh/en 值直接写 "单价 (USDT)"/"Unit price (USDT)"
3. 纯数字单元格（单价 29.9）无货币标记不会被换算，不用锁

## 3. timeline/动态文案：labelKey/timeKey 模式

订单状态时间线 label/time 是函数返回的中文字符串，词翻译会半译（"等待卖家发货"→"等待卖家Shipping"）。标准做法：
```ts
function orderTimeline(order): Array<{label; labelKey; time; timeKey; state}> {
  return [{ label: "等待卖家发货", labelKey: "timeWaitShip", ... }]
}
// 渲染
<b data-i18n={`seller.orderDetail.tl.${node.labelKey}`}>{node.label}</b>
```
translations 键 `seller.orderDetail.tl.*` 整段替换，杜绝半译。

## 4. AppleSelect 白面板下拉（三端复用）

**组件**：`components/seller/AppleSelect.tsx`（props: value/onChange/options[{value,label}]/ariaLabel?/style?）。白底触发按钮+白面板+选中黑行，替代原生 select（原生高亮态 OS 级不可 CSS 化）。

**data-i18n-raw 豁免（坑 #27）**：AppleSelect 的 label 是**数据值**（仓库名/选项），词翻译会半译 "默认仓"→"Default仓"。给两个 label span 加 `data-i18n-raw`，并在 LanguageSync 词翻译跳过列表（`isChineseTextNode` 的 `parent.closest(...)`，约 L339）加 `[data-i18n-raw]`。**这是新通用豁免属性**，与 data-i18n（整段替换）、data-i18n-dynamic（词词典）三套机制并存：
- `data-i18n` = 翻译键整段替换
- `data-i18n-dynamic` = 值必须是**中文原文**走词词典（传翻译键会渲染键名！坑 #28）
- `data-i18n-raw` = 完全不参与翻译（数据值用）

**样式全局化（坑 #29）**：AppleSelect 样式原 `.sap .apple-select*` 只匹配卖家端（.sap 祖先）。管理端/买家端组件换用后无样式。seller-proto.css 追加**全局版**（无前缀 `.apple-select*`，色值写死 #1D1D1F/#D2D2D7/#F5F5F7），.sap 内仍走高特异性原版。seller-proto.css 在 app/layout.tsx 全局引入，所有端都加载。

**批量替换 select**（42 个/20 文件）：delegate_task 3 并行子代理分批（卖家端/买家端+通用/管理端），context 里给全 AppleSelect API + 替换规则：
- 受控 select → value/onChange 直传；`e.target.value as X` 类型断言 → 包箭头函数
- option 无 value → value=label；data-i18n option 保留中文 label
- 非受控纯展示（币种/银行/月份）→ 组件内加 useState 包装
- 服务端组件（GET 表单 select）**不能换**（AppleSelect 是客户端组件）——保留原生，仅靠 .inp 箭头样式

**用户红线（坑 #30）**："之前挨个细调过的页面就不改了" —— 全站批量改动时**跳过已细调页面**（买家端 C1-C17、卖家端 S1-S5），子代理改完用 `git checkout -- <file>` 回滚涉及已细调页面的文件，其余保留。落地前先确认每个文件归属（grep 页面路由引用）。

## 5. 页面级 i18n 化清单模板（每页照此查）

- [ ] grep 全部 data-i18n 键对照 translations.ts（缺键→补，S2 曾缺 61 键）
- [ ] 中英混排扫描（`[中文][A-Za-z]` 相邻）
- [ ] 金额表头/数值 data-currency-lock + translations 值带 (USDT) 后缀
- [ ] timeline/动态文案 labelKey/timeKey 键
- [ ] 原生 select 是否可换 AppleSelect（服务端表单除外）
- [ ] 17TRACK/物流类提示句按用户要求清理
