# 2026-08-10 观察者修复 / form-translate / 侧栏重构 / 插键按区（#141-146）

## ★1. data-i18n 被 React 重渲染覆盖回中文（系统性，必须知道）

**现象**：弹窗/受控组件里的 `[data-i18n]` 元素切语言后先被 LanguageSync 替换成英文，随后 React 重渲染（如"输入即翻"setState）又把文本覆盖回 JSX 原文（中文）→ 页面永久中文。

**根因链**：
- LanguageSync `applyLanguage` 用 `element.textContent = getTranslation(...)` 替换（607 行附近）
- 组件内任何 setState → React 重渲染 → 按 JSX 原文重写 data-i18n 元素文本
- 旧观察者只监听 `characterData` 且只对金额/货币节点（`moneyTextSources`/`hasMoneyToken`）触发 → data-i18n 文本被覆盖后观察者不触发 → 中文永久

**修复（已部署）**：观察者 characterData 分支增加 data-i18n 元素检测——文本被 React 覆盖后再次应用翻译。无循环：替换后值相同（`element.textContent !== value` 不赋值）→ 不触发 characterData。

**同类教训**：data-i18n 的 DOM 替换与 React 受控渲染是竞争关系；凡是"切语言+打开弹窗/输入即翻"组合的页面都要实测（发货设置弹窗/运费模板编辑复制弹窗是重灾区）。

**另一个触发点**：运费模板编辑/复制弹窗输入框值（模板名/适用范围）——"先切语言再打开弹窗"时语言事件已过、form 还是空 → 打开后无事件再触发。修复：useEffect 依赖 `[form.name, form.scope]`，值变化自动补译（防循环：nameI18n 更新不改 form）。

## ★2. form-translate 必须传"键=文本"对象（数组→索引键错位）

`POST /api/i18n/form-translate` 的 `fields` 若传数组 `["包邮","通用"]`，服务端 `Object.entries(['包邮','通用'])` 得到 `[["0","包邮"],["1","通用"]]` → 返回 `{0:..., 1:...}` → 前端按源文本查找永远 miss → 输入即翻失效（中文不变）。

**正确**：`fields: Object.fromEntries(keys.map(k => [k, k]))` —— 键=文本本身，返回键=文本，`nameI18n[文本]` 直接命中。
**检查**：SellerShippingTemplates.tsx + SellerAccountSettings.tsx 两处都改过；新写"输入即翻"一律传对象。

## 3. 拆翻混合的整句预置（延续 #136-140）

"已同意退还"→"已Agree退还"类混合：拆段翻（"已"单字残留 + "同意"→Agree + "退还"未翻）。修复=整句预置词典（`UiTranslation`，`source` 唯一键，`findUnique({ where: { source } })`），命中优先整串替换；同时预置拆段词（已同意/退还）双保险。本轮新预置：已转回余额/正常/已同意/退还/余额划转保证金/占用可提现/申请退还后释放/保证金(核心词 Deposit)。

## 4. 卖家端侧栏结构（2026-08-10 用户拍板，components/PortalShell.tsx sellerNavGroups）

1. 店铺运营：工作台 → 入驻资料 → 通知中心（账号设置移走）
2. 商品订单：商品管理 + 订单管理（不变）
3. 发货管理：运费模板 + 发货模板（不变）
4. 客户服务：只留 售后工单 + 买家消息（反馈移走）
5. 资金管理：只留 资金中心（余额划转从导航删，页面仍在 URL 可直达）
6. 新组"设置与开发"（titleKey `seller.nav.settingsDev`）：账号设置 + 反馈与建议

## 5. 插翻译键必须按语言区锚点定位（错插教训）

translations.ts 是 `Record<LanguageCode, TranslationMap>`，6 个语言区（es/fr/pt/ru/zh-CN/en；**ar 区没有 seller.nav.* 键——历史遗留**）。第一版脚本 `re.search` 永远命中第一个锚点 → 7 个不同语言的 settingsDev 键全插在 es 区 → JSON 重复键后者覆盖，所有语言都返回最后值（灾难）。

**正确做法**：按"该语言区的锚点值"定位（如 `"seller.nav.funds": "<该语言值>"`），逐区插入对应语言的值；每区插完验证 `grep -n` 键出现次数 = 语言区数。

## 6. 通知中心多选/删除/翻页（app/seller/notifications + SellerNotificationList）

- 分页：服务端 `searchParams.page`，每页 10，count 总数；`pagination` prop 可选（admin 端共用组件不传则不渲染分页栏）
- 删除 API：`POST /api/seller/notifications/delete`（{ids:[...]} 或 {all:true}，currentEmail 校验）
- 复选框/全选/批量条/删除全部；删除后 router.refresh
- 组件里裸中文按钮（删除全部/上一页/下一页/全选）**不要挂不存在的 data-i18n 键**（getTranslation undefined → textContent 赋 undefined → 显示空）；裸中文走兜底即可

## 7. 其他

- 卖家订单详情+列表商品名跳转编辑商品已删（用户拍板"功能不好"）→ 纯文本保留 DynamicText 翻译；**JSX 中文注释（含全角括号）会触发 TS 连锁解析错误**（TSC 报错在注释附近行），安全做法：JSX 内注释用英文或删掉
- 买家订单详情顶部方案 B（用户从 A/B/C 三选）：返回链接独立左上（‹ 蓝字）+ 订单号/下单时间浅灰提示框（F5F5F7 圆角 12px，字段竖排 lbl 小字灰 + val 大字加粗）——改动前先出 HTML 多方案（D:\跨境商城\会话产物\）让用户挑
- 售后列表"详情"链接改 op-btn 胶囊（96×28 白底灰边，与订单操作列一致）
- 保证金划转上限（延续 #130/131）：`maxTransfer = required > 0 ? max(0, required - net) : 100`——已缴足（net>=required）则 0，输入框 disabled + "已缴足应缴额"绿字提示（该文案已整句预置 en: Paid in full）
