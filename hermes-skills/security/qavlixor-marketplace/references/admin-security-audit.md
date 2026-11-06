# 管理端安全审计完整缺陷清单（2026-08-07 全量扫描）

范围：app/admin 页面 + app/api/admin 全部 33 路由 + lib/api-auth 权限体系 + components/admin + prisma/schema.prisma。产出 21 项（7 严重 / 9 中 / 5 低）。**修复状态见 `security-audit-fixes-2026-08.md`**。

## 严重（7）
- **S1 storage/health 完全无鉴权**（route.ts GET/POST）——全项目唯一无 requireRole 的 admin 路由；GET 暴露全平台数据计数、POST 触发 41MB 文件读写落盘。✅ 已修（2026-08-07）
- **S2 校验订单污染资金**：test-orders 未指定 storeIds 时 `where:{}` 全平台生成；syncOrderToPrisma 写 paymentStatus=paid；refreshSellerWallet 不过滤 `orderChannel="validation"` → 校验单直接计入卖家可提现余额，7 天自动完成后 30 天全额可提现。✅ 已修（资金口径排除 validation + 时间范围限 90 天内）
- **S3 卖家提现处理无状态机**（`api/withdrawals/[id]`）：paid↔rejected 任意互切 → 已打款改驳回=双倍赔付。买家侧有守卫（status!=="submitted" 拦），卖家侧缺失。✅ 已修（仅 submitted/paying 可处理 + updateMany 条件写）
- **S4 confirmIntent 可确认已取消/已驳回单**（lib/payment-intents.ts）：wallet 分支只拦 paid，cancelled 充值直接置 paid 余额增加；deposit 分支只拦 approved，rejected 缴纳改 approved；expired 意向无拦截。✅ 已修（wallet 拦 cancelled/rejected；deposit 拦 kind≠pay 或 rejected/refunded/cancelled）
- **S5 禁用账号失效**：users/[id] PATCH 写 `status:"disabled"`，但 login 只拦 `deactivated`；requireRole buyer 兜底完全不查 User.status → 禁用后 7 天 JWT 内照常下单提现。✅ 已修（requireRole 查 User.status 拦 disabled+deactivated；login 语义统一）
- **S6 直营店**：lib/direct-stores.ts 明文共享密码 `DIRECT_STORE_PASSWORD`（写死在源码）+ ensureDirectStore 按店名把任意同名店铺强制升级 self_operated；admin products/import 的 storeName 可指定任意店 → ops 内鬼可把目标店变直营（免保证金/发品拦截失效）。未修（建议：密码走环境变量 + 白名单）
- **S7 财务驳回已发货订单**（api/admin/payments/[orderNo] reject 只拦 closed）：paid+已发货订单被 reject → payment failed + 订单回 pending_payment，卖家已发货货款中断。✅ 已修（仅 pending_payment+paymentStatus=pending 可 reject）

## 中（9）
- **M1 AdminUser.status=disabled 只在 requireRole 生效**：requireAdminPermission 不查、middleware 只验 JWT、页面服务端组件直查库 → 禁用员工 7 天内仍可读全部 /admin 页面。✅ 已修（requireAdminPermission 读 requireRole 写入的 30s 缓存）
- **M2 change-reviews 审核只验 role=admin**：finance/logistics 等无 ops/service 权限的角色也能 approve/reject 卖家昵称/店铺名变更。未修（建议加 requireAdminPermission "ops"）
- **M3 ops 可禁用任意员工**（users/[id] 仅要求 ops）→ 对其他职能 DoS；员工管理应 root/system 专属。未修
- **M4 权限矩阵过宽**：ops 拥有 risk（冻结任意订单结算）、risk 拥有 system（免费发短信/邮件、看生产配置）。未修（按岗位收紧）
- **M5 保证金审核 PATCH 无状态机**（api/admin/deposits/[id]）：approved→rejected 来回跳直接改写净额；退还 approved 无打款凭证强制。未修
- **M6 商品/商户审核无状态机**（products/[id]/review、sellers/[id]/review）：不校验 submitted 状态，可重复审核；approve 会把 closed/restricted 店铺重置为 active。未修
- **M7 买家提现处理无事务 TOCTOU**（admin/buyer-withdrawals/[id]）：findUnique 守卫 + update 非原子，并发双打款/双解冻，frozen 可为负；reject 分支钱包缺失时 create 丢金额。未修（改 updateMany where status=submitted count===1）
- **M8 操作日志审计字段失效**：appendOperationLog 写 Prisma 时 actorType/actorId 硬编码 "system"/"internal"，操作人只在 detail 文本；api/actions/route 任何登录用户可伪造刷日志。未修
- **M9 管理员登录凭据硬编码源码**：7 角色明文密码（auth-model.ts）+ login 直接比对明文，AdminUser.passwordHash 从未参与登录 → 密码无法轮换、源码泄露即沦陷。**设计使然**（演示账号体系，docs/internal-test-accounts.txt 明示），不修

## 低（5）
- **L1 资金字段 Float/Decimal 混用**：BuyerRecharge.amount/BuyerWithdrawal.* 为 Float，钱包/订单为 Decimal；代充金额未 toFixed 浮点尾差写 Decimal。未修（统一 Decimal + 整数最小单位）
- **L2 PaymentTransaction.providerReference(TXID) 无唯一约束**：并发确认同 TXID 双花。未修（加部分唯一索引）
- **L3 卖家提现 NaN 绕过校验**（withdrawals:37 `Math.max(0,NaN)=NaN <50` false → 通过）→ 500 DoS；买家侧有 Number.isFinite。未修
- **L4 test-orders 时间范围无上下限 + 店铺数无上限**：可生成 1970/未来订单污染统计。✅ 已修（90 天内 + 不晚于当前）
- **L5 ops 公开接口**：/api/ops/service-status 公开+CORS*（暴露服务器 IP/到期日/服务配置，?refresh=1 无限流触发第三方探测）；price-review 只验 role 不验权限 key。未修

## 已确认安全项
- admin API 除 S1 外均有 requireRole；categories/merchants/freeze/products-import/buyer-withdrawals/deposits-top-up/users-balance 授权与金额校验齐全
- cron/settlement 生产有 CRON_SECRET 保护
