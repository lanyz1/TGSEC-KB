# 2026-08-12 客服三波: 头像体系 + 纯客服账号 + 发起404修复 + 管理端未登录/域名隔离

承接 `2026-08-12-support-chat-iteration.md`(二波: 独立客服页/agent/会话管理)。

## 头像体系三档(勿混用)

| 档位 | 资源 | 适用 |
|---|---|---|
| 客服 | `/support-avatar.svg`(蓝底白Q) | 客服会话(seller_support / buyer_support) |
| 普通用户 | `/user-avatar.svg`(灰底深灰Q) | 买家/店铺**没上传头像**时 |
| 真实 | CDN url | 用户/店铺有头像 |

- 三处 peerAvatar 逻辑**都要按会话类型分支**:`getChatConversationList`(列表)、`mapConversation`(详情)、`getCommerceConversation` 卖家视角覆盖(`if (!isSupportConv) mapped.peerAvatar = buyerUser?.avatarUrl ?? USER_AVATAR`)
- 常量:`const SUPPORT_AVATAR = "/support-avatar.svg"`, `const USER_AVATAR = "/user-avatar.svg"`(message-repository 顶部)
- 教训:客服会话曾走到 `store.logoUrl`(卖家上传的店铺logo)和买家 avatarUrl → 混用。**任何会话头像都要先判 isSupportConv**
- 买家视角客服会话 store 名:buyer_support → "平台客服";卖家视角 seller_support → "XX客服"(按 subject 类型)

## 纯客服账号(isAgentOnly)—— 客服只有回复消息权限

AdminUser 加 `isAgentOnly Boolean @default(false)`(需 db push)。

五处联动(漏一处就有洞):
1. `lib/api-auth.ts` **requireRole**:`const granted = staff?.isAgentOnly ? [] : (permissionsJson ? parse : adminPermissions[email])` —— 强制无任何管理权限(即使权限表有值)
2. `lib/api-auth.ts` **getAdminPermissions**:同款 `staff?.isAgentOnly ? [] : ...`(30s 缓存,改完要 invalidate)
3. `app/api/auth/login/route.ts`:staff 分支 `entry = staff.isAgentOnly ? "/agent" : (account?.entry ?? "/admin")` —— 登录直达客服工作台
4. `app/admin/layout.tsx`:**重定向守卫**(放在 x-pathname 获取之后):
   `if (email && (pathname === "/admin" || pathname.startsWith("/admin/")))` —— **`/admin` 无尾斜杠不匹配 `startsWith("/admin/")`,必须两个条件**(实测踩过:只写 startsWith 时 /admin 根路径放行)
5. `/admin/roles` 页 + AdminPermissionsManager:每行加"仅客服账号"开关(勾选后权限勾选区置灰 disabled),存 `/api/admin/permissions` 的 isAgentOnly 字段

- **验证模式**:生产不知密码时,建**临时账号**验证全流程(登录 entry → /admin 重定向 → 管理 API 拒绝 → 客服 API 可用)→ 测完 deleteMany 清理。密码 hash 见下。
- 管理 API 层:requireRole 返回 granted=[] 后,requireAdminPermission 全部拒绝(404/403),客服消息 API(requireRole 不过滤权限)不受影响 —— 正是"只回复消息"的权限边界

## 生产密码 hash(建临时账号/重置密码用)

项目 `lib/password.ts` 是 `sha256:salt:hash`(node:crypto 内置,**不是 bcrypt**);生产服务器 pnpm 结构无顶层 bcryptjs,ESM `.mjs` 直接 import bcryptjs 会 ERR_MODULE_NOT_FOUND。生成:
```js
const salt = crypto.randomBytes(16).toString("hex");
const hash = crypto.createHash("sha256").update(`${salt}:密码`).digest("hex");
// 存 `sha256:${salt}:${hash}`
```

## 发起客服复用已删除会话 → 404(重要)

`/api/chat/support` 的**复用查询必须排除 `sellerDeletedAt: null`**(卖家分支),否则:
- 用户删过该类型客服会话(消息中心 ⋯ 删除,软删除)→ 复用查询仍命中 → 返回已删会话 id
- 前端跳 `/seller/support/{id}` → 详情 `visibleWhere` 排除已删 → 404
- 症状:订单/售后/资金正常,"入驻/开店""其他问题" 404 —— 因为用户只删过这两个类型的会话
- 修复一行:`where: { type: "seller_support", sellerEmail, subject, status: {not:"closed"}, sellerDeletedAt: null }`

## 管理端未登录隐藏侧边栏 + 域名隔离

### 未登录显示侧边栏根因
- **middleware matcher 缺根路径**:`"/admin/:path*"` **不匹配 `/admin`**(无斜杠)→ 未登录访问 /admin 绕过 middleware 守卫 → AdminLayout 渲染 PortalShell(侧边栏)+ IdentityGuard 嵌入式登录
- 修复:matcher 数组加 `"/admin"` 和 `"/seller"`(seller 同理)
- **AdminLayout 兜底**:`if (!email && pathname !== "/admin/login") redirect("/admin/login")` —— 注意 `/admin/login` 自身在 layout 内,**必须排除防死循环**
- **PortalShell bare 模式**:未登录 admin 时 `bare={!email}` 只渲染 children(登录页全屏),不渲染 ConsolePortalShell 侧边栏/顶栏。PortalShell 是客户端组件拿不到 email,所以 bare 由服务端 AdminLayout 传

### 管理端域名隔离(/admin 从主站隐藏)
- nginx server_name 已含 `admin.qavlixor.com`(443+80),Cloudflare DNS 已解析 → 域名通道现成
- **middleware host 守卫**(防攻击面):
```ts
if (pathname.startsWith("/admin")) {
  const host = (request.headers.get("host") ?? "").toLowerCase();
  const isAdminHost = host === "admin.qavlixor.com" || host.startsWith("admin.qavlixor.com:");
  const isLocal = host.startsWith("localhost") || host.startsWith("127.0.0.1") || host.endsWith(".local");
  if (!isAdminHost && !isLocal) return new NextResponse("Not Found", { status: 404 });
}
```
- 主站 qavlixor.com/admin → 404;admin.qavlixor.com 正常。登录 cookie 是 host 级(admin 域名登录只在 admin 域名有效,隔离更彻底)
- 部署后验证:主站/admin 404、admin 域名登录全流程(登录→entry=/admin→侧边栏出现)

## 批量订单 SKU 选择区布局(次要)
商品分组组头(标题+全选+已选n/m+折叠 ▾/▸)+ 商品搜索(按标题过滤)+ 展开/收起全部;SKU 行不重复商品标题。
