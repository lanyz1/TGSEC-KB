# TikFlow 审计修复落地 + 验证(2026-08)

审计发现见 `references/tikflow-audit-2026-08.md`;本文件记录 13 项修复的落地方式与验证结果,修复模式可复用于同类 Next.js SaaS。

## 修复清单(严重 3 / 中 4 / 低 5)

| 项 | 修复落地 |
|---|---|
| S1 沙箱 webhook 白嫖 | webhook 沙箱分支:①`NODE_ENV=production` 直接 404;②开发环境 `getSession()` 要求登录;③`settleRecharge(externalRef, ownerUserId?)` 校验归属 + `type==="RECHARGE"` |
| S2 生产弱口令 | seed 不再硬编码 `admin12345`:`seedPassword()` 默认 `randomBytes(12).toString("base64url")`,`SEED_ADMIN_PASSWORD`/`SEED_DEMO_PASSWORD` 环境变量可覆盖,控制台打印一次 |
| S3 禁用失效 | `getSession()` 升级:verifySession 后查库核验 `status==="active"` + tokenVersion 一致(见下) |
| M1 cron 无鉴权 | tick 路由改为与 usdt-scan/tiktok-refresh 相同的 `if (secret && mismatch) 401` 门控(GET/POST 都包) |
| M2 改密不失效 | `User.tokenVersion Int @default(0)`;JWT 载荷带 tokenVersion;改密 `tokenVersion: { increment: 1 }`;getSession 校验 `(payload.tokenVersion ?? 0) !== user.tokenVersion` 即拒 |
| M3 登录无限流 | 新增 `src/lib/auth/login-rate-limit.ts`:内存 Map、IP+账号双维度、5 次失败锁定、指数退避(1min→5min→25min→1h 封顶)、成功清除、预检与失败统一返回 `invalid_credentials` |
| M4 注册枚举 | `account_exists` 409 → 统一 `invalid_input` 400(前端 auth-form 是通用 error 映射,无需改) |
| L1 订单永不过期 | `expirePendingOrders(maxAgeHours=24)`:PENDING 超时置 FAILED;instrumentation 注册 `ORDER_EXPIRE_SECONDS` 定时器(默认 900s 跑一次) |
| L2 externalRef 碰撞 | `CR-${globalThis.crypto.randomUUID()}`(勿用 node:crypto,见坑 1) |
| L3 phone 占用 | profile PUT 前 `findFirst({ phone, id: { not: session.userId } })` → 409 `phone_taken` |
| L4 USDT 无来源审计 | `settleUsdtDeposit(txHash, amount, fromAddress?)` 把链上地址写进 note;tron scan 调用处传 `tr.from` |
| L5 videoUrl 协议注入 | `safeExternalUrl()`:正则 `^https?:\/\/` 前置校验(必须显式协议,相对路径也拒),4 处 `<a href>` 接入 |

## 修复期技术坑(3 个,均实测)

### 坑 1:Next.js 14 webpack — `node:crypto` 进客户端 bundle 报 UnhandledSchemeError
- 现象:lib 文件被客户端组件引用(如 wallet.ts ← recharge-panel.tsx),`import { randomUUID } from "node:crypto"` 编译报 `UnhandledSchemeError: Reading from "node:crypto" is not handled by plugins`,服务端 route 里用则没事。
- 修复:`globalThis.crypto.randomUUID()`(浏览器/Node 均支持),不 import。
- 判别:看报错 `Import trace for requested module` 指向的入口是不是客户端组件;stripe.ts 的 `node:crypto`(createHmac/timingSafeEqual)只在 route handler 用,不用改。

### 坑 2:Windows — dev server 子进程锁 Prisma query_engine DLL
- 现象:`prisma generate`/`db push` 报 `EPERM: rename query_engine-windows.dll.node.tmpXXX`。
- 根因:`next dev` 的 bash 包装进程被杀后,**node 子进程仍活着**占 DLL;`process(action=kill)` 只杀了 shell。
- 修复:PowerShell 找残留子进程再 taskkill:
  ```powershell
  Get-CimInstance Win32_Process -Filter "name='node.exe'" | Where-Object { $_.CommandLine -like '*<项目路径>*' } | Select ProcessId
  taskkill /PID <pid> /F
  ```

### 坑 3:vitest 共享 SQLite — beforeEach 清理不完整导致外键失败
- 现象:全量跑时 `user.deleteMany()` 报 `Foreign key constraint violated`,单文件跑通过;`fileParallelism:false` 下文件执行顺序不稳定,某文件残留 campaign/tiktokAccount 数据引用 user。
- 根因:某测试文件 beforeEach 只删 walletTransaction+user,依赖其他文件先清表——脆弱。
- 修复:每个文件 beforeEach 自足清理,自底向上删表(walletTransaction → campaign → tikTokVideo → tikTokAccount → user),不依赖执行顺序。

### 坑 4:Windows/git-bash — `tsx -e` top-level await 脚本静默失败(验证假阴性)
- 现象:用 `npx tsx -e "…await prisma.user.update(…)"` 做禁用/改密等 DB 变更,**无任何输出、变更未生效**;随后 curl 验证"修复未生效"——实际是脚本根本没跑(假阴性),差点误判代码没修好。
- 根因:git-bash 下 `tsx -e` 的顶层 await 静默吞掉;另外 MSYS `/tmp/xxx.ts` 路径会被 tsx 解析成 `C:\tmp\xxx.ts` 报 `ERR_MODULE_NOT_FOUND`(bash 的 /tmp ≠ Windows C:\tmp)。
- 修复:①DB 变更脚本**必须打印确认输出**(如 `console.log("DONE status=" + r.status)`),验证前先 `findUnique` 确认变更真的落了库;②脚本放**项目目录内** `.mts` 文件 + async IIFE 包裹,跑完删除;③验证"修复未生效"时,先怀疑自己的变更脚本,再怀疑代码。
- 正确模板:
  ```bash
  cat > .set-status.mts << 'EOF'
  import { PrismaClient } from "@prisma/client";
  const p = new PrismaClient();
  (async () => {
    await p.user.update({ where: { email: "x@y.z" }, data: { status: process.argv[2] as any } });
    console.log("DONE"); await p.$disconnect();
  })();
  EOF
  npx tsx .set-status.mts disabled
  ```

## 验证结果(实测)
- 单元测试 82 → 92 全过(新增:S1 归属/类型校验、L1 过期、M2 版本、M3 限流、L5 URL);`tsc --noEmit` 0 错误;`next build` 成功。
- curl 攻击链复现:未登录 webhook → 401;本人建单+结算 → 到账;伪造他人 externalRef → `order_not_found`。
- S3/M2 运行时验证:禁用用户 → 旧会话 API 401 + 登录 401;改密 → 旧 cookie 401、新密码登录 200(⚠️ 中途一度"不生效"是坑 4 的 tsx 静默失败假阴性,换 .mts 脚本重测即通过;dev server 需重启加载新代码是次要因素)。
- ⚠️ 改完 session/jwt 类核心文件必须**重启 dev server** 再验证:Next dev 对 route handler 热更新不可靠,跑在旧代码上会产生假阴性(先怀疑自己的变更脚本,再怀疑热更新,见坑 4)。

## 生产上线动作(修复后仍需人工)
- 生产 .env 必设:`CRON_SECRET` 强随机;`SEED_ADMIN_PASSWORD`;`PAYMENT_SANDBOX=false` + 真实 PayPal/Stripe/USDT 凭证(否则 webhook 沙箱分支在生产 404,充值不可用)。
- 部署文档(DEPLOY.md)同步标注种子密码随机化说明。
