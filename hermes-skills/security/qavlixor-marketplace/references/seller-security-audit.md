# 卖家端安全审计清单（2026-08-07 全量扫描，17 项缺陷）

扫描范围：app/api/seller/* 全部 21 路由 + 共享路由（orders/[id]/fulfillment、aftersales/[id]、messages/[id]/actions）+ lib 资金/订单/物流（funds-repository、order-repository、product-repository、deposit-rules、payment-intents、payment-repository、seller-scope、batch-ship-service、rate-limit、email-verification、session）。未改任何代码。

## 严重（5）

1. **商户状态校验缺失** — requireRole（lib/api-auth.ts:20-46）只验会话角色，不查 sellerAccount.status；login/route.ts:55-59 对 suspended 也发 seller 角色；session 里的 sellerApproved 签了但无任何 API 消费。入驻提交（application/submit 或 draft 建店）后即有 scope → 发品上架/提现/退款/发货全可用。修：requireRole 通过后统一查 status=approved 或消费 sellerApproved。
2. **提现 TOCTOU** — withdrawals/route.ts:54-100 可用额检查→邮箱码→create 非原子，并发双提现超提（恶意卖家自持邮箱可无限取码故意触发）。修：事务+条件扣减（availableAmount gte amount 作为闸门）。
3. **保证金划转 TOCTOU** — deposit/transfer/route.ts:33-56 先 getFundsSnapshot 检查再 $transaction create+decrement，并发两笔 → 幽灵保证金（net>真实可用），差额/全额退按 net 放行虚额。无邮箱码/限流。修：条件 decrement 为唯一闸门。
4. **商品审核整体绕过** — products POST（route.ts:86-141）接受客户端 status=已上架；product-repository.ts:39-45 prismaStatus 直接把"已上架"映射 reviewStatus=approved → 免审进买家商品池（只需缴足保证金）；已上架商品改标题/图片再提交"已上架"也不触发审核。修：服务端状态机，published 必经 approved。
5. **部分退款提前完成订单** — aftersales/[id]/route.ts:88-90 isPartial → orderStatus=completed 且不写 afterSalesAvailableUntil（该字段只在 confirm/route.ts:36 确认收货时写入）→ 未妥投订单货款立即进入可提现（funds-repository.ts:97,212）。0.01 USDT 部分退款即提前套现。修：仅 delivered/receipt_confirmed 才可 completed，且补写保护期。

## 中（7）

6. **资金公式双口径** — prismaSnapshot（funds-repository.ts:113）用 deposit.balance.net（pay−refund−deduction）；refreshSellerWallet（:221-223）只减 kind=pay approved。提现闸门（withdrawals:56-62）读 wallet.availableAmount → 保证金退还/罚扣后：显示可用已恢复但提现闸门双重锁定（退还资金永久卡死）；罚扣后显示可用 > 实际可提现。修：统一净额口径，退款/罚扣后主动 refresh。
7. **保证金退还竞态** — deposit/refund/route.ts:27-63 overview 检查与 create refund 无锁无事务，并发双退 → net 扣两次。修：事务+条件写入+幂等键。
8. **取消订单无事务+并发双取消** — orders/[id]/cancel/route.ts:29-67 状态检查与写入分离；releaseProductStock（product-repository.ts:441）非条件 increment → 库存双回补超卖 + 双罚扣记录。
9. **店名鉴权+非唯一+自助改名（跨店越权链）** — Store.name 无 @unique（schema:264-268）；account PATCH（route.ts:60-63）直改店名绕过 change-request 审核流。改名与他人同名后，所有 store.name 比较鉴权全串店：cancel:33、products/[id]:66,159、fulfillment:43、batchShip:54-57、aftersales:52、funds-repository:81（getFundsSnapshot）、transfer:33 → 可取消他人订单（罚扣记对方保证金）、改删他店商品、资金页直接展示他店订单/台账。订单号 19 位（doc-number.ts:39-41）可枚举且取消无限流。修：一律 storeId 鉴权 + name 加唯一约束 + 改名走审核。
10. **售后多次退款无累计** — refundedAmount 覆盖式写入（aftersales/[id]:68,90）；messages/[id]/actions/route.ts:71-84 会话内 refund 建单无 claim 锁、无进行中售后检查；AfterSaleCase.orderId 无唯一约束（schema:797-810）→ 部分退款叠加丢失（卖家少扣）或部分+全额超退（平台多付）。修：refundedAmount 累加且 ≤ totalAmount；建单统一走 after_sales_pending 原子翻转锁（aftersale 创建路由已有先例，messages actions 未复用）。
11. **local-db 镜像失步** — fulfillment/route.ts:86 状态守卫读镜像（可能过期）；order-repository.ts:232 syncLogisticsToPrisma 用镜像对象覆写 orderStatus（closed 可被拉回 shipped）。修：守卫与写入都以 Prisma 条件更新为准。
12. **演示账号写权限** — seller-scope.ts:7-28 demo seller 绑定"北线好物店"完整写权限，口令公开（auth-model demoAccounts）；提现仅因 @example.com 收不到码而受阻。修：demo 邮箱服务端拒绝写操作或绑隔离演示店。

## 低（5）

13. **NaN/Infinity 金额** — withdrawals:37 / recharge:23 / deposit:32 用 Math.max(0, Number(x))，NaN 比较全 false 通过检查 → Prisma 写入 500（轻微 DoS）。应前置 Number.isFinite。
14. **输入长度缺失** — products 标题/详情无上限；提现 account 无上限 + withdrawalAccount id 190 字符截断碰撞（withdrawals:40,82）。
15. **限流弱点** — rate-limit.ts:25-41 进程内存级、PM2 多实例×4、XFF 可伪造（nginx 未覆盖时）；取消/发货/售后/保证金路由无限流。
16. **取消罚扣无余额约束** — deduction 使 net 为负，0 保证金卖家可无限取消，罚金只挂负净额（取消路由不检查 deposit 余额）。
17. **deposit POST 无单笔上限**（对比 recharge 100000）。

## 审计方法论备忘（下次扫这库直接复用）

- 归属校验统一按 store.name 比较而非 storeId → 全局搜 `scope.storeName`、`=== storeName`、`!== scope.storeName` 即得全部鉴权点。
- 资金公式两条路径（prismaSnapshot 读时重算 vs refreshSellerWallet 写 wallet 表）必须逐项对齐：completedTotal / rechargeTotal / activeWithdrawalAmount / withdrawnAmount / deposit 扣减口径（net vs pay-only）。
- 资金路由 check-then-act（提现/划转/退还/取消）逐一验证事务性；aftersale 已有 updateMany 原子翻转先例（C3/C8），检查新路由是否复用。
- prismaStatus() 的"客户端状态→reviewStatus"映射是审核绕过高发点，凡是接受 status 入参的 POST/PATCH 都要查。
- 状态机守卫读 local-db 镜像的位置（fulfillment/batchShip）与写主库的位置交叉验证，防过期镜像回写。

## 已确认安全（勿重复扫）

- 充值/保证金收银台 confirmIntent 仅 admin finance 权限 + 链上金额指纹自动确认可达（payment-intents.ts:134-224），卖家无法自证到账。
- 邮箱验证码单次消费 + 5 次尝试上限（email-verification.ts:86-97），无重放。
- requireRole 买家兜底（api-auth.ts:38-44）正确堵卖家会话直调买家 API。
- 无命令注入/文件读写面；商品图片 URL 白名单合理。
