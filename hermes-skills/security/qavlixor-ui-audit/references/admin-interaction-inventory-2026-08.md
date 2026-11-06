# 管理端全部页面交互元素全量清单（2026-08-07 功能层审计）

源码驱动盘点：app/admin 19 个 page + components/admin 17 组件 + components/seller/Admin* 8 组件 + PortalShell 管理壳 + 12 个关键 API 路由。后续管理端功能改动/QA 验证直接对照本清单，不必重读全部源码。

## 页面 → 组件映射
- /admin（总览）→ page.tsx 服务端直渲染（无客户端组件）
- /admin/merchants → AdminMerchantManager.tsx；/admin/merchants/[id] → 服务端直渲染
- /admin/sellers → AdminSellerQuickReview.tsx；/admin/sellers/[id] → components/seller/AdminSellerReviewForm.tsx
- /admin/products → AdminProductQuickReview.tsx；/admin/products/[id] → components/seller/AdminProductReviewForm.tsx
- /admin/orders → AdminOrderFreezeButton.tsx + components/seller/AdminAutoConfirmButton.tsx；/admin/orders/[orderNo] → components/admin/AdminPaymentReviewForm.tsx
- /admin/withdrawals → AdminWithdrawalQuickActions.tsx + AdminBuyerWithdrawalActions.tsx；/admin/withdrawals/[id] → components/seller/AdminWithdrawalForm.tsx + FileUploadButton
- /admin/deposits → AdminDepositQuickActions.tsx + AdminDepositTopUpForm.tsx；/admin/deposits/[id] → AdminDepositQuickActions.tsx
- /admin/aftersales → components/seller/AfterSaleQuickActions.tsx；/admin/aftersales/[id] → components/seller/AfterSaleActionForm.tsx（admin 动作 3 项）
- /admin/users → AdminUserManager.tsx（加余额弹窗/禁用启用）
- /admin/categories → 页面内联客户端组件；/admin/change-reviews → AdminChangeReviews.tsx
- /admin/test-orders → AdminTestOrdersClient.tsx
- /admin/logistics → 服务端直渲染；/admin/logistics/[id] → components/seller/AdminLogisticsUpdateForm.tsx
- /admin/contacts、/admin/roles、/admin/roles/edit、/admin/logs → 服务端直渲染（零交互或纯只读）
- /admin/settings → AdminMailTestPanel/AdminChainTestPanel/AdminLogisticsTestPanel/AdminStorageTestPanel/AdminAlertTestPanel
- /admin/login → components/seller/LoginSubmitForm.tsx + PasswordInput

## 全局壳（PortalShell admin）
- 侧栏 18 导航项（6 组：经营概览/商户管理/审核管理/交易资金/运营服务/系统权限），badge 60s 轮询 /api/admin/nav-counts，99+ 封顶
- 顶栏：LanguageSwitcher（localStorage + qavlixor-language-change 事件，点外部关闭）、NotificationBell（/api/admin/notifications-recent 60s 轮询、红点 99+、点外部关闭、「查看全部」→ /admin/notifications **页面不存在——源码缺口**）、「切换账号」→ /admin/login
- 身份卡 → /admin（/api/admin/identity 实时加载）；IdentityGuard 未登录拦截

## 每页交互元素要点

### /admin 总览
- 链接：处理审核/生成校验订单/进入打款队列/查看全部×3/操作日志/今日重点 3 队列/KPI 4 卡（跳对应队列页）/列表项跳详情
- 只读：待人工处理金额（1.5% 手续费说明）、运营管理员角色卡

### /admin/merchants
- 筛选：类型/状态/风险 3 个 AppleSelect（切换类型时清空勾选）+ 搜索框（4 字段前端过滤）+ 计数
- 批量栏：每行 checkbox + 全选本页（勾满反选）+「为选中店铺生成订单」（未选 disabled，跳 /admin/test-orders?stores=逗号拼接）+「批量追加备注」（仅弹提示，无功能）
- 行内编辑：「编辑/收起」展开——店铺类型/风险/状态下拉 + 后台备注输入 + 「保存资料」（PATCH /api/admin/merchants/[id]，枚举校验 400、无内容 400、404）
- 操作列：详情 / 店铺页 / 生成校验订单

### /admin/sellers 与 [id]
- 列表：进入审核链接 + 快捷「通过/驳回」（POST review；已通过 disabled；仅 submitted 可审否则 409；approve 不覆盖 closed/restricted/suspended）
- 详情：4 个资质文件「查看文件」（新窗口）、核验 checklist 4 项（纯前端）、AdminSellerReviewForm（意见 textarea + 审核通过/驳回并通知/返回列表）

### /admin/products 与 [id]
- 状态 tab（?status=）+ 类目级联筛选（?category=，两级）+ 分页（每页 40，?page=）
- 快捷「通过上架/驳回修改」（仅 submitted_for_review 可审否则 409）+ 审核详情
- 详情：审核清单 4 项（纯前端）+ AdminProductReviewForm（审核通过并上架/驳回修改/返回列表）

### /admin/orders 与 [orderNo]
- 「自动确认到期订单」（POST /api/orders/auto-confirm，force:false，显示已处理 N 个）
- 每单：「监管详情」「处理售后」（有售后时）「冻结结算」（POST freeze → disputed + manual_frozen，需 risk 权限；release 分支解冻）
- 详情：AdminPaymentReviewForm（paymentStatus≠paid 才渲染）——TXID 输入（自动带入买家提交值）+ 备注 + 确认到账/驳回凭证；**驳回仅限 pending_payment+pending（否则 400 走售后/冻结）**；confirm 带 TXID 走链上核验（failed 400）；closed 订单不可确认收款

### /admin/withdrawals 与 [id]
- 卖家卡：处理打款链接 + 快捷「标记处理中/驳回」（终态不渲染；API 仅 submitted/paying 可处理，终态 400，并发条件更新 409）
- 买家区块：submitted 单显示「打款」（无确认直接执行）/「驳回」（**window.confirm 确认**）；打款释放冻结、驳回解冻回余额；条件更新防双处理（409）
- 详情：**服务端权限守卫——非 finance 角色渲染「无权限」页**；AdminWithdrawalForm：处理状态下拉 + 凭证编号 + 凭证文件上传（JPG/PNG/PDF → /api/uploads 回填 URL）+ 备注 + 确认已打款/驳回提现；财务核对 checklist 4 项（纯前端）

### /admin/deposits 与 [depositNo]
- KPI 4 卡 + 类型 tab（?kind= pay/refund/deduction）
- AdminDepositTopUpForm：店铺下拉（已关店标记）+ 金额（min=1）+ 备注（≤80 字）+ 确认充值（前端校验未选店/金额<1；API 金额 1~100000，立即 approved 计入净额）
- 卡片：查看详情 + 快捷「确认到账(pay)/同意退还(refund)/驳回」（仅 pending_review 且非 deduction）；**refund approve API 强制要求 payoutVoucher 但快捷操作无凭证输入框 → 列表同意退还会 400，须走详情**；已终态不可再改（409）
- 详情：该店应缴/已缴净额/未缴差额/档位构成/全部记录

### /admin/aftersales 与 [id]
- 列表快捷「强制退款/关闭售后」：**两次点击确认**（首点变红「确认执行」+提示，次点提交，refundAmount=订单总额）
- 详情：已退款/已关闭 → 完结锁定面板无表单；否则 AfterSaleActionForm admin 版：单选组 强制退款（退款原因下拉+金额 0~总额+说明必填）/退回商家处理（说明必填）/关闭售后（说明必填，danger）——均需二次确认「再次点击确认XX」+「保存草稿」（仅本地提示）+「取消」；拒绝态显示锁定提示条
- API 边界：admin 需 arbitration 权限；终态锁仅 已退款/已关闭（409）；退款需订单已付款（400 改关闭售后）；累计退款≤订单总额（400）；并发防双退（409）；平台强制退款自动罚扣保证金 ×5% 最低 1 最高 100 + 通知卖家；关闭售后释放结算、订单还原 completed/closed

### /admin/users
- 筛选：类型/状态下拉 + 邮箱昵称搜索；KPI 4 卡
- 「加余额」（员工行 disabled）：弹窗（金额默认 100 min=1 + 备注 ≤120 + 确认增加/取消；遮罩点击关闭；弹窗互斥）→ POST balance（0<amount≤1,000,000；卖家进 SellerWallet+MR(paid)，买家进 BuyerWallet+BR(approved)）
- 「禁用/启用」：**禁用 window.confirm，启用无确认**；PATCH status；@globalmart.test/@seller.local 测试账号和 root 超管不可禁用（400）

### /admin/categories
- 每行「通过/驳回」：POST /api/admin/categories；成功后行移除；仅 pending 可审；直营店自定义类目免审不出现

### /admin/change-reviews
- pending 行：备注输入（共享 state，提交清空）+「同意/驳回」；全局 acting 锁防并发；失败 window.alert
- approve 事务内生效：nickname→User.displayName+SellerAccount.contactName，storeName→Store.name；通知卖家 notificationMessage；仅 ops 权限

### /admin/test-orders
- 店铺筛选框 + 「全选（筛选结果 N）」（只选当前筛选结果）+「清空已选」（无选择 disabled）
- 店铺 checkbox（取消勾选自动清该店已选变体；?stores= 参数预选）+ 指定商品变体 checkbox（规格值/SKU/价格；不勾=随机轮换）
- 每店数量 number（钳制 1~20）+ 状态下拉（自动/待发货/运输中/已签收/售后中）+ 时间范围 2×datetime-local（**前端转 ISO UTC 再提交**；API：end>start、90 天内、不晚于当前）
- 「生成批量订单」：前端校验未选店/无已上架商品；成功提示含跳过店铺；预览区实时同步（SKU 口径 preview/variant 一致）

### /admin/logistics 与 [id]
- 列表：查看详情/订单监管链接；详情：AdminLogisticsUpdateForm——状态下拉（待揽收/运输中/已签收/异常）+ 事件说明 textarea + 保存物流事件（同步订单状态）

### /admin/contacts、/admin/roles、/admin/roles/edit、/admin/logs
- contacts：纯只读时间线（无交互）
- roles：卡片「查看权限」→ /admin/roles/edit?role=；edit：角色名输入 readOnly + 权限 checkbox 全 disabled（**无任何可编辑控件**）+ 返回角色
- logs：纯只读双时间线（各 80 条）

### /admin/settings
- 规则输入框全部 readOnly
- 4 个诊断面板（+邮件 5 个）：输入 + 测试/发送按钮（空输入 disabled）+ 刷新状态按钮；存储面板「上传测试文件」仅 ready 可点；告警面板「发送测试告警」仅 ready 可点

### /admin/login
- 邮箱 + 密码（PasswordInput）+「进入总后台」（POST /api/auth/login role=admin，失败红字，?next= 回跳）

## 关键 API 状态机速查（边界真源）
| API | 权限 | 关键边界 |
|---|---|---|
| sellers/[id]/review POST | ops | 仅 submitted 可审（409）；reject 需 reason；approve 不覆盖 closed/restricted/suspended |
| products/[id]/review POST | ops | 仅 submitted_for_review（409）；reject→draft/rejected，approve→published/approved |
| merchants/[id] PATCH | ops | 枚举校验 400；无内容 400 |
| payments/[orderNo] POST | finance | reject 仅 pending_payment+pending（400）；closed 不可确认；TXID 链上核验 failed 400 |
| withdrawals/[id] POST | finance | 仅 submitted/paying（400 终态）；updateMany 条件写 count≠1→409；成功后 refreshSellerWallet |
| buyer-withdrawals/[id] POST | finance | action 枚举 400；仅 submitted 可翻终态（409）；冻结不足回滚+400 |
| orders/[orderNo]/freeze POST | risk | freeze/release 双分支 |
| deposits/[id] PATCH | finance | deduction 不可审（400）；终态不可改（409）；refund approve 必须 payoutVoucher（400） |
| deposits/top-up POST | finance | 1~100000；立即 approved |
| users/[id] PATCH | ops | 测试账号/root 不可禁用（400）；员工走 AdminUser upsert |
| users/[id]/balance POST | finance | 0<amount≤1,000,000；按角色分流钱包 |
| change-reviews/[id] POST | ops | 仅 pending_review（400）；事务生效+通知 |
| categories POST | ops | 仅 pending（400） |
| test-orders POST | ops | count 1~20；时间范围校验；仅 published+approved 商品 |
| aftersales/[id] POST | admin: arbitration | 终态锁 已退款/已关闭（409）；退款需已付款；累计退款上限；并发防双退；强制退款罚扣保证金 |
