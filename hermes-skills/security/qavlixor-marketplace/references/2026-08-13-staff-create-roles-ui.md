# 2026-08-13 新增客服 + 角色权限页 UI 方案A + 运维技巧

## 新增客服功能(角色权限页 root 专属)

- 入口: `/admin/roles` 右上角"＋ 新增客服"按钮, **仅 root 可见**(`isRoot` 控制), 其他管理员看不到
- API: `POST /api/admin/staffs`(app/api/admin/staffs/route.ts) — 仅 root(`auth.email === ROOT_EMAIL`), 校验邮箱格式/唯一/密码≥8位/名字非空
- 创建逻辑: `prisma.adminUser.create({ email, passwordHash: hashPassword(password), displayName, supportNickname, isAgentOnly(默认 true), permissionsJson: isAgentOnly ? "[]" : null, status: "active" })`
  - **默认 isAgentOnly=true**(新增的"客服"账号=纯客服, 只能进 /agent 回复消息)
  - 创建后 `appendOperationLog` + `invalidateAdminPermCache`
- 前端: AdminPermissionsManager 弹窗(邮箱/密码/名字/客服昵称/仅客服开关), 成功 `router.refresh()` 重拉服务端列表
- 9 个新翻译键 ×6 语言: admin.roles.createBtn/createTitle/createEmail/createPassword/createName/createAgentHint/cancel/create/created(锚点 admin.roles.disabled)

## 角色权限页 UI 方案 A(用户选中)

- 员工卡片: 16px 圆角白卡, 渐变头像(按角色配色: ops蓝/finance橙/risk红/logistics青/service紫/arbitration粉/root黑) + 姓名 + 状态徽章(值班中绿/已禁用红/仅客服蓝) + 邮箱
- 权限胶囊: 选中=蓝底白字(#0071E3), 未选=灰边白底, `pointerEvents:none` 当 agentOnly 开启
- 仅客服开关: Apple 风格 `.perm-switch`(globals.css, 绿 #34C759 toggle)
- root 卡: 黑色徽章"超级管理员·全部权限" + 保存禁用
- 翻译: admin.roles.onDuty("值班中") 6 语言

## 密码 hash 格式与服务器生成(重要)

- `lib/password.ts`: `sha256:${salt}:${hash}`, salt=randomBytes(16).hex, hash=sha256(`${salt}:${password}`)
- **bcryptjs 在生产 pnpm node_modules 不可直接 import**(ERR_MODULE_NOT_FOUND)→ 建/重置 AdminUser 密码用 node 内置 crypto 生成同格式:
  ```js
  const salt = crypto.randomBytes(16).toString("hex");
  const stored = `sha256:${salt}:${crypto.createHash("sha256").update(`${salt}:${password}`).digest("hex")}`;
  ```
- 新建员工登录报"账号或密码不正确"排查: 先查 DB(createdAt desc)确认账号存在且 hash 格式标准; 大概率是**浏览器自动填充覆盖创建时密码**或登录入口用错(admin 账号必须走 admin.qavlixor.com, 主站登录页会报错); 直接重置密码为已知值并自校验(hash 重算比对)再实测登录

## 浏览器自动填充坑(新增客服表单)

- root 登录后 Chrome 记住 root 邮箱 → 打开新增客服弹窗点邮箱框**自动填 root 邮箱** → 提交报"超级管理员账号已存在"(误导为系统 bug)
- 修复: 邮箱框 `autoComplete="off"`、密码框 `autoComplete="new-password"`; 报错文案明确化("该邮箱是超级管理员账号, 不能用于新增客服, 请更换邮箱。")
- 教训: 所有"创建类"表单(含弹窗)一律禁自动填充, 防邮箱/密码被浏览器旧值污染

## React 受控 input 无头测试必须用 native setter(重要测试技巧)

- puppeteer 直接 `input.value = x` + dispatchEvent('input') 对 React 受控组件**不生效**(React 有 value tracker)→ 表单 state 不更新 → 提交空值
- 正确写法:
  ```js
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setter.call(input, "value");
  input.dispatchEvent(new Event("input", { bubbles: true }));
  ```
- 验证"保存成功"别用 `.stack > div` 第一个(可能是按钮容器), 用 `Array.from(...).filter(d => d.style.color)` 找 message 元素

## 保存成功提示走翻译键(防 LanguageSync 半机翻)

- API 返回中文 message(如"已更新 X 的权限。")直接显示会被 LanguageSync 机翻成"已Update ... Test"(半中半英, 且邮箱被改大小写)
- 规则: 成功提示一律 `getTranslation(..., "ui.sel.220")`(已保存。); 失败保留后端错误详情(result.message)
- 动态/API 消息不显示原始中文, 走键或拼接翻译值

## 子域名隔离(middleware, 含 Cloudflare 回源 host 大坑)

- admin.qavlixor.com / seller.qavlixor.com 访问买家路径(根路径 `/`、`/login`、`/register`、`/products`、`/account/*`、`/cart`、`/search` 等)会渲染买家页面 → 出现"登录买家中心"混淆
- **⚠️ 大坑: 不能用 `new URL(path, request.url)` 拼重定向目标**——Cloudflare 回源时 Next 收到的 `request.url` host 是 `localhost:3003`(nginx proxy_pass 目标),实测跳 `https://localhost:3003/admin` 直接访问不了。**必须用固定域名**:
  ```ts
  const isLocal = host.startsWith("localhost") || host.startsWith("127.0.0.1") || host.endsWith(".local") || host.startsWith("0.0.0.0");
  const adminOrigin = isLocal ? `http://${host}` : "https://admin.qavlixor.com";
  return NextResponse.redirect(new URL("/admin", adminOrigin));
  ```
- **全路径隔离**(不只根路径): admin 域名下 `!pathname.startsWith("/admin") && !pathname.startsWith("/agent") && !pathname.startsWith("/api") && !pathname.startsWith("/_next") && pathname !== "/favicon.ico"` → 重定向 /admin;seller 域名同理(放行 /seller /api /_next)。**必须放行 /api**(登录接口靠 admin 域名调用)和 /_next(静态资源)
- **matcher 必须补全买家路径**: `"/"`, `"/login", "/login/:path*"`, `"/register"`, `"/products"`, `"/cart"`, `"/search"` 等 —— 只列 /admin 的话 /login 不进 middleware,买家登录页照样渲染
- 配套: `/admin` 仅 admin host 访问(主站 404); 未登录 /admin 根路径(无尾斜杠)必须单独 matcher 项 `/admin` —— `/admin/:path*` **不匹配** `/admin`
- 验证: `curl -s -o /dev/null -D - https://admin.qavlixor.com/login | grep -i location` 看重定向目标是不是固定域名; 用户端强刷(CF 对跳转有短暂缓存)

## 登录/访问死循环(ERR_TOO_MANY_REDIRECTS)三连修(重要)

用户新客服登录后卡在"Logging in"或浏览器报 `ERR_TOO_MANY_REDIRECTS` 的完整排查链:

1. **买家 cookie 残留 → 管理端全 404**:cookie domain `.qavlixor.com` 全子域共享,主站登过买家 → 访问 admin 域名被当作"已登录但无管理权限"(`getAdminPermissions` null)→ 所有 /admin/* 页 404("哪个都进不去"根因)。修复:middleware 会话角色守卫——admin 域名下 `session && session.role !== "admin"` → 清 cookie(带 domain 与不带 domain 各清一次)重定向登录页。
2. **⚠️ 守卫必须排除开放页**:会话角色守卫若覆盖 `/admin/login`(开放页)→ 买家 cookie 访问登录页也被重定向 → **ERR_TOO_MANY_REDIRECTS 死循环**。守卫条件必须 `!isAdminOpenPath`(/admin/login、/admin/notifications;seller 端 /seller/login、/seller/register、onboarding 同理)。
3. **⚠️ /agent 守卫邮箱后缀是最大坑**:`app/agent/page.tsx` 原写 `email.endsWith("@globalmart.test")`——**自定义邮箱客服(如 <EMAIL-REDACTED>)登录成功后被踢回 `/login`** → middleware 拦 /login → /admin → 再跳 → 死循环。修复:删后缀判断,直接 `prisma.adminUser.findUnique({ where: { email } })` 查表(任何在职员工可进客服工作台);跳转目标 `/login`(买家登录页)→ **`/admin/login?next=/agent`**(配合域名隔离)。
4. **/agent 不套买家壳**:AppShell `portal = pathname.startsWith("/admin") || pathname.startsWith("/agent") ? "admin" : ...`——否则客服工作台顶部出现买家导航栏(Search/Account/Favorites)。

排查方法:无头浏览器监听 `page.on("requestfailed")` 抓 URL(`/login?next=/agent net::ERR_TOO_MANY_REDIRECTS` 一眼定位是哪个守卫在踢);curl `-D -` 看跳转链目标。修完必须无头走完整登录流验证(登录页 → 填表 → 跳 /agent → 断言页面文本)。

## 插键脚本第三次事故:语言错位 + 缺逗号(2026-08-13)

插入 6 语言新键时两个必踩坑(本次 chat.* 8 键 + admin.roles.* 9 键全中):
- **语言错位**:键值数组顺序 `[zh, en, es, fr, pt, ru]`,但文件里语言区顺序是 es→fr→pt→ru→zh→en,锚点语言若按"文件出现顺序"配 `lang_idx` 会插错语言值(es 区插进英文)。**正确映射:锚点语言 → 值数组索引**(es→2, fr→3, pt→4, ru→5, zh→0, en→1),或直接把值数组按文件区序定义。
- **行尾缺逗号**:插入块每行必须以 `,` 结尾,否则 `TS1005 ',' expected`。
- 插完验证:每键 `tr.count('"' + key + '"')` = 6 + **抽查各语言区的值**(正则取所有值看语言对应)+ tsc。插入用"从后往前"(锚点位置排序后逆序插入)避免偏移;若插错(zh 区双份/语言错位)直接 `git checkout <prev> -- lib/translations.ts` 回滚重来,别手工删。



## 客服/用户头像体系(2026-08-13 修复混用)

- 三层头像: 客服会话固定 `/support-avatar.svg`(蓝底白Q); 普通会话用户/店铺无头像 → `/user-avatar.svg`(灰底深灰Q); 有真实头像 → CDN 原样
- 坑: 买家视角客服会话原取 `store.logoUrl`(卖家店铺logo)→ **混用卖家头像**;卖家视角客服会话被 `buyerUser?.avatarUrl` 覆盖。修复 = message-repository 里 `SUPPORT_AVATAR`/`USER_AVATAR` 常量 + 客服会话分支固定;普通会话 null → USER_AVATAR(不再彩色首字块)
- 决策依据: 用户明确要求"客服没设头像用平台logo, 不要混用别人的头像";灰/蓝区分客服与普通用户

## 客服退出聊天 = 登出(2026-08-13, 含 Next cookies 同名覆盖大坑)

- 需求: 客服(仅客服账号)点 /agent"退出聊天"要能退出去。原实现 exitHref="/admin" → 纯客服访问 /admin 被 AdminLayout 守卫弹回 /agent → **退不出去**(视觉=点了没反应)
- 修复: 客服退出 = 调新 API `POST /api/auth/logout` 清会话 → `window.location.href = "/admin/login"`;买家/卖家保持原行为(回 /account、/seller)。ChatWorkspace 里 `role === "support"` 渲染 `<button onClick>` 调用登出,其他角色渲染 `<a href>`
- **⚠️ Next cookies.set 同名覆盖大坑**:`res.cookies.set(key, v1); res.cookies.set(key, v2)` 是 Map 语义——**只发出最后一个**(实测 logout 只出一条带 Domain=.qavlixor.com 的清除,host-only 那条根本没发 → 会话残留,退不出去)
- **⚠️ 登录 cookie 在 Cloudflare 回源下是 host-only**:login route 的 `new URL(request.url).hostname` 回源时 = localhost:3003 → 不满足 endsWith(".qavlixor.com") → 只设无 Domain 的 base cookie(浏览器按响应 URL 存为 admin.qavlixor.com host-only)。**登出清除必须同时发 host-only 与 Domain 两条**,且不能用 cookies.set(覆盖),用 headers.append:
  ```ts
  const CLEAR = "; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure";
  res.headers.append("Set-Cookie", `${SESSION_COOKIE}=${CLEAR}`);
  res.headers.append("Set-Cookie", `${SESSION_COOKIE}=; Domain=.qavlixor.com${CLEAR}`);
  ```
- middleware 会话角色守卫的 cookie 清除同样改 headers.append 双条(原 cookies.set 两次只清 domain 那条,host-only 残留)
- 验证: curl 登录拿 cookie(-c jar)后 `curl -b jar -X POST .../api/auth/logout -D -` 断言**两条** set-cookie 都出现;无头完整流:登录 → 点退出 → URL=/admin/login → 再访问 /agent 被踢回登录页

- 无头实测: root 登录 → roles 页 → 点胶囊/开关 → 保存 → 断言 message 出现 → DB 脚本验证字段 → **恢复原状再保存** → DB 再验证(铁律: 测试后数据必须复原)
- 生产 DB 直查用 paramiko + 服务器 node mjs 脚本(PrismaClient), 见 2026-08-12-support-agent-admin refs
