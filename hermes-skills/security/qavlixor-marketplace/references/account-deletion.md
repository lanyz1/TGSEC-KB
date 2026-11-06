# 卖家账号全量删除 runbook（2026-08-11 <EMAIL-REDACTED> / Tourwin Store 实测）

用户要求"删掉某卖家账号所有信息，可重新注册"时按此执行。

## 盘点（先查后删）
paramiko 连生产 → 上传临时 `_q.mjs`（读 .env.local 注入 env → `import('@prisma/client')`）→ node 跑 → rm。
- `user` 按 email 查 id → `sellerAccount` 按 userId → `store` 按 sellerAccountId（记录 storeId/storeName）
- **用 `$queryRawUnsafe` SQL 查各表计数**（不要全依赖 prisma client 模型——服务器 client 可能缺模型/字段，如 product.count undefined）

## 级联删除顺序（子表先删，否则 FK 23503 阻塞）
Message(conversationId∈conv) → Conversation(buyerUserId/storeId/sellerAccountId) → OrderItem → Shipment(orderId) → PaymentTransaction(storeId) → Order(storeId) → AfterSaleCase(storeName='X' OR buyerEmail) → ProductImage → ProductVariant → ProductOperationMetric(productId∈) → Product(storeId) → SellerWallet(storeId) → SellerDeposit(storeId) → StoreFavorite/BuyerFavorite/BuyerAddress(userId/storeId) → NotificationMessage(recipientEmail) → EmailVerificationCode(email) → UploadedFile(targetId) → PaymentIntent(refsJson::text LIKE) → SellerChangeRequest(storeId OR submittedByEmail) → QuickReply(ownerEmail) → **WalletRecharge(storeId)** → Store → SellerAccount → User

## ★踩坑（实测）
- **WalletRecharge 表没有 userId 列**（只有 storeId/submittedByEmail）——按 userId 删报 42703
- **Store 删除被 WalletRecharge 外键阻塞**（WalletRecharge_storeId_fkey）——必须先清 WalletRecharge 再删 Store
- SellerChangeRequest 无 sellerAccountId（用 storeId/submittedByEmail）；QuickReply 无 sellerAccountId（用 ownerEmail）；UploadedFile 无 userId（用 targetId）
- **输出残留检查用 String()/Number() 拼接，不要 JSON.stringify BigInt**（count 返回 BigInt 会崩）
- 每步 try/catch 打印 `✓ label: n` / `✗ label: err`，失败的表单独补跑（先查 information_schema.columns 拿真实列名）

## 验证 + 可重注
```sql
SELECT (SELECT count(*) FROM "User" WHERE id=... OR email='...') AS u,
       (SELECT count(*) FROM "Store" WHERE id=...) AS s, ... -- 全 0
```
User 表无该邮箱 = 可重新注册（注册体系=邮箱验证）。注册后为全新账号。

## 收尾（项目铁律）
- 必写 `docs/ops-log/YYYY-MM-DD-操作日志.md`（含关联盘点、删除清单、验证结果、踩坑）
- 删除中若遇到 FK 阻塞，参考本文档顺序重排，别硬删
