# 管理端组件 i18n 轮(2026-08-06,components/admin 下 10 组件)

承接 A1-A16 页面轮之后的组件轮(规则见 SKILL.md「管理端批量 i18n 落地模式」+ 本轮新增坑,均已并入 SKILL.md)。

## 本轮成果:10 组件 202 键(zh/en 双区 = 404 行),tsc EXIT 0,键双区存在性 PASS、文本节点裸中文 0 残留
| 组件 | 键数 | 说明 |
|---|---|---|
| AdminTestOrdersClient | 49 | 混合节点最多:目标店铺（已选 n / 共 m）、全选+筛选结果+（n）、n 单·m 商品、SKU：x·数量 xN、已选店铺 {join} 没有…、aside 计数「 个」;2 处 USDT 加 data-currency-lock |
| AdminLogisticsTestPanel | 23 | 六面板同构(eyebrow/title/status 三元/4 格 grid/chip/actions) |
| AdminChainTestPanel | 24 | 面板已有 data-currency-lock=""(article 级),金额 label 不用再加 |
| AdminMailTestPanel | 25 | 三重三元 customReady/smtpReady/waiting |
| AdminSmsTestPanel | 22 | 签名/模板 三元是 `a||b ? "已填写" : "未填写"`;placeholder +86 <PHONE-REDACTED> 无中文不标 |
| AdminAlertTestPanel | 18 | |
| AdminStorageTestPanel | 18 | |
| AdminDepositTopUpForm | 9 | 表单已 data-currency-fixed="USD",金额 label 仍加 data-currency-lock 保持精确 USDT |
| AdminChangeReviews | +5 | 原 10 键已存在;补 loading/notePlaceholder/approve/reject/processed(processed 拆 `已处理{row.reviewedAt ? ...}`) |
| AdminPaymentReviewForm | 9 | section 已有 data-currency-lock="" |

## 本轮新增模式(已并入 SKILL.md,简要索引)
1. 全角括号独立成键 parenOpen/parenClose(zh（／）→ en (/)。
2. 相邻 span 空格进 en 值(selectFiltered en「 filtered」;countUnit zh「 个」/en「」空串)。
3. en 值含 ASCII 双引号 → 行构建时统一转义 `\"`,别断言无引号。
4. 表达式位探针补扫 `([?:]) *"([^"]*中文[^"]*)"`(文本节点探针盲区)。
5. 行尾以 HEAD 为准:本仓库 HEAD 是 CRLF,python 字节级读写保真;patch 工具方向可反(本次 CRLF→LF)。

## 豁免清单(表达式位/数据位命中的人工分类,本轮全部命中均豁免)
setMessage/window.alert 的 JS 串、labels 配置键记录(如「平台 TRC20 收款地址」「SMTP 地址」)、AppleSelect options 值(自动/待发货/— 请选择店铺 —/（已关店）)、DynamicText 渲染数据(物流/售后/状态值)、JS 注释。

## 待办(components/admin 剩余,下一轮)
AdminDepositQuickActions、AdminOrderFreezeButton、AdminProductQuickReview、AdminSellerQuickReview、AdminWithdrawalQuickActions。
⚠️ AdminMerchantManager.tsx 由并行任务负责(工作区已 M,勿动勿回滚)。
