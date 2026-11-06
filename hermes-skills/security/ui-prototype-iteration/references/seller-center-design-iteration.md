# Qavlixor 卖家端 — Design Iteration Record

Cross-border seller backend (类 Shopify/TikTok Shop 卖家中心), currency USDT, 15 views.

## Files (Desktop)
- `卖家端功能模块清单.md` — pure-functional spec (colors/radii stripped, per user request)
- `Qavlixor-卖家端-全部页面.html` — main clickable prototype (hash-routed SPA, 15 views)
- `Qavlixor-工作台-v1.html` / `-v2.html` — earlier dashboard-only iterations (v2 = approved structure)
- `Qavlixor-配色样图.html` — classic palettes comparison (all rejected: "太老套")
- `Qavlixor-科技风配色样图.html` — neon comparison (rejected: "AI 味道太重")
- `Qavlixor-TikTok风样图.html` — TikTok comparison (rejected: "还是不满意")
- `Qavlixor-Apple风样图.html` — Apple HIG comparison → user chose **A2**

## Approved theme: Apple HIG "A2 纯白极简" — copy-paste :root block
```css
:root{
  --nav-bg:#F9F9F9; --nav-ink:#6E6E73; --nav-ink-active:#1D1D1F;
  --nav-item-hover:rgba(0,0,0,.05); --nav-item-active:rgba(0,0,0,.07); --nav-border:rgba(0,0,0,.08);
  --bg:#FFFFFF; --surface:#FFFFFF;
  --border:#E8E8ED; --border-strong:#D4D4D9;
  --ink:#1D1D1F; --muted:#6E6E73; --faint:#98989F;
  --brand:#000000; --brand-ink:#1D1D1F; --brand-soft:rgba(0,0,0,.05);
  --link:#0071E3;
  --g:#34C759; --gs:rgba(52,199,89,.12);
  --blue:#007AFF; --blue-soft:rgba(0,122,255,.1);
  --orange:#FF9500; --orange-soft:rgba(255,149,0,.12);
  --amber:#FF9500; --amber-soft:rgba(255,149,0,.12);
  --red:#FF3B30; --red-soft:rgba(255,59,48,.1);
  --gray-soft:#F2F2F4; --gray-ink:#6E6E73;
  --mono:ui-monospace,SFMono-Regular,"Cascadia Mono",Consolas,monospace;
  --r-lg:16px; --r-md:10px; --r-sm:8px;
  --shadow:0 1px 2px rgba(29,29,31,.03);
}
```
Badge deep-text variants on tint bg: green `#248A3D`, blue `#0A60C0`, orange `#B25A00`, red `#D70015`, gray `var(--gray-ink)`. Buttons capsule `999px`; `.btn.primary` bg `#000` hover `#2E2E30`. Chart line `#1D1D1F` (gradient 10%→0), grid `#EFEFF2`, axis text `#98989F`. Login brand panel: bg `#000`, white logo block, slogan accent `#0071E3`, point icons stroke `#0071E3` on `rgba(255,255,255,.09)` chips.

## Theme roll-out checklist applied (reuse for future swaps)
- [ ] :root block wholesale
- [ ] nav text `color:#fff` → `var(--ink)` (logo name, identity shop/avatar)
- [ ] avatar bg `#1E2A44` → `rgba(0,0,0,.07)`
- [ ] `#FBFCFE` headers (tbl th, order-row-head, chat-body, ctx-panel, review-card .rh) → `#FAFAFC`
- [ ] thumb bgs `#EEF2F7` → `#F2F2F4`
- [ ] chart JS hexes (stroke/fill/grid/hover/tooltip)
- [ ] `.st.*` badge classes re-pointed to new tokens (not brand vars)
- [ ] old-hue hovers (`.btn.primary:hover:#1E8D6C`, `.chat-tools .send:hover`) → `#2E2E30`
- [ ] todo icons inline hex `#1D4ED8/#B45309` → `#0A60C0/#B25A00`
- [ ] login/auth brand panel colors
- [ ] modal radius 16px, mask shadow rgba(0,0,0,.14)

## Per-page polish status (2026-07-31, page-by-page iteration — user picks order)
1. ✅ 工作台 — KPI 4 (今日销售额/今日订单/今日客单价=销售额÷订单数/可提现余额, no dots, Apple trend colors); chart upgraded: 上期对比虚线 + legend + end-point value label + sparse axes + y-labels outside plot + resize-fit
2. ✅ 商品列表 — batchbar(改价/库存/上架/下架/删除-risk), 已驳回 tab + row reason, sortable cols (price/stock/sales/updated), stock warnings (0=缺货红, <10=仅剩N件橙, synced to stepper), ⋯ row menu, 批量上传 3-step modal, 导出数据 modal, thumbnails 52px SVG product art
3. ✅ 发布商品 — 4-level category cascade (no 一级/二级 prefixes), title helper (live count + format + banned-word tips), completeness bar 55→95% synced to step, image grid (main tag + hover-delete + dashed add), 发货时限 select (feeds order countdown), 运费设置 3-way radio (包邮/运费模板 dropdown/自定义首件续件满额), NO 运营数据 card for new products, no "自动翻译 7 语" copy anywhere
4. ✅ 订单列表 — tabs filter + `.cnt.hot` red 待发货 count, countdown `.odl` per pending row (global ticker), search-dimension dropdown (订单号/买家/运单号/SKU), 每页 20/50/100, batchbar (批量发货 3-step modal / 批量导出 modal / 批量取消 risk modal), order thumbs 48px, 批量发货 button → batch-ship workspace
5. ✅ 订单详情 — status timeline (5 nodes), 72px product main image + spec/SKU lines, buyer-note card + right-rail note sync, 物流信息 card (countdown + 去发货 + collapsible logistics trace timeline), 金额卡 = 商品金额+买家运费→预计收入 (NO 佣金 — platform has no commission, only 1.5% withdraw fee noted in hint)
6. ✅ 物流发货 — carrier-specific track# rules (trackRules map, placeholder-only guidance, hard block on submit), ship-deadline bordered alert (clock SVG + label + 16px bold countdown + right tip), 收件人核对 card, package split (pkgBox sum=order qty enforced), doShip updates badge+timeline in place, read-only 运费模板 line, NO 运费承担 radios (product page owns it), NO label printing (user removed: "暂时用不上")
7. ✅ 售后列表 — 商品卡式 `.as-card` (top row checkbox+单号+状态+tag+右对齐 timeout / body 左 48px 商品图+标题+SKU、右 诉求+meta / ops 行); timeout 文案承载状态机(剩余4h·超时自动升级 / 已拒绝·可改判 / 平台处理中·不可操作 / 已完成); 已拒绝卡带「改判退款」主按钮; batchbar (批量同意退款 confirm / 批量升级仲裁 risk / 导出 8 fields)
8. ✅ 售后详情 — SVG 证据卡 (2图1视频, vid-tag 角标, 计数徽章); 4-way 处理表单真联动 (agree=原因下拉+金额+说明 / reject=原因下拉+拒绝理由+**举证材料 img-grid(商家侧对称上传)**+内部备注 / evid=补充说明 / arbitrate=risk-box+danger 按钮→modal-arbitrate); timeline 统一 .tl
9. ✅ 买家消息 — 会话搜索框+全部/未读页签 (clFilter/clTab); **未读红点在时间下方右侧列 .cl-right(用户纠正,非昵称旁)**; 真发送 sendMsg(Enter 发送/Shift+Enter 换行, 空拦截, < 转义, 自动滚底); 常用语浮层 quick-panel(点击插入); 会话流内买家图片消息 .msg-imgs + 卖家订单卡片 .order-card(点击跳订单详情); 已读回执 "14:03 · 已读"; ctx panel thumb 48px
10. ✅ 资金中心 — dual cards + 6 tabs (概览/提现/保证金/冻结明细/财务流水/充值; 保证金退还 tab+区块+按钮 DELETED per user); **余额单一资金池模型**(充值→余额、提现←余额、保证金仅从余额划转不可直充, 侧边栏冻结明细菜单项删除); 流水金额修正为全额入账(无佣金, +89.90/+91.00/+56.20, 余额列联动重算); 提现实时校验 wdCalc(50 下限/余额上限/手续费联动/禁用按钮); 待结算行「签收后 08-03 释放」; 月结账单 modal-statement(7 行结算卡+导出 PDF); 地址簿 modal-addrbook(选用→填地址+联动网络); 流水筛选 flFilter(类型/时间/搜索+计数); **网络选择=net-opt 卡片列表**(非 radio, 用户要求)
11. 账号设置 — dual form cards
12. 登录 — black brand panel; remove "自动翻译 N 语" style copy (rewrote point to "多语言商品页即时生成,直达 180+ 个市场")
13. 注册 — single-column
14. 入驻流程 — 4-step form density
15. 审核状态页 — 3-stage progress
16. ✅ 运费模板 — sidebar menu (商品订单 group, box icon) + management page (包邮默认/标准/大件 templates: 计价规则/满额包邮/使用商品数/编辑·复制·删除) + 新建模板 modal (名称 + 包邮|按件计费 + 设为默认) + delete risk modal (关联商品自动改用默认模板). Feeds publish-page dropdown + ship-page read-only line.
17. ✅ 批量发货 workspace — 订单列表页头按钮 → dedicated page (待发货 table with .odl countdowns + seg tabs + batchbar reusing modal-ship + 导入运单 Excel). Route registered in ROUTES.

Pending at end: 账号设置 → 登录注册入驻审核 → **全站默认语言改英文**(用户收尾任务), 订单详情内部备注 + 打印发货单 gaps.

## Cross-page components now in the prototype (reuse for new pages)
- `batchbar` (id per page: orderBar/asBar…) + `updSel*`/`clearSel*` + `toggleAll*` JS
- Export modals: `modal-export` (products), `modal-export-order`, `modal-export-as`, `modal-export-fund` — same shape, different fields
- 3-step upload modals: `modal-upload` (products), `modal-ship` (shipments) — 模板下载→上传→校验结果
- Risk modals: `modal-cancel-risk`, `modal-del-risk`, `modal-arbitrate`; confirm modal `modal-refund-ok` — `.risk-box` red panel
- SVG product art set: 6 SKUs (keyboard/speaker/cable/humidifier/mouse/stand), inline, glyph-free
- `.tl` timeline (status + logistics trace), `.odl` countdown, `.note-tag`/`.msg-line` buyer-note, `.pthumb-lg` 72px detail image, `.img-grid` publish-page gallery
- `trackRules` map + `setTrackRule/chkTrack` (carrier→tracking# regex), `.ship-alert` bordered countdown bar, `pkgBox` package-split rows + `addPkg/delPkg/updPkg`, `modal-shipping-new` (region chips + 3 pricing modes + 运费试算器 calcFee) + `modal-tpl-del`, publish-page `tplSelBox` (template dropdown) + `feeBox` (custom fee), `view-shipping-templates`, `view-batch-ship` (batchBar/selCntB/updSelB)
- Chat: `.cl-search` + `.cl-tabs` + `clFilter/clTab`, `.cl-right` (unread dot under time), `sendMsg` (Enter send), `toggleQuick/useQuick` + `.quick-panel`, `.msg-imgs`/`.mi` (buyer image msg), `.order-card` (embedded order card → order-detail), `.mt` read receipt
- Aftersales: `.as-card` product-card layout (as-top/as-body/as-prod/as-main/as-timeout/as-ops), `asForm/asSubmit` 4-way form switcher (asAgree/asReject/asEvid/asRisk), merchant evidence via shared `.img-grid`
- Funds: `wdCalc/wdSubmit` (withdraw live validation + `.btn.disabled`), `depCalc/depSubmit` (保证金划转 from 余额, 方向 pill→arrow→pill), `.net-grid/.net-opt` network card list + `netSel/addrPick` (address dropdown ↔ network highlight sync), `modal-statement` (monthly statement .st-card), `modal-addrbook` (address book + useAddr), `flFilter` (ledger type/time/search filter + live count), `.deposit-note` (gray info bar)

## Rejected directions (do not resurface)
- Classic: 暖金商务 #B98A2F / 靛蓝 SaaS #4F46E5 / 青碧金融 #0E8F8F / 曜黑极简 #E8A33D ("太老套")
- Tech: 霓虹青 #00E5FF / 极光紫 #8B5CF6 / 荧光绿 #00E68A / 冰蓝 #38BDF8, all full-dark + glow + grid ("AI 味道太重")
- TikTok: 黑粉 #FE2C55 / 官方蓝 #0A84FF / 粉青 #25F4EE, black sidebar + pink accents ("还是不满意")
- Original pre-session constraint "白底深色字 12/8px 圆角" was also stripped by user (they wanted full freedom)
