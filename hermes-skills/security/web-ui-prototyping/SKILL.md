---
name: web-ui-prototyping
description: >-
  测绘引擎·Web UI prototypes: seller-center/admin design & iteration.
owned: true
tier: general
pack: survey-skill
---

# web-ui-prototyping（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/web-ui-prototyping/`

溯源（仅标记）：`hermes/creative`

---

# Web UI Prototyping(卖家后台 / 管理端)

## When to use
- User asks to design/redesign a web app UI(seller center, dashboard, admin panel, 后台)
- Iterating page-by-page on an existing single-file HTML prototype
- Picking colors / visual direction — this user usually can't describe the target; compare visually instead

## Workflow(proven on Qavlixor 卖家端, 15 页单文件 SPA)
1. **Strip to functional spec first.** Given a design handoff doc, remove ALL colors/radii/shadows/layout-appearance; keep routes, modules, fields, states, actions, validation rules. The user re-designs from the stripped spec.
2. **Direction-finding = FULL-PAGE comparison renders, NOT component swatches.** One HTML page with 2–4 complete dashboard renders(sidebar + topbar + KPI + chart + todo + table), each a real page scaled down:
   ```css
   .frame{width:1100px;transform:scale(.36);transform-origin:top left;pointer-events:none}
   .shot{overflow:hidden} /* wrapper, clickable to select */
   ```
   Click-to-select highlights the chosen card; user replies with a letter. Component-only color cards were rejected ("太老套" / "AI 味重"); full-page renders got a decision. Dark tech style (glow/gradients/grid-lines) was called "AI 味太重" — the winning direction was Apple-minimal light.
3. **Lock the design system, then apply globally via `:root` CSS variables.** One patch block swaps the whole theme. Keep radii/shadow/colors all in tokens.
4. **Per-page fine-tuning, ONE page at a time.** User says "下一页吧" — go in order. Before editing, present a table of candidate issues per page; edit, verify, move on.
5. **After EVERY page finishes, deliver a parity-gap report.** User-explicit standing rule: 每页微调完必须输出「该页与主流平台(Shopify / TikTok Shop / 亚马逊 / Temu)的关键差距」表 — 按重要性排序(高/中/低),标注主流做法 vs 当前状态 vs 影响,末尾给建议(先补哪条)。用户会挑着做("先把 1246 做了"),做完后差距表更新为剩余项。
6. **Verify with browser tools:** navigate `file:///...`, loop all routes via `show('route')` in browser_console, assert `js_errors` empty, then `open_preview`.

## User's locked design system(Qavlixor 卖家端 · Apple A2 纯白极简)
- 白底 `#FFFFFF`,浅灰侧栏 `#F9F9F9`,卡片 1px `#E8E8ED` 边框圆角 16px
- 文字 `#1D1D1F` / 次要 `#6E6E73` / 弱化 `#98989F`
- **主按钮纯黑胶囊**(`#000000` 底白字,全圆角),hover `#2E2E30`
- 链接/点缀蓝 `#0071E3`(仅少量)
- 状态徽章 Apple 系统色浅底深字胶囊:绿 `#34C759` / 蓝 `#007AFF` / 橙 `#FF9500` / 红 `#FF3B30` / 灰 `#8E8E93`
- 页面标题 24px 粗(大标题层级),表头 11.5px 灰字,表格行 hover `#FAFAFC`,分页胶囊当前页黑底白字
- 完整色值 + 组件规范 + 给用户的提示词见 `references/qavlixor-design-spec.md`

## Hard bans(user-explicit, violating = rework)
- **禁止产品吹嘘文案**:never "自动翻译 7 语" / "一键铺全球" / "智能生成" 类话术 — write functional facts only("≤60 字")
- **禁 AI 味装饰**:no gradients(按钮/背景), no glow/辉光, no 霓虹, no 网格线背景, no 毛玻璃滥用, no emoji icons(use SVG line icons)
- No decorative colored dots on KPI cards
- **严禁偷懒/偷奸耍滑**(user's standing execution principle):每个功能模块动手前先列全流程步骤(模板下载→上传→校验→确认 / 风险提示 / 金额确认 / 导出设置),完成后逐项在浏览器实测再交付。toast 只用于无风险轻操作(上架/下架/保存/搜索演示)——涉及钱、删除、发货、仲裁、取消的操作用 toast 顶替弹窗就是返工。

## JS pitfalls(all hit while building this prototype)
1. **parseFloat on date strings silently breaks sorting** — `parseFloat("2026-07-31 09:12")` → `2026`; same-year rows compare equal → sort does nothing. Fix: regex-test both values with `/^-?\d+(\.\d+)?$/` before numeric compare, else `localeCompare`.
2. **SVG chart doesn't follow container resize** — fixed `viewBox="0 0 760 240"` renders once; window resize leaves the chart stale AND hover coordinates wrong. Fix: track `let curW`; on `resize` read `chartBox.clientWidth`, `setAttribute('viewBox','0 0 '+curW+' 240')`, redraw; compute hover x from curW. Guard `Math.abs(w-curW)>10` to avoid feedback loops. Also update grid/axis x-extent to curW.
3. **Patch vs external edits** — after `sed`-editing the same file, patch warns "modified since last read"; harmless if old_string still unique, but re-read before continuing.
4. Big table rewrites: give every row `data-*` attributes(pid/status/price/stock/sales/updated)up front so filtering + sorting + warnings are pure JS with no HTML surgery per feature.
5. **CSS patch can swallow a base class** — adding `.title-tip{...}` by replacing the adjacent `.hint{...}` line killed every `.hint` on the page. When inserting new component rules next to a base class, keep the base-class definition in the replacement text (re-add it if your old_string covered it).
6. **file:// preview serves stale DOM after external edits** — after `sed`-editing the file, browser snapshot still showed old content (`"— · —"`). `location.reload()` in browser_console fixes it; then re-verify with a console expression before trusting the DOM (snapshot lies, console doesn't).
7. **Consecutive patches on the same region can orphan a function** — patching A→B, then using the freshly-written B as old_string for another change, dropped `fakeShip` entirely (replacement didn't re-include it). When a second patch targets content you just wrote, include the just-written body in new_string, or anchor on a different surrounding line. After any multi-patch pass, grep for all function names (`grep -c "function fakeShip"`) before trusting. Same happened with `paySel` (replaced by asForm/asSubmit) and the `.thumb` CSS class (renamed to `.prod .thumb` by an over-broad old_string). Rule: after every batch of patches, grep the file for every function/class name you depend on.
8. **New view = `<section>` AND a `ROUTES` entry; verify via class, not inline style** — adding `view-batch-ship` without `'batch-ship'` in `ROUTES` makes `show('batch-ship')` silently fall back to dashboard. And views are shown by toggling the `.active` class (CSS `.view{display:none}.view.active{display:block}`), so testing `el.style.display !== 'none'` is ALWAYS true and false-passes. Assert `document.getElementById('view-x').classList.contains('active')` after `show('x')`.
9. **sed handles UTF-8 Chinese files fine for global replaces** — e.g. swapping placeholder glyphs (⌁◈✳⛌▦✎) for inline SVG product images, or `#FBFCFE`→`#FAFAFC`; use `|` as the sed delimiter when the replacement contains `/` (SVG paths). `search_files` fails on Chinese path segments (rg IO error) — fall back to `grep -n` via terminal with the quoted path.

## Next.js 实现阶段(i18n / AppleSelect 三端复用)
原型验收后进入 Next.js 逐页实现(S1-S6 已验证流程)。**全站批量改动前先问/确认范围**:用户明确「之前挨个细调过的页面就不改了」(买家端 C1-C17、卖家端 S1-S5)——子代理改完用 `git checkout -- <file>` 回滚涉及已细调页面的文件。
- **中英混排根因**:未加 data-i18n 的文案被 LanguageSync 词翻译半译("返回Order Details"/"批量Shipping")→ 每页所有静态中文加 data-i18n 键
- **金额三件套**:带 USDT 文本加 data-currency-lock;表头 "(USDT)" 后缀必须写进 translations 值(data-i18n 整段替换会丢 JSX 后缀)
- **timeline 动态文案**:labelKey/timeKey 动态键模式
- **AppleSelect 三端复用**:data-i18n-raw 豁免数据值词翻译;data-i18n-dynamic 值须中文原文(传键名会显示键名);样式须全局版(.sap 作用域只管卖家端);批量换 select 用 delegate_task 并行 + 回滚已细调页
- 完整坑列表与流程见 `references/qavlixor-nextjs-i18n-appleselect.md`

## Batch & export modules(全站统一 · user-mandated)
所有页面的批量操作条 + 导出弹窗统一对标**商品管理页模式**。**任何涉及钱、删除、发货、仲裁、取消的批量操作,绝不用 toast 糊弄**——用户明确批评过("批量发货怎么没有下载模版,批量导出也没有导出弹窗,批量取消也没有风险提示,你怎么卡壳了")。
- **批量条 batchbar**(复用同款):浅灰底 `#FAFAFC` + 细边框,结构 = `已选 N 项` + 竖分隔线 `.sep` + 按钮组(主操作 `.btn.sm.b-act` 黑底白字,次要描边按钮,危险 `.btn.sm.danger` 红字)+ 取消。行 checkbox 用专属 class(商品 `rowck` / 订单 `orowck` / 售后 `asck`),`updSelX()` 切 `.show`,`clearSelX()` 复位。
- **批量发货 / 批量上传 = 三步弹窗**(modal-ship / modal-upload,共用 up-step/upload/up-check/up-errs 样式):① 下载模板(Excel 模板 + 示例数据两个按钮)→ ② 上传虚线框(.upload,点击触发 `fakeXxx()` 显示结果)→ ③ 校验结果(成功/警告/失败徽章 + 行级错误明细)。底部确认按钮。
- **批量导出 = 导出设置弹窗**(modal-export-*):格式单选(xlsx/csv)· 范围单选(当前筛选 N 条 / 全部)· 字段勾选卡(fld-grid,~8 字段默认全选)。
- **批量取消 / 批量删除 / 升级仲裁 = 风险提示弹窗**:`.risk-box`(红底 `--red-soft` + 红字 `#D70015`,列 2-3 条后果)+ 必要字段(如取消原因必选)+ `.btn.danger` 确认。
- **批量同意退款 = 金额确认弹窗**:工单数 + 退款总额 + 到账说明,`.btn.primary` 确认。
- **toast 仅限无风险轻操作**(上架/下架/保存草稿/搜索演示)。

## Seller-center page tuning checklist(what "mainstream parity" means here)
- 工作台:KPI 数据自洽(客单价 = 销售额 ÷ 订单数);趋势图带**上期对比虚线 + 图例 + 末点数值标注**;resize 自适应
- 商品列表:状态页签真实筛选(data-status)、表头排序、库存 0 → 红色"缺货"/ <10 → 橙"仅剩 N 件"(步进器联动)、行内 ⋯ 菜单(预览/复制/删除)、批量条(改价/改库存/上下架/删除)、批量上传弹窗(模板下载→上传→校验结果)、导出弹窗(格式/范围/字段勾选)、"已驳回"状态 + 行内驳回原因
- **运费模板模块**(参照 Shopify / TikTok Shop,用户点名要求):侧边栏「商品订单」组新增「运费模板」菜单(`data-route="shipping-templates"`,新路由必须同步加 ROUTES 表);`view-shipping-templates` 列表:模板名 / 计价规则 / 满额包邮 / 状态(默认·启用)/ 使用商品数 / 操作(编辑·复制·删除,默认模板不可删,删除走风险弹窗提示关联商品自动改回包邮模板);**新建模板弹窗**(580px):名称 + **适用地区多选 chips**(`.region-chips` + `.chip`,`:has(input:checked)` 选中黑框:全球默认/北美/欧洲/东南亚/中东/大洋洲/日韩/南美/非洲,未覆盖地区买家端显示「暂不支持配送」)+ **计价方式三选** 包邮 / 按件(qty)/ 按重量(weight) — `tplFee2()` 切换 `tplQtyBox`(首件+续件+满额)/ `tplWtBox`(首重≤1kg + 续重每 500g + 满额)/ 包邮折叠 + **运费试算器** `calcFee()`(数量+订单金额输入 → 实时运费:按件 `首件+续件×(n-1)`,按重量 `首重+续重×ceil((kg-1)×2)`,满额达标=0,包邮=0)+ 设为默认;**发布商品运费设置三选**(包邮 / **运费模板 tplSelBox 下拉** / 自定义,`shipFee()` 三态互斥切换);物流发货页只读展示 `.tpl-note` 信息条(`运费模板 | 包邮模板 | 订单商品采用包邮,买家免运费` 右对齐灰字)
- 发布商品:步骤条 + 完整度联动(55→70→85→95%),末步按钮变"保存并提交审核";运营数据卡用户已要求**整体删除**(不要"空态"占位,直接去掉);**标题辅助区**(实时字数 X/60 + 状态反馈 空/偏短/良好/接近上限 + 建议格式 + 违禁词提醒,与列表页驳回原因呼应);**图片管理区** img-grid(已传缩略图 + 主图角标 + hover 圆形删除 + 虚线"添加/替换"按钮,占位用 SVG 图片图标非 emoji);四级类目级联下拉不显示"一级/二级"前缀;**发货时限必填字段**(第 4 步物流售后:24/48/72h/7 天下拉)——与订单列表待发货倒计时形成数据闭环(商品发货时限 = 订单倒计时来源);**运费设置字段**(第 4 步,参照淘宝/TikTok):`包邮`(默认,提示转化率+搜索加权)/ `自定义运费` 单选(radio,`shipFee()` 切换显示费用区),费用区 = 首件运费 + 续件运费 + 满额包邮(可留空),规则文案\"运费 = 首件 + 续件×(数量-1);订单 ≥ 满额包邮时运费为 0\"——订单详情\"买家运费\"字段的数据来源,演示订单=包邮 0.00 自洽
- 订单列表:状态页签点击过滤(每单的**信息条行 + 商品行都要加 `data-ostatus`**,过滤时两行一起处理;待发货计数红色高亮 `.cnt.hot`);**待发货超时倒计时**(信息条行右侧"剩余 HH:MM:SS",每秒 tick:行带 `data-sec` 秒数,setInterval 每秒减一并格式化,<1h 变深红,归零显示"已超时,请尽快发货";**倒计时选择器用全局 `.odl`,列表与详情页共用一份 tick**);**订单批量条**(勾选商品行 → 批量发货/批量导出/批量取消,复用商品页 batchbar 模式);搜索维度下拉(订单号/买家/**运单号/SKU**);分页器每页条数下拉(20/50/100);导出设置弹窗与商品页统一(格式/范围/字段勾选);买家留言订单的信息条行加 `.note-tag` 灰标签(可点击跳详情,差距项 #3 的落地)
- 订单详情:page-head 概览(单号/状态/时间)+ 操作按钮(取消/去发货);**订单状态时间线卡**(`.tl-item` + `.tl-dot`,done=实心黑点 / cur=光圈,节点间细连线 `::before`);商品明细用 **72px 商品主图**(见下条);金额结算卡 **= 无佣金**:平台只有提现手续费 1.5%,金额卡只显示 商品金额/买家运费/**预计收入**(= 商品金额+运费,全额进待结算),提示行写明「提现时收取 1.5%」——用户明确纠正过「我们平台没有平台佣金,只有提现手续费,实收应改为预计收入」,全站禁出现"佣金"字样(改前先 grep);**买家留言卡**(`.msg-line` 引用块 + 留言时间,右侧买家信息卡"买家备注"同步同文案);物流信息卡带**发货时限倒计时**(`.odl` 全局联动)+ **内嵌物流轨迹时间线**(待发货订单默认折叠,`toggleTrace()` 展开 5 节点轨迹:揽收→干线→清关→派送→签收;发货后默认展开,数据来自物流接口);售后状态卡
- 物流发货:表单(物流公司下拉+其他/运单号/发货仓/预计送达时限下拉/备注);顶部**发货时限倒计时提示条** `.ship-alert`(橙色**边框方框** + 时钟 SVG `.sa-ic` + 三段式排版:标签 `.sa-label` / 倒计时 16px 红粗 `.odl` / 右侧灰说明 `.sa-tip`);**物流公司-运单号匹配校验**:`trackRules` 常量表按公司(YunExpress `^YT\d{8,12}$` / DHL `^\d{10}$` / FedEx `^\d{12}$` / UPS `^1Z[A-Z0-9]{16}$` / 其他 `^[A-Za-z0-9]{8,20}$`),切公司 `setTrackRule()` 只更新 placeholder + 清空输入(**不加 err-msg 红字提示**——用户明确要求"不用在方框后面提示,不按规定填的直接拦截即可"),`chkTrack` oninput 红框校验,`doShip` 提交前按**当前所选公司**规则拦截;~~运费承担~~(曾加过发货时单选 卖家/买家承担,用户要求**删除**:与商品「运费设置」重复,运费归属统一由商品发布页管理,发货页只保留运费模板只读行);**包裹拆分**(`pkgBox` 多行:包裹 N + 件数 + 运单号;`addPkg/delPkg`;`updPkg` 实时合计,合计≠订单件数时红框+提交拦截;**网格布局** `.pkg-row{grid-template-columns:64px 96px minmax(0,1fr) 32px}` 列对齐,运费模板行 `.tpl-note` 独立信息条与包裹区拉开间距——用户嫌"太拥挤"后的排版定稿);**收件人核对卡**(收货人/电话/地址 + "发货前核对"提示,主流发货页标配防错发);**批量发货工作台** `view-batch-ship` 独立页(订单列表页头「批量发货」按钮进入):待发货表(行带 `.odl` 倒计时,全局 tick 自动覆盖)+ 勾选批量条(`bck`/`updSelB/toggleAllB/clearSelB`) + 「导入运单 Excel」/「批量发货」按钮**复用 `modal-ship` 三步弹窗**;**保存并发货 `doShip`**:公司规则校验运单号→包裹件数合计校验→更新左卡状态徽章(`#shipStatus`)→轨迹节点推进(商家发货 done、运输中 cur)→toast;右栏=收件人核对 + 物流轨迹(统一 `.tl` 样式);**打印面单用户已要求移除**("暂时用不上",勿默认加回;modal-label 与 `.ls-*` 样式已删,再做发货流程不要自带面单打印)
- **商品主图/缩略图语义**:订单详情商品明细 = 商品主图 → **72px 方形大图**(`.pthumb-lg`,浅灰底+细边框+圆角 12px)+ 标题/规格/SKU 三行信息,对齐 TikTok/淘宝商品卡;列表页缩略图(商品列表/订单列表/消息面板)= 同一套**内联 SVG 产品插图**(每个演示商品一个专属图:键盘/音箱/数据线/加湿器/鼠标/支架,`.thumb svg{width:58%}` 由外层容器控尺寸),不用装饰性字符;后续接真实图片只需把 SVG 换成 `<img>`
- **售后列表 = 商品卡式布局**(用户点名"对标主流做成商品卡那种"):`.as-card` 三段 = `.as-top`(勾选 checkbox + 工单号 + 状态徽章 + 类型 tag + `.as-timeout` 右对齐时限)/ `.as-body`(左 `.as-prod`:**48px 商品主图 + 标题 + 规格 SKU**(`as-prod-t`/`as-prod-s`),右 `.as-main` 诉求 `.as-desc` + 元信息 `.as-meta` 关联订单/买家/申请金额)/ `.as-ops` 底部操作;**超时自动升级提示**:处理中卡时限红字「剩余 4 小时 · 超时自动升级仲裁」;已拒绝卡「已拒绝 · 买家可申诉,申诉后可改判」+「**改判退款**」主按钮;平台介入卡按钮 disabled + 「平台处理中 · 商家不可操作」;已退款卡终态「已完成 · 日期」;批量条(批量同意退款 / 批量升级仲裁 / 导出)+ 卡勾选
- 售后详情:左侧 工单信息(类型/金额/买家/诉求)/ **买家证据卡**(SVG 占位 `.evid svg` + `.vid-tag` 视频角标 + 计数徽章「2 图 · 1 视频」,禁 emoji)/ 处理时间线(统一 `.tl` 样式,3 节点:提交→系统通知→商家处理中 cur);右侧**处理操作四态联动表单** `asForm()`:同意退款(退款原因下拉 5 项:质量问题/描述不符/错发漏发/运输损坏/买家原因 + 金额 + 说明)/ 拒绝退款(拒绝原因下拉 4 项:举证不足/已使用人为损坏/超期/其他 + 理由 + **商家举证材料 `img-grid`**(图片+视频占位,最多 6 个,"举证材料将同步给平台仲裁参考")+ 内部备注)/ 请求补充证据(补充说明)/ **升级仲裁(`asRisk` 风险框 + 提交按钮变 `.btn.danger`「确认升级仲裁」→ `asSubmit()` 打开 modal-arbitrate)**;`asSubmit()` 按所选操作分别反馈

## Related
- `claude-design`(通用设计品味/流程)— overlap is fine; this skill is user/workflow-specific + JS pitfalls
- `design-md`(token 规范文件)
