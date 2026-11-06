# 2026-08-11 运维：删号级联 / 管理员密码重置 / fill 脚本模式 / 保证金口径

## 1. 卖家账号全量删除流程（用户会反复要求，已执行 2 次）

用户要求"删掉 XX 邮箱所有信息 + 确认可重新注册"时的标准流程：

### ① 盘点关联（SQL 直查，勿依赖 prisma client 模型名猜测）
```sql
SELECT id FROM "User" WHERE email='...';           -- 拿 uid
SELECT id, "businessLicenseNumber" FROM "SellerAccount" WHERE "userId"=uid;  -- 可能为空=纯买家
SELECT id, name FROM "Store" WHERE "sellerAccountId"=sid;  -- 店名（AfterSaleCase 按 storeName 归属）
```
- 账号可能没有卖家身份（sellerAccount=[]）：全表按 `contactEmail`/`businessLicenseNumber`/`businessEntityName` 搜该邮箱确认无执照记录，只删买家侧数据即可。
- 删除前先 count 各关联表（订单/商品/售后/会话/消息/资金/通知），日志里留盘点数。

### ② 级联删除顺序（先子后父，防外键阻塞）
Message → Conversation → SupportTicket → OrderItem → Shipment → PaymentTransaction → ScheduledOrderJob → Order → AfterSaleCase → ProductImage → ProductVariant → ProductOperationMetric → Product → SellerWallet → SellerDeposit → StoreFavorite → BuyerFavorite → BuyerAddress → NotificationMessage → EmailVerificationCode → UploadedFile → PaymentIntent → SellerChangeRequest → QuickReply → **WalletRecharge（最后清，它的外键会阻塞删 Store）** → Store → SellerAccount → User

### ③ 表名/列名陷阱（schema 名 ≠ 直觉名）
- **AfterSaleCase**（不是 AfterSale）；按 `storeName`/`buyerEmail` 删
- **NotificationMessage**（不是 Notification）；按 `recipientEmail` 删
- **WalletRecharge：无 userId 列**！只有 `storeId`/`submittedByEmail`——按 userId 删报 42703；**必须按 storeId 清空后才删得掉 Store**（外键 WalletRecharge_storeId_fkey 阻塞，23503）
- **SellerChangeRequest**：无 sellerAccountId，用 `storeId`/`submittedByEmail`
- **QuickReply**：用 `ownerEmail`（无 sellerAccountId）
- **UploadedFile**：无 userId，用 `targetId`（storeId/uid 都试）
- **PaymentIntent**：refsJson 含订单号/店 id，用 `"refsJson"::text LIKE '%<id>%'` 删
- Message 的 sender/receiver 是 `senderEmail`/`receiverEmail`（Message 表无 senderId/receiverId 列，只有 conversationId；Conversation 才有 buyerUserId/storeId/sellerAccountId）

### ④ 验证 + 可注册确认
```sql
-- 残留全 0 检查（User/Store/SellerAccount/Product/Order/AfterSale/SellerWallet/Conversation/WalletRecharge/PaymentIntent）
SELECT count(*) FROM "User" WHERE id='...' OR email='...';  -- =0 即可重新注册
```
- BigInt 序列化问题：`JSON.stringify(count(*))` 会崩（BigInt），用 `String(r[0]?.c)`。
- 每次删号必须写 docs/ops-log/YYYY-MM-DD-操作日志.md（删号清单+踩坑）。

## 2. 管理员密码重置（登录 401 "账号或密码不正确" 排查）

- admin 登录密码校验走 **AdminUser.passwordHash**（不是 User 表；User 表 root 的 passwordHash 是无效占位 `"session-auth"`——那是买家的 session 占位格式，**别改 User 表**）。
- 哈希格式：`sha256:<salt>:<hex>`（lib/password.ts，非 bcrypt）。
- DB 里若是无效占位（如 `session-auth`）→ 任何文档密码都 401 → 重置 AdminUser：
```js
import { randomBytes as rb, createHash as ch } from 'node:crypto';
const salt = rb(16).toString('hex');
const pw = `sha256:${salt}:${ch('sha256').update(`${salt}:${pass}`).digest('hex')}`;
await prisma.adminUser.update({ where: { email }, data: { passwordHash: pw } });
```
- 重置后要告知用户"我改过密码"（用户会问"账号密码你改了吗"）。

## 3. fill 铺货脚本模式（服务器 node 脚本调服务端 API）

- **node 直接 import TS 库会失败**（scripts/*.mjs 不能 import lib/*.ts）——正确模式：**脚本走 HTTP 调服务端 API**（如 /api/admin/products/import-source）。
- **.mjs 里禁止 TS 语法**：`as string[]` 类型断言 → `SyntaxError: Unexpected identifier`。
- **认证**：旧明文 cookie（`gm_role=admin; gm_email=...`）已失效；必须登录拿签名会话：
```js
const res = await fetch(`${BASE}/api/auth/login`, { method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ role:'admin', email: ADMIN_EMAIL, password: ADMIN_PASS }), redirect:'manual' });
const session = (res.headers.getSetCookie?.() ?? []).map(c => c.split(';')[0]).find(c => c.startsWith('gm_session='));
```
- 铺货参数见 import-source API：`platform`（aliexpress/1688）、`keyword` 或 `numIids`、`storeName`（2026-08-11 新增：强制挂靠指定店，店不存在自动 ensureDirectStore 建 self_operated）、`markup`、`minImages`、`cleanImages`、`budgetMs`。
- **速卖通铺货 cleanImages 必须 false**：GPT 视觉清洗对英文图 fail-closed 误删 → 图不足全跳过（实测 clean=true 跳过 17 个，false 后 46 个全建）。
- **品牌过滤**：关键词搜索会混入兼容件/竞品（搜 "bambu lab" 返回 Creality/Anycubic/BIGTREETECH）——先 item_search 本地过滤（title 含品牌词）再传 numIids，别直接传 keyword。
- 铺货期间禁 pnpm build / pm2 restart（文档 warning）。

## 4. 保证金两处口径（不是 bug，用户会误报"不一致"）

- **资金中心（/seller/funds）显示**：`computeDepositRequirement(storeId)`——只算**当前已上架商品**的类目档位（现状）。
- **提交上架校验**：`computeDepositRequirement(storeId, { extraCategories: [新商品类目] })`——算**含本次提交后**（未来）。
- 例：电脑办公=中风险档 300，现状普通档 100 → 资金中心显示 100、提交被拦要补 200，提示语有"含本次提交后"字样。两处都符合规则。
- 用户困惑时解释口径差异即可；可提议 UI 优化（被拦提示给补缴按钮/资金中心显示含草稿类目）。
