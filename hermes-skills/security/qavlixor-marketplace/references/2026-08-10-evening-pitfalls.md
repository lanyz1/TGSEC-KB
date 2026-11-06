# 2026-08-10 晚场 pitfalls（#104-#113）

## #104 ★LanguageSync textContent 替换 vs React fiber 断链（下拉"点不动"真凶）
**现象**：AppleSelect（发货仓/发货时限）点击选项后，面板 is-active 正确跳到新选项（onChange 生效、value 已更新），但触发按钮 label 永远显示旧值——看起来"点不动"。
**根因**：LanguageSync 裸中文兜底用 `element.textContent = value` 替换 DOM 文本节点 → React fiber 引用的原文本节点被销毁（断链）→ React 后续更新（选择新值）写到已脱离 DOM 的旧节点上 → DOM 永远显示替换残留值。React 状态其实一直是对的。
**诊断信号**：`is-active`（React 渲染）与 `label`（DOM 文本）不一致 = fiber 断链。查词典确认选项翻译值正常、onChange 正常，但 label 不动。
**修复**（AppleSelect.tsx）：label span 加 `key={active?.value ?? ""}`（值变化强制 React 重建节点，绕开断链）+ `data-no-translate`（阻止 LanguageSync 替换）双保险；选项 span 也加 data-no-translate，翻译改为组件内 `translateDynamicValue(lang, label, "operation")`（挂 qavlixor-language-change 事件）。
**通用教训**：凡是 LanguageSync 会替换的文本节点所在的 React 受控组件，都要防"DOM 替换 → fiber 断链"。改动 DOM 文本的翻译层（textContent）天然与 React 冲突——宁可组件内翻译（React 状态驱动），不要靠外部 DOM 替换。

## #105 CSS 特异性陷阱：全局 button 8px 规则
**现象**：取消订单按钮圆角 8px，发货/查看（同为 .op-btn）999px 胶囊。
**根因**：全局规则 `.seller-portal button { border-radius: 8px !important }`（管理端/卖家端通用表单规则）特异性（0,1,1+!important）压过 `.op-btn`（0,1,0+!important）。
**修复**：`.seller-portal .op-btn`（0,2,1）前缀提高特异性。
**诊断**：浏览器 console 遍历 `document.styleSheets` 找匹配元素的 border-radius 规则及 specificity/important；同 class 不同元素渲染差异（a vs button）= 元素选择器规则在作怪。
**相关**：旧 `.sap .op-btn`（26px 圆形图标按钮，⋯）与新胶囊 .op-btn 同名冲突——旧用途改名 `.op-btn-ic` 隔离。

## #106 部署中断 → 服务器 crash loop → 502
**现象**：部署命令被掐断（terminal 中断）后，全站 Cloudflare 502。
**根因**：deploy.py 服务器端"解压→build"中途被杀 → 代码文件半程损坏 → PM2 4 实例启动即崩（restarts 99-166 crash loop）→ 全挂。
**恢复**：完整重新部署（git archive→gzip→SFTP→解压→db push→next build --no-lint→pm2 restart×2→200 探测）。
**预防**：①部署期间不可中断（~100s 跑完）；②deploy.py git commit 步骤容错（`nothing to commit` 不再退出——本次部署卡住的直接原因：脚本第 2 步 commit 失败即 sys.exit）。

## #107 服务器 Prisma Client 旧版（schema 变更静默失败）
**现象**：forgot-password API 返回 ok:true，但 User.resetToken 没落库。
**根因**：deploy.py 用 `db push --skip-generate` → 服务器 Prisma Client 不认识新字段 → `update().catch(() => null)` 静默吞错。
**修复**：deploy.py 去掉 `--skip-generate`（db push 自动 generate Client）+ 服务器手动 `pnpm prisma generate` + `pm2 restart`（generate 后必须重启实例才加载新 Client）。
**诊断**：API ok 但 DB 无变化 + prisma clientVersion 报 Unknown argument = Client 旧版。

## #108 uiTranslation 入库字段名：i18nJson 不是 translations
**现象**：批量补词脚本报"入库 14"但实际全失败（静默 catch），查询查不到。
**根因**：`p.uiTranslation.create({ data: { translations: ... } })`——模型字段是 `i18nJson`（Json 必填），无 translations 字段 → Prisma 报 "Argument i18nJson is missing"。
**正确写法**（照抄 scripts/batch-bare-words.mjs）：
```ts
await prisma.uiTranslation.upsert({
  where: { source: w },
  update: { i18nJson: { "zh-CN": zh, ...map }, scope: "dynamic" },
  create: { source: w, scope: "dynamic", i18nJson: { "zh-CN": zh, ...map }, note: "..." },
});
```

## #109 GLM 翻译分批：>4 词/批容易超时崩溃
**现象**：translateToAllLanguages 一批 6 词 → Node 进程直接退出（无错误输出）；1-2 词正常（~19s）。
**规律**：GLM 每词 ~11.7s，一批 >4 词超过 tsx 进程稳定窗口。**2 词/批最稳**；结果 `writeFileSync('/tmp/x.json')` 再 SFTP 下载（避免 stdout 截断丢 JSON）。

## #110 邮件配置找回：旧 .env.backup 是金矿
**现象**：忘记密码点击只有提示、邮箱无信——①前端 forgotPassword 是占位（只 setNote 无 API）②生产 .env.local 无邮件配置。
**恢复**：`grep -l 'EMAIL_FROM\|SMTP_HOST' /www/tiktok/.env.backup.*` 找到 Zoho SMTP（smtp.zoho.com/<EMAIL-REDACTED>），`while read line; do key="${line%%=*}"; grep -q "^${key}=" .env.local || echo "$line" >> .env.local; done` 合并（不覆盖现有）。
**验证**：`sendEmail` 直调返回 `{sent:true, providerRef}`。
**忘记密码已实现全链路**：User.resetToken/resetTokenExpires + POST /api/auth/forgot-password（防枚举+30min+邮件）+ /reset-password 页 + POST /api/auth/reset-password（sha256 hash token 存库）。

## #111 通知偏好接入模式
User.notifyPrefsJson（{order,aftersale,fund}，缺省全开，system 锁定）+ GET/PUT /api/seller/notify-prefs + 前端开关（tg button）+ **发送链路过滤**：lib/notification-service.ts 的 `PREF_GROUP: Record<templateKey, group>` 映射 + `isNotifyAllowed()`（role==="seller" && recipientEmail → 查偏好 → 关闭跳过）。未归类 templateKey 不受开关控制始终发。

## #112 店铺主体变更（entity）接入模式
change-requests API 扩展 `entity` 类型：newValue=JSON.stringify(6 字段)，长度上限 1000（vs 40），校验 `typeof entityType === "string" || Array.isArray`；管理端审核（admin/change-reviews/[id]）approve 分支解析 JSON 更新 SellerAccount（businessEntityType/businessRegisteredCountry/businessLicenseNumber/businessRegisteredAddress/legalRepresentativeName/contactPhone）；管理端列表 entitySummary() 摘要显示（类型/执照号/法人），避免表格显示原始 JSON；通知文案 label 三分支。

## #113 下拉翻译体检方法（35 处）
原生 select（option 带 data-i18n / data-i18n-dynamic 即已接）+ AppleSelect（选项 span 依赖兜底+补译，首次 10-15s）。固定词预置 UiTranslation 后秒翻。报告 HTML 模板见会话产物《下拉翻译体检报告.html》（分类 ✅已接/⚠️补译/❌未预置 + 建议预置词表）。
