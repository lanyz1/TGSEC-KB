# 卖家端页面/组件全景 + 交互清单格式（2026-08-07 全量提取）

源：`app/seller/` 34 页 + `components/seller/` 34 组件 + chat 组件 + PortalShell 壳，已逐一读源码产出全量交互清单。

## 交互清单交付格式（用户指定，复用）
```
### 页面路径（如 /seller/funds）
- [元素类型]「文案」：行为描述；边界/异常
```
- 元素类型：按钮/链接/输入/下拉/勾选/单选/页签/步进器/批量栏/表头/段式 tab 等
- 「文案」= 界面原文（中文）；行为=触发后做什么（含 API 端点）；边界/异常=校验拦截、禁用条件、空态、锁定态、notFound 等
- 覆盖一切可交互元素，不写测试步骤；组件级清单要把 admin/buyer 端组件单独标注
- 全量提取流程：find app/seller + components/seller → 按 wc -l 分批 read_file 并行读 → 补查被引用的共享组件（SellerProductManager/SellerProductForm 在 components/ 根、chat 在 components/chat）→ 导航壳看 PortalShell

## 卖家端页面 → 组件映射
| 路由 | 主要组件 | 要点 |
|---|---|---|
| /seller/login | SellerLoginForm | 默认邮箱 <EMAIL-REDACTED>；忘记密码仅提示不跳转 |
| /seller/register | SellerRegisterForm | 3 协议全勾才可提交；密码强度条 |
| /seller/application-status | —（静态） | Urge Review/Back to Login 均回 /seller/login；申请号硬编码 RB-20260731-0088 |
| /seller/approved | —（静态） | 进后台/创建商品 |
| /seller/onboarding | OnboardingWizard + OnboardingParts | 4 步单页向导；submitted/approved/suspended 整表单 disabled；rejected 可重提 |
| /seller/onboarding/{point-of-contact,primary-representative,review,submitted} | — | 全部 302 → /seller/onboarding 或 application-status |
| /seller | SalesLineChart + todo + 最近订单 | 无店铺时渲染开店引导卡 |
| /seller/products | SellerProductManager（在 components/ 根，不在 components/seller/） | 状态筛选/类目筛选/排序/库存步进器/批量改价改库存上下架删除/导出 CSV 真实下载（Blob）、Excel 待接入/批量上传待接入 |
| /seller/products/new、/seller/products/[id] | SellerProductForm（components/ 根） | 4 步：类目 4 连级联+自定义类目、标题 60 字+促销词检测（best/cheap/最低价/最便宜/全网最/第一）、SKU 表、参数对≥3、运费三选；已审核商品编辑态=上下架+保存修改（免审核）；非本店商品 notFound |
| /seller/orders | SellerOrdersTable + SellerOrderExportButton | 页签 ?status=；搜索 GET 表单；仅待发货可勾选/批量；批量取消=提示需逐单；导出任务提示（后端待接） |
| /seller/orders/[id] | SellerOrderCancelButton + SellerTrackingTimeline | 待发货可取消（罚扣 5% 最低/最高封顶，取消原因必填）；物流卡"查看物流"折叠轨迹 |
| /seller/orders/[id]/logistics | SellerFulfillmentForm | 物流公司 14 项（Other→自定义输入）；单号 6-40 位字母数字短横线；拆包件数和必须=订单件数；保存并发货/仅保存草稿（草稿→待揽收） |
| /seller/batch-ship | SellerBatchShipList | CSV 模板下载预填订单号；解析跳表头/示例行；>500 行报错；确认发货逐单结果 |
| /seller/aftersales | SellerAfterSalesList | KPI 4 卡；锁定工单（平台介入/已退款/已关闭）不可勾选；批量同意退款/升级平台 |
| /seller/aftersales/[id] | AfterSaleActionForm | 4 动作 radio（同意/拒绝/补充证据/升级仲裁）；同意→金额 0~订单总额；拒绝→理由必填+举证≤6+内部备注；二次确认；已拒绝 locked 仍可改同意/补充 |
| /seller/funds | SellerFundsCenter + SellerChargePanel + SellerWithdrawRequestForm + SellerDepositTransferPanel + DepositWithdrawPane + SellerDepositPayLink | 6 tab（?tab=）；充值仅 USDT 真实（其他通道跳 /checkout/payment-restricted）；提现 4 方式（Bank/Wise 部分字段标"演示"）、金额≥50≤可提现、验证码 60s；保证金差额/取消率提示；转回余额需条件（未完结订单/关店） |
| /seller/funds/{deposit,withdraw,ledger,frozen} | — | 302 → /seller/funds?tab=… |
| /seller/balance | — | 302 → /seller/funds |
| /seller/transfer | SellerDepositTransferPanel | 划转记录表 |
| /seller/shipping-templates | SellerShippingTemplates | 真实后端（Store.shippingTemplatesJson）；区域 chips 9 区至少 1；删除提示自动切默认模板 |
| /seller/shipping-settings | SellerShippingSettings | **纯前端 state 无后端**（数据不持久化）；新仓名可添加进列表；设为默认唯一 |
| /seller/account | SellerAccountSettings | 昵称/店名变更走 /api/seller/change-requests 管理端审核（pending 时输入禁用）；通知偏好/主体变更/闭店申请=待接；闭店清单 4 项真实 |
| /seller/notifications | SellerNotificationList | 全部已读=本地态（后端待接）；tab ?tab= |
| /seller/messages、/seller/messages/[id] | components/chat/ChatWorkspace（ChatList/ChatWindow/ChatComposer/ChatContextPanel） | 轮询 4s/10s；Enter 发送；常用语仅卖家/客服；图片预览遮罩；失败重试；[id] 进入即已读；无效 id notFound |

## 关键架构事实（排查/改版前必知）
- **`app/seller/layout.tsx` 是空壳**（`return children`）——卖家侧边栏/顶栏导航在 `components/PortalShell.tsx` 的 `sellerNavGroups` + `ConsolePortalShell`（分组折叠按钮、当前页高亮、角标 60s 轮询 /api/seller/nav-counts、顶栏"切换账号"→/seller/login）
- **components/seller/ 目录 ≠ 全是卖家组件**：AdminWithdrawalForm / AdminLogisticsUpdateForm / AdminSellerReviewForm / AdminProductReviewForm / AdminAutoConfirmButton / AfterSaleQuickActions 是管理端用；BuyerAfterSaleRequestForm 是买家端用（卖家端测试时勿按卖家逻辑断言）
- **SellerProductManager / SellerProductForm 在 `components/` 根目录**（不在 components/seller/），做商品页任务别找错目录
- 消息页复用买家端同款 ChatWorkspace，role="seller" 区分
- Modal 原语（components/seller/Modal.tsx）：Esc/点遮罩关闭、锁滚动、portal 挂 body；二次确认模式"再次点击确认"多处复用
- 服务端组件传数据给 client（OrderRow/ProductRow 等）→ 交互全在 client 组件
- 待接清单（演示/占位，改版勿当真后端）：通知偏好、闭店申请提交、主体变更、提现地址簿、Bank/Wise 到账币种与收款银行、商品批量上传 Excel 导入、导出任务（订单/售后/资金流水/月结单 PDF 均为"提交任务"提示）、发货模板（SellerShippingSettings 全本地态）
