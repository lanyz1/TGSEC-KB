# 卖家端审核与功能落地(2026-08-06)

## S 阶段进度(S1-S15 全部完成)
S1 工作台 / S2 商品管理 / S3 订单管理 / S4 订单详情 / S5 物流填写 / S6 批量发货 / S7 运费模板(零改动) / S8 售后工单 / S9 售后详情 / S10 通知中心 / S11 入驻认证(零改动+删偏好语言字段) / S12 买家消息(零改动) / S13 资金中心 / S14 账户设置 / S15 商品编辑页。卖家端侧栏 6 组全审完。

## S15 商品编辑页修 58 个缺失翻译键(commit e42958d)
**症状**:英文态整个表单 placeholder/按钮/标签显示**原始键名**(`seller.productForm.titlePlaceholder` 等)——translations.ts 里 `seller.productForm.*` 键一个都不剩(批量脚本整块误删)。**排查法**:python 正则提取组件全部 data-i18n 键 → 比对 translations.ts → 58 个全缺。**修复**:从组件提取 57 个键+中文原文(文本节点 + placeholder 两种属性顺序都要匹配)+ 补 1 个模板字符串 placeholder → zh/en 双区插入 → zh 值里 `"规格"` 英文双引号炸 TS(坑 #32 第三次)成对换「」→ tsc + 英文态验证键名消失。类目级联按钮 ariaLabel=\"一级类目\" 等是 aria-label(无障碍名),视觉显示选中类目名,可接受不改。

## 关键功能落地
- **右上角通知铃铛**(commit 41a6982):`components/NotificationBell.tsx` 挂 PortalShell 顶栏(LanguageSwitcher 旁,卖家端+管理端共用)。API `/api/seller/notifications-recent`(最近 6 条+7 天计数,60s 轮询)。红徽章/白面板 14px 圆角/点外部关闭/View all → /seller/notifications。**未读计数=7 天内 NotificationMessage 条数(表无 unread 字段,已读是一次性清圆点)**。坑:未读"Unread {n}"占位被整段替换吃 → 拆 label 键。
- **保证金余额划转**(commit 65a3b70 + fbe5a1a + 48f52a1,资金模型落地):缴纳=从可提现余额划转(新 API `/api/seller/deposit/transfer`,创建 SellerDeposit kind=pay status=approved + 扣钱包 + refreshSellerWallet);退还=划转回余额(refund API status 改 approved 即时生效,无审核);独立页 `/seller/transfer`(划转面板+划转记录表),导航"冻结明细"→"余额划转"。**核心:余额公式纳入保证金**——`funds-repository.ts` 两处(prismaSnapshot ~112 行 `- deposit.balance.net`;refreshSellerWallet ~219 行 `- depositPaidTotal`)否则重算会还原划转。退还时 net 减 → 余额自动恢复("超额未冻结可转回"闭环)。**API 校验余额用 getFundsSnapshot 计算口径(页面显示值),别读 SellerWallet 表(表值是旧口径,划转会误判余额不足)**。
- **S13 保证金卡/页收尾**:保证金 tab 删"应缴/已缴/差额"重复行(总览卡已有)→ ⓘ 悬浮提示(CSS .info-dot-wrap:hover .info-pop,内容=档位构成+规则列表,data-i18n-raw 防半译)→ 保证金 tab 底部加保证金流水表(提为 `depositRecordsCard` 变量,deposit/depositWithdraw 两 tab 共用)→ 转回面板删顶部三列。
- **聊天界面删快捷操作**(commit 0c430f9):ChatContextPanel 删快捷操作 ctx-card(物流公司/单号/原因/退款/标记发货/发起退款/取消订单)+ 清理 state/submit/import。API /api/messages/[id]/actions 保留(其他端可能用)。
- **卖家昵称/店铺名需管理端审核**(commit df7baad):见 SKILL.md"卖家端审核流模式"。

## S14 账户设置 i18n(commit 2f637d8)
SellerAccountSettings 40+ 处 data-i18n(5 卡标题/表单标签/按钮/3 个密码 placeholder/通知偏好 5 开关 labelKey+hintKey/实体状态/关闭清单拆键/未满足拆数字+label),65 键 zh/en。PasswordInput title 改英文。**教训:第一轮批量脚本漏写盘(见 SKILL.md 批量脚本纪律)**。

## 环境坑复现
- dev 反复崩(本周 8 次,Jest worker/EPIPE/未知):用户访问时崩 → 先 `process poll` 看进程再 `netstat` 清端口重启。用户已确认"崩了自动重启"。
- **误操作 404 排查**:`/seller/account（<EMAIL-REDACTED>）` 全角括号邮箱路径 404 是用户复制粘贴带入,不是 bug——先看 dev 日志 `GET ... 404` 的 URL 再判断。
- **prisma generate 双轨方案**:见 SKILL.md 环境坑(新 make-dev-schema.mjs 方案替代旧 sed 方法)。

## S15 类目行压缩布局与截断修复(commit 6112f67 + 64c0d8d)
用户要求"新类目名搞个短框放到第一行右边"——类目行 = 4 个 AppleSelect + 自定义输入框同行。
- **容器宽度不足放不下时的压缩**:card-b 内 flex 容器仅 489px,原 4 个自适应 select(97×3+157)+输入框 160 = 640px 必换行。解法 = 4 个 AppleSelect 固定 `style={{width:84}}` + 输入框 `width:120` → 480px 同行(84×4+3×8gap+120=480)。**教训:flex 同行放不下 → 先量容器宽 + 各子元素宽(JS `getBoundingClientRect`),按总宽反推每元素固定宽度,不要用 flexWrap 退让(用户明确要同一行)**。
- **⚠️ 固定窄宽下长 label 截断**:第四级 option label"➕ 其他（自定义）"(7 字+icon)在 84px 内显示成"其他（自定义"截断。解法 = **缩短 label**"➕ 其他"+"➕ 其他"完整显示。**教训:选项 label 在固定窄下拉里截断时,缩短 label 文本比加宽下拉更优(加宽会重新挤爆同行布局)**。
- **输入框 placeholder 显示空**:新类目名输入框 placeholder 无翻译键,英文态词翻译异常 → 加 `data-i18n-placeholder="seller.productForm.customCatPlaceholder"` 键(zh"新类目名"/en"New category name")。**教训:任何输入框 placeholder 要么纯英文/数字,要么必须带 data-i18n-placeholder 键,否则英文态显示异常/键名**。
- **又一处键缺失**:步骤条 `seller.productForm.step1-4`(基本信息/图片与参数/价格与库存/物流与发布)同样被误删 → 补 4 键。**排查英文态页面所有可见键名文本逐个补,58 键大修后别忘小键**。
- 验证方式:JS 点开 AppleSelect 菜单(菜单项是真实 button 元素,JS 派发 click 不触发 React 事件——必须用 browser_click 真实点击或用 `dispatchEvent(new MouseEvent('mousedown'...))` 序列),选"➕ 其他"后量输入框 `getBoundingClientRect().top` 与最后一个 select 的 top 差值 <12px = 同行达标。

## 数据归属排查模式(页面空 vs 数据库有数据)
批量生成测试数据(运费模板/售后工单)时"库里 count=5 但页面显示 0"的排查:
1. **先 node 直查 prisma 确认数据在库**(`afterSaleCase.count()` / `findMany`),排除渲染层问题。
2. **页面 SSR 层确认 afterSaleCases 为空数组**(浏览器 fetch 页面 HTML 看 KPI 数字,别只看视觉)。
3. **查 resolveSellerStore(currentEmail()) 解析出的店铺**:demo 卖家账号(<EMAIL-REDACTED>)的 SellerAccount→Store 关联是"**演示查看店铺**"(cmsb0n9ys0004upd4g4p7bjoj),而售后/运费模板历史数据全在旧店"北线好物店"名下 → `where: {storeName: scope.storeName}` 查"演示查看店铺"自然 0 条。**根因 = 数据归属店铺错误,不是查询/渲染 bug**。
4. **修法**:数据插到当前账号实际归属的店铺名下(O-DEMO-O1~O5 订单正是"演示查看店铺"的,关联它们),或把已有数据 UPDATE 到正确 storeName。
5. **教训:侧栏显示"北线好物店 S-3002"是客户端 account API 的另一数据源,服务端 resolveSellerStore 才是页面查询真源——两者可能不一致,排查先查服务端 scope 解析结果**。运费模板同理:写 `Store.shippingTemplatesJson` 必须写对 storeId(演示查看店铺),写旧店页面空。
