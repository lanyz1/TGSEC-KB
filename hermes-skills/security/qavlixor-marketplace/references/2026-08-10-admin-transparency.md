# 2026-08-10 管理端代充透明原则 + 通知体系排查法

## 用户拍板：管理端代充对买卖家透明（#167）

- **管理端给卖家后台充值余额（top-up）/给买家卖家加余额（balance route）→ 不发任何通知**（卖家/买家都不提示）
- 前端资金记录**显示成用户自己充值**：卖家端充值记录=普通"充值"、财务流水="钱包充值"、保证金流水="缴纳"；买家端="充值"
- 后台操作痕迹只留运营日志（`appendOperationLog`/`appendBusinessEvent`，管理端可见）
- 实现：`app/api/admin/deposits/top-up/route.ts` 删除 notify 调用 + import（注释"用户拍板：管理端代充不发通知"）
- 存量已发通知不清理（历史数据不动）

## 通知体系速查（排查通知类问题用）

### templateKey → 偏好分组（lib/notification-service.ts PREF_GROUP）
- order：order_created / order_paid / order_cancelled / order_cancelled_by_buyer / order_cancelled_by_seller / order_closed / shipment_updated / payment_confirmed / payment_pending
- aftersale：after_sale_created / after_sale_escalated / after_sale_updated
- fund：deposit_deducted / deposit_proof_submitted / deposit_reviewed
- 未归类键（change_request_result / conversation_message / contact_* / payment_proof_submitted）不受卖家开关控制，始终发送

### 卖家端通知中心实际能收到的 9 种（DB role=seller 实测）
| templateKey | 触发 | 跳转（targetUrlOf） |
|---|---|---|
| order_paid | 确认收款→安排发货 | /seller/orders/{orderNo} |
| order_cancelled_by_buyer | 买家付款前取消 | /seller/orders/{orderNo} |
| after_sale_created | 买家提交售后 | /seller/aftersales/{id} |
| after_sale_updated | 买家补充材料（文案随补充类型变：说明/证据 N 份） | /seller/aftersales/{id} |
| after_sale_escalated | 买家申请/商家升级平台仲裁（卖家+管理端都收） | /seller/aftersales/{id} |
| deposit_deducted | 仲裁强制退款罚扣（退款额×5%，最低1/最高100） | /seller/funds |
| deposit_reviewed | 缴纳审核驳回/平台直充到账（两种文案） | /seller/funds |
| change_request_result | 店名/主体变更审核结果 | /seller/account |
| conversation_message | 买家新会话——消息中心消费，**通知中心不展示** | ❌ 不跳转 |

### targetUrlOf 跳转规则（app/seller/notifications/page.tsx）
- after_sale* + afterSaleId → 售后详情；order*/paid + orderNo → 订单详情；deposit*/withdraw* → /seller/funds；change_request* → /seller/account；兜底 orderNo → 订单详情；无 → null 纯展示（前端 item.url 为空则无 Link）

### 排查方法（"通知类型不齐全"类问题）
1. 先按**角色**查：`prisma.notificationMessage.groupBy({ by:['templateKey','role'], _count })`——全站 16 种 vs 卖家 9 种（买家/admin 各不同）
2. 每种取多条真实案例：`findMany({ where:{templateKey, role}, take:6 })` 看文案变体
3. 生成 HTML 文档时标注：触发场景 + 真实案例多条 + ✅跳转/❌不跳转
4. order_created 只发买家；payment_pending 只发管理端；卖家收的是 order_paid（管理端生成校验订单后卖家看到的是"已确认收款，请安排发货"）

## 服务器跑脚本的坑

- **node 直接跑 .mjs 静态 `import { PrismaClient } from '@prisma/client'` → ERR_AMBIGUOUS_MODULE_SYNTAX**（双入口冲突）
- 解决：**动态 `const { PrismaClient } = await import('@prisma/client')`**；tsx 跑同样建议动态 import
- Prisma client 属性名按模型原样（`p.uiTranslation`，不是 uITranslation）；UiTranslation 唯一键是 `source`（不是 sourceText，findUnique where source）
- 长任务挂后台：`nohup node _q.mjs > /tmp/q.log 2>&1 &`（paramiko exec_command 会因 stdout 管道卡住超时——用 ps aux 验证启动 + tail 日志）
- 批量翻译词典预置：GLM（SILICONFLOW_API_KEY）5词/批、temperature 0.1、正则 `\[[\s\S]*\]` 抽 JSON，入库 uiTranslation（source 唯一，upsert 用 findUnique+update/create）
