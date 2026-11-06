# Qavlixor 坑库（2026-08 会话实战）

## $transaction catch 陷阱（失败后仍继续执行）
`prisma.$transaction(...).catch((e) => { return json({ok:false,...}); })` —— **catch 回调的 return 值被丢弃**，外层函数继续跑（写日志/返回 ok）→ 余额不足时仍建了假单/记了日志。正确姿势：`let txError: string | null = null; await prisma.$transaction(...).catch((e) => { txError = e.message; }); if (txError) return json({ok:false, message:txError}, {status:400});`。事务内先 re-read 再校验（如 wallet 余额），不要用事务外读到的旧值。

## 新增表/功能后扫汇总统计（KPI 漏计）
新增 BuyerWithdrawal 表后，管理端 A1 总览"提现申请"KPI 只 count 了 `Withdrawal` 表 → 买家提现漏计（显示 0 实则有待处理）。**新增业务表/功能后必须 grep 管理端总览与队列的所有汇总计数**（`admin/page.tsx` 的 count/filter/reduce、各队列页 KPI），确认新表纳入合并计数（`pendingWithdrawalCount + pendingBuyerWithdrawalCount`）。

## 逻辑缺陷扫描清单（前后端链路）
扫\"哪里不通顺\"时的固定检查项（2026-08 管理端复验实战）：
1. 双存储一致性：`isEnabled() = USE_JSON_DB !== "1"`，正常全走 Prisma；local-db.json 仅兜底。读路径先确认走哪套
2. appendOperationLog 双写（local-db + Prisma.operationLog）——A15 读 Prisma 优先，有数据就不会空
3. 金额操作（提现/代充/打款）都要事务 + 防呆（余额/冻结足够才扣，避免负数）
4. 状态语义：转出类（提现）paid 显示"已打款"，入账类（充值）才"已到账"
5. 新表接入后 KPI/队列计数合并（见上）
6. 并发路径（提现申请、余额扣减）必须 `$transaction` 原子，且余额类扣减用**条件更新**（`updateMany where amount >= 所需` + count 判定）——事务内"读→判断→decrement"在 READ COMMITTED 下仍可并发透支（安全审计 M1）
7. 金额相关改动先查 `references/security-audit-buyer-2026-08.md`：充值即到账(S1)、demo admin 密码(S2)、首 SKU 计价(M2)、reserve 吞错(M3)、收银台无认证(M4)、confirm 重置售后期(M5)、buyerEmail 伪造(M6)、下单幂等(M7)、停用账号会话(M8)

## @url 链接 404（Hermes 桌面客户端行为）
用户从聊天里点 `[@url:http://...](@url:http://...)` 标签 → Hermes 渲染坏 URL（dev 日志可见 `/admin/merchants](http:/localhost:3000/admin/merchants) 404`，URL 混入 `](http:` 残留）。**给用户链接必须用纯文本/纯 markdown 链接，不要用 @url 标签**。诊断法：查 dev 日志最近 404 的完整路径，能直接看到被污染的 URL。

## datetime-local 时区偏移（服务器 UTC vs 用户 +8）
`new Date('2026-08-05T17:11')` 无时区后缀按**服务器本地时区**解析（服务器=UTC）→ 用户输入的墙钟时间被当成 UTC → 订单时间晚 8 小时。
修复：前端把 datetime-local 值先 `new Date(value).toISOString()`（浏览器按用户时区解析后转 UTC ISO）再传后端；后端 `new Date(iso)` 解析即正确。验证：生成后查库 createdAt 毫秒转 +8 对比范围。

## 管理端铃铛 API 按 portal 拼路径
`NotificationBell` 请求 `/api/${portal}/notifications-recent`——admin portal 需要独立建 `/api/admin/notifications-recent`（seller 版 requireRole 含 admin 但路径不对仍 404）。新增 portal 时两个 API 都要建。

## AdminUser 表 vs 权限硬编码
- 员工账号权限 = `lib/api-auth.ts` 的 `adminPermissions` **硬编码 map**（root/ops/service/finance/risk/logistics/arbitration @globalmart.test）
- `AdminUser` 表默认**为空**——仅用于"禁用员工"记录（禁用 = upsert status=disabled）
- 禁用生效需两处校验：`requireRole` 的 admin 分支 + `POST /api/auth/login` admin 分支，都查 `AdminUser.status === "disabled"` → 401/403
- 员工列表展示 = 权限表 keys（id 形如 `staff-<email>`），User 表无 admin

## 校验订单生成（/api/test-orders + AdminTestOrdersClient）
- 订单写 Prisma `Order` 表（非 local-db.json）；变体在 `ProductVariant` 表（Product 无 sku 列——**商品级 sku 是取 variants[0]**）
- 指定商品要**变体粒度**：page.tsx 传完整 variants（含 sku/optionValues/price），组件按变体渲染 checkbox，API 读 `variantIds` 精确匹配变体（兼容旧 `productIds`）
- 预览渲染要用 `order.variant?.sku` 不是 `order.product.sku`（product.sku = 首变体）
- optionValues 是 JsonValue → 前端 `String()` 转换后 JSON.parse 显示规格值

## dev 崩溃恢复（Jest worker + EPIPE，高频）
`process poll` 发现 not_found → `netstat -ano | grep -E ":300[01].*LISTEN" | awk '{print $5}' | sort -u | taskkill /F /PID` → 后台 `pnpm dev`（watch: Local/EADDRINUSE）→ sleep 18 && curl home=200 → 重登对应角色。用户已确认"dev 模式崩了自动重启"。

## 买家端测试账号
- <EMAIL-REDACTED> 原 passwordHash 是 `session-...`（失效占位）——2026-08 已按 lib/password.ts 算法（sha256:salt:hash）重置为文档测试密码 QavTest@2026（dev 本地）
- <EMAIL-REDACTED>（sha256 有效）密码未知；登录失败先查 hash 前缀（sha256=可登录，session-/imported=失效）

## 总管理加余额分流
`POST /api/admin/users/[id]/balance`：User 有 sellerAccount.store → SellerWallet.availableAmount + WalletRecharge(paid)；纯买家 → BuyerWallet + BuyerRecharge(approved)；员工行禁用按钮。买家余额买家端 /account 展示（无抵扣消费逻辑——下单使用是未接后续）。

## 买家余额闭环（充值/提现/资金记录/管理端审核）
- 表：`BuyerWallet`(userId 唯一, available/frozen) + `BuyerRecharge` + `BuyerWithdrawal`（2026-08-06 建）
- 充值 `POST /api/buyer/recharge`：提交即到账（approved，dev 无人工链路）+ `BC-` 单号；note=`买家充值 · {方式}`
- 提现 `POST /api/buyer/withdrawals`：校验 available → **available-=amount, frozen+=amount**（冻结）+ `BW-` 单号 + fee 1.5%（payout=amount-fee）。**冻结+建单必须在 `prisma.$transaction` 内原子执行**（防并发超扣；事务内 re-read wallet 再校验）——**注意：仅靠事务内 upsert 读+判断+decrement 仍有竞态**（READ COMMITTED 下两笔并发都读到旧余额、双双通过判断），必须用**条件更新** `updateMany({ where: { userId, availableAmount: { gte: amount } }, data: { decrement } })` 按 count===1 判定（2026-08-07 安全审计 M1 确认）
- 管理端 `POST /api/admin/buyer-withdrawals/[id]`：`paid` → frozen-=amount（释放，**先校验 frozen >= requestedAmount 防呆**，否则可扣成负数）；`rejected` → frozen-=amount + available+=amount（解冻回余额）；都要日志留痕
- 买家端资金记录状态语义：充值 approved →"已到账"；**提现 paid →"已打款"**（提现是转出，显示"已到账"语义错——踩过）
- 管理端提现队列 `app/admin/withdrawals/page.tsx` 底部"买家提现"区块：查 BuyerWithdrawal include user，待打款/已打款/已驳回 + AdminBuyerWithdrawalActions（打款/驳回按钮）
- 买家端 /account 余额卡 = `components/buyer/BuyerBalancePanel.tsx`（客户端组件：余额 + 充值/提现按钮弹窗 + 资金记录列表；page.tsx 传 balance + fundRecords）
- **API 验证用 node fetch 带 cookie**（`login.headers.get('set-cookie').split(';')[0]` 复用），浏览器 console fetch 相对路径常报错（TypeError: Failed to parse URL / Failed to fetch）；多角色流程（买家申请→管理员打款）用 node 脚本最稳

## 货币系统 USDT 化（根因记录）
用户问"为什么一直出现 CNY，谁规定的"——答案：`lib/currency-constants.ts` 的 `CURRENCY_BY_LANGUAGE = { "zh-CN": "CNY", ... }` 历史按语言映射展示币种（对标速卖通中文站显示人民币），中文界面金额 ×7.16 全变人民币。2026-08-06 已改：全语言默认 USDT + FALLBACK_RATES USDT:1。USDT 换算行为：`formatLocalAmount` 用 Intl en-US + currency=USDT 抛异常 → catch fallback `"USDT 89.00"` 格式（幂等，正好符合需求）。验证：node `--experimental-strip-types` 直接调 `currencyForLanguage('zh-CN')` + `convertPriceText`；或浏览器切中文看商品详情价。

## 七国翻译现状（2026-08 已全量机翻完成）
`translations` 结构：`{ "zh-CN": zh, en: { ...zh, ...en }, es: { ...zh, ...en, ...esPack, ...es, ...esFull }, fr/pt/ru/ar 同理 }`——**es/fr/pt/ru/ar 各 2013 键已全量机翻**（2026-08 批量完成，deepseek），缺失键回退链 zh→en→语言包→全量包。zh 2013 键 / en 1984 键（含补的 home.channel.creator/creatorText）。
- 检查法：`execute_code` 数各 `const <lang>: TranslationMap = {` 块的键数（正则匹配到配对大括号）
- **en 缺键无害模式**：zh 值本身就是英文的键（如 `admin.top.eyebrow = "Operations Console"`）不必在 en 区重复——回退 zh 显示正常英文，别当缺陷修
- **en 真漏翻检查**：zh−en 键集差集 + 筛 zh 值含中文的（曾漏 `home.channel.creator/creatorText` → 英文界面首页横幅显示"创作者装备"）；`seller.identity.title=店铺名` 是数据值豁免

## UI 键批量机翻工作流（translations.ts 全量 5 语言）
`scripts/gen-ui-lang-packs.mjs`（2026-08 实战）——把 zh 区 UI 键机翻成 es/fr/pt/ru/ar：
1. 解析 `const zh: TranslationMap = {` 块（正则匹配到配对大括号）提取键值
2. **按文案去重**（相同 value 只翻一次——2013 键去重后 ~1587 条）→ `Map<value, keys[]>`
3. 每批 12 条（BATCH=12，串行）调 `makeTranslator()`（i18n-scan-lib，一次翻 6 语言）→ `result[value][lang]` 反向映射到所有 keys
4. **断点续跑**：启动时加载 `work/ui-pack-{lang}.json` 已有键跳过（`doneKeys` 过滤 remaining）；每 5 批 + 结束时落盘（中途 API 挂不丢进度）
5. 合并进 translations.ts（python）：生成 `const esFull: TranslationMap = {...2013键...};` 变量块 + 语言区 spread 追加 `...esFull`；**值转义** `replace('\\','\\\\').replace('"','\\"')`
6. 验证：tsc EXIT 0 + `pnpm build`（注意 dev 跑着时禁 build）+ 浏览器切西语看真实页面
- **翻译通道**：**永远 deepseek**（api.deepseek.com + deepseek-chat + .env.local 的 TRANSLATE_API_KEY）——**用户明确指示"自动翻译以后都走 deepseek 通道，不要再走 fk"**（fkcodex 中转会 503 `No available channel` 通道耗尽、且其 key 在官方 api 验证无效是正常的）。生产 .env.local 已是 deepseek；本地也改过。API 偶发 500/503 → 脚本自动重试 3 次（间隔 3s）
- 后端/脚本后台跑用 node 绝对路径：**`/d/node22/node.exe`**（`node` shim 在 Hermes background 下执行必失败 exit 1 无输出——`echo`/`which` 正常但 node 命令崩；前台正常；用绝对路径 node.exe 解决）

## 自动翻译架构（用户问"不是有个自动翻译吗"——分清 UI 键 vs 动态内容）
**自动翻译只管动态内容，不管 translations.ts 的 UI 键**：
- 链路：LanguageSync 漏翻中文 → `POST /api/i18n/report-miss`（限流：单批≤30、pending≤500、IP 每分钟≤10）→ `TranslationMiss` 表（pending）→ cron 机翻 → `UiTranslation` 表（scope=console/dynamic）→ `GET /api/i18n/extra` → LanguageSync 启动拉取合并 → **页面即生效（无需重新部署）**
- 翻译服务：OpenAI 兼容协议，`TRANSLATE_API_KEY`/`TRANSLATE_BASE_URL=https://api.deepseek.com`/`TRANSLATE_MODEL=deepseek-chat` 在 **.env.local**（不在 .env）——一次批量翻 6 语言（en/es/fr/pt/ru/ar）+ zh-CN 原样
- cron（生产已配）：`sync-content-i18n.mjs` 每 10 分钟（flock 防重锁 `/tmp/tiktok-content-i18n.lock`）+ `sync-i18n.mjs` 每日 04:47；数据源=商品描述/聊天/通知/工单/售后原因/备注/漏翻队列
- 生产现状（2026-08 盘点）：UiTranslation ~8496 条（console 248 + dynamic 8248），TranslationMiss 2158 全 done
- 验证机翻：`cd /www/tiktok && timeout 180 node scripts/sync-content-i18n.mjs`（幂等，输出"新增 N 条，失败 0"）
- UI 键切语言显示英文 = 正常（UI 键不走机翻，见七国翻译现状）

## loadEnvFiles 的 .env.local sqlite DATABASE_URL 覆盖（机翻 cron 崩溃根因）
**症状**：`node scripts/sync-content-i18n.mjs` 立即崩（EXIT=1，2 秒内），输出 `PrismaClientInitializationError: Invalid prisma.uiTranslation.findMany() invocation: the URL must start with postgresql://`（错误 toString 是一大段 library.js 源码 dump，真正的错误信息在 dump 里——用 `awk '/PrismaClientInitializationError/,0'` 过滤）。
**根因**：`scripts/i18n-scan-lib.mjs` 的 `loadEnvFiles` 先加载 `.env.local`——其**第 1 行带 BOM 的历史遗留 `DATABASE_URL="file:./dev.db"`**（sqlite）——JS `\s` 匹配 \uFEFF 所以 BOM 挡不住正则 → DATABASE_URL 被设为 sqlite → Prisma（provider=postgresql）初始化失败。诊断坑：逐查询 probe 全 OK（probe 用 require 不带 loadEnvFiles，baked url 正常）≠ 脚本能跑（loadEnvFiles 污染 env）。
**修复**（已落地）：loadEnvFiles 改为 `.env`（生产）覆盖 `.env.local`：`const last = file === ".env"; if (last || !(match[1] in process.env)) process.env[match[1]] = value;`
**部署后热更新单个脚本**：`sftp.put(local, "/www/tiktok/scripts/i18n-scan-lib.mjs")` 单文件上传即可，无需整包重部署；然后手动跑一次脚本验证 EXIT=0。
