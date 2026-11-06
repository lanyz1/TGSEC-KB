## 九、信任客户端与流量篡改

### 9.1 前端参数信任（价格/数量/角色）

```javascript
// 前端 JS 计算价格提交，后端不重新计算
POST /order {"product_id":1,"price":99,"qty":2,"total":198}
→ 修改 price=0.01，total=0.01 → 后端若信任即 0.01 成交

// 加密但密钥在前端（JS 可提取）
var price = encrypt(99, "hardcoded_key");   // key 在前端 bundle 中可提取
// 对策：找同一接口的"明文参数变体"（部分接口没加密）或提取密钥后重算签名

// 批量分配字段（Mass Assignment/BOPLA）
POST /api/user/register {"username":"x","password":"y","balance":99999,"is_admin":true}
// 后端 @RequestBody User user 直接映射 → 多余字段被绑定
```

### 9.2 本地存储/Cookie 篡改

```
1. localStorage/sessionStorage 存放余额/积分/会员状态/购物车价格 → 直接修改
2. Cookie 存放购物车价格/优惠信息 → 篡改
3. Cookie 中的 user_id/role → 直接改（若后端信任）
4. JWT 中的 role/balance/uid → alg=none/弱密钥/过期不校验
5. 签名 Cookie 弱算法（base64+固定 key）→ 逆向伪造
6. 前端缓存的业务状态（"已登录/已实名/已签约"）→ 篡改后绕过前端流程
```

### 9.3 流量劫持与中间人篡改（核心保留内容）

```
1. 明文 HTTP 传输（无 TLS 或 TLS 可降级）：
   - 支付/登录/改密接口走 http:// → 中间人篡改金额/参数
   - HTTPS 降级（HSTS 缺失/302 跳 http）→ sslstrip
2. 客户端不校验证书：
   - 自签证书/公共 CA 证书直接放行 → 中间人全流程篡改
3. APP 端：
   - 抓包绕过证书固定（frida 绕过 SSL Pinning / 反编译提取证书）
   - 请求签名算法在前端 → 逆向后批量伪造签名请求
4. 篡改场景：
   - 支付金额/订单状态/商品价格/转账目标账户
   - 登录响应中的角色/权限字段
   - 接口响应中的"验证通过"标记（后端信任前端回调）
5. 流量侧信道：
   - Referer/响应头泄露 token/订单号
   - 缓存（CDN/浏览器）泄露业务数据
```

### 9.4 仅前端校验绕过

```
- 手机号/邮箱格式校验仅在 JS → 抓包提交任意值
- 文件扩展名/大小仅前端校验 → 绕过上传任意文件
- 支付完成仅前端跳转，后端依赖前端回调 → 直接触发回调
- 前端隐藏"确认"按钮（未成年/实名/协议勾选）→ 直接提交请求绕过
- 前端限制提交次数/倒计时 → 抓包重放绕过
```

### 9.5 业务层防护绕过通用技巧

```
1. 并发测试调整速率：不触发限流阈值，用脉冲式高并发
2. 参数名大小写/变体：amount → Amount/AMOUNT/amount_2 → 绕过字段校验
3. Content-Type 切换：application/json ↔ form-urlencoded ↔ multipart → 不同解析分支
4. XFF/代理头：绕过 IP 限流（见 6.3）
5. 分阶段测试：每步间隔时间，避免异常行为检测
6. 请求体编码：URL 编码/Base64/双层 JSON → 绕过参数级 WAF/风控
7. 重复字段：{"amount":100,"amount":0.01} → 后端取值不一致 → 校验用前值、扣款用后值
8. 数组/对象混淆：amount=100 vs amount[0]=100 vs amount={"value":100}
```

