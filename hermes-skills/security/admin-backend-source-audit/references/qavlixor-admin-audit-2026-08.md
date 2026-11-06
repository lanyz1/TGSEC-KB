# Qavlixor 商城管理端安全审计实例(2026-08)

项目:D:\跨境商城\qavlixor-marketplace(Next.js App Router + Prisma/PostgreSQL)
范围:app/admin/ 页面、app/api/admin/ 全部 API、lib/api-auth.ts、components/admin/、lib/ 资金/订单/审核逻辑、prisma/schema.prisma
产出:21 项发现(7 严重 / 9 中 / 5 低)。复扫或验证修复时对照此锚点,避免重新发现同一批问题。

## 严重

1. **storage/health 无鉴权** — app/api/admin/storage/health/route.ts:1-22(全项目唯一无 requireRole 的 admin API)。GET 泄露全平台数据计数,POST 触发 41MB local-db.json 读写/备份。
2. **test-orders 污染真实资金结算** — app/api/test-orders/route.ts:94-99,166-175 + lib/order-repository.ts:197(create 分支按状态直接写 paymentStatus=paid)+ lib/funds-repository.ts:93-113,204-224(资金统计只按 paymentStatus=paid,不过滤 orderChannel=validation)。未指定 storeIds 时 where={} 对全平台店铺生成;已签收校验单 7 天自动完成、30 天保护期后全额可提现 → 卖家余额虚增可真实提现。
3. **卖家提现无状态机** — app/api/withdrawals/[id]/route.ts:24-58。已打款↔驳回↔处理中任意互转,paidAt 可重置,无事务,打款不校验余额。买家侧 buyer-withdrawals/[id]/route.ts:20 有 submitted 守卫,卖家侧缺失(不一致)。
4. **confirmIntent 可确认 cancelled/rejected/expired 单据** — lib/payment-intents.ts:134-224(cancelled 充值单置 paid 并 refreshSellerWallet;rejected 保证金单改 approved;expired 不拦)。入口 app/api/admin/pay-intents/[intentNo]/route.ts:10-22,无链上核验。
5. **禁用买家/卖家功能失效** — app/api/admin/users/[id]/route.ts:25 写 status="disabled",但 login 只拦 "deactivated"(app/api/auth/login/route.ts:57-58);requireRole 买家兜底分支不查 User.status → 被禁用用户仍可登录下单。
6. **直营店密码硬编码 + 同名店铺强制升级** — lib/direct-stores.ts:8(DIRECT_STORE_PASSWORD 明文,全部直营店共享)、:76-83(ensureDirectStore 把同名任意店铺 storeKind 改为 self_operated → 免保证金/发品不拦);/api/admin/products/import 的 options.storeName 可触发。
7. **财务可驳回已确认收款/已发货订单** — app/api/admin/payments/[orderNo]/route.ts:38-60。reject 只拦 orderStatus=closed;已发货订单被重置回 pending_payment,卖家已发货、货款已进结算口径。

## 中

8. **禁用员工页面层不生效** — lib/api-auth.ts:53-57(requireAdminPermission 不查 AdminUser.status)+ middleware.ts:51(只验 JWT role)+ 各 admin 页面服务端组件直接查库。禁用后 7 天 JWT 内仍可看全部页面数据;删除 AdminUser 记录也放行(硬编码权限表)。
9. **change-reviews 无权限 key** — app/api/admin/change-reviews/route.ts:11 与 [id]/route.ts:12 仅 requireRole(["admin"]),finance/logistics 也可审核资料变更。
10. **员工管理越权** — app/api/admin/users/[id]/route.ts:12 仅要求 ops,ops 可禁用/启用任何非 root 员工(DoS 其他职能)。
11. **权限矩阵过宽** — lib/api-auth.ts:10-18:ops 持有 risk(可冻结任意订单结算);risk 持有 system(可向任意手机/邮箱发测试短信邮件、看生产配置)。
12. **保证金审核无状态机** — app/api/admin/deposits/[id]/route.ts:8-40。approved↔rejected↔pending_review 随意互切,直接改写 getDepositBalance 净额;退还 approved 仅改状态+备注,无打款凭证强制。
13. **商品/商户审核无状态机** — app/api/admin/products/[id]/review/route.ts:21-27、app/api/admin/sellers/[id]/review/route.ts:25-28。可重复审核;approve 把 closed/restricted 店铺重置为 active;驳回已通过商户后商品仍上架(状态分裂)。
14. **买家提现 TOCTOU** — app/api/admin/buyer-withdrawals/[id]/route.ts:33-65。守卫读后写,并发双打款/双解冻;reject 分支钱包不存在时 create 丢金额。
15. **审计字段失效** — lib/local-db.ts:208-219(actorId 恒为 "internal")+ app/api/actions/route.ts:5-23(任何登录用户可伪造/刷日志)。
16. **管理员密码硬编码** — lib/auth-model.ts:56-120 明文密码,AdminUser.passwordHash 不参与登录校验,无法轮换。
17. **代充无事务 + 浮点** — app/api/admin/users/[id]/balance/route.ts:32-65(钱包 increment 与充值记录分离;金额未 toFixed;rechargeNo 随机段碰撞)。
18. **ops 公开端点泄露** — app/api/ops/service-status/route.ts:171-188(公开 CORS*,泄露服务器 IP/到期日/服务配置,?refresh=1 无限制消耗第三方配额)、price-review/route.ts:9-12(只验 role 不验 key)。
19. **登录限流可绕过** — lib/rate-limit.ts:37-41 clientIp 信任 X-Forwarded-For 客户端头。
20. **cron/settlement 兜底** — app/api/cron/settlement/route.ts:4-10,生产漏配 CRON_SECRET 时 NODE_ENV 保护失效,公开可触发结算(含 force 参数)。

## 低

21. **schema 问题** — 资金字段 Float/Decimal 混用(schema.prisma:367-424);PaymentTransaction.providerReference 无唯一约束(TXID 查重非原子,lib/payment-confirm.ts:27-37);卖家提现 NaN 绕过(app/api/seller/withdrawals/route.ts:37-46,`NaN < 50` 为 false);test-orders 时间范围无上下限;Withdrawal 缺 (storeId,status) 索引;status 字段 String 无枚举。

## 无问题确认项(已覆盖)
- categories / merchants/[id] / orders freeze / products import(-source) / buyer-withdrawals(状态守卫) / deposits/top-up(金额上限) / users/[id]/balance(金额校验)授权与基本金额校验齐全。
- cron/settlement 生产有 CRON_SECRET 保护(仅漏配时公开)。

## 方法论要点(本实例验证)
- 31 个 admin API 逐文件 grep 鉴权,漏网 1 个(storage/health)——middleware 不保护 /api/。
- 状态机检查要双向:重复审核 + 状态回退(打款→驳回)都要试。
- "禁用"语义在 login/PATCH/requireRole/requireAdminPermission/页面五层各自为政 → 逐层对 status 值。
- 资金污染类问题看"统计过滤条件是否含测试标记"这一个点即可定位。
