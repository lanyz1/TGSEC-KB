<!-- archived from /root/.hermes/skills/security/qavlixor-notification-and-time/SKILL.md on 2026-10-21 -->

---
name: qavlixor-notification-and-time
description: >-
  测绘引擎·用 when qavlixor 通知/时间显示改动。recipientEmail 铁律、时间 ISO 模式、通知多语言。
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-notification-and-time`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-notification-and-time/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-notification-and-time（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-notification-and-time/`

溯源（仅标记）：`hermes/software-development`

---

# qavlixor 通知投递与时间显示规范

## 通知投递铁律(2026-08-14 生产实证)
- **通知必须带 recipientEmail**:卖家通知中心按 `recipientEmail=卖家邮箱` 查询。空邮箱 = 记录存在但**永远查不到**——生产曾 5 条 seller/order_paid 通知全空,一条没投出去,表面"发了"实际全废。
- 发卖家通知用 `sellerEmailOfStore(storeId)`(lib/notification-service.ts):store → sellerAccount.userId → user.email 三级查。
- 排查"收不到通知":先读调用点(是否真发、发给谁),再查生产数据验证假设,别凭代码印象断言。生产验证 SQL:
  `SELECT "role","templateKey",count(*) FILTER (WHERE "recipientEmail" IS NULL OR "recipientEmail"='') FROM "NotificationMessage" GROUP BY 1,2`
- 真实下单卖家通知的 3 条支付链路都要发 order_paid:payment-confirm(收银台确认)/ checkout 余额分支 / pay-balance(余额补付)。

## 时间字段模式(时区一类 bug 防线)
- 后端返回时间**一律完整 ISO 带 Z**(`toISOString()`),**禁用 `.slice(0,16).replace("T"," ")`**——那是 UTC 字符串,前端直接显示错 8 小时(资金中心曾全字段中招)。
- 前端渲染统一 `fmtLocal`: `new Date(iso).toLocaleString("zh-CN",{hour12:false})`,列表/CSV 导出全覆盖。
- SSR/服务端组件读查看者语言:`(await cookies()).get(languageStorageKey)?.value ?? "zh"`(languageStorageKey 在 lib/translations.ts)。
- 存储/调度统一 UTC;订单号前 12 位 = yyMMddHHmmss(UTC)。

## 通知多语言(2026-08-14 用户拍板纳入 6 语言)
- 通知 title/body 存库是中文原文(不在 translations.ts UI 键体系)。多语言走 **lib/notification-templates.ts** 模板字典:16 模板 × 6 语言 × 角色/参数分支,`renderNotificationText(lang, row)` 渲染,未知模板/缺参数回退原文(存量兼容,不用改库)。
- 新增通知模板:①body 用占位符(`${p.orderNo}` 风格)②metadata 带渲染参数(合并版 order_paid 需 count+store)③字典补 6 语言。
- **排除**:conversation_message(消息本体,绝不模板化)、contact_*(客服主题)。
- 渲染点:卖家/管理端通知中心页 + 两个 notifications-recent API(铃铛)。
- 通知模板统一 order_paid(生成订单与真实下单一致,2026-08-14);生成订单按店合并一条(metadata.count),真实单一条一通知。
