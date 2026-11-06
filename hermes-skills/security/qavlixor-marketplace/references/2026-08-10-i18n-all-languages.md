# 2026-08-10 翻译体系"7 语言全通"改造（#114-#115）

## #114 ★用户拍板：翻译体系 7 语言全通（不管源语言）
**决策**（用户原话："我要7语言的，不管源是哪国语言都能进我们翻译体系的"）：任意源语言（中文/英文/西语/阿语/俄语…）都要进翻译体系，外国客户上传的内容自动翻译，零手动修补。

**现状分层（回答用户"翻译系统只处理中文源吗"时的准确表述）**：
- 裸中文兜底（界面未标记文案）：改造前只扫中文（`chineseTextPattern`），英文硬编码永不翻（bug 模式见下）
- data-i18n 键：7 语言值全备，切语言取对应值（与源无关）
- 动态词典/商品 i18nJson：key=源文本原文（任意语言），i18nJson 存 AI 翻译 7 语言——商品层早已双向

**改造落地（LanguageSync applyBareChinese 通用化）**：
```ts
function textNeedsTranslation(language, text) {
  // 中文目标：拉丁/西里尔/阿语文本需要翻译；ar/ru 目标：中文/拉丁等需要翻译；
  // 拉丁目标（en/es/fr/pt）：含中文/西里尔/阿语需要翻译；纯拉丁只查词典不补译
  //（同字符集无法可靠区分 en/es/fr/pt，miss 不补译防把界面英文文案乱翻）
}
```
- 整串查词典：`if (whole && whole !== trimmed)` 直接替换（去掉了原 `!chineseTextPattern.test(whole)` 限制——中文目标下英文源命中词典即替换）
- 拆翻仅保留中文段逻辑（拉丁段拆翻无意义）
- 补译收集：拉丁目标语言下 `纯拉丁文本`（`/^[A-Za-z\s.,!?;:'"()-]+$/`）跳过不补译（防误翻），中文/ar/ru 目标正常收

**铁律豁免双保险（关键！用户问"会不会误伤之前不走翻译的"）**：
- 前端 applyBareChinese：`isNoTranslateTerm(trimmed)` 跳过（NO_TRANSLATE_TERMS = USDT/US$/TRC20/ERC20/BEP20/TRX/ETH/BTC/USDC/PayPal/Wise/SWIFT/BIC，纯专有名词才豁免，含中文混合文本如"USDT 充值"仍处理）
- 服务端 report-miss 路由：同样过滤 `!(NO_TRANSLATE_TERMS.test(item) && !CJK.test(item))`
- 已保留的既有豁免（核对清单）：.language-switcher（语言列表）、missDataLikePattern（6+位数字/邮箱/URL/物流追踪号）、data-i18n-raw（管理端审核）、data-no-translate（聊天正文）、input/textarea/select/script/style/contenteditable

## #115 硬编码英文源 bug 模式（界面层翻译单向的坑）
**现象**：售后工单 deadline 显示 "Within 30 days after receipt confirmation"（英文），切任何语言不翻；中文界面也显示英文。
**根因**：`app/api/orders/[id]/aftersale/route.ts` 写入时就是英文硬编码（AfterSaleCase.deadline 字段存英文）——翻译体系界面层以中文为源（裸中文兜底只扫中文），英文源文本永远不翻。
**修复三层**：①写入源改中文（"确认收货后 30 天内"，走裸中文兜底）②存量修正（`updateMany where deadline='英文'` 批量改中文，本次 22 条）③词典预置该中文词（切语言秒翻，不等补译）。
**通用教训**：凡数据库字段/服务端拼接的界面文案，一律存中文源（底层原值中文），显示层翻译；英文硬编码 = 中文界面显示英文的 bug。发现此类先查写入点，不是渲染点。

## 补译限流放宽（2026-08-10 下午，与 #114 配套）
**根因**：report-miss 每 IP 10 次/分太严——切语言频繁/多页面并发共用 IP 额度 → 超限静默拒绝（返回 `{ok:true}` 但无 translations）→ 前端不重翻 → 词永远不翻，看起来"补译没生效"。
**修复三件套**：①限流 10→30 次/分 ②MAX_LIVE 8→15（GLM 并发 40，15 条 1-2s）③前端 `reportedMisses` 改为**成功回填后才永久标记**（被限流/失败的词下次切语言自动重报，原来上报前就 add 导致永久卡死）。

## #129 ★切中文显示键名乱码（zh 基础对象占位/缺失键，买家订单详情实测）
**现象**：英文界面切中文后，data-i18n 元素显示 `ui.fix.4`/`ui.cn.1` 等键名；二次刷新（SSR 中文原值）恢复——用户报"中文翻译乱码"。
**根因链**：`translations` 是 `Record<LanguageCode, TranslationMap>`，`"zh-CN": zh`（zh 是独立 const 基础对象），`en: {...zh, ...en}`（en 继承并覆盖 zh）。getTranslation = `translations[code][key] ?? translations[fallback][key] ?? key`——**键不存在或值为键名时直接返回键名**。实测 zh 对象里 **147 个键值就是键名本身**（历史占位 `"ui.fix.4": "ui.fix.4"`）+ **22 个键在 zh 对象缺失**（ui.cn.* 等，只在 en/es 等区有）→ 切中文 getTranslation 返回键名；英文界面因 en 覆盖正常。
**修复脚本模式（一次跑通）**：
1. 正则定位 zh 对象：`re.search(r'const zh: TranslationMap = \{', s)` → 到下一个 `\n(const |export )`
2. 收集 JSX 原值：`re.finditer(r'\bdata-i18n="([^"]+)"[^>]*>([^<{][^<]*)<', code)`（宽松版含属性在前的，如 `<span className="lbl" data-i18n="...">中文</span>`）→ {key: 中文原值}
3. 占位替换：`re.sub(r'"KEY": "KEY"', '"KEY": "中文"', zh_block)`
4. 缺失补插：在 zh 对象 `};` 前插入 `  "key": "中文",` 行（注意 zh 对象行范围 = `const zh` 到下一个 `const en: TranslationMap` 前的 `};`）
5. 验证：`grep -oE '"ui\.fix\.4": "[^"]*"'`（第一处应为 zh 的中文值）+ `npx tsc --noEmit`
**配套教训**：
- **SSR 固化的 getTranslation 文本**（无 data-i18n 标记，如进度条状态 `{getTranslation(currentClientLanguage(), "ui.sel.325")}`）切语言后客户端不更新（SSR 用 defaultLanguage）→ 包一层 `<span data-i18n="键">` 让 LanguageSync 接管
- 值=键名的占位不只在 zh：其他语言区也可能有（切西语/阿语出现键名同理批量修）；29 个无 JSX 原值的占位需手工补
- **LanguageSync-React 冲突三模式汇总**：①textContent 替换销毁 React fiber 文本节点 → React 更新写脱离 DOM 的旧节点 → label 永不更新（修：React 元素加 `key={active?.value}` 强制重建 + data-no-translate）②data-i18n 元素被 React 重渲染覆盖回原文（修：MutationObserver 的 characterData 分支监听 `closest("[data-i18n],...")` 再触发 applyLanguage）③SSR 固化 getTranslation 文本（修：挂 data-i18n）
- **form-translate API 传参陷阱**：`fields` 必须传"键=文本"对象（`Object.fromEntries(keys.map(k => [k, k]))`）——传数组会被 `Object.entries` 转成索引键 `0/1`，返回错位前端永远 miss（SellerShippingTemplates + SellerAccountSettings 两处都踩过）
