# 保证金划转上限修复 + 超额退回（2026-08-10 会话沉淀）

## 规则全景（用户拍板演进）

- **应缴额 = max(类目档位, 90 天 GMV 阶梯)，封顶 DEPOSIT_CAP=5000**——是动态值，**不是 300 上限**；300 只是某店当前应缴。
- 08-08 拍板：**保证金只能足额缴纳，不能超额预缴**（前后端都有校验）。
- 08-10 补漏洞：**gap=0 且应缴>0 时旧逻辑仍放行 100**（`maxTransfer = gap > 0 ? gap : 100`）——用户实测划 100 超缴。修复后按 **应缴-已缴净额封顶**。

## 封顶规则（前后端同一公式）

```ts
const required = Math.max(0, Number(snapshot?.deposit?.requirement?.requiredAmount ?? 0));
const net = Math.max(0, Number(snapshot?.deposit?.balance?.net ?? 0));
const maxTransfer = required > 0 ? Math.round(Math.max(0, required - net) * 100) / 100 : 100;
// required>0 且 net>=required → maxTransfer=0（已缴足，禁止划转）；required=0（无经营敞口）→ 允许基础档 100
```

- 后端：`app/api/seller/deposit/transfer/route.ts`（校验金额 > maxTransfer 拦截，错误信息带"档位上限 X / 当前已缴 Y / 最多还可划转 Z"）
- 前端：`SellerDepositTransferPanel` props 传 `requiredAmount` + `net`（调用处 SellerFundsCenter depositPay tab 传 `deposit.requirement.requiredAmount` / `deposit.balance.net`）；组件内算 maxTransfer：
  - `maxTransfer <= 0` → 输入框 `disabled` + 按钮 `disabled`（`saving || balance < 1 || maxTransfer <= 0 || Number(amount) > maxTransfer`）
  - **"已缴足"提示用行内 span（绿色），不要用 placeholder**——placeholder 会被 LanguageSync 拆翻成混合文本（实测"已缴足Amount Due额"）。行内裸中文走兜底翻译正常。
- snapshot 结构：`snapshot.deposit.requirement.requiredAmount` / `snapshot.deposit.balance.net` / `snapshot.deposit.gap`（getFundsSnapshot 返回）

## 超额退回（差额退）脚本模式

页面 refund API（`/api/seller/deposit/refund` type=difference）有 `hasOpenOrders` 拦截（未完结订单不能退）。**超额部分与订单无关，管理员清理时用脚本直接建单**：

```ts
// 1. 建 refund 单（approved 即生效）
await p.sellerDeposit.create({ data: {
  depositNo: generateDocNo('DP'), storeId: store.id, kind: 'refund',
  requiredAmount: ov.requirement.requiredAmount, paidAmount: amount,
  status: 'approved', reason: '差额退', submittedByEmail: '<EMAIL-REDACTED>',
} });
// 2. 并发复检（net < 0 则回滚删单）
const after = await getDepositOverview(store.id);
if (after.balance.net < -1e-6) { await p.sellerDeposit.delete({ where: { depositNo: targetId } }); }
// 3. 刷新钱包（余额自动 +amount）
await refreshSellerWallet(store.id);
// 4. 留痕
await appendOperationLog({ action: '保证金转回余额', targetType: 'deposit', targetId, detail });
await appendBusinessEvent({ action: '保证金转回余额', targetId, path: '/seller/funds#deposit', detail });
```

- amount 取 `getDepositOverview(store.id).refundableDifference`（净额 - 应缴的超额部分）
- 验证：退后 `net === requiredAmount`、`refundableDifference === 0`、钱包 available 增加 amount
- 实测：EchoSail 509→300（退 209）后又被用户划 100（400）→再退 100 归位 300

## 模型/DB 坑

- **SellerDeposit 字段是 `paidAmount`（没有 `amount` 字段）**——select amount 报 Prisma 校验错
- Prisma 物理表名小写（`sellerdeposit`），`$queryRawUnsafe` 引用模型表名会 42P01——用 `@map` 确认或走 Prisma API
- 保证金卡片页面数值 = `deposit.balance.net`（当前保证金余额/净额，**不是已缴历史总和**——用户明确纠正过这个概念）
