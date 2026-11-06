<!-- archived from /root/.hermes/skills/security/qavlixor-order-gen-rules/SKILL.md on 2026-10-21 -->

---
name: qavlixor-order-gen-rules
description: >-
  测绘引擎·用 when 修改 qavlixor 订单生成(管理端生成订单)相关功能。生成规则+全链路联动+改动检查清单。
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/qavlixor-order-gen-rules`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/qavlixor-order-gen-rules/…')`，不要相对 `references/legacy/` 解析。

# qavlixor-order-gen-rules（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-order-gen-rules/`

溯源（仅标记）：`hermes/software-development`

---

# qavlixor 订单生成规则与联动(改功能前必读)

## 功能定位
管理端「生成订单」(/admin/test-orders)= 给店铺批量生成**对外完全真实**的订单(状态/买家/物流/支付/库存/资金全链路),可立即生成或定时分批。

## 核心文件
| 文件 | 职责 |
|---|---|
| lib/test-order-generator.ts | 生成核心(规则/扣库存/落库/通知/日志) |
| app/api/test-orders/route.ts | 管理端 API(立即/定时登记,raw+offset→UTC) |
| app/api/cron/scheduled-orders/route.ts | 定时执行器(每分钟 cron 扫描到点落库) |
| lib/order-repository.ts | syncOrderToPrisma 落库 |
| lib/funds-repository.ts | 钱包快照(待结算/可提现) |

## 生成规则速览
- 状态池: 待发货/运输中/已签收/售后中(轮换或指定)
- 买家: 随机欧美名 + gmail 邮箱(虚构,无真实账号)
- 商品: 店池轮换(≤30 个已上架审核通过品),奇数单1件/偶数2件
- 订单号: 19位,前12位=yyMMddHHmmss(**UTC**,定时模式=计划时间)
- 物流时间线: 下单→(1-48h)发货→(7-15天运输)签收→(7天)自动确认(autoConfirmAt)

## 落库全链路(改一处必查联动)
```
订单号(定时带计划时间) → 【扣库存 reserveProductStock, 不足整单跳过】
→ 落库 Order(orderChannel=validation, inventoryDeducted=true)
→ 【已签收: shippedAt+deliveredAt+autoConfirmAt(签收+7天); 运输中: shippedAt】
→ 支付流水 PAY-{orderNo} paid → 销量+ → 刷新钱包(待结算立即生效)
→ 操作日志 → 卖家通知(按店合并一条 order_paid, 真实文案)
```

## 改动检查清单(改订单生成必须逐项核对)
1. **库存**: 生成扣库存(reserveProductStock);取消/退款回补条件 = `orderChannel !== "validation" || inventoryDeducted === true`(存量旧单 false 不回补!)
2. **资金**: 待结算=paid 未确认收货;确认(autoConfirmAt 或手动)后进可提现;售后中冻结
3. **通知**: 卖家通知模板统一 **order_paid**(与真实下单一致, 2026-08-14 起);按店合并防刷屏;recipientEmail 必填(sellerEmailOfStore)
4. **时间**: 存储/执行 UTC;订单号时间戳 UTC;展示前端转本地(fmtLocal);定时模式订单号必须带计划时间
5. **翻译**: 任何新增文案立即入 6 语言(见 qavlixor-i18n-complete skill)
6. **存量数据**: 改逻辑时区分"新生成"vs"存量693单"(存量没扣库存/没时间字段, 别追溯补否则资金骤变)

## 坑
- 立即生成单状态快进(已签收时间在未来)是造数固有特性,内部时间线自洽即可
- orderChannel=validation 不能简单改 normal(库存/退款分支依赖)
- 售后中状态是伪装(无真实 AfterSaleCase 工单)
