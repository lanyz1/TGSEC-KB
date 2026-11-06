# 保证金缴纳死锁修复 + 删号第二例（2026-08-11）

## 一、保证金死锁（用户实测：提交上架拦 200 差额，缴纳却提示"已全额缴纳"）

### 死锁机制
- **提交上架校验**：`computeDepositRequirement(storeId, { extraCategories: [incomingCategory] })`
  （app 内提交路径，261 行附近）→ 按"**含本次提交类目**"算档位。电脑办公=中风险档
  DEPOSIT_TIERS[1]=**300**，已缴 100 → 差 200 → 拦上架。
- **缴纳额度**：transfer API + 资金中心快照走 `getDepositOverview(storeId)` → `computeDepositRequirement(storeId)`（**无 extraCategories**）
  → 只算已上架商品类目（100）→ 已缴足 → maxTransfer=0 → "已缴足应缴额"，**缴不了差额**。
- 结果：系统要求补 200 又不让缴 200 = 死锁。

### 修复（lib/deposit-rules.ts getDepositOverview）
```ts
const draftCategories = await prisma.product
  .findMany({ where: { storeId, status: "draft" }, select: { category: { select: { name: true } } } })
  .catch(() => []);
const draftRoots = [...new Set(draftCategories.map((x) => x.category?.name).filter(Boolean))] as string[];
computeDepositRequirement(storeId, draftRoots.length ? { extraCategories: draftRoots } : undefined)
```
草稿商品类目计入应缴 → 资金中心/缴纳额度/提交校验**三处口径一致**。
transfer API 与前端面板（SellerDepositTransferPanel maxTransfer = requiredAmount - net）都吃
getFundsSnapshot→getDepositOverview 的快照，**一处改全通**。

### 验证方法
- 构造"电脑办公"类目草稿商品（POST /api/seller/products status=draft）→ 资金中心 Required Amount 应变 300。
- ⚠️ 测试别用 qa-seller（其店 EchoSaila 是 self_operated 直营店：平台覆盖 displayBalance.net=requiredAmount，gap 恒 0，
  面板恒显示 "Paid in full"，无法验证缴纳额度）。要用**普通店**验证。
- 注意：草稿删除后应缴回落（补缴额度随之消失），用户需保持草稿或一次性缴足。

## 二、删号第二例：纯买家账号（无 SellerAccount）

用户要求删 <EMAIL-REDACTED>（"连带营业执照"）——实测该账号**无 SellerAccount**（按
contactEmail/businessLicenseNumber/businessEntityName/店名全表搜均无），纯买家身份。

### 纯买家账号删除范围
User + BuyerAddress(userId) + NotificationMessage(recipientEmail) + EmailVerificationCode(email)
+ StoreFavorite/BuyerFavorite(userId) + 订单/会话按 buyerUserId（本例 0）。无需动 Store/SellerAccount/Product。

### 确认"有没有卖家身份"的 SQL 三连
```sql
SELECT id FROM "SellerAccount" WHERE "userId"='<uid>';
SELECT id FROM "SellerAccount" WHERE "contactEmail"='<email>' OR "businessLicenseNumber" LIKE '%<前缀>%' OR "businessEntityName" LIKE '%<前缀>%';
SELECT id FROM "Store" WHERE name LIKE '%<前缀>%';
```

## 三、删号/查库通用表名陷阱（第一例 <EMAIL-REDACTED> 踩坑）
- 表名≠model 名想当然：售后=`AfterSaleCase`（不是 AfterSale）、通知=`NotificationMessage`（不是 Notification）、
  `WalletRecharge` **无 userId 列**（只有 storeId/submittedByEmail）——按 userId 删报 42703。
- 外键删除顺序：Store 删除被 `WalletRecharge_storeId_fkey` 阻塞 → 先清 WalletRecharge 再删 Store。
- 服务器独立 node 脚本的 Prisma client 可能缺模型（product.count undefined）→ 用 `$queryRawUnsafe` / `$executeRawUnsafe` 直连最稳。
- 删 User 前最后验证：`SELECT count(*) FROM "User" WHERE email='<email>'` = 0 即确认可重新注册（注册=邮箱验证）。
- 每次删号后写 docs/ops-log/YYYY-MM-DD-操作日志.md（强制）。

## 四、Admin 密码重置（同批发现）
- 服务器 DB 里 `AdminUser.passwordHash` 曾为无效占位 `"session-auth"` → 登录恒 401"账号或密码不正确"。
- 重置脚本：node 生成 `sha256:${salt}:${hash}`（crypto，见 lib/password.ts 的 hashPassword 格式）写回
  `AdminUser.passwordHash`（注意：admin 登录校验走 **AdminUser 表**，不是 User 表）。
- 铺货脚本登录：POST /api/auth/login（role/admin 或 seller）→ 从 Set-Cookie 提取 `gm_session=`（签名会话 cookie，
  旧 fill-leaves 的 gm_role/gm_email 明文 cookie 格式已失效）。
