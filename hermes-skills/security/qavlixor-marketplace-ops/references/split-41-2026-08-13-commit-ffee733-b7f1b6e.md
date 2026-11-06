## 2026-08-13 实录(纯客服账号权限隔离,commit ffee733 + b7f1b6e)
用户"客户不要和我后台的员工混在一起,任务分割清楚,客服只有回复消息的权限,剩下的内部人员处理"。
**机制(AdminUser 加 `isAgentOnly Boolean @default(false)`)**:
1. `requireRole`(api-auth.ts)与 `getAdminPermissions` 对 isAgentOnly 账号**强制 `adminPermissions = []`**(即使 permissionsJson 有值也忽略)——管理 API 的 requireAdminPermission 全部拒绝;
2. **登录 API**(app/api/auth/login/route.ts):`entry = staff.isAgentOnly ? "/agent" : (account?.entry ?? "/admin")` → 客服登录直达客服工作台;
3. **/admin 布局守卫**(app/admin/layout.tsx):isAgentOnly 访问管理后台 → `redirect("/agent")`。**⚠️ 坑:`/admin` 无尾斜杠不匹配 `startsWith("/admin/")`,条件必须写 `pathname === "/admin" || pathname.startsWith("/admin/")`**;守卫用 middleware 设的 `x-pathname` header,layout 需 import prisma;
4. **客服消息 API 不受影响**:`/api/chat/*`、`/api/messages/*` 用 `requireRole(["admin"])` 不校验 adminPermission → 仅客服账号仍可回复消息 ✅;
5. **角色权限页**(/admin/roles,AdminPermissionsManager)每账号加"仅客服账号"开关:勾选后权限勾选区 `opacity:.45 + pointerEvents:none` 置灰失效,`/api/admin/permissions` body 带 `isAgentOnly` 保存。
**验证 = 临时账号法(创建→验证→删)**:生产建 `<EMAIL-REDACTED>`(isAgentOnly,密码 hash 用**项目自带 `sha256:{salt}:{hex}` 格式**(lib/password.ts,`crypto.createHash`——服务器 pnpm 结构下 bcryptjs import 不到,别找 bcrypt)→ 登录断言 `entry:"/agent"` → 访问 /admin 断言重定向 /agent → 管理 API 断言拒绝 → 客服会话 API 断言 200 → 删临时账号。**规则:客服账号 = isAgentOnly(仅回消息) + supportNickname(身份) + support-avatar.svg(头像) 三件套,与后台管理账号完全隔离;验证新权限机制用临时账号,别动真实账号**。

