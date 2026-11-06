# 2026-08-10 尾部打磨批次（#168）

## 密码框小眼睛全站统一（PasswordInput 组件）
- `components/PasswordInput.tsx` 已有"小眼睛"明文切换（visible state + .password-toggle 按钮 + .password-input-wrap CSS 12918 行起）
- 已覆盖：买家安全页、卖家账号设置修改密码（原本就有）
- **本次补全**（原来漏的普通 `type="password"` 输入框）：
  - `app/reset-password/page.tsx`（忘记密码→设置新密码，两个框）
  - `components/seller/SellerLoginForm.tsx`（卖家登录）
  - `components/seller/SellerRegisterForm.tsx`（注册，两个框）
- 买家登录页原本就有 Show password 按钮（未动）
- 全站搜索 `type="password"` 应只剩 0 处（全部换 PasswordInput）
- 注意：PasswordInput 透传除 type 外全部 props（className/value/onChange/data-i18n-placeholder 等原样可用）

## 语言切换器图标改白色地球
- 位置：`components/LanguageSwitcher.tsx` 68 行 `.language-switcher-globe`
- 之前：黑底圆形 + 🌐 emoji（用户嫌丑）
- 现在：白底圆（#fff + 1px #d8d8de 边框）+ 蓝色(#0071e3) 线条地球 SVG（circle + 横线 + 经线 path，15px）
- CSS 在 globals.css ~4863 行（background #fff / border / color #0071e3）

## 页头英文 eyebrow 删除
- 位置：`components/PortalShell.tsx` 252 行（ConsolePortalShell 页头）
- 之前：`<p className="eyebrow">Seller Workspace / Operations Console</p>` + h2 标题
- 现在：只剩 `<h2 data-i18n={titleKey}>{title}</h2>`
- 卖家端（Seller Workspace）和管理端（Operations Console）两端同删（同类审美问题）
- LanguageSync.tsx 55-58 行的 "SELLER WORKSPACE" 等词典键留着无害（不渲染即不生效）

## 侧栏继续删项（卖家端）
- 本次删"入驻资料"（/seller/onboarding 入口），店铺运营组只剩 工作台|通知中心
- 页面保留（URL 可直达），只删导航项——用户风格：导航删项≠删页面

## 通知类型 HTML 交付教训（用户两次纠正）
1. 第一次给全站 16 类型 → 用户说"不齐全"→ 实际要的是**卖家端单一角色**（DB role=seller 只有 9 种）
2. 第二次只给 1 条案例 → 用户要**每种类型多条真实案例**（文案变体，如 after_sale_updated 有"补充说明/补充证据/不同留言"变体、deposit_reviewed 有"已驳回/直充到账"两种文案）
3. **每条标注跳转行为**（✅跳转/❌不跳转）——用户要筛选"哪些通知跳转"
4. 跳转规则来自 `app/seller/notifications/page.tsx` 的 `targetUrlOf()`：
   - after_sale* → /seller/aftersales/{afterSaleId}
   - order*/shipment* 带 orderNo → /seller/orders/{orderNo}
   - deposit*/withdraw* → /seller/funds
   - change_request* → /seller/account
   - 无 metadata → null（不跳转）
5. 数据源：生产库 notificationMessage groupBy templateKey+role 取真实案例
6. 交付物：D:\跨境商城\会话产物\通知类型案例.html（用户打开方式：cmd start chrome 可能不弹窗，直接 exec chrome.exe 路径 + 复制桌面副本双保险）
7. 管理端代充场景：加保证金通知=deposit_reviewed"已到账"变体；生成校验订单卖家收的是 order_paid（order_created 只发买家）

## 相关决策（用户拍板）
- 管理端代充（top-up）/加余额（balance route）：**不发通知**（删了 top-up 的 notify，balance 本来就没有）
- 前端显示成"自己充值"：充值记录/财务流水("钱包充值")/保证金流水("缴纳")均无"后台/平台"字样——已核验无需改
- 存量"保证金已到账（平台后台直充）"历史通知保留不清理
