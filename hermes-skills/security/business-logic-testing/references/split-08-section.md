## 七、业务流程劫持与状态机攻击

### 7.1 多步骤流程跳步/回退（BLA2/BLA5）

```
典型流程：创建→填写→确认→验证→完成（每步都有独立 API）
攻击：
1. 直接调用最后一步：POST /checkout/finalize 跳过中间步骤
2. 参数携带步骤标记：{"step":4} / {"verified":true} → 直接到终态
3. 回退攻击：已完成 → 回到待支付 → 用新价格重付（改价套利）
4. 前置条件伪造：校验结果由前端传入（{"id_card_verified":true}）
5. 审批流：
   - 审批人身份：POST /approve/123 {"approver":"me"} → 自审自批
   - 审批状态：改 status 参数为 approved/通过
   - 审批跳步：跳过"部门主管"直提"总经理"
   - 并发审批：多人审批同一单 → 一票否决被绕过？
6. 多租户流程：A 租户流程状态在 B 租户可见/可改（跨租户流程劫持）
```

### 7.2 订单状态篡改与并发状态机

```
正常流程：待支付 → 已支付 → 已发货 → 已完成
POST /order/status {"order_id":123,"status":"completed"}  → 直接完成
POST /order/status {"order_id":123,"status":"refunded"}   → 直接退款

测试要点：
1. 状态字段名枚举：status/orderStatus/state/status_code
2. 状态值枚举：0-9 逐个尝试 + 业务词汇（paid/completed/shipped/cancelled）
3. 非法转移矩阵：对每个"当前状态"枚举所有可设目标状态，找非法转移放行项
   （待支付→已完成？已取消→已发货？退款中→已支付？）
4. 状态变更并发：同一订单并发提交两个不同目标状态（completed + refunded）→ 双终态
5. 状态字段类型混淆：status=1 vs status="1" vs status=true → 不同分支
6. 历史状态审计：状态回写是否有审计日志？无日志 = 无追溯
```

### 7.3 收货地址/商品信息修改（支付后篡改）

```
1. 支付后修改收货地址为攻击者地址 → 截获商品
2. 货到付款订单修改商品/数量/金额 → 少付多拿
3. 修改订单中的商品 SKU/规格 → 高价商品换成低价结算
4. 物流单号篡改 → 伪造"已发货/已签收"
5. 售后申请中改地址 → 退款与退货地址分离
```

### 7.4 退款/售后逻辑滥用

```
1. 重复退款：同一订单退款接口并发/重放 N 次（BLA1 核心场景）
2. 退款金额大于实付：改 refund_amount 参数
3. 退货不退回商品：申请"退货退款"后只走退款流程，不寄回（跳过退货前置）
4. 发货后申请退款不退货（仅退款模式被滥用）
5. 修改退款状态：直接把退款单状态改为"已退款"
6. 退款目标账户篡改：退款到他人账户/余额 vs 原路退回不一致
7. 退款与订单状态不一致：已退款订单仍显示可再次退款
8. 部分退款精度：多次部分退款累加超过实付（0.01+0.01...→>100%）
9. 售后期绕过：修改本地时间/改订单时间字段绕过售后时限
```

### 7.5 Host 头注入与重定向链（认证劫持）

```http
# 重置密码/激活链接由 Host 头生成 → 劫持令牌
POST /reset-password
Host: attacker.com          → 重置链接指向攻击者域名
X-Forwarded-Host: attacker.com   → 代理层 Host 覆盖
X-Original-URL: /reset-password   → 路径覆盖

# 开放重定向
GET /login?redirect=https://attacker.com  → 登录后跳转钓鱼
GET /oauth/authorize?callback=https://attacker.com  → 授权回调劫持

# 测试要点：
1. 生成链接类功能（重置/激活/邀请/分享）全部测试 Host 头注入
2. 重定向参数（redirect/return/next/callback/url）测开放重定向 + 协议绕过
3. 双 Host 头 / Host 头注入（Host: target.com\r\nX-Forwarded-Host: attacker.com）
```

