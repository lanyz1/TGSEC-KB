# 2026-08-10 第二轮会话坑（#101-#106）

## ㊿通知偏好接入模式（User.notifyPrefsJson）
原来是"待接"占位（开关静态渲染 + 保存按钮禁用）。完整接入 4 层：
1. **schema**：User 加 `notifyPrefsJson String?`（JSON `{order, aftersale, fund}`，缺省全开，system 锁定不入参）
2. **API**：`app/api/seller/notify-prefs/route.ts`（GET 读/PUT 存，未登录 401；PUT 只收 3 个布尔）
3. **前端**：SellerAccountSettings——`NOTIFY_PREFS` 常量去 `on` 字段；`tg` span → button（可点切换 + `aria-pressed` + system `disabled`）；保存按钮调 PUT + prefsMessage 提示；initial 加 notifyPrefs（page.tsx 从 `user.notifyPrefsJson` 解析传入）
4. **发送链路**：`lib/notification-service.ts` 加 `isNotifyAllowed()`——PREF_GROUP 映射 templateKey→分组（order_created/order_paid/order_cancelled*/order_closed/shipment_updated/payment_* → "order"；after_sale_* → "aftersale"；deposit_deducted/deposit_proof_submitted/deposit_reviewed → "fund"；**未归类键（conversation_message/change_request_result 等）不受开关控制始终发**）；notify() 开头 `if (!(await isNotifyAllowed(input))) return null`（关闭分组连 NotificationMessage 都不创建）。
**验证套路**：服务器脚本直接调 `notify()`（order_paid 关闭→null 被过滤 / after_sale_created 开→创建）比浏览器快；前端保存落库用 DB 直查 notifyPrefsJson。
**坑**：新增前端 state 时先加 setXxxMessage state 再写函数；页面卡片用 `textContent.includes` 匹配标题时注意 i18n 后是英文（"Notification Preferences" 大写 P，小写匹配失败）。

## ㊿op-btn 胶囊 CSS 冲突（两轮才解决）
卖家端订单操作列 `.op-btn` 胶囊（方案 A）被两个覆盖源压住：
- **覆盖源 1**：旧 `.sap .op-btn`（seller-proto.css:409，26×26 圆形图标按钮——SellerProductManager"⋯"更多操作菜单用）特异性 0,2,0 > 新 .op-btn 0,1,0 → 发货/查看/取消全变 26px 圆。**修复：旧用途改名 `.op-btn-ic`（CSS + 组件 className 同步）**。
- **覆盖源 2**：全局重置块 `.seller-portal button{border-radius:8px !important}`（admin/seller 共用表单规则）0,1,1+!important > `.op-btn` 0,1,0+!important → 取消订单（button 元素）8px 圆角、发货/查看（a 元素）999px——**同一 .op-btn 类不同元素不同圆角，症状最迷惑**。**修复：`.seller-portal .op-btn` 前缀提特异性 0,2,1**。
- **排查工具**：浏览器 console 遍历 `document.styleSheets` 找 `borderRadius==='8px'` 且 selectorText 含 button 的规则（一次性看全命中源）。
- **配套**：.op-btn 加 button UA 重置（appearance:none/line-height:1/padding:0）使 button 与 a 渲染完全一致；"操作"表头 textAlign right→center 与按钮列对齐；取消订单去掉 `danger`（红描边）与发货/查看统一白底灰边（用户要求，弹窗内确认按钮仍保留红色）。

## ㊿聊天正文不翻译（用户拍板 2026-08-10）
用户原话："我们是平台，不需要迁就买家和卖家，对话的具体内容不需要实时翻译，别的名字标题这些依旧按照实时翻译走"。实现：ChatWindow 消息正文 `<DynamicText as="span" value={message.body} kind="note" />` 全部改 `<span>{message.body}</span>`（system 消息同样）+ 消息流容器 `.chat-body` 加 `data-no-translate`（裸中文兜底排除整块）。头部名字/会话标题/状态徽标保留 DynamicText。

## ㊿忘记密码全链路（原来只是占位 setNote）
卖家登录页 `forgotPassword()` 原来只 `setNote("重置密码邮件将发送到你的注册邮箱...")`——无 API 无邮件。完整实现：
1. schema：User 加 `resetToken String?` / `resetTokenExpires DateTime?`（token 明文只进邮件链接，库内存 sha256）
2. `POST /api/auth/forgot-password`：查 User（不存在也返回"已发送"防枚举）→ 生成 token 30 分钟 → sendEmail（重置链接含 token；`result.sent` false 返回 502）
3. `POST /api/auth/reset-password`：token hash 校验 + 过期检查 → `hashPassword` 更新 → 清 token
4. `/reset-password` 页面：`useSearchParams` 读 token + 新密码/确认密码 + 成功跳卖家登录
5. 卖家登录页：校验邮箱格式 → fetch → 成功提示"已发送"（防枚举文案）
**邮件配置**：生产 = Zoho SMTP（EMAIL_FROM=<EMAIL-REDACTED> / SMTP_HOST=smtp.zoho.com / 465 / SMTP_SECURE=true）。**配置曾从 .env.local 丢失（用户报"没收到邮件"）——旧备份 `.env.backup.20260701094400` 里有完整配置，按 key 缺失合并恢复**。验证：node 调 sendEmail 看 `{sent:true, provider:"smtp"}`。
**坑**：服务器 schema 加字段后**必须重新 `prisma generate` + `pm2 restart`**（deploy.py 的 db push --skip-generate 导致 token 落库静默失败——API 返回 ok 但 DB 没写，症状隐蔽；deploy.py 已改 db push 自动 generate）。

## ㊿导出弹窗/Modal 标题翻译
`data-i18n-title="ui.fix.83"` 传给 Modal 组件但 Modal 没透传（props 只收 title）→ h3 无属性 → LanguageSync 找不到 → 标题永不翻译。**修复：Modal.tsx 加 `"data-i18n-title": titleKey` prop + 内嵌语言监听（useState lang + window qavlixor-language-change 事件）→ `getTranslation(lang, titleKey)` 渲染 h3 文本**——全站所有带 data-i18n-title 的 Modal 通吃（20 处）。弹窗内字段列表（导出 8 字段）是裸中文 → 加 `seller.products.exportField.*` 键（8×7 语言，锚点法插入，插后跑 check-translations）。

## ㊿订单状态徽标统一（lib/order-status.ts）
列表页有 statusTone 函数（待售后/待付款/待发货→orange、已关闭/已退款→red、已完成/已收货→green、其余 blue）但详情页写死 `st blue` → 待发货详情页蓝色不一致。**抽共享 `lib/order-status.ts` 的 `statusTone()`，列表页 + 详情页两处 import 同一函数**。物流详情页状态徽标只判 `shipped`（已签收也显示"运输中"）→ 改为 `["已签收","已完成","已关闭"].includes(order.status) ? "green" : shipped ? "blue" : "gray"` + 时间轴"包裹在途"文字在已签收时显示"—"。
**坑**：patch 该物流页时 replace_all 匹配了 3 处相似片段导致结构错乱——恢复文件（git checkout）后用小范围唯一上下文逐个 patch。
