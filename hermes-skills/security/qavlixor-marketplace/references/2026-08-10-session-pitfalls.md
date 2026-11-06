# 2026-08-10 会话新坑速查（翻译收尾/部署/客服入口）

接 `2026-08-09-session-pitfalls.md`（#64-#69）。本次 #70-#91。

## #70 聊天买家名显示邮箱（存量数据 + 双接口纠正）
- **根因链**：① 存量 Conversation.buyerName 常存邮箱（创建时 `displayName || normalizedEmail` 兜底）；② 卖家端列表 `peerNameFor` 与单会话 `mapConversation.buyer` 都直接用 buyerName（含邮箱）。
- **修复**：① 列表 API join User 表取 displayName（`nameByBuyer` map）纠正；② 单会话 API（getCommerceConversation）同样 join displayName 覆盖 `mapped.buyer`；③ 兜底规则：seller 视角**不再显示邮箱**（`buyerName && !includes("@")` 才算名字），无名字显示 🎮（`seller_support` 显示"平台客服"）。
- **前端**：ChatWindow 头部用 `conversation.buyer`（单会话 API 字段），列表用 `conversation.peerName`——两处数据源不同，**改 API 要两头都改**（本次就是列表改了窗口没改，二次部署）。

## #71 混合文本拆翻（裸中文兜底增强）
- **场景**："FLYYYYYY测试店铺"（英文+中文）切语言中文段不翻——旧规则 `/[0-9A-Za-z$€£¥]/.test(text)` 直接跳过混合文本。
- **新逻辑**（applyBareChinese 三段式）：① 整串查词典（"48 小时内发货"等预置词命中）；② 未命中拆连续中文段 `[\u4e00-\u9fff]{2,}` 逐段翻译重组（"FLYYYYYY"保留+"测试店铺"→"Test Store"）；③ 未命中段上报 report-miss（秒级回填后重扫命中）。
- **保留**：`missDataLikePattern`（6+位数字/邮箱/URL）跳过；`data-i18n-raw` + `.language-switcher` 排除（防误伤语言列表）。

## #72 表单输入即翻：显示语言必须挂事件 detail
- `currentClientLanguage()` 读 localStorage——**测试环境/多标签页不可靠**（读空→回退中文→翻译永不生效）。SellerAccountSettings 的店名/昵称输入即翻用 `nameLang` state（语言事件 detail 驱动 + 初始 localStorage 兜底）。
- 同款机制：SellerProductForm 输入即翻（fieldI18n 缓存，tr() 显示译文、保存原文）；API 用 `POST /api/i18n/form-translate {fields:{原文:原文}}`，返回 `{translations:{原文:{lang:...}}}`（key 按字段名——前端按原文索引）。

## #73 部署后用户"看不到修复" = SPA 旧缓存（不是没部署）
- **机制**：Next.js SPA 客户端导航不重新加载 HTML——已开标签页永远用打开时加载的旧 JS；强刷（Ctrl+Shift+R）/新开标签才生效。
- **验证部署链路**（用户质疑时给证据链）：① `curl -sI https://qavlixor.com/` → `cache-control: private, no-cache, no-store` + `cf-cache-status: DYNAMIC`（HTML 不被 Cloudflare 缓存）；② 静态资源 hash 文件名（新 build 自动换）；③ 服务器 build 产物 grep 修复特征串；④ 浏览器无痕窗口实测复现。
- **教训**：回复"修复完成"时必须附"如何验证"（强刷步骤），否则用户看不到效果会质疑欺骗。

## #74 服务器 522 事故（Cloudflare → 源站超时）
- **排查链**：外网 200 + PM2 online ≠ 无事故——查 `last reboot`（云厂商看护硬重启，无 shutdown 记录）+ nginx error.log 时间线（实例 recv/connect 失败 → 522 → 自动重启恢复）。
- **根因**：4 实例 Node 各 1.3GB + **无 swap** + 部署 build 峰值 → 系统无响应。
- **预防（已落地）**：`fallocate -l 4G /swapfile && swapon` + fstab 持久化；PM2 `--max-memory-restart 1600M`（单实例泄漏自动重启不拖垮全部）+ `pm2 save`。
- 522 是瞬时故障模式：让用户等 1-2 分钟刷新，持续再查。

## #75 卖家端联系官方客服（support 会话机制早已存在）
- **chat 体系**：`visibleWhere` admin/support 角色可见 `buyer_support`+`seller_support` 会话；`viewerSenderRole` admin→"support"；消息 GET 已支持 admin——**机制完整，只缺入口 UI**。
- **新增**：`POST /api/chat/support`（创建/复用未关闭的 seller_support 会话，sellerEmail+buyerEmail 同卖家）；卖家端侧栏"反馈与建议"入口（PortalShell 客户服务组）。
- **注意**：管理端 `/admin/contacts` 是"官网联系表单记录"（NotificationMessage queued），**不是客服会话**——客服工作台（回复 support 会话）需另做。

## #76 新 API 基建（本项目 import 规范）
- 认证：`@/lib/api-auth` 的 `requireRole`（返回 `{ok, email}`）；DB：`@/lib/prisma` 的 `prisma`（或 `const db = prisma as any` 对齐 message-repository）。
- `normalizeEmail` 在 message-repository **未导出**——新代码内联 `String(v??"").trim().toLowerCase()`。
- **lint TS6053 "file not found" 是误报**（write_file 的 lint 工具路径问题）——文件实际已写入，用 `npx tsc --noEmit` 真验证。
- 新表：SellerFeedback（sellerEmail/category/content/contact/status/reply）——**建表需 `pnpm db:push`**（部署流程：解压后先 db push 再 build）。

## #77 订单操作列 UI（先预览后落改）
- 用户选"方案 A"：`.op-btn` 胶囊（白底描边 96×28 圆角 999，取消=红描边 `.op-btn.danger`），等宽垂直堆叠 gap 6；shipBy（"今天 18:00 前"）独立一行置顶（从组头 float:right 移入操作列）。
- **UI 样式类修改流程**：HTML 多方案预览（D:\跨境商城\会话产物\）→ Chrome 打开 → 用户选/描述 → 落改。

## #78 通知中心"全部已读"点击无反应（自动执行设计使按钮变摆设）
- **根因**：`app/seller/notifications/page.tsx` 有"**进入通知中心即全部已读**"（服务端 `updateMany readAt`）→ 用户再进页面时 unreadCount=0 → "全部已读"按钮永远 `disabled` → 点击无反应。
- **修复**：① 移除"进入即已读"（未读保留显示，由用户主动操作）；② 单条点击 Link 即标记该条已读（本地 setRead + fetch）；③ `/api/notifications/read` 支持 body `{ids:[...]}` 单条/多条（不带=全部，seller/admin 共用）。
- **通用教训**：任何"进入即自动处理"的设计会让对应操作按钮变摆设（disabled 无反馈）——保留用户主动操作 + 即时 UI 反馈。
- 管理端通知页（app/admin/notifications）**保留自动已读**（无按钮、未报问题——别顺手改）。

## #79 ★ translations.ts 插键：值语言判断区不可靠（本次事故链）
- **陷阱**：用"锚点键值语言"判断所在语言区会失败——**es/fr/pt 区很多键值懒翻成英文**（如 seller.nav.messages="Buyer messages"），导致 4 个区全判成 en，插入值全错。
- **事故链**：值判错 → es/fr/pt 插成 en 值 → 键名后插入把原键值挤坏（`"keyA": "keyB": "VAL", "ORIG",`）→ 修复 replace 后出现双重键名（`"keyA": "keyA": "VAL",`）→ 逐层修复。
- **正确做法**：① **grep -n 锚点键** 得各区行号，**按行号/位置定位区**；② 插入格式：`"锚点键": "原值",\n  "新键": "值",`（整行替换，不插在键名中间）；③ **replace 值=占位值时串位**（zh 值"反馈与建议"=占位串——第 6/7 次 replace 全落 zh 区）——用"nav 键值=title 键值"配对校验（正则提取相邻键对）。
- **插后必验证**：`grep -c` 键分布（应=7 区）+ 相邻键值语言配对 + `npx tsx scripts/check-translations.mts`。

## #80 部署流程 v3：deploy.py 已集成 db push
- `scripts/deploy.py` 现自动执行：tsc 增量 → git commit → tar.gz → SFTP → **解压后 `pnpm prisma db push --skip-generate`（schema 变更自动应用）** → `next build --no-lint`（跳过重复 typecheck，本地 tsc 把关）→ pm2 restart×2 → curl 探测。全流程 85-100s。
- 新表/字段变更**不再需要手动 db push**——直接 `python scripts/deploy.py "说明"`。
- next.config.ts `typescript: { ignoreBuildErrors: true }`（本地 tsc 是唯一类型闸门）。

## #81 弹窗标题不翻译（Modal 吞掉 data-i18n-title）——全局修复模式
- **根因**：调用处 `title="导出商品" data-i18n-title="ui.fix.83"` 把属性传给 Modal 组件，但 Modal 只解构 `title/children/footer...`——`data-i18n-title` 被丢弃，h3 无该属性；且 LanguageSync 对 `[data-i18n-title]` 只做 `setAttribute("title", ...)`（tooltip 语义），**不是文本翻译**。
- **修复（Modal.tsx）**：props 加 `"data-i18n-title"?: string`（解构 `titleKey`）→ 内嵌语言监听（`useState lang` + `qavlixor-language-change` 事件 detail + localStorage 初始兜底，同 #72 模式）→ `displayTitle = titleKey && lang !== "zh-CN" ? getTranslation(lang, titleKey) || title : title` → h3 渲染 displayTitle。
- **收益**：全站 20 处 data-i18n-title 弹窗标题通吃（删除确认/取消订单/售后处理等）。
- **验证**：卖家端切 AR → 打开导出弹窗 → 标题"تصدير المنتجات"。

## #82 导出弹窗字段翻译（裸中文 → data-i18n 键）
- 字段 label（商品ID/商品名称/类目/价格/库存/销量/状态/更新时间）原是纯裸中文——拆翻能翻但"商品ID"→"ProductID"（无空格）不理想——**正规做法**：EXPORT_FIELDS 加 `i18nKey`，渲染包 `<span data-i18n={f.i18nKey}>`，键 `seller.products.exportField.*`（8 键 × 7 语言 = 56 键，GLM `translateToAllLanguages` 批量生成）。
- **插键成功姿势（#79 踩坑后的正解）**：translations.ts 锚点键**出现顺序 = es,fr,pt,ru,ar,zh,en**（grep -n 验证过：seller.nav.messages 在 187/2225/4265/6306/8347/11156/14117 行）——**按位置顺序直接插正确语言值**（不要用"占位值 + 后修正"——zh 值=占位时 replace 串位，见 #79）。
- **验证**：`grep -c "seller.products.exportField."` 应=56；抽查每键 7 值顺序（es→en）与翻译表一致。

## #83 状态徽标只判中间态 → 终态显示错（物流详情"已签收"显示"运输中"）
- **根因**：`app/seller/orders/[id]/logistics/page.tsx` 顶部状态徽标 `shipped ? "运输中" : "待发货"`——只判"是否发货"，已签收订单也满足 shipped → 永远"运输中"。时间轴"运输中"节点文字同理（已签收仍显示"包裹在途"）。
- **修复**：徽标判断覆盖终态列表 `["已签收","已完成","已关闭"].includes(order.status)` → 显示"已签收"（`st green`）；"包裹在途"文字加 `&& !终态` 条件。
- **通用教训**：**状态显示判断必须覆盖终态**——只判中间态（shipped）会让终态订单显示中间态文案。改状态显示前 grep 该状态字段的所有渲染点，检查是否缺终态分支。

## #84 ★ patch replace_all 模糊匹配会破坏 JSX 结构（本次事故）
- **事故**：物流页修复时 3 处相似片段（含 card-h + tl-item 组合），replace_all=true 后 fuzzy 匹配把结构改坏（card-h/tl-item 重复插入、card-b 层级错乱）——diff 肉眼可见错乱。
- **处置**：`git checkout -- <file>` 恢复 → **精确唯一匹配**（用更长的上下文锚定唯一位置）分两次小 patch 成功。
- **教训**：**replace_all 只用于真正同构的批量替换**；涉及 JSX 结构（多元素组合）时不要赌 fuzzy 匹配——先 `grep -n` 确认各处上下文差异，用唯一上下文逐个替换。任何 patch 后**检查 diff 结构完整性**（配对标签/层级）再 tsc。

## #85 服务器快速查数/插数脚本模式（psql 直连密码失败的替代）
- `psql -U postgres` 直连会 **password authentication failed**（.qav_pgpw 不是 postgres 用户密码）——用 Prisma 脚本：
  1. 上传 `_q.mts` 到 /www/tiktok：读 `.env.local` 逐行 `process.env[KEY] = value`（去引号，仅设未定义项）→ `import { PrismaClient } from '@prisma/client'` → 查/改/删 → `$disconnect()`。
  2. `npx tsx _q.mts > /tmp/q.log 2>&1; tail -3 /tmp/q.log; rm -f _q.mts /tmp/q.log`（**stderr 会吞错误——必须重定向看 log**；`node _q.mjs` 直接跑 ESM 会因 import 解析失败——统一用 tsx）。
- 用途：造测试数据（通知未读）、查订单状态分布（`shipment.status` 是英文枚举 not_shipped/shipped/delivered，**Order 模型无 status 字段**——中文状态是 API 映射值）、清理测试记录。

## #86 状态配色统一（列表/详情双端一致——抽共享函数）
- **根因**：列表页 statusTone（待发货=orange）vs 详情页固定 `st blue`——复制粘贴导致两处不一致，用户要求统一。
- **修复**：抽共享 `lib/order-status.ts` `statusTone(status)`（待售后/待付款/待发货→orange；已关闭/已退款→red；已完成/已收货→green；其他→blue）——列表页 + 详情页（订单状态卡 + 商品明细卡头）import 同一函数。
- **通用教训**：**同一业务状态的配色/文案多处渲染时必须抽共享函数**——复制粘贴必漂移（本次详情页是 2 处 `st blue` 硬编码）。

## #87 输入即翻模式第 3 处落地（运费模板编辑弹窗）
- 模板名称/适用范围输入框（form.name/form.scope）——同 #72 模式：nameI18n + nameLang（语言事件 detail）+ showLocalizedName + `POST /api/i18n/form-translate`——显示译文保存原文。
- **该模式已 3 处复用**（SellerProductForm / SellerAccountSettings / SellerShippingTemplates）——**新表单的输入框要翻译直接照抄**：`useEffect` 监听 `qavlixor-language-change`（detail 驱动 setNameLang + 收集含中文字段批量翻译缓存）+ `value={showLocalizedName(form.x)}`（编辑时用户输入原文直接显示，切语言显示缓存译文）。

## #88 服务端分页模式（余额划转记录——记录多时页面无限变长）
- 页面签名：`{ searchParams }: { searchParams: Promise<{ page?: string }> }`（await）→ `page = Math.max(1, parseInt(...)||1)`；`findMany take:10 skip:(page-1)*10` + `count` → `totalPages`。
- 分页条：上一页/下一页用 `.op-btn` 胶囊 Link（`?page=N`），首末页用 `<span className="op-btn" style={{opacity:.4,pointerEvents:"none"}}>` 置灰；中间文本 `{page} / {totalPages} 页 · 共 {total} 条`。键 `ui.sel.245`（下一页）/`ui.sel.246`（上一页）已存在。
- 每页 10 对齐订单分页风格；**新列表页防变长直接照抄此模式**。

## #89 ★ UiTranslation 批量入库：字段是 i18nJson 不是 translations（两次静默失败事故）
- **事故链**：售后类型词批量补库——① 第一次脚本用 `translations` 字段 create（静默 catch）→ 报\"入库 14 个\"实际全失败；② 修字段名后又遇 `Argument i18nJson is missing`（**UiTranslation 模型只有 `source/scope/i18nJson/note`，无 translations 字段**，schema 882-889 行）。
- **正确姿势**（范本 `scripts/batch-bare-words.mjs`）：
  ```js
  await prisma.uiTranslation.upsert({
    where: { source: src },
    update: { i18nJson: tr, scope: 'dynamic' },
    create: { source: src, scope: 'dynamic', i18nJson: tr, note: 'xxx-batch' },
  });
  ```
  `i18nJson` = `{ "zh-CN": 原文, en: ..., es: ... }`（translateToAllLanguages 的返回结构直接可用）。
- **配套教训**：① **脚本 create/upsert 千万别静默 catch**——打印失败计数（`ok/fail`），跑完 grep `RESULT` 行；② 批量翻译分批（GLM 15 词×7 语言一次会 aborted 超时——**每批 ≤5 词**）；③ **箭头函数里不能 `continue`**（esbuild TransformError）——用 `try/catch` 计数。
- **补库后必验证**：`findMany({ where: { source: { in: words } } })` 对比缺失清单。

## #90 补译机制（report-miss）限流根因 + 修复参数
- **链路**：LanguageSync 收集未命中词 → 4s 防抖合并 ≤30 条 → `POST /api/i18n/report-miss` → 服务端实时翻译入 UiTranslation + 返回 translations → 前端 registerDynamicEntries + 重扫全站（applyDynamicElements + applyBareChinese）**秒级回填**。
- **静默失败三层（用户\"切语言不翻\"的真凶）**：
  1. 服务端 `rateLimited` **每 IP 每分钟 ≤10 次**——超限返回 `{ok:true}`（无 translations）→ 前端不重翻 → 原文不变（频繁切语言/多页面并发共享 IP 额度很快打满）；
  2. `MAX_LIVE=8`——30 条上报只实时翻 8 条，其余进 TranslationMiss 队列等 10 分钟 cron；
  3. 前端 `reportedMisses` 上报即永久标记 → **被限流丢弃的词永不重试**。
- **修复（2026-08-10 已部署）**：限流 10→30 次/分；`MAX_LIVE` 8→15（GLM 40 并发够）；前端改为**成功回填才 `reportedMisses.add(key)`**（限流/失败自动下次重报）。
- **验证姿势**：`fetch('http://127.0.0.1:3000/api/i18n/report-miss', {method:'POST', body: JSON.stringify({texts:['测试词']})})` → 15s 返回 7 语言即链路通。
- **固定类型词直接预置词典**（售后类型/诉求词等——换货/退货退款/仅退款/质量问题…15 词已入库）——不依赖补译，切语言即时翻。

## #91 卖家端批量发货侧栏入口已删（用户拍板）
- PortalShell 发货管理组只剩 运费模板/发货模板；`/seller/batch-ship` 页面 + 订单页\"批量发货\"按钮**仍在**（用户未拍板是否彻底下线——直接访问 URL 还能用）。删功能按 #52 四层法确认范围再动。
- `docs/员工测试手册-卖家端.md`（桌面另有副本）——卖家端全 34 页面 + 21 API + 跨端联动（X 买家 14 项 / Y 管理端 10 项 / Z 通知 4 项）+ 业务规则 R1-R10 + 翻译体系 T1-T7 + 异常边界 U1-U8 + 发版回归清单。**员工测试/发版回归直接引用，别重写**。

## #92 ★ 聊天消息正文不实时翻译（用户 2026-08-10 拍板——翻译范围收缩）
- **拍板原文**："我们是平台，不需要迁就买家和卖家，对话的具体内容不需要实时翻译，别的名字/标题这些依旧按照实时翻译走就可以了。"
- **实现**：ChatWindow 的 `chat-body` 容器加 `data-no-translate`（裸中文兜底排除）→ 消息正文去掉 DynamicText（system 消息 + 普通消息都改 `<span>{body}</span>`）→ 聊天内容零翻译开销、不再触发补译（省 report-miss 限流额度）。
- **保留翻译**：对话头部名字（peerName DynamicText store-name）、会话标题（topic）、状态徽标（status）——照旧。
- **注意**：此决策**覆盖**此前"聊天 body 要翻译"（#90 之前的铁律解读）——docs/翻译铁律.md 的"聊天消息=翻译"条目应同步修正（下次维护铁律文档时改）。

## #94 ★ 忘记密码全链路 + 邮件配置找回 + Prisma Client 重新生成坑
- **占位功能模式**：卖家登录页 forgotPassword 原只有 `setNote("重置密码邮件将发送…")`——**无 API 调用**（用户"点击有提示但收不到邮件"=功能根本没实现）。教训：**"有提示但无效果"类 bug 先看函数体是否真的调了 API**——纯 setState 提示 = 占位。
- **邮件配置找回**：生产 `.env.local` 邮件变量（EMAIL_FROM/SMTP_*）曾被覆盖丢失——**旧配置在服务器 `.env.backup.*` / `.env.local.bak-*` 系列里**（本次从 `.env.backup.20260701094400` 找回）：
  ```
  EMAIL_FROM="<EMAIL-REDACTED>" / EMAIL_PROVIDER="smtp" / SMTP_HOST="smtp.zoho.com"
  SMTP_PORT="465" / SMTP_USER="<EMAIL-REDACTED>" / SMTP_SECURE="true"
  ```
  恢复姿势：`grep -E '^(EMAIL|SMTP)_' <备份> > /tmp/mailenv.txt` → 逐行 `grep -q "^${key}=" .env.local || echo "$line" >> .env.local`（**只补缺失键，不覆盖现有**）。**以后配置丢失先查备份系列，别让用户重配**。
- **SMTP 连通测试**：`npx tsx` 脚本 `await sendEmail({to, subject, text})` → 返回 `{sent:true, provider:"smtp", providerRef:...}` 即通（Zoho 9s 左右）。
- **忘记密码实现要点**：① User 加 `resetToken String?` + `resetTokenExpires DateTime?`（sha256(token) 存 hash，`randomBytes(24).toString("hex")` 作链接 token，30 分钟有效）；② POST `/api/auth/forgot-password`——**防枚举**（邮箱不存在也返回"已发送"）；`sendEmail` 返回 `!sent` 时 502（配置缺失要报错给前端，别静默）；③ POST `/api/auth/reset-password` 校验 token 后 `hashPassword`（`@/lib/password`）更新；④ 重置页 `/reset-password?token=<REDACTED> 必须包 Suspense**）；⑤ 登录页接入真实 API（校验邮箱格式 + loading/error/note 三态）。
- **★ Prisma Client 重新生成坑（本次实测踩到）**：schema 加字段后**服务器 Prisma Client 必须重新生成**——旧 Client 上 `update({ data: { resetToken } })` 静默失败（`catch(() => null)` 吞掉）→ API 返回 ok 但 token 未落库（**"接口成功但数据没写"=查 Prisma Client 版本**）。修复：`pnpm prisma generate` + **PM2 重启**（实例加载旧 Client 需重启才换新）；deploy.py 的 db push 已去掉 `--skip-generate`（以后 schema 变更部署自动 generate）。本地 tsc 过了不代表服务器 Client 新——**生成后必须重启实例再验证落库**。
- **邮件恢复后注册验证邮件一并恢复正常**（同一套 email-provider/Zoho）。

## #93 消息"都在一侧"类 bug 排查链路（本次实测正常的参考路径）- 用户报"买家联系卖家对话框卖家和买家消息都在左侧"→ 实测 **代码/渲染正常**（me=右 flex-end、buyer=左 flex-start）→ 判定疑似旧缓存。
- **排查链路（下次直接照走）**：① CSS 作用域——`.chat-body`/`.msg.me`/`.msg.buyer` 在 `seller-proto.css` 的 `.sap` 前缀下（**ChatWorkspace 根有 `<div className="sap">`**，买卖两端都有）；② senderRole 数据——生产 Message 表是标准 buyer/seller/system/support 值（脚本查分布）；③ role prop 传递——ChatWorkspace → ChatWindow `role={role}`（买家页传 "buyer"）；④ 浏览器实测 DOM：`getComputedStyle(msg).alignSelf`（me=flex-end / buyer=flex-start）。
- **support 消息**（senderRole="support"，平台客服）恒显示在左侧属**正常**（对方视角）——不是 bug。
- 最终结论类问题回复必须给"强刷验证 + 具体会话/截图复现"路径（用户浏览器旧缓存高发，见 #73）。
- ✅ 待办 3/4 已确认（店名输入即翻、订单操作列方案 A 已部署待强刷）。
- **管理端客服工作台仍未做**（admin/contacts 扩展 support 会话回复——发消息 POST 端点待查 ChatComposer）。

## #95 ★ 新增全局 CSS 类前先查重名 + .sap 前缀特异性（op-btn 圆形覆盖胶囊事故）
- **事故链**：订单操作列方案 A（#77）部署后，用户反馈"发货变成圆形徽标、查看/取消是纯文字"——`.op-btn` 胶囊样式**没生效**。
- **根因**：`app/seller-proto.css:409` 存在**历史 `.sap .op-btn`**（26×26 圆形图标按钮，⋯ 更多操作专用）——`.sap .op-btn`（0,2,0）**特异性高于** `globals.css` 新 `.op-btn`（0,1,0）→ 订单页在 `.sap` 作用域内被旧圆形定义覆盖；transfer 分页按钮（#88 用 op-btn）同样被圆形化。
- **修复**：旧用途**改名隔离**（`.op-btn` → `.op-btn-ic`，SellerProductManager 的 ⋯ 按钮同步改类名）——新胶囊定义成为唯一 `.op-btn`。
- **通用教训**：**新增全局类名必须 `grep -rn "\.类名" app/*.css` 查全站重名**——特别是 seller-proto.css / seller-apple.css 的历史类（.sap 前缀特异性更高，静默覆盖 globals.css 新定义）。用户报"样式没生效/变样了"先查 CSS 特异性覆盖，别急着改 JSX。

## #96 ★ 服务器 502 crash loop：部署中断损坏代码的恢复（与 #74 522 不同故障模式）
- **现象**：Cloudflare 502 全站挂；`pm2 jlist` 4 实例全 `waiting restart` + `restarts 99-166`（**crash loop**）；`next-server` 进程 0；内存充足（排除 OOM）。
- **根因**：**部署命令被中断**（terminal 工具掐断）→ 服务器 `tar xzf` 解压半程 → 代码文件损坏 → 实例启动即崩无限重启。
- **恢复**：**完整重新部署**（git archive HEAD → 上传 → 解压覆盖 → db push → next build → pm2 restart×2）→ 4 实例 online + 外网 200（build 日志尾部 "Generating static pages (87/87)" = build 成功标志）。
- **教训**：① 部署中途**不可中断**（~100s 跑完，中断=服务器损坏）；② crash loop 恢复 = 重跑完整部署（解压会覆盖损坏文件），别只 restart；③ build 日志 JSON.parse 报错段是 Next 内部警告，判断 build 成败看 "Generating static pages (N/N)" 完成行。
- **Windows 打包坑（execute_code 里手动部署时）**：`subprocess.run("git archive | gzip", shell=True)` 用 **cmd 不是 bash**——`gzip` 不存在（255）。用 Python：`gzip.GzipFile(fileobj=f, mode="wb").write(git_archive_stdout)`。另外自定义 `def run(cmd, t=...)` 调用时参数名写对（`t=` 不是 `timeout=`——TypeError 中断脚本）。

## #98 ★★ CSS !important 全局规则覆盖自定义类（取消订单圆角 8px 事故——与 #95 不同故障模式）
- **现象**：订单操作列三按钮中，发货/查看（`<a>`）圆角 999px 胶囊，**取消订单（`<button>`）圆角 8px**——同一 `.op-btn` 类渲染结果不同。
- **排查链**（浏览器实测）：`getComputedStyle(btn).borderRadius` 对比元素差异 → 发现元素类型差异（A vs BUTTON）→ **遍历 `document.styleSheets` 找覆盖源**：
  ```js
  for (const sheet of document.styleSheets) { for (const rule of sheet.cssRules) {
    if (/button/i.test(rule.selectorText) && rule.style?.borderRadius === '8px') hits.push({sel, important: rule.style.getPropertyPriority('border-radius')});
  }}
  ```
- **真凶**：`seller-apple.css`（打包后全局）的 **`.seller-portal button { border-radius: 8px !important }`**（与 admin-portal/buyer-portal/payc-page 并列的全局表单规则）——**!important + 特异性（0,1,1）> .op-btn（0,1,0）**；发货/查看是 `<a>` 不受 button 规则影响。`!important` 都压不过 = 对方也是 !important 且特异性更高。
- **修复**：**.op-btn 加 `.seller-portal` 前缀**（`.seller-portal .op-btn`，0,2,1 + !important 压过 0,1,1 + !important）——hover/danger 变体同步前缀。
- **配套**：`.op-btn` 加 button UA 重置（`appearance:none; -webkit-appearance:none; font-family:inherit; line-height:1; padding:0; margin:0; text-align:center`）——`<button>` 与 `<a>` 渲染完全一致（UA 默认内边距/行高会造成视觉微差）。
- **通用教训**：① 同页同类的 `<a>` 和 `<button>` 表现不同 = 有**元素级规则**（全局 `xx button {}`），不是类定义问题；② **`!important` 压不过 = 对方也是 !important**，此时必须**提高自身特异性**（加父级前缀），加更多 !important 无效；③ 卖家端自定义组件样式默认加 `.seller-portal` 前缀最稳（该作用域有全局 `button/input/select/textarea` 8px !important 规则）。

## #97 deploy.py 已更新（v3.1）：commit 容错 + db push 自动 generate
- **db push 去掉 `--skip-generate`**（#94 的 Prisma Client 坑根治）：schema 变更部署时自动重新生成 Client，不再需要服务器手动 `prisma generate` + 重启。
- **commit 容错**（本次部署卡住的直接原因）：`git commit` 无改动时 exit 1（nothing to commit）→ 脚本退出 → 部署卡死。已改：`r.returncode != 0 and "nothing to commit" not in (stdout+stderr)` 才退出——无改动继续部署。
- 部署命令仍是一条：`python scripts/deploy.py "说明"`（tsc 增量 → commit → tar.gz → SFTP → 解压+db push → build --no-lint → restart×2 → 探测）。
## #99 卖家昵称字段删除（用户拍板）+ 操作列最终态
- **拍板**："卖家个人信息 卖家昵称删掉，只保留店铺名字"——账号设置页个人信息只留店铺名称。
- **全链路清理（SellerAccountSettings.tsx）**：① 删昵称输入框整行；② 保存逻辑 `changeQueue` 类型 `"nickname" | "storeName"` → 只 `"storeName"`（删昵称入队分支）；③ `pendingNickname` 定义 + 按钮 disabled/文字条件（`pendingNickname || pendingStoreName` → 只 pendingStoreName）删；④ 输入即翻 collect 数组只 `[formRef.current.storeName]`；⑤ PATCH /api/seller/account body 只传 storeName；⑥ 表单回滚（submitted 判断）只 storeName。
- **保留（无害）**：类型字段 displayName（initial 数据仍返回）、emitIdentity 广播（侧栏存量昵称显示）、头像 alt fallback（`form.storeName || form.displayName || "商"`）——**不删数据**，只是界面不展示/不可改。管理端 nickname 审核逻辑保留（存量）。
- **操作列最终态（#77/#95/#98 之后的用户最终拍板，2026-08-10）**：① "操作"表头 `textAlign: "right"` → `"center"`（与按钮列居中对齐）；② 取消订单**去掉 `.op-btn.danger`**（红描边红字）→ 与发货/查看订单完全一致（白底 #D2D2D7 灰边深字）——**危险操作红色标识被用户否决**（操作列内统一；弹窗内确认按钮 `.btn danger` 仍可保留红色）。op-btn 类最终形态见 #98（`.seller-portal .op-btn` + button UA 重置）。

## #100 客服工作台（遗留待办）——本会话确认仍未做
- 管理端 `/admin/contacts` 仍是"官网联系表单记录"（NotificationMessage queued），**无 support 会话回复 UI**；卖家端"联系官方客服"（POST /api/chat/support 创建 seller_support 会话）已上线但管理端看不到/回不了。
- 待做：admin/contacts 扩展"客服会话"标签页（seller_support/buyer_support 会话列表 + 消息 GET（已支持 admin）+ 回复框（发消息端点查 ChatComposer 的调用）。

## #101 ★ 通知偏好接入架构（"待接"占位 → 完整链路，全站可复用模式）
- **存储**：`User.notifyPrefsJson String?`（JSON `{order, aftersale, fund}`；缺省 null=全开；system 锁定不入库）。
- **发送过滤（核心）**：`lib/notification-service.ts` 加：
  - `PREF_GROUP: Record<templateKey, "order"|"aftersale"|"fund">`（order_created/paid/cancelled*/closed/shipment_updated/payment_* → order；after_sale_* → aftersale；deposit_* → fund——**未归类的键不受开关控制始终发**）；
  - `isNotifyAllowed({recipientEmail, role, templateKey})`：非 seller / 无邮箱 / 未归类 / 无偏好记录 → true；`prefs[group] !== false` 才放行；
  - `notify()` 开头 `if (!(await isNotifyAllowed(input))) return null`——**关闭分组不产生 NotificationMessage 记录**。
- **API**：`app/api/seller/notify-prefs`（GET 读 / PUT 写，`user.upsert({where:{email}})`；system 不入参强制 true；未登录 401）。
- **前端**（SellerAccountSettings 通知偏好卡片）：NOTIFY_PREFS 去掉写死 `on` → `notifyPrefs` state 驱动；`<span className="tg">` → `<button type="button" className={\`tg ${on?"on":""} ${locked?"disabled":""}\`} aria-pressed disabled={locked} onClick=toggle>`；保存按钮调 PUT + 成功提示（3s 消失）。
- **验证姿势**：DB 写偏好 `{order:false,...}` → `await notify({recipientEmail, role:"seller", templateKey:"order_paid",...})` 返回 null（FILTERED）vs `after_sale_created` 创建记录（CREATED）——测完清理。
- **可复用**：任何"用户可关闭的通知类"照此模式（PREF_GROUP 映射表 + 过滤函数 + 开关 UI + PUT API）。

## #103 ★ 硬编码操作提示语（短命提示）必须直接接翻译键——补译通道来不及
- **用户报**："通知偏好已保存 这句话不走翻译"——saveNotifyPrefs 里 `setPrefsMessage("通知偏好已保存")` 硬编码中文。
- **根因**：这类提示是**短命提示**（`setTimeout(…, 3000)` 3 秒自动消失）——裸中文兜底走 report-miss 补译要 10-15 秒回填，**提示早就消失了**，用户永远看不到翻译（且白白占用补译限流额度）。
- **修复模式**：硬编码提示 → 翻译键（7 语言）+ `getTranslation(currentClientLanguage(), key)` 替换。本次 6 句批量接入（`seller.account.prefsSaved/prefsSaveFailed/entitySubmitted/entityRequired/entitySubmitFailed/closeSubmitted`）：
  1. GLM `translateToAllLanguages` 生成 7 语言（**每批 ≤2-3 句**，6 句一次必超时崩溃——#89 的 ≤5 词在本场景要更保守）；
  2. 插键按 #82 位置顺序法（es,fr,pt,ru,ar,zh,en——锚点 `seller.account.save` 7 区）；
  3. 代码 `setXxxMessage("中文")` → `setXxxMessage(getTranslation(currentClientLanguage(), "key"))`；
  4. 验证：服务器 `npx tsx` 跑 `getTranslation(lang, key)` 抽查各语言值（比浏览器实测稳定——短命提示 3 秒消失，浏览器点击定位容易错过）。
- **通用规则**：**任何 setXxxMessage/setNote 里的中文提示语一律翻译键**；短命提示（<10s 自动消失）绝不能依赖裸中文兜底/补译。全站此类提示存量不少（保存成功/失败/已提交），遇到页面继续按此模式批量清理。
- **顺带**：实体变更弹窗标题键 `seller.account.entityModalTitle`（7 语言）同批插入；清理过时键值（"提交变更（待接）"→"提交变更"、en "(coming soon)" 后缀）。

- **提交 API**（`app/api/seller/change-requests`）：`requestType` 白名单加 `"entity"`；newValue 为 **JSON 字符串**（6 字段：entityType/country/licenseNumber/address/representative/contactPhone）；长度上限 1000（原 40）；JSON 结构校验（entityType 须 string 或数组）；`currentValue` = 现有主体字段 JSON.stringify（**对比防重复提交**）；待审核去重提示按类型三分支标签。
- **管理端审核**（`app/api/admin/change-reviews/[id]`）：approve 分支改三分支（nickname → User.displayName+SellerAccount.contactName / storeName → Store.name / **entity → 解析 JSON 更新 SellerAccount 6 字段**：businessEntityType（数组取 `[0]`）/businessRegisteredCountry/businessLicenseNumber/businessRegisteredAddress/legalRepresentativeName/contactPhone）；通知文案 label 三分支 + entity 值摘要（"（详见审核记录）"不塞 JSON）。
- **管理端列表**（AdminChangeReviews）：`TYPE_LABEL` 加 `entity: "店铺主体"`；`entitySummary(value)`（JSON → `类型 / 执照号 / 法人` 摘要）替代原始 JSON 显示。
- **卖家端**：主体卡片"提交变更"按钮（去掉 disabled 占位）→ Modal 弹窗 6 字段编辑（预填当前值 + 必填校验 entityType/licenseNumber）→ POST → 本地 `pendingChangesState` 追加 entity → 按钮变"变更审核中"禁用。
- **翻译键**：`seller.account.entityModalTitle` 7 语言（插键按 #82 位置顺序法）；顺带清理过时键值（"提交变更（待接）"→"提交变更"、en "Submit Change (coming soon)"→"Submit Change"）。
- **验证**：浏览器提交（弹窗→改执照号→提交→DB 见 pending_review 单）→ 脚本执行审核逻辑（解析 JSON 更新）→ 执照号变化确认 → 清理还原。
- **可复用**：任何"卖家提交 → 管理端审核 → 更新字段"的资料变更类型照此扩展（提交 API 白名单 + 审核三分支 + 列表 label/摘要 + 前端弹窗）。
