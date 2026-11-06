# 密码框小眼睛全站统一（2026-08-10）

用户需求：设置/修改密码框要有"小眼睛"明文切换（不知道输入是大写还是小写）。

## 统一组件

`components/PasswordInput.tsx` —— 带 👁 明文切换的密码输入框：
- props 为 `Omit<React.InputHTMLAttributes<HTMLInputElement>, "type">`，**除 type 外原样透传**（className/placeholder/data-i18n-placeholder/autoComplete 都走 props）
- 内部 `useState visible` 切换 `type="text" | "password"`
- wrapper `<span class="password-input-wrap">` + `<button class="password-toggle">`（睁眼/闭眼两个 SVG）
- CSS 在 `app/globals.css` `.password-input-wrap`（position:relative, input padding-right:40px !important 为眼睛留位）/ `.password-toggle`（absolute right 9px 居中）

## 使用现状（全站密码框清单）

| 位置 | 状态 |
|---|---|
| 买家端 账户设置→安全（改密码 3 框 + 注销密码框）| ✅ 原本就有（BuyerAccountForms.tsx 用 PasswordInput）|
| 卖家端 账号设置→修改密码（3 框）| ✅ 原本就有（SellerAccountSettings.tsx）|
| 买家登录 | ✅ 原有独立 Show password 按钮（保留）|
| 忘记密码→设置新密码页（app/reset-password/page.tsx 新密码+确认）| 🔧 2026-08-10 补：普通 input→PasswordInput |
| 卖家登录（SellerLoginForm.tsx）| 🔧 2026-08-10 补 |
| 卖家注册（SellerRegisterForm.tsx 密码+确认）| 🔧 2026-08-10 补 |

## 换组件操作要点

- 直接替换 `<input className="inp" type="password" ...>` → `<PasswordInput className="inp" ...>`（删掉 type 属性）
- 记得加 `import { PasswordInput } from "@/components/PasswordInput";`
- 页面级表单（reset-password 等）是 client 组件才能用（useState）——reset-password 本身就是 "use client" 页

## 陷阱

- 买家登录页的 Show password 是另一套实现（表单内按钮），不要重复叠加眼睛
- 眼睛按钮 aria-label 用翻译键 ui.sel.125 / ui.cn.41（显示/隐藏），title 是硬编码英文（可接受，tooltip 不进翻译体系）
