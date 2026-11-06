# 保证金（Deposit/Margin）规则与核查法 — 2026-08-10

用户问"应缴300u为什么能缴509u"的完整调查。核心结论：**509 是历史累计已缴净额，不是"现在能缴"**；现在只能足额缴纳（08-08 拍板）。

## 规则（lib/deposit-constants.ts + lib/deposit-rules.ts）

- `DEPOSIT_TIERS = [100, 300, 500, 1000]`，`TIER_NAMES = [普通/中风险/高风险/高风险+]`
- 一级类目 → 档位：服饰鞋包/家居日用/厨房餐厨/运动户外/宠物用品/图书文娱=普通100；美妆个护/母婴玩具/电脑办公=中风险300；其余=高风险500；未知类目按普通兜底
- **应缴 = max(类目档, 近90天支付GMV阶梯)，封顶 `DEPOSIT_CAP = 5000`**（GMV阶梯：500k→5000 / 200k→3500 / 50k→2000 / 20k→1000 / 5k→500）
- **★应缴是动态的，不是固定上限**——用户常把"当前应缴300"理解为"上限300"；上限实际是5000，且随类目/GMV变化
- **08-08 用户拍板：保证金只能足额缴纳，不能超额预缴**
  - `POST /api/seller/deposit/transfer`：`maxTransfer = gap > 0 ? gap : 100`；`amount > maxTransfer` 拦截（gap=0 时上限=基础档100）
  - 前端 SellerDepositTransferPanel 同口径校验（传入 gap prop）
  - 旧组件 SellerChargePanel kind=deposit 无 max 校验（已不用，缴纳走余额划转面板）
- `net = paidApproved - refundApproved - deducted`；超额 = net - required → `refundableDifference` 可转回余额（`POST /api/seller/deposit/refund`，差额退/全额退两模式）
- SellerDeposit 模型字段：**paidAmount**（没有 amount 字段！select 时写 amount 会报 Prisma validation）、requiredAmount、kind（pay/refund/transfer）、depositNo（DPT- 前缀）

## 核查方法（用户报"金额不对/超额"时）

1. 先查 overview：`getDepositOverview(storeId)` → requiredAmount / net / gap / refundableDifference
2. 再查全量缴纳历史（**勿 take 截断**——用户看到的累计数是多笔测试缴叠加出来的）：
   `sellerDeposit.findMany({ where: { store: { name } }, select: { kind, status, paidAmount, createdAt } })` 后 JS 聚合
3. 常见真相：qa/测试店铺多笔 1u/100u 补缴累计超应缴（如 EchoSail：14 笔合计509 vs 应缴300 → 超额209 可转回）——不是 bug，是历史累计
4. 回答口径：先澄清"已缴净额≠本次可缴"，再给 gap/超额/可转回数字，最后问是否清理测试痕迹

## 页面入口

- 资金页 `/seller/funds?tab=deposit`：保证金卡片（应缴金额/已缴净额/缺口）+ "缴纳保证金"按钮 → depositPay tab（SellerDepositTransferPanel，从可提现余额划转，无外部支付）
- 退还：差额退（net>应缴）/ 全额退（店铺关闭）→ depositWithdraw tab
