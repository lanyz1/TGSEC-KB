# 通知中心：16 种通知类型清单（2026-08-10 生产库核实）

## 类型分组（lib/notification-service.ts PREF_GROUP → 卖家通知偏好开关）

- **order（订单）**：order_created / order_paid / order_cancelled / order_cancelled_by_buyer / order_cancelled_by_seller / order_closed / shipment_updated / payment_confirmed / payment_pending
- **aftersale（售后）**：after_sale_created / after_sale_escalated / after_sale_updated
- **fund（资金）**：deposit_deducted / deposit_proof_submitted / deposit_reviewed
- **未归类（不受偏好开关控制，始终发）**：change_request_result（资料变更审核）、payment_proof_submitted（admin 收）、contact_*（官网联系表单 admin 收）、conversation_message（特殊：并入消息中心会话列表，不走通知中心）

## 各类型触发场景 + 接收角色（速查）

| templateKey | 接收 | 触发 |
|---|---|---|
| order_created | 买家 | 下单（余额支付=已支付；其他=待付款提醒）|
| order_paid | 卖家 | 确认收款后请发货 |
| payment_confirmed | 买家 | 财务确认到账 |
| payment_pending | admin | 新订单待收银台付款 |
| payment_proof_submitted | admin | 买家提交 TXID（站内+邮件双通道）|
| order_cancelled | 买家 | 买家取消 |
| order_cancelled_by_buyer | 卖家 | 买家付款前取消（库存自动回补）|
| order_cancelled_by_seller | 买家 | 卖家取消（货款原路退回）|
| order_closed | 买家 | 超 30 分钟未付款自动关闭 |
| shipment_updated | 买家 | 发货/批量发货/物流单号更新 |
| after_sale_created | 卖家 | 买家提交售后申请 |
| after_sale_updated | 买家/卖家/admin | 状态变化/处理回复/买家补充材料（同键不同文案，最高频 ~168 条）|
| after_sale_escalated | 卖家+admin | 买家申请平台介入/商家升级仲裁 |
| deposit_deducted | 卖家 | 仲裁强制退款罚扣保证金（退款额×5% 最低1最高100）|
| deposit_reviewed | 卖家 | 保证金凭证审核通过/驳回 |
| deposit_proof_submitted | admin | 卖家提交保证金 TXID |

## DB 查询脚本（按类型统计 + 每类型最新一条案例）

```mjs
// node 动态 import（静态 import @prisma/client 会 ERR_AMBIGUOUS_MODULE_SYNTAX）
const { PrismaClient } = await import('@prisma/client');
const p = new PrismaClient();
const groups = await p.notificationMessage.groupBy({ by: ['templateKey'], _count: { _all: true }, orderBy: { _count: { templateKey: 'desc' } } });
for (const g of groups) {
  const one = await p.notificationMessage.findFirst({ where: { templateKey: g.templateKey }, orderBy: { createdAt: 'desc' }, select: { title: true, body: true, role: true, createdAt: true } });
  console.log(g.templateKey, g._count._all, one?.title, (one?.body ?? '').slice(0, 90));
}
```

## ★ 视角教训（用户澄清过）

第一版 HTML 按全站 16 种交付，用户反馈"不齐全/很多遗漏"→ 澄清后才知道**只指卖家端通知中心看到的**。**报告/清单类任务先确认视角（买家/卖家/管理端）或直接按 role 维度分组呈现。**

### 卖家端通知中心实际类型（role=seller，9 种）

按页签分类（app/seller/notifications 的 categoryOf：after_sale*→aftersale；deposit/withdraw/payment/fund→fund；order/shipment/paid→order；其余→system）：

| 页签 | templateKey | 触发 |
|---|---|---|
| 订单 | order_paid | 确认收款→安排发货 |
| 订单 | order_cancelled_by_buyer | 买家付款前取消 |
| 售后 | after_sale_created | 买家提交售后申请（最高频 51 条） |
| 售后 | after_sale_updated | 买家补充材料（卖家版文案"买家补充了售后材料"） |
| 售后 | after_sale_escalated | 升级平台仲裁（卖家版文案"售后已升级平台仲裁"） |
| 资金 | deposit_deducted | 仲裁强制退款罚扣保证金 |
| 资金 | deposit_reviewed | 保证金缴纳审核通过/驳回 |
| 系统 | change_request_result | 店铺资料变更审核结果 |
| 系统 | conversation_message | 买家新会话（消息中心消费，通知中心不显示） |

DB 查询按角色过滤：`groupBy({ by: ['templateKey','role'] })` 后取 `role === 'seller'`。

## 注意
- 通知偏好：isNotifyAllowed 仅对 seller 角色 + PREF_GROUP 内键生效；无 notifyPrefsJson 记录 = 全开；system 锁定不可关
- 给用户做"通知类型一览"HTML 时：分组（订单蓝/售后橙/资金绿/其他灰）+ 真实案例（title/body/日期/累计条数）+ 无存量数据的标注"代码已实现"
