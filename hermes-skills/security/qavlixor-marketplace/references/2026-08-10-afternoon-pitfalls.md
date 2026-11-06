# 2026-08-10 下午会话坑速查（#86-#99）

> 翻译体系续战 + 通知/物流/配色修复 + 部署提速 + 服务器 522。SKILL.md 已 100KB 超限，本文件为新增内容的落点。

## #86 裸中文兜底混合文本拆翻（LanguageSync applyBareChinese）
- 旧规则 `/[0-9A-Za-z$€£¥]/` 直接跳过 → "FLYYYYYY测试店铺" 中文部分永不翻译（含字母=拼接文本）
- 新逻辑（三段）：①整串查词典（"48 小时内发货" 预置命中直接替换）②未命中 → 拆中文段 `[\u4e00-\u9fff]{2,}` 逐段查词典重组（"测试店铺"→"Test Store"→"FLYYYYYY Test Store"）③未命中段 push missing 上报补译（回填后重扫命中）
- `missDataLikePattern`（6+位数字/邮箱/URL）仍整串跳过——数据保护不变
- 注意：拆翻重组无空格（"商品ID"→"ProductID"）——字段名类文本应走 data-i18n 键而非依赖拆翻

## #87 输入框"输入即翻"（账号设置店名/昵称 + 发品表单）
- 模式：监听 `qavlixor-language-change` 事件 detail 存入 state（**绝不读 localStorage/currentClientLanguage()**——Browserbase 测试环境 localStorage 异常读空 → 返回 zh-CN → 显示层永不翻译）
- POST /api/i18n/form-translate（fields: {原文: 原文}）→ 返回 {translations: {原文: {lang: text}}} → 缓存 nameI18n[原文][lang]
- 显示 `nameI18n[text]?.[lang] ?? text`；form 值保持原文（提交/保存永远原文）——显示层换肤不碰数据
- 输入框 disabled（审核中）同样生效（纯展示场景）

## #88 Modal 弹窗标题翻译（全站 20 处弹窗通吃）
- 陷阱双层：①调用处 `data-i18n-title` 属性传给 Modal 组件被忽略（组件不接收该 prop，不透传 DOM）②即使透传，LanguageSync 的 `[data-i18n-title]` 处理只 `setAttribute("title", ...)`（tooltip 语义）不改文本内容
- 修复（components/seller/Modal.tsx）：props 解构 `"data-i18n-title": titleKey` + 内嵌语言事件监听（lang state）+ `displayTitle = titleKey && lang !== "zh-CN" ? getTranslation(lang, titleKey) || title : title` 渲染 `<h3>`
- 所有带 data-i18n-title 的 Modal 调用处自动生效，无需逐个改

## #89 插键串位（第二次教训——占位值=目标值）
- 场景：先插占位"反馈与建议"再按语言顺序替换——zh 语言值恰好=占位值 → replace 无法区分 → 第 6/7 次替换串位（zh 区被写 en 值、en 区残留中文）
- 正确做法：**直接按区语言顺序插正确值**（es,fr,pt,ru,ar,zh,en 与文件顺序一致——用 nav.messages 锚点位置验证过），不要"占位后替换"两步走
- 插入点：锚点**键名前**换行插入（`line_start = s.rfind("\n", 0, pos)+1`）；**不要在键名后插**（会把原键的值挤到同行 → `"nav.feedback": "VAL", "原值",` 结构破坏）
- 验证铁律：`re.findall(r'键A": "([^"]*)",\n\s*键B": "([^"]*)",')` 配对检查同语言 + 键数 = 区数×语言数；插后必跑 `npx tsx scripts/check-translations.mts`

## #90 patch replace_all 模糊匹配灾难（重要工具教训）
- 复杂 JSX（卡片头+时间轴嵌套节点）old_string 不唯一时，fuzzy 匹配会把**不相邻的相似片段**也替换 → 结构错乱（card-h 重复、tl-item 重复嵌套）
- 修复流程：`git checkout -- <file>` 恢复 → **精确唯一 old_string 逐处 patch**（每处只替换最小唯一片段，绝不用 replace_all 处理 JSX 结构）
- 判断：grep 到 3 处相同代码 ≠ 3 处都要 replace_all——先 git diff 看替换效果，结构类代码逐处来

## #91 通知"进入即已读"设计陷阱（"全部已读点击无反应"）
- 根因：page.tsx 服务端进入即 `updateMany readAt` → 前端 unreadCount=0 → "全部已读"按钮永远 disabled → 点击无声
- 修复：①移除进入即已读（未读保留显示）②/api/notifications/read 支持 body.ids（单条/多条，不带=全量）③单条点击 Link onClick 本地 setRead + fetch {ids:[id]}
- 教训：**让按钮"永远可用但有反馈"或"有未读才可用"**——不能有"进入页面自动完成按钮功能"的设计（按钮变摆设）

## #92 物流详情状态只判 shipped
- 顶部徽标 `shipped ? "运输中" : "待发货"` → 已签收订单也显示"运输中"
- 修复：`["已签收","已完成","已关闭"].includes(order.status)` 优先 → 徽标"已签收"+ green；时间轴"包裹在途"文字同条件显示"—"
- 通用教训：状态徽标要覆盖完整状态集，不能只判断单一布尔

## #93 状态配色一致性 → 抽共享函数
- 列表页 statusTone（待售后/待付款/待发货=orange；已关闭/已退款=red；已完成/已收货=green；其他=blue）vs 详情页固定 `st blue`
- 修复：`lib/order-status.ts` export statusTone，列表页+详情页共同 import（服务端组件跨页 import 共享 lib 函数可行）——以后改配色一处生效
- 用户明确要求"列表和详情一致"——UI 一致性类问题优先抽共享模块

## #94 部署后用户看到旧效果（"是不是你骗我"）
- 机制：SPA 客户端导航不重新加载 HTML → 已开标签页永远用旧 JS chunk；部署只影响新打开的页面
- 验证部署链路：curl HTML 响应头（cache-control no-cache + cf-cache-status DYNAMIC = 未缓存实时）+ buildId 对比 + build 产物 grep 修复代码 + 浏览器实测
- 回应质疑：给证据（不是空口），然后给用户 30 秒验证法（Ctrl+Shift+R 强刷 / 无痕窗口复现）
- 可提议加"版本更新提示"（前端轮询 buildId 变化弹刷新提示）——用户可选

## #95 服务器 522 排查与预防
- 现象：Cloudflare 522（源站无响应）；日志无攻击迹象（全是正常 CF 请求 + connect() failed 111）
- 根因链：4 实例共 5.3GB + 无 swap + 部署 build 峰值 → 系统无响应 → 云厂商看护硬重启（last reboot 无 shutdown 记录）
- 预防（已落地）：`fallocate -l 4G /swapfile && chmod 600 && mkswap && swapon` + fstab 持久化；PM2 `--max-memory-restart 1600M`（4 实例）+ pm2 save
- 诊断命令：`last reboot`（重启时间）+ `grep 07:2x /var/log/syslog`（启动过程）+ `pm2 jlist`（实例内存）

## #96 deploy.py 一键部署（85-100s）
- 流程：本地 tsc 增量（--incremental 已有，~2s）→ git commit → git archive|gzip → paramiko SFTP → 服务器 `tar xzf` → `pnpm prisma db push --skip-generate`（schema 变更自动应用，dbpush:0=成功）→ `next build --no-lint`（本地 tsc 已把关，跳过重复 typecheck）→ pm2 restart×2 → curl 200
- 提速点：tsconfig incremental + next.config typescript.ignoreBuildErrors + build 命令 --no-lint
- 用法：`python scripts/deploy.py "改动说明"`——commit message 参数化，一条命令全自动

## #97 卖家端反馈与建议 + 联系官方客服
- chat 体系已支持 admin/support 角色（visibleWhere：admin 可见 buyer_support+seller_support；viewerSenderRole → "support"）——机制完整只缺入口和 UI
- 新增：SellerFeedback 模型（prisma，db push 自动建表）+ /api/seller/feedback（POST 提交 + GET mine 列表）+ /api/chat/support（创建/复用 seller_support 会话，按 sellerEmail+status!=closed 复用）+ 卖家端 /seller/feedback 页 + 侧栏"反馈与建议"入口（PortalShell 客户服务组）
- 管理端客服工作台（admin/contacts 显示 support 会话 + 回复）待做——发消息 API 已支持 admin
- 部署 schema 变更：deploy.py 已加 db push 步骤，无需手动

## #98 UI 多方案预览（用户铁律执行样例）
- 订单操作列三按钮（发货/查看订单/取消订单）样式不统一且拥挤 → 先做 HTML 多方案（D:\跨境商城\会话产物\）Chrome 打开用户挑 → 用户选方案 A
- 方案 A 落改：全局 `.op-btn` 胶囊（白底 1px #D2D2D7 描边、96×28、圆角 999、font 12/500；.danger 红描边 #FF3B30）+ 操作列垂直堆叠 gap 6 + 发货时限独立一行置顶（移出组头 float:right）
- 发货时限文字（"今天 18:00 前"）橙色 #FF9500 独立行——不再与按钮挤

## #99 测试环境账号/会话陷阱（Browserbase）
- 浏览器实测被多店铺会话阻碍：导航后侧栏店铺名变化（EchoSail ↔ 北 Northline Goods）→ 订单归属店铺 ≠ 当前会话 → 详情页 404（权限隔离正常行为）
- 验证本店订单前先确认当前会话店铺（侧栏店名），或重新登录干净会话
- psql 直连失败（postgres 密码错）→ 用项目 Prisma 脚本（tsx + .env.local 注入 + @prisma/client）代替——服务器 /www/tiktok 下临时 _q.mts 跑完即删
