# 2026-08-10 反馈页 i18n 补全 + 卖家端按钮样式 + 页头英文 + 密码框眼睛

## 反馈页（/seller/feedback）纳入翻译系统（#168）

**根因**：SellerFeedbackPanel.tsx 用了 `seller.feedback.*` 键，但 translations.ts 里 14 个键只有 zh 区（11209-11216），6 个键（catSuggestion/catBug/catOther/eyebrow/contentPlaceholder/contactPlaceholder）完全不存在 → 切英文显示键名字面量（`seller.feedback.eyebrow`）或中文。

**修复**：补 21 键 × 6 语言区（es/fr/pt/ru/zh/en，126 处）+ 组件裸中文改键（submitted/submitFailed/supportFailed/statusDone/statusPending/officialReply）+ 删英文 sub。

**★ 插键脚本正确方法（本 session 踩 3 次坑后定稿）**：
1. **失败法 A**：循环内 `re.search(键)` 全局检查"是否已存在" → 第一次插入后其他区全部误判已存在 → 只插了 zh 区 5 键。
2. **失败法 B**：插入后 `re.finditer` 重算位置但 for 循环继续用旧索引 → 6 次全插到 es 区（90 处全乱）→ `git checkout lib/translations.ts` 恢复重来。
3. **✅ 定稿法**：每语言区用**值特征锚点**（该语言 title 的唯一翻译值，如 es="Comentarios y sugerencias"）定位 title 行；`seg = 本区 title 行 到 下一 title 行之间`；**在 seg 内**检查键是否已存在（避免跨区误判）；插入后**不重算位置**（各区 title 行值唯一，互不影响）；6 个语言循环各独立 search。
4. Python 陷阱：f-string 表达式内不能含反斜杠（`insert.count('"seller.feedback.')` 在 f-string 里报 SyntaxError）→ 拆开写。

## 卖家端内容区 `.btn` 基础样式缺失（#169）

**根因**：`.btn` 只定义了登录表单作用域（`.slog .btn`，seller-apple.css:675-678）；内容区按钮退化默认样式（浅灰底 8px 圆角）——反馈页"提交反馈/发起客服会话"被 vision 判定"像浏览器默认按钮"。

**修复**：seller-apple.css 新增 `.seller-portal .btn` 通用样式（Apple 胶囊：白底灰边 999px、`.primary` 黑底白字、`.sm` 小尺寸、`:disabled` 透明度），radius 加 `!important`（与 seller-proto.css:50 `.sap .btn` 的 999px!important 对齐；实测不加 !important 时仍显示 8px，覆盖源未明）。

**影响**：该样式作用于全部卖家端内容区按钮（订单/售后/资金/通知页），全站统一胶囊——符合用户"全站按钮胶囊"偏好。

## 页头英文 eyebrow 删除（用户嫌丑，2 次）

- PortalShell.tsx:252 页头 `<p className="eyebrow">Seller Workspace / Operations Console</p>` → 删除，只留中文 h2 标题。
- 反馈页 sub"Feedback & Suggestions"同样删。
- **教训**：卖家/管理端页头**不要放大写英文 eyebrow**（用户明确"太丑了"），标题只用中文（data-i18n 切语言）。

## 密码框小眼睛统一（#170）

`components/PasswordInput.tsx`（已有小眼睛：wrap + toggle 按钮 + 睁眼/闭眼 SVG，CSS 在 globals.css 12918+）。本 session 把 **reset-password 页 + 卖家登录（SellerLoginForm）+ 卖家注册（SellerRegisterForm 2 处）** 全部从 `type="password"` 换成 `<PasswordInput className="inp" ...>`（type 自动接管）。买家登录（app/login）原本已有 Show password。**教训**：全站密码框一律用 PasswordInput，新增密码框不要写裸 input type=password。

## 语言切换器图标（#171）

`.language-switcher-globe` 从黑底 + 🌐 emoji → **白底圆形（#fff + 1px #d8d8de 边框）+ 蓝色(#0071e3)地球线条 SVG**（circle + 横线 + 椭圆经线，15px）。用户明确要求"白色地球那个样式"（非 emoji、非黑底）。

## 相关 refs
- 2026-08-10-admin-transparency（管理端代充不发通知，用户拍板"前端显示成自己充值"）
- 2026-08-10-notification-types（16 类型清单 + targetUrlOf 跳转规则）
