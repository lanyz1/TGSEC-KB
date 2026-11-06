# 2026-08-10 商品审核通知链路 + 本轮修复沉淀

## 商品审核结果通知卖家（新链路，原完全无通知）

**根因**：`app/api/admin/products/[id]/review/route.ts` 审核通过/驳回只写运营日志 + businessEvent，**从未发通知** → 卖家通知中心永远没有审核结果。

**修复**（部署 + DB 词典预置）：
1. `review/route.ts`：findUnique include 加 `store.sellerAccount.user.email`；update 后动态 import notify，发 `product_reviewed`（title=商品审核已通过/未通过，body=商品名+备注/驳回原因，metadata={productId, productTitle}）。**用 row.store 而非 updated.store 取邮箱**（updated 的 include 没带 sellerAccount，TS2339 坑）。
2. `app/seller/notifications/page.tsx`：
   - `targetUrlOf` 加 `if (row.templateKey.startsWith("product_")) return "/seller/products";`（放在 deposit 行后、change_request 行前）
   - `categoryOf` 兜底 return "system"（product_reviewed 自动归系统页签，无需改逻辑，加注释）
3. `PREF_GROUP` 不加键 → 未归类键不受卖家通知偏好开关影响，始终发（符合预期）
4. 整句词典预置（防混合翻译乱码，如"product审核Approved"）：商品审核已通过/未通过、已通过审核并上架、未通过审核已驳回、可在商品管理中查看、请修改后重新提交、审核备注、原因 — 写服务器 DB `uiTranslation`（source 唯一，i18nJson 6 语言）
5. 测试数据：DB 直接插 notificationMessage（字段=recipientEmail/role/channel/templateKey/title/body/status:"sent"/metadataJson/sentAt；**无 recipientId 字段**）→ 浏览器卖家通知中心验证显示+跳转 → 删测试数据

## 翻译键补全脚本定稿法（两次踩坑后验证）

给 translations.ts 批量补键（N 键 × 6 语言区）：
- ❌ 坑1：`re.search` 全局判断"键已存在" → 只插了第一区（其他区被误判存在）
- ❌ 坑2：插入后 `re.finditer` 重算所有 title 位置、for 循环仍用旧 pos → 6 次全插同一区（es 区）
- ✅ 定稿：**每语言独立执行**——按该语言 title 键的**值特征**做唯一锚点（如 `"seller.feedback.title": "Feedback & Suggestions"`），区段边界=下一个任意语言 title 行；区内检查键存在才插；插入后**不重算、不循环复用位置**（6 个语言各跑一次独立的 search+insert）
- zh 区已有键会跳过（脚本天然幂等）
- 插完 `grep -c` 验证：N 键 × 6 区 + 每区 title 重复 = 总数
- 出错先 `git checkout lib/translations.ts` 恢复再重来

## 页面"没纳入翻译"体检法

1. `grep -c '"seller.feedback' lib/translations.ts` 看键总数
2. `for k in ...; do grep -c "键$k" ...; done` 看每个键的行数：**title 6 区 vs 其他键 1 区 = 根因**（键只在 zh 区）
3. 代码里用但 translations.ts 不存在的键（getTranslation fallback 中文）→ 一并补
4. 浏览器切 en 实测：data-i18n 键缺失会**显示键名字面量**（如 seller.feedback.eyebrow）——一眼定位
5. 裸中文（成功提示/状态标签/拼接文案）逐一改 data-i18n + 补键

## 卖家端 .btn 通用样式缺失（按钮退化默认样式）

**根因**：seller-apple.css 的 `.btn` 只在 `.slog`（登录表单）作用域定义 → 内容区按钮（反馈页等）退化浏览器默认（浅灰底 8px 圆角）。

**修复**：seller-apple.css 表单控件区加 `.seller-portal .btn` 通用定义（白底灰边胶囊）+ `.btn.primary`（黑底白字）+ `.btn.danger`/`.btn.sm`；**border-radius: 999px !important**（实测有隐藏覆盖源，不加 important 会显示 8px）。

## 密码框小眼睛统一

`components/PasswordInput.tsx` 已有（眼睛切换 type=password/text + .password-input-wrap/.password-toggle CSS 在 globals.css）。全站统一：reset-password 页、SellerLoginForm、SellerRegisterForm 换 PasswordInput（买家登录原本有 Show password；卖家账号设置/买家安全页原本就用 PasswordInput）。改时记得加 import。

## 页头英文 eyebrow

PortalShell.tsx 252 行 `<p className="eyebrow">Seller Workspace / Operations Console</p>` 已删（用户嫌丑，只留中文标题 h2）。语言切换器图标 = 白底圆 + 蓝色地球 SVG（globals.css .language-switcher-globe background #fff + border + color #0071e3）。
