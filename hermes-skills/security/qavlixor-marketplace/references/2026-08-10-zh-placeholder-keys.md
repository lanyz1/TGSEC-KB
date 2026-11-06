# zh 占位键乱码 + 渲染层写死占位 + 买家忘记密码（#129-131，2026-08-10）

## 一、★切中文显示键名（ui.fix.4 等）——zh 基础对象占位键（#129）

**现象**：买家订单详情页英文切中文后，标签显示 `ui.fix.4`/`ui.cn.1` 等键名（乱码）；二次刷新恢复。卖家端英文界面正常（en 覆盖），中文界面全乱。

**根因（数据层）**：`lib/translations.ts` 结构为 `"zh-CN": zh`（zh 是**基础 const 对象**），其他语言 `{ ...zh, ...en, ...esPack... }` 继承覆盖。**`const zh: TranslationMap = {`（10343 行）里有 147 个键值就是键名本身**（历史遗留占位 `"ui.fix.4": "ui.fix.4"`），另有 **ui.cn.\* 等 22 个键在 zh 对象里根本不存在**。`getTranslation` 逻辑 `translations[code][key] ?? fallback[key] ?? key`——zh 区占位/缺失 → 返回键名。SSR 渲染 JSX 原值（中文）正常，切语言客户端替换才暴露。

**修复模式（脚本批量，可复用）**：
1. 定位 zh 对象：正则 `const zh: TranslationMap = \{`（注意**带类型注解**，`const zh = {` 匹配不到）→ 到下一个 `\n(const |export )` 结束
2. 占位键：`re.findall(r'"([^"]+)": "\1"', zh_block)` 找值=键名
3. 中文原值来源：全站 JSX 正则 `\bdata-i18n="([^"]+)"[^>]*>([^<{][^<]*)<` 收集 `{key: 中文}`（注意 data-i18n 前面可能有其他属性，用 `\b` 前缀）
4. 替换占位 + 在 zh 对象末尾 `};` 前插入缺失键（按行号定位：`lines[zh_end]` 是 `};`，在其前插）
5. 验证：服务器 `npx tsx` 跑 `getTranslation('zh-CN', key)` 逐个确认

**本会话结果**：147 占位中 118 个修复（JSX 有原值）、22 个缺失键补插（ui.cn.1→订单号等）；剩余 29 个无 JSX 原值的占位 + 其他语言区（es/fr/pt/ru/ar）可能有同类占位——切那些语言出现键名时按同样模式批量修。

**进度条 "In Progress" 不翻译**：`OrderProgressSteps.tsx` 46 行 `<small>{getTranslation(currentClientLanguage(), "ui.sel.325")}</small>`——SSR 固化的 getTranslation 文本（无 data-i18n 标记）切语言不更新。修复：包一层 `<span data-i18n="ui.sel.325">` 让 LanguageSync 处理。

## 二、订单会话商品卡片仍无图——渲染层写死 BOX_SVG（#130）

**现象**：数据层补了 imageUrl（见 #128）后仍无图。

**根因（渲染层，两层问题通用教训）**：**数据补了必须检查渲染层是否读**。`ChatWindow.tsx` 订单卡片（66-82 行）的缩略图**写死 `{BOX_SVG}` 占位**（76 行），根本没读 `payload.imageUrl`——商品卡片（53 行）读、订单卡片（76 行）不读。修复：76 行改为 `{payload.imageUrl ? <img src={payload.imageUrl} .../> : BOX_SVG}`。

**教训**：修复"缺图/缺数据"类问题时，数据层（cardPayload 补字段）+ 渲染层（组件读字段）两层都要查——数据补了渲染没读 = 用户实测还是老样子。

## 三、买家登录页忘记密码（#131）

**现象**：买家登录页（`/login`，用 `components/seller/LoginSubmitForm.tsx` role="buyer"）没有忘记密码入口——卖家登录页（`SellerLoginForm.tsx`）已有。

**修复**：LoginSubmitForm 加 `forgotPassword()`（复用 SellerLoginForm 逻辑）+ 密码框下 `slog-forgot` 链接（`data-i18n="auth.login.forgot"`）+ 成功绿色 note（`seller-auth-note` style color #1D9B4C）。后端 `/api/auth/forgot-password` + `/reset-password` 页 **buyer/seller 共用**（都查 User 表，无需 role 区分）。

**注意**：`slog-forgot` 样式在 `app/seller-apple.css`（`.slog .slog-forgot`，限定 .slog 容器内）——买家登录页是 slog 布局所以生效；若在非 slog 容器用需自带样式。

## 四、通知中心多选/删除/翻页（附）

卖家端通知中心（`/seller/notifications`）：服务端分页 10 条/页（`searchParams.page`，同 transfer 模式）；删除 API `POST /api/seller/notifications/delete`（`{ids}` 或 `{all:true}`，currentEmail 校验）；组件复选框 + 全选 + 批量条 + 页头"删除全部"（confirm）+ 分页栏。`SellerNotificationList` 被 admin 端复用——**pagination prop 必须可选**（admin 不传时不分页栏）。
