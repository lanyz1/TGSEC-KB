<!-- archived from /root/.hermes/skills/security/admin-backend-source-audit/SKILL.md on 2026-10-21 -->

---
name: admin-backend-source-audit
description: >-
  测绘引擎·Use when auditing admin/backend source code for 权限/资金/状态机漏洞.
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/admin-backend-source-audit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/admin-backend-source-audit/…')`，不要相对 `references/legacy/` 解析。

# admin-backend-source-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/admin-backend-source-audit/`

溯源（仅标记）：`hermes/security-research`

---

# 管理端/后台源码安全审计(静态)

## 触发
用户要求对管理端(/admin 路径 + admin API + 权限体系 + 资金/订单/审核逻辑 + schema)做全量漏洞/逻辑缺陷扫描,输出缺陷清单。区别于运行时黑盒渗透(fintech-api-pentest / web-penetration-testing),本技能是**静态源码审计**。

## 输出格式(用户偏好,遵守)
- 中文;只列真实问题(每条附代码证据 文件:行),无问题明确说"无"。
- 每条固定字段:严重度(严重/中/低)、文件:行、问题描述、攻击场景、建议修复。
- 按严重度分组;结尾附"无问题确认项"(哪些范围已覆盖且无问题,避免下次重复扫描)。

## 审计流程

### Phase 0 建文件清单
- `find app/api/admin app/admin components/admin lib prisma -type f` 枚举全部路由/组件;`wc -l` 排序定位大文件。
- 管理接口常在 admin 目录之外:app/api/ops、app/api/actions、app/api/cron、app/api/withdrawals、app/api/test-orders 都要纳入。

### Phase 1 权限核心(最先读)
1. api-auth.ts:requireRole / requireAdminPermission / 权限矩阵表。
2. session.ts(JWT 载荷与有效期)+ middleware.ts(matcher 覆盖哪些路径)+ login route(拦哪个 status 值)。
3. **逐文件 grep 每个 admin API 的鉴权调用** —— Next.js middleware matcher 通常只覆盖页面路径、**不覆盖 /api/**,API 鉴权必须逐文件核实,几乎总有一个漏网的(实例:storage/health 全无鉴权,GET 泄露全平台数据计数)。
4. 禁用状态在哪些层生效(常不一致):login 检查的 status 值 vs 禁用 PATCH 写入的值 vs requireRole 内查的 AdminUser.status vs requireAdminPermission(常常不查)vs 页面服务端组件(直接查库不查 status)→ 拼出"禁用失效"链条(写入 disabled、登录只拦 deactivated、JWT 7 天仍可看全部页面数据)。
5. 权限矩阵 vs 角色描述是否匹配:ops 是否意外持有 risk(可冻结结算)、risk 是否持有 system(可发短信/邮件、看生产配置);"员工管理"端点是否仅要求普通角色(ops 可禁用其他员工 = DoS 越权)。
6. 硬编码密码/测试账号:登录直接比对源码常量、DB passwordHash 不参与 → 源码泄露即沦陷;共享密码批量账号(直营店池)。

### Phase 2 管理操作安全(状态机 + 金额 + 并发)
每个审核/打款/驳回/确认端点逐一查:
- **状态机守卫要双向**:①能否重复审核(已 approved 再 approve/reject);②能否**回退**(已打款→驳回、已确认到账→待审、已驳回→通过)。只拦 closed 或只拦部分状态是典型缺陷。确认类函数(confirmIntent)幂等分支常只拦 confirmed/cancelled,**漏拦 expired/rejected 单据** → 已取消充值单确认到账、已驳回保证金改判通过。
- **金额校验**:负数、NaN(`Math.max(0, NaN) = NaN` 且 `NaN < 50` 为 false → 绕过范围校验,必须 `Number.isFinite`)、上限、超额、对已打款单不校验余额。
- **并发/事务**:状态守卫是"读后写"(findUnique 查状态 → 再 update)就有 TOCTOU,并发请求双打款/双解冻;正确模式是 `updateMany({ where: { id, status: "submitted" } })` 且 `count === 1` 才继续,或整段 `$transaction`。钱包更新与单据更新分离 = 不一致窗口。
- 驳回动作对已发货/已结算订单的影响:已确认收款+已发货订单可否被驳回重置回 pending_payment → 资金流撕裂。
- 确认到账是否有链上核验;TXID 查重是否原子(无唯一约束时并发双花)。

### Phase 3 数据完整性/审计
- OperationLog 写入时 actorId/actorType 是否硬编码("internal")→ 无法按操作人追溯;beforeData/afterData 是否从不填写。
- 是否有任意登录用户可写日志的端点(/api/actions)→ 日志污染/伪造审计。
- 测试数据工具(test-orders/校验订单):生成的单 paymentStatus 是否直接 paid;资金/结算统计是否过滤 orderChannel=validation;时间范围是否可填任意过去/未来;店铺选择是否可覆盖全平台真实店铺。
- 代充/加余额:钱包 increment 与流水记录是否同一事务;金额是否 toFixed(浮点尾差);单据号随机段是否碰撞。

### Phase 4 注入/敏感泄露
- 公开无鉴权端点(health/status/fill-progress)泄露的业务计数、服务器 IP、到期日、env 配置状态;CORS * + 无鉴权组合。
- 测试端点(邮件/短信)可向任意地址发送 → 服务商配额滥用;`?refresh=1` 无频率限制 → 反复触发外部探测消耗第三方配额。
- 限流 clientIp 是否信任 X-Forwarded-For 客户端头(可伪造绕过,依赖 nginx 覆盖);修复取 XFF **最右**一项(离服务器最近的代理追加,最难伪造),无 header 回退 "direct"。
  - **实测更优(2026-08-13)**:Cloudflare 回源链路 XFF = "客户端伪造, 真实用户IP, CF边缘IP"(CF 追加真实 IP、nginx 再追加 CF IP)→ 取**倒数第二项** = 真实用户 IP 且客户端伪造前缀被跳过;取最右 = CF IP 全站共享一个桶,IP 限流直接废掉。直连单段取末段。修复后须 nginx 侧配套(勿覆盖 CF 追加的真实 IP)。
- **依赖审计(pnpm)**:国内镜像(npmmirror)无 audit 端点,`pnpm audit` 报 ERR_PNPM_AUDIT_ENDPOINT_NOT_EXISTS → 必须 `--registry=https://registry.npmjs.org`。修复传递依赖漏洞(sharp/postcss/nanoid 等 Next 依赖):**pnpm v11 的 overrides 不在 package.json**(该字段已废弃),必须放 `pnpm-workspace.yaml` 的 `overrides:` 键,然后 `pnpm install --force` 重解 lock。修完 `pnpm audit --prod --registry=https://registry.npmjs.org` 验证清零。
- **/api/cron/* 鉴权**:常见门控 `if (secret && header !== secret) 401` —— **CRON_SECRET 未设置时完全公开**;tick 类无资金端点常被 `// TODO(生产):加鉴权` 注释跳过,GET/POST 都要查;验证生产 .env 是否真设了 CRON_SECRET。
- 错误响应是否回传内部 message/堆栈。

### Phase 5 schema
- 资金字段 Float vs Decimal 混用(精度不一致,统计对不上)。
- providerReference(TXID)无唯一约束 → 查重靠应用层读后判断,非原子。
- **建唯一约束前必须查业务值域**:`providerReference` 这类"凭证"字段可能承载业务标记字面值(实例:余额支付写 `"balance"` ×44、生成订单写 `""` ×19),`prisma db push` 建 @unique 直接报 **P2002 静默失败**(deploy 脚本不检查 db push 结果 → 索引永远没建上)。先 `GROUP BY ... HAVING count(*)>1` 查重复,确认为标记值后 `UPDATE ... SET col=NULL`(业务类型已由 method/status 字段标识,清 NULL 无损),再重跑 db push + `pg_indexes` 验证索引存在。
- 状态字段用 String 无枚举约束;缺 (storeId,status) 等常用索引;级联删除缺失(User/Store 删除被 Restrict 挡)。

## Pitfalls(实战验证)
- **Next middleware matcher 漏根路径**:`"/admin/:path*"` 不匹配 `/admin`(无尾斜杠)→ 守卫绕过,未登录渲染侧边栏+嵌入登录。matcher 必须同时列 `/admin` 与 `/admin/:path*`(seller 同理)。
- **Cloudflare/反代回源 request.url 的 host 是 localhost**:nginx 透传 Host 正常但 CF 回源时 middleware 里 `request.url` host 可能为 localhost:3003,`NextResponse.redirect(new URL("/admin", request.url))` 会跳 localhost → 浏览器打不开。重定向必须用固定域名(生产域名硬编码,isLocal 例外)。
- **Next cookies.set 同名覆盖(Map 语义)**:`res.cookies.set("gm_session", "", ...)` 两次(host-only + domain)只发最后一条 → 清 cookie 漏清。必须 `res.headers.append("Set-Cookie", ...)` 两条手动拼。同理登录:CF 回源下 cookieLogin 判断 hostname 失败 → 只设 host-only cookie(无 Domain)→ 登出必须清 host-only 那条。
- **会话角色守卫必须排除开放页**:middleware 里"非 admin 会话访问 /admin → 清 cookie 重定向 /admin/login",若拦截条件包含 `/admin/login` 自身 → ERR_TOO_MANY_REDIRECTS 死循环。开放页(/login、/notifications、注册流程)必须在守卫白名单。
- **PM2 fork 多实例限流稀释**:进程内内存限流每实例独立,实际阈值 ≈ 配置 × 实例数(实测 4 实例 × 10 次/分钟 = 40 次才 429)。审计"限流是否生效"必须连打超过 阈值×实例数 次验证,或直接读代码确认多实例。
- **邮箱后缀鉴权误伤自定义邮箱用户**:`email.endsWith("@globalmart.test")` 这类守卫会把用户自建的自定义邮箱客服(<EMAIL-REDACTED>)挡在门外 → 登录成功后被踢 → 重定向循环。守卫应查用户表(AdminUser),不猜邮箱域。
- **浏览器自动填充污染表单**:管理端表单(新增员工)填 root 邮箱 → 报"超级管理员账号已存在"让人误以为逻辑 bug。根因=Chrome 自动填充;修复=表单 `autoComplete="off"`/`new-password` + 报错文案写"该邮箱是超级管理员账号,请更换邮箱"。
- **无头验证 React 受控输入**:直接 `input.value=...` 不触发 React state,必须 `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input, val)` + dispatchEvent('input')。否则表单提交空值,误判"功能坏了"。
- **多子域名 cookie 共享**:`.qavlixor.com` 域 cookie 全子域共享 → 买家 cookie 残留访问 admin.qavlixor.com → AdminLayout 权限 null → 管理端全 404("哪个都进不去"根因)。修复:middleware 会话角色守卫(角色不匹配清 cookie 回登录页)。
- 状态机检查"回退方向"最易漏:审核 API 无状态校验时,approve 会把风控 closed/restricted 店铺直接重置为 active。
- 复用店铺/自动升级类函数(ensureStore/ensureDirectStore)会把同名普通店铺升级成特权类型(如 self_operated 免保证金/发品不拦)→ 检查升级条件是否白名单。
- 校验订单污染结算是最隐蔽的"严重"级问题:资金统计过滤条件(如 paymentStatus=paid)不含测试标记,测试单 7+30 天后自动进入可提现余额。
- 禁用员工 ≠ 会话失效:JWT 有效期内的已登录会话在页面层仍可看全部数据;API 写操作被拦 ≠ 页面只读数据安全。
- 权限矩阵"含 all"的 root 邮箱、以及 demo 密码即生产密码,都要在审计结论里显式标注。
- 支付网关"沙箱回退"分支最易出白嫖漏洞:webhook 路由常按 `xxxConfigured()` 分流,未配凭证时落入**无验签分支**,仅凭 externalRef/orderId 即可结算到账 → 任意注册用户 建单→伪造回调→余额凭空到账→提现。审计必查三点:①沙箱分支是否要求登录+订单归属校验;②生产环境是否禁沙箱分支;③settle 函数是否校验 tx.type(防对非 RECHARGE 单结算)。
- **资金审核"读后写"竞态修复模式(实测有效,SQLite)**:approve/reject 提现单先 `findUnique` 查状态再 `update` → 并发双请求可致 **已 approve(已打款)的单被 reject → 余额退回 = 双花**。修复:`updateMany({ where: { id, status: "REVIEWING" } })` + `count===1` 才继续;reject 侧先占 `REJECTING` 临时锁再退余额+置 REJECTED($transaction 内异常自动回滚,临时锁不残留);approve 对 REJECTING 单 count=0 天然幂等。无需行锁。
- **生产敏感文件权限 644 必查**:`.env`(DB 密码/COOKIE_SECRET/支付凭证)与 `prisma/prod.db`(密码 hash + **用户 Cookie**)默认 644 其他用户可读 → `chmod 600`。审计清单加 `ls -la .env prod.db` 实测项。
- **支付通道配置状态 API 泄露**:`GET /api/wallet/methods` 类返回 `{PAYPAL:false,USDT:true}` 的通道可用性端点未登录可探测 → 泄露支付凭证配置情况。修复:加 session 门控。
- **`req.json()` 未捕获 → 非法 JSON 抛错 500**:`schema.safeParse(await req.json())` 的 req.json() 遇非法 JSON(JSON.parse 拒绝 NaN 等)抛异常,不在 try 内即 500。统一 `await req.json().catch(() => ({}))` + safeParse 返回 400。
- **生产安全响应头(加固项)**:Caddy/反代加 HSTS(31536000) + X-Content-Type-Options:nosniff + X-Frame-Options:SAMEORIGIN + Referrer-Policy:strict-origin-when-cross-origin;Next 动态页慎加 CSP(内联脚本易误伤)。
- 登录无速率限制 + 种子/部署文档弱口令(admin12345 类)组合 = 直登后台;API 层若用"只验 JWT 不查库"的 getSession()(页面层 getCurrentUser 查 status),则禁用用户在 JWT 有效期内仍可调全部 API —— 两个都要在结论里显式列出。
- 改密后旧 JWT 仍有效(默认 7 天)= 账号被盗夺回后攻击者会话不失效;修复模式:`User.tokenVersion` 列 + JWT 载荷带版本 + 改密时 +1,校验 `(payload.tokenVersion ?? 0) !== user.tokenVersion` 即拒(`?? 0` 兼容存量 token,首次改密前不踢人,平滑迁移)。
- 修复验证假阴性:运行时验证"修复未生效"时,**先确认自己的 DB 变更脚本真的执行了**(Windows/git-bash 下 `tsx -e` 顶层 await 会静默失败无输出;MSYS `/tmp` 被 tsx 解析成 `C:\tmp` 报 MODULE_NOT_FOUND),再怀疑代码/热更新。变更脚本必须打印确认输出 + 变更后 `findUnique` 复核;脚本放项目目录内 `.mts` + async IIFE;改 session/jwt 核心文件后重启 dev server 再验(Next dev 对 route handler 热更新不可靠)。详见 `references/tikflow-audit-fix-2026-08.md` 坑 4。

## 参考
- `references/qavlixor-admin-audit-2026-08.md` — 实例:Qavlixor 商城管理端全量审计 21 项发现(含文件:行锚点),复扫/验证修复时对照,避免重新发现同一批问题。
- `references/qavlixor-rescan-2026-08-13.md` — Qavlixor 复扫对照(修复后最终状态):21 项中 20 已修复(7 严重全修 + 中10/15/17/18/19 与低21 providerReference 于 2026-08-13 修复落地,commit 7fc52ba)/2 接受风险(SSH root 密码、Float/Decimal),含依赖清零方法(pnpm-workspace.yaml overrides)与生产配置修复状态。下次复扫先看此表。
- `references/tikflow-audit-2026-08.md` — 实例:TikFlow 投流 SaaS 全量审计(S1 沙箱 webhook 白嫖充值 / S2 生产弱口令 / S3 禁用失效 + M/L 级清单,含文件:行锚点),复扫验证修复时对照。
- `references/tikflow-audit-fix-2026-08.md` — TikFlow 审计 13 项修复落地 + 实测验证(攻击链复现),含修复期技术坑:Next 14 `node:crypto` 进客户端 bundle 报 UnhandledSchemeError(改 `globalThis.crypto.randomUUID()`)、Windows dev server 子进程锁 Prisma DLL(prisma generate EPERM,须 taskkill 子进程)、vitest 共享 SQLite 清理顺序(每文件 beforeEach 自足删表防外键)。
- `references/tikflow-rescan-2026-08-16.md` — TikFlow 复扫对照:历史 13 项全修确认 + 新 4 项修复落地(提现 approve/reject TOCTOU 双花 → 条件更新 updateMany+REJECTING 临时锁、.env/prod.db 644→600、methods API 鉴权、withdraw req.json 500、Caddy 安全响应头),含资金竞态审计快路径。
