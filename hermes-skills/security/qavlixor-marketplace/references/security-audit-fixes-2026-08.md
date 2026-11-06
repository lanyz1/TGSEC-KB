# 三端安全扫描修复状态（2026-08-07 全量扫描 → 26 真缺陷 + 2 设计使然）

3 子代理并行扫描（买家 41 调用 / 卖家 30 / 管理端 26），复核后 26 项真实缺陷。**全部 26 项已修复**（24 项 commit `acafcfd` + 收官 2 项 `70a5b64`）**并全量部署上线**（`8e07b15`，生产验证通过）。来源文件：`security-audit-buyer-2026-08.md`、`seller-security-audit.md`、`admin-security-audit.md`。

## ✅ 已修复（24 项，tsc EXIT 0 + 运行时回归通过）

### 资金安全（10）
1. **校验单污染结算**（管理S2）：`lib/funds-repository.ts` refreshSellerWallet 的 paidOrders 过滤 `orderChannel !== "validation"`——校验订单工具生成的测试单不再计入可提现/结算
2. **test-orders 时间范围**（管理L4）：`app/api/test-orders/route.ts` 限 90 天内且不晚于当前（回归：2020 范围 400 / 正常范围 200）
3. **买家提现并发超提**（买家M1）：`app/api/buyer/withdrawals/route.ts` 条件原子扣减 `updateMany({where:{userId, availableAmount:{gte:amount}}})` count===1 为唯一闸门
4. **卖家提现 TOCTOU**（卖家S2）：`app/api/seller/withdrawals/route.ts` create 后立即 refreshSellerWallet 重算 withdrawable，超额删单回滚 400
5. **卖家提现状态机**（管理S3）：`app/api/withdrawals/[id]/route.ts` 仅 submitted/paying 可处理 + updateMany 条件写 count===1
6. **confirmIntent 状态守卫**（管理S4）：`lib/payment-intents.ts` wallet 分支拦 cancelled/rejected；deposit 分支拦 kind≠pay 或 rejected/refunded/cancelled
7. **财务驳回订单守卫**（管理S7）：`app/api/admin/payments/[orderNo]/route.ts` reject 仅限 pending_payment + paymentStatus=pending（已发货订单不可驳回）
8. **买家提现最低金额前置**（买家L2）：`amount < 50` 直接 400（原事务提交后才报错，响应与状态不一致）
9. **部分退款状态机**（卖家S5）：`app/api/aftersales/[id]/route.ts` 部分退款不再无条件置 completed——仅已确认收货（completed/receipt_confirmed）可 completed（且补写 afterSalesAvailableUntil），其余保持 after_sales_pending
10. **售后退款累计上限**（卖家M4）：退款前校验 `已退 + 本次 ≤ totalAmount`（400 拦截）；refundedAmount 改累加写入

### 越权（7）
11. **requireRole 全面状态校验**（卖家S1+买家M8+管理S5 一修三）：`lib/api-auth.ts`——admin 分支 AdminUser.status（+cacheStaffStatus 写缓存）；seller 分支查 sellerAccount.status==="approved"（suspended/待审 403，`opts.allowUnapprovedSeller` 豁免）；buyer/seller 分支查 User.status 拦 disabled/deactivated
12. **入驻 API 豁免**：`app/api/seller/application/submit|draft/route.ts` 改 `requireRole(["seller"], { allowUnapprovedSeller: true })`；onboarding 页走 verifySession 不受影响
13. **requireAdminPermission 禁用校验**（管理M1）：读 requireRole 写入的 adminUserStatusCache（module 级 Map）
14. **店名查重**（卖家M3 部分）：`app/api/seller/account/route.ts` 改名查重拒绝（dev 已有 'B测试店'×2 重名历史数据；未推 schema @unique 避免生产 push 冲突）
15. **会话身份伪造**（买家M6）：`app/api/messages/[id]/route.ts` 买家角色强制 buyerEmail=auth.email
16. **change-reviews 权限**（管理M2）：`app/api/admin/change-reviews/*` 加 requireAdminPermission(auth,"ops")（原来任意 admin 角色可审核）
17. **storage/health 鉴权**（管理S1）：`app/api/admin/storage/health/route.ts` GET/POST 补 requireRole(["admin"])（原全项目唯一无鉴权 admin 路由）

### 状态机与边界（7）
18. **商品审核绕过**（卖家S4）：`app/api/seller/products/route.ts` toStatus(value, forceReview=true) POST 已上架→待审核；`[id]/route.ts` PATCH 内容变更（标题/详情/SKU 名）强制回待审核（库存/价格免审保留）
19. **多 SKU 计价**（买家M2）：`app/api/checkout/orders/route.ts` ResolvedItem 加 price（按 sku 从 operation.skuItems 查变体价，取不到回退 product.price），total/unitPrice 用 item.price
20. **重复确认收货**（买家M5）：`app/api/orders/[id]/confirm/route.ts` completed/receipt_confirmed 幂等返回不重置售后期；仅 delivered/shipped 可确认 + updateMany 条件写
21. **审核状态机守卫**（管理M5/M6）：deposits/[id] 仅 submitted/pending_review 可审（+退还 approved 强制打款凭证）；products/[id]/review 仅 submitted_for_review；sellers/[id]/review 仅 submitted + approve 不覆盖 closed/restricted/suspended
22. **取消订单并发**（卖家M6）：`app/api/seller/orders/[id]/cancel/route.ts` updateMany where orderStatus in CANCELLABLE_STATUSES count===1（防库存双回补/保证金双罚）
23. **保证金划转/退还 TOCTOU**（卖家S3/M2）：transfer 改条件扣减闸门（availableAmount gte amount）+ 事务内建单；refund create 后复检 net 不为负，跌破回滚 409
24. **买家提现管理端并发**（管理M7）：`app/api/admin/buyer-withdrawals/[id]/route.ts` updateMany where status=submitted count===1 先 claim 再动钱包（冻结不足回滚状态）

### 低危（6，并入上表批次）
- **NaN/Infinity 金额校验**（卖家L3）：seller withdrawals/recharge 改 `Number.isFinite` 前置（原 Math.max(0, NaN)=NaN 绕过区间检查）
- **售后证据外链白名单**（买家L3）：aftersale + evidence 两处 evidence 仅接受 `^\/(?:api\/upload-files\/|uploads\/)`
- **无效商品 ID 404**（买家L5）：getProductWithOperation 返回 null，products/[id]/cart/checkout 三调用方 notFound()
- **库存扣减显式失败**（买家M3）：reserveProductStock target 不存在返回 ok:false（原 ok:true 超卖）、catch 返回 ok:false
- **requireAdminPermission 同步函数读缓存**（见 13）
- **M1 核实为误报**：refreshSellerWallet 的 available 公式用的是 `deposit.balance.net`（deposit-rules.ts net = paid−refund−deduction 净额口径）——保证金退还/罚扣无双重锁定，未改

## 🔧 通用修复模式（跨三端复用）
- **条件原子写 = 状态机守卫 + 并发防重一体两用**：`updateMany({where:{id, status:{in:[合法态]}}, data})` 的 `count===1` 作为唯一凭据——比 findUnique 守卫 + update 安全（TOCTOU 免疫），比 SELECT FOR UPDATE 简单（Prisma 无原生行锁）
- **金额闸门**：`updateMany({where:{userId, availableAmount:{gte:amount}}, data:{decrement}})` count===1 拦并发超提
- **requireRole 状态校验模式**：admin→AdminUser.status；seller→sellerAccount.status=approved（入驻豁免参数）；buyer/seller→User.status。同步函数（requireAdminPermission）读 async 函数（requireRole）写入的 module 级缓存
- **资金统计口径**：结算/可提现过滤 `orderChannel !== "validation"`；完成后订单才进可提现
- **服务端不信任客户端 status**：POST 强制审核流（已上架→待审核）；PATCH 内容变更回审核，非内容变更（库存/价格）免审
- **create 后复检回滚**：check-then-create 并发场景（卖家提现/保证金退还）在 create 后立即重算约束，超限删单回滚 409

## ✅ 收官（2 项已修，commit `70a5b64`，全量部署 `8e07b15` 上线）
25. **收银台归属校验**（买家M4）：`app/api/pay/[intentNo]/route.ts` POST/renew 前统一 `assertIntentOwner`——注册用户 session 邮箱须 == `intent.createdByEmail`（403 "该支付单不属于当前账号"）；游客（无会话）仅限 guest 单（创建者邮箱无注册 User 行）否则 403，guest 通过后 IP 限流 10 分钟 20 次（内存 Map）。GET 保持公开（游客支付页渲染）。实测三场景：游客提交已注册单 403 / 本人通过（进 TXID 格式校验）/ 他人账号 403
26. **权限矩阵收紧**（管理M3/M4，用户拍板）：`lib/api-auth.ts` adminPermissions 最终形态——ops=`["ops"]`（冻结结算归 risk）、risk=`["risk"]`（sms/mail 测试 + production/status 仅 root 的 system 权限）、arbitration 仍含 service。验证模式：risk/ops 调 `/api/admin/sms/test` → 403；root → 400（权限通过、参数校验拦）

## 🚀 部署状态（2026-08-07 全量上线）
- 本地 main `8e07b15`（= 七国翻译 c12a61c + 安全修复 acafcfd + 收银台/权限 70a5b64 + 日志）**已全部部署生产**：备份→archive→服务器 build 15.7s→pm2 restart→4 实例 online→home 200/public 200→生产权限实测（risk 调 sms-test 403 ✅）
- 生产验证要点：登录后 curl 关键修复接口（权限 403/放行、提现 400 拦截）确认新代码生效

## ⚠️ 遗留注意
- **2 项设计使然不修**：硬编码演示账号密码（auth-model.ts，演示体系需求）；买家充值即到账（用户明确"代充/自充即到账"）
- 生产数据：dev.db 有 'B测试店' 重名 ×2（店名唯一约束不能直接推）
- **git add -A 教训**：会误提交 work/ 中间产物（ui-pack-*.json）与 .hermes/desktop-attachments——.gitignore 已加 work/；提交前 `git status --short` 检查
