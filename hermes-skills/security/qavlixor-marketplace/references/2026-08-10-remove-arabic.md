# 2026-08-10 删阿拉伯语（7→6 语言）+ 本会话翻译/订单修复集

## ★ 删除一种语言（7→6）的完整清单（以删 ar 为例）

translations.ts 结构（删除前先 `grep -n "^const \|^export const "` 拿全部分块行号）：
- LanguageCode 类型行（`code: "en" | ... | "ar"`）→ 去 ` | "ar"`
- languages 数组条目（`{ code: "ar", ... }`）→ 删行
- import 行（`import { esPack, frPack, ptPack, ruPack, arPack }`）→ 去 `, arPack`
- 大块：`const arFull`（8257 行）到 `const zh`（10343 行）前；`const ar`（19790 行）到 `export const translations`（20660 行）前
- translations 定义里引用行（`ar: { ...zh, ...en, ...arPack, ...ar, ...arFull },`）→ 删行
- 其他文件残留：LanguageSync.tsx 的 `t()` 返回对象去 ar（**参数签名保留 ar?=en 可不动调用处**）+ `if (normalized === "ar")` 分支行删；lib/dynamic-translations.ts 的 `t()` 返回去 ar + `ar: { ... }` 对象行；lib/policy-i18n.generated.ts 所有 `^\s*"ar":` 行（111 处）；lib/machine-translator.ts prompt 模板 JSON shape 去 `"ar": "..."`

## ★★ 删大块代码的安全方法（本会话踩坑）

- **用行号切片，不要用正则找块边界**。正则 `\nconst ` 不匹配 `\nexport const ` → ar 块删除时找不到下一个边界 → 从 ar 定义删到文件尾（translations 定义/getTranslation 全没了）。
- 流程：①先 `grep -n "^const \|^export const "` 确认所有块边界行号 ②Python 按 0-based 行号 `del lines[start:end]` ③删除前打印边界行内容验证（如 `lines[8256][:40]`）④删除后验证关键导出计数（`grep -c "export const translations"` 应为 1、`getTranslation` 应为 1）⑤坏了立即 `git checkout <file>` 恢复重来（本会话就是先恢复再重删）。
- 引用清理后用 `npx tsc --noEmit | grep "error TS" | awk -F'(' '{print $1}' | sort | uniq -c` 分类残留，逐个文件清。

## 翻译体系：zh 区占位键/缺失键批量修复（#129-131）

- `getTranslation` = `translations[code][key] ?? translations[fallback][key] ?? key`——fallback 也是 zh-CN，所以 **zh 对象缺失/占位 → 返回键名显示乱码**（英文界面因 en 覆盖正常，切回中文就露馅）。
- 修法：`const zh: TranslationMap = {` 块内 `"key": "key"` 占位 → 从 JSX 原值收集（正则 `\bdata-i18n="([^"]+)"[^>]*>([^<{][^<]*)<` 扫 app/components 全部 tsx，键→中文文本映射）批量替换；zh 缺失但 JSX 有原值的键 → 在 zh 对象末尾 `};` 前补插（用行号定位，插 `  "key": "值",` 行）。
- 注意 en/es/fr/pt/ru 区也可能有同类占位（切那些语言同样乱码）——用户报哪个区修哪个。

## 订单卡片图（#128 续）：数据层修复 ≠ 渲染层修复

- 订单会话 cardPayload 补了 imageUrl（创建时查 Product.images[0] + 存量脚本），但 ChatWindow 订单卡片缩略图**写死 `{BOX_SVG}`**（商品卡片读 payload.imageUrl、订单卡片没读）→ 图永远不显示。修复：76 行改 `{payload.imageUrl ? <img/> : BOX_SVG}`。
- 教训：补数据后必须检查渲染层是否真的读了该字段。

## 订单搜索加固（#133）

- 搜索串原为 `${order.id} ${order.buyer} ${items}`；buyer 映射已含 displayName→email→guestEmail 前缀，但搜完整邮箱不中。加 `order.buyerEmail ?? ""`（Order 类型加可选字段 `buyerEmail?: string`，orderFromPrisma 返回 `row.buyer?.email ?? row.guestEmail ?? ""`）。**可选字段**避免 4 处手工构造 Order 的地方报 TS2741。
- 数据教训：售后工单 buyer 是提交时快照，买家改名后（QA买家2→Bello Weitz）工单显示旧名、订单显示新名——搜旧名无结果属数据非 bug，先查 User.displayName 现状再下结论。
- **搜索字段下拉持久化（#136）**：`<select name="field" defaultValue="orderNo">` 硬编码 → 提交后刷新回到默认。修：从 searchParams 读 `field` 参数（`params.field` 需加进 searchParams 类型注解，否则 TS2339）`defaultValue={fieldParam}`；并按字段过滤搜索（buyer→`${order.buyer} ${order.buyerEmail}`、tracking→order.logistics、sku→items.sku join、默认/orderNo→全字段 haystack 含 id/buyer/email/items/logistics/skus）。教训：**表单控件 defaultValue 勿硬编码，从 URL 参数恢复**。

## 通知中心多选/删除/翻页（#127 续）

- 服务端分页：searchParams.page，每页 10，totalCount 按 tab 过滤统计；组件 `pagination?` **可选**（admin 端共用组件不传则无分页栏）。
- 删除 API：POST /api/seller/notifications/delete `{ids}` 或 `{all:true}`，currentEmail 校验，deleteMany。
- 批量条：复选框（checkbox click stopPropagation 防触发行点击）+ 全选 + 已选 N 条 + 删除选中；页头"删除全部"用 window.confirm。
- 分页文案/删除按钮**不要挂不存在的 data-i18n 键**（getTranslation undefined → textContent=undefined 显示空）——裸中文走兜底即可。

## 其他本会话修复

- **售后 reason 串英文片段**（"Requested 8.99 USDT"）：存量数据英文，7 语言全通后会补译；可主动预置词典（`Requested`→已申请）秒翻，无需部署（客户端词典后台增量拉取）。
- **买家登录页忘记密码**：LoginSubmitForm（买家/卖家共用）加"忘记密码？"链接 + forgotPassword（校验邮箱→POST /api/auth/forgot-password→成功 note 绿色提示）；链接样式 `.slog .slog-forgot` 在 seller-apple.css（`.slog` 容器内生效，买家登录页也在 slog 布局内）。
- **进度条 In Progress 不翻**：SSR 固化 getTranslation(currentClientLanguage())（服务端返回 defaultLanguage）→ 包一层 `<span data-i18n="ui.sel.325">` 让 LanguageSync 切语言处理。
- **form-translate 必须传对象**：`fields: Object.fromEntries(keys.map(k => [k, k]))`——传数组会被 Object.entries 转索引键 0/1 返回错位（模板弹窗+账号设置两处同修）。
- **data-i18n 被 React 重渲染覆盖回中文**：观察者加 data-i18n 元素 characterData 监听（React 覆盖后再替换，值相同不赋值→无循环）。

## 验证清单（删语言后）

1. 浏览器打开语言切换器 → 只剩 6 种（无 العربية）
2. 切每种语言页面正常（无键名/无 ar 残留值）
3. localStorage 存过 ar 的用户 → normalizeLanguage 自动 fallback 到默认语言
4. 新商品提交 → GLM 只生成 6 语言
