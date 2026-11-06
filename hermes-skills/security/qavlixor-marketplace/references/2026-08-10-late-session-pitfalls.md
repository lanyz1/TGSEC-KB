# 2026-08-10 后段会话坑（#104-#117）

（#70-#103 见同目录 2026-08-10-session-pitfalls.md；本文件覆盖通知中心/导出弹窗/物流/订单配色/忘记密码/补译调优/消息拍板/下拉体检等后段工作）

## #104 CSS 特异性覆盖（op-btn 圆角 8px vs 999px）
- 现象：发货/查看订单(a 元素)=999px 胶囊，取消订单(button)=8px 圆角——同一 .op-btn 类
- 根因：全局 `.seller-portal button { border-radius: 8px !important }`（表单统一规则）特异性高于 `.op-btn`，且同为 !important
- 排查法（可复用）：①浏览器 getComputedStyle 对比**同 class 不同元素类型**（A vs BUTTON）——radius 不同 ⇒ 元素类型相关规则 ②遍历 document.styleSheets 找含 button 的 8px 规则（含 getPropertyPriority 看 !important）③提高专用类特异性（`.seller-portal .op-btn`）
- 教训：!important 不敌更高特异性 !important；button 元素 UA 残留（appearance/line-height/padding）也要重置才能与 <a> 渲染一致

## #105 部署中断 → 服务器 crash loop
- 现象：部署命令被掐断后全站 502；PM2 4 实例全部 waiting restart（restarts 100+）
- 根因：tar 解压半程 → 代码文件损坏 → 启动即崩循环
- 恢复：完整重新部署（git archive→上传→解压→db push→build 87/87→restart×2）即可
- 预防：①部署中不可中断（~100s 跑完）②deploy.py git commit 容错（nothing to commit 不再 exit 1——否则无改动时部署卡死在 [2/6]）

## #106 db push --skip-generate 陷阱
- deploy.py 原用 `prisma db push --skip-generate` → schema 加字段后服务器 Prisma Client 旧版 → update 新字段**静默失败**（catch(()=>null) 吞掉）
- 症状：API 返回 ok:true 但字段没落库（如 resetToken 为 NULL）
- 修复：db push 不带 --skip-generate（自动 generate Client）；deploy.py 已改；已部署环境手动 `pnpm prisma generate` + pm2 restart

## #107 UiTranslation 入库字段 = i18nJson（不是 translations）
- 批量补词典词：`upsert { where:{source}, update:{i18nJson, scope:'dynamic'}, create:{source, scope:'dynamic', i18nJson:{'zh-CN':原文, en, es, fr, pt, ru, ar}, note} }`
- 写错字段（translations）→ Prisma 报 "Argument `i18nJson` is missing" → catch 静默吞 → **看似入库实际没入**
- 验证：findMany where source in [...] 抽查确认

## #108 批量翻译分批（GLM 超时）
- translateToAllLanguages 单批 6 句超时崩溃（Node v22 TransformError/无输出）；**每批 2-4 词稳妥**（单句约 19s）
- 服务器 tsx 脚本：翻译结果写 /tmp/*.json 再 sftp 下载回本地插键（避免 stdout 截断）
- 脚本陷阱：箭头函数内不能 continue（用 try/catch 计数）

## #109 补译机制调优（切语言补译"失效"根因）
- 三层根因：①服务端限流 10 次/分/IP（切语言/多页面并发共用额度）→ **静默拒绝**（返回 ok:true 但无 translations）→ 前端不重翻 ②MAX_LIVE=8（30 条上报只实时翻 8 条，其余等 cron）③前端 reportedMisses 永久去重（被限流的词不再重试）
- 修复：限流 10→30 次/分；MAX_LIVE 8→15；前端**成功回填才标记**（被限流/失败的词下次切语言自动重报）

## #110 忘记密码全链路（占位→实现）+ 邮件配置恢复
- 原实现是占位：`forgotPassword() { setNote("重置密码邮件将发送...") }`——无任何 API
- 实现：User.resetToken/resetTokenExpires + POST /api/auth/forgot-password（token sha256 落库 + 30min + 防枚举 + 未配置返回 502）+ /reset-password 页面 + POST /api/auth/reset-password + SellerLoginForm 接真实 API（带 email 输入框值）
- **邮件配置丢失恢复**：.env.local 被覆盖后邮件全挂——检查服务器 `.env.backup.*`（Zoho SMTP 在 .env.backup.20260701094400：EMAIL_PROVIDER=smtp / SMTP_HOST=smtp.zoho.com / <EMAIL-REDACTED>）——grep EMAIL_/SMTP_ 变量合并回 .env.local（不覆盖已有）
- SMTP 验证：node 脚本调 sendEmail → `{sent:true, providerRef}` 即通

## #111 消息正文不翻译（用户拍板 2026-08-10）
- **对话具体内容显示原文**（不翻译不补译）；**名字/标题/状态仍实时翻译**
- 实现：ChatWindow 消息正文去掉 DynamicText（渲染原文 span）+ 消息流容器 `.chat-body` 加 data-no-translate（裸中文兜底也跳过）
- 顺带验证：消息左右分列代码逻辑正确（mine=senderRole===role；.sap .msg.me flex-end）——用户报"都左侧"多为旧缓存

## #112 短命提示语必须翻译键
- 操作反馈提示（保存成功/失败/已提交）setTimeout 3-5 秒消失 → 裸中文兜底补译 10-15s **来不及** → 必须翻译键 + getTranslation
- 本会话 6 句：seller.account.prefsSaved/prefsSaveFailed/entitySubmitted/entityRequired/entitySubmitFailed/closeSubmitted（7 语言）

## #113 下拉翻译体检（35 处扫描法）+ 固定词预置
- 原生 select option：裸中文兜底**不扫 select 内**——必须 data-i18n / data-i18n-dynamic 标记
- AppleSelect 面板（div/span）：裸中文兜底覆盖（词典命中秒翻，miss 补译 10-15s）
- 固定选项词**预置 UiTranslation 词典 → 秒翻**（本会话 17 词：售后类型/请选择/本月/差额转回/发货仓系列/闭店原因/运费模板名含金额混合文本——翻译质量可接受）
- 体检报告形式：HTML 表格（页面/组件/下拉/选项/状态 ✅⚠️❌/建议）放 D:\跨境商城\会话产物\

## #114 卖家端侧栏店名不翻译
- PortalShell 220 行 `identityTitleKey = portal === "seller" ? undefined : ...`——卖家端无键 → data-i18n=undefined → 永不翻译
- 修：卖家端店名挂 `DynamicText as="strong" kind="store-name"`（词典翻译显示，保存值始终原文）
- 通用教训：动态值（店名/昵称）不能靠 data-i18n 键——用 DynamicText（data-i18n-dynamic 词典链路）或组件内挂 qavlixor-language-change 事件

## #115 通知偏好接入（User.notifyPrefsJson）
- 存储：User.notifyPrefsJson（{order, aftersale, fund}，system 锁定，缺省全开）
- API：GET/PUT /api/seller/notify-prefs（未登录 401）
- 发送链路：notify() 前 `isNotifyAllowed`——PREF_GROUP 映射 templateKey→分组（order/aftersale/fund），未归类键始终发，seller+recipientEmail 才查偏好
- 前端：开关 button.tg（locked 禁用）+ 保存落库 + 3 秒提示

## #116 店铺主体变更接入（entity change-request）
- 提交 API：/api/seller/change-requests 支持 requestType="entity"（newValue=JSON 6 字段：entityType/country/licenseNumber/address/representative/contactPhone；长度 1000；JSON 结构校验；与 currentValue 对比防重复；同类型待审核去重）
- 管理端审核：admin/change-reviews/[id] 三分支（nickname→User+SellAccount.contactName / storeName→Store.name / entity→解析 JSON 更新 SellerAccount 主体字段）
- 管理端列表：TYPE_LABEL 加 entity + entitySummary() 摘要（避免表格显示原始 JSON）
- 卖家端：弹窗 6 字段编辑（必填校验）+ 提交后 pendingEntity 审核中状态

## #117 订单状态徽标配色统一
- 抽共享 `lib/order-status.ts` statusTone(status)：待售后/待付款/待发货→orange；已关闭/已退款→red；已完成/已收货→green；其余 blue
- 列表页 + 详情页同一函数——避免两处不一致

## 其他本会话小坑
- 翻译键插入（再次验证 #41）：7 区语言顺序 es,fr,pt,ru,ar,zh-CN,en（按锚点出现顺序）；**占位值=目标值**（zh 值"反馈与建议"=占位）时 replace 串位 → 按行号（锚点行+1）精确修正；插后必跑 check-translations.mts + grep 抽查 7 区值
- Modal data-i18n-title 透传：Modal 组件需接收 titleKey prop + 内嵌 qavlixor-language-change 监听（getTranslation 标题文本）——否则标题永不翻译（LanguageSync 只处理 title 属性非文本）
- 忘记密码测试：POST /api/auth/forgot-password 对未注册邮箱返回 ok（防枚举）——真实链路测试必须用已注册邮箱 + 查 resetToken 落库
- 服务器操作：PrismaClient 脚本查 store.sellerAccountId 需 include store 或用 req.storeId 二次查询
