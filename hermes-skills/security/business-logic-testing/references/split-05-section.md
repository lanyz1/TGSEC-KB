## 四、越权与逻辑组合链

### 4.1 IDOR/BOLA 深度利用

**BOLA（Broken Object Level Authorization，OWASP API1:2023）**：API 收到对象 ID 后执行操作，但未验证"该对象是否属于当前用户"。实证研究（100+ HackerOne 披露）显示 **41.7% 是 Action-Level BOLA**——对他人的对象执行**状态变更动作**（改单、退款、删文件），比纯读取更严重。

```
# 对象 ID 形态：顺序整数、UUID、可预测字符串、GraphQL Global ID
GET /api/orders/1001              → 遍历 1001-2000 读他人订单
PUT /api/orders/1001/status       → 改他人订单状态
DELETE /api/files/1001            → 删他人文件
POST /api/transfer                {"to_account":...,"from_order_id":1001}  → 用他人订单做退款来源

# GraphQL Global ID（base64 编码，系统性利用点）：
POST /graphql
{"query":"{ order(id: \"T3JkZXI6MTAwMQ==\") { id amount status } }"}
# base64("Order:1001") 可解码/枚举；N+1 嵌套查询可一次拉取他人数据

# 批量操作接口（BOLA 放大器）：
POST /api/orders/batch {"order_ids":[1001,1002,...,9999]}   → 一次批量越权
```

**IDOR 变体绕过（关键）：**
```
1. 大小写：/api/order/1001 vs /api/Order/1001 → 不同路由可能不同校验
2. 双 ID：传 user_id 和 order_id 两个参数，后端只校验其一
3. 数组 ID：id=1001 → id[]=1001（参数类型不同绕过校验）
4. 编码：1001 → base64(1001) → hex(1001) → 十进制转十六进制
5. 前后端不一致：前端校验 owner，后端不校验（直接构造请求）
6. 多租户/团队场景：team_id 可切换 → 跨租户访问（租户隔离破坏）
7. 会话换绑：把 victim 的资源 ID 放入自己可控制的另一资源（间接引用）
```

### 4.2 垂直越权与 BFLA

```
1. 前端隐藏但后端不校验：
   普通用户直接访问 /admin API（仅前端隐藏按钮，后端无权限校验）
2. API 版本差异：
   /api/v1/admin/users → v1 无权限检查，v2 有
3. 路径遍历：
   /api/user/../admin/users → 路径解析到 admin 路由
4. HTTP 方法差异：
   GET /api/admin/users → 普通用户可用 GET 列出用户
   PUT /api/user/1/role → 修改自己的角色为 admin
   OPTIONS/HEAD/TRACE 探测隐藏方法
5. 功能级授权缺失（BFLA，API5:2023）：
   普通用户调用仅管理员应可调用的函数端点
6. 批量分配/字段覆盖（BOPLA，API3:2023）：
   PUT /api/profile {"name":"test","role":"admin","is_admin":true,"balance":999999}
   POST /api/user {"username":"x","password":"y","verified":true}  → 直接置 verified
7. 状态字段注入：
   POST /api/order {"status":"completed"}  → 新对象直接以高级状态创建
```

### 4.3 未认证/弱认证接口

```
- /api/admin/backup        无认证可下载数据库备份
- /api/internal/*          内部接口未加认证
- /api/debug/*             调试接口暴露
- /actuator/*              Spring Boot Actuator（含 heapdump 下载 → 内存凭据）
- /console                 Web 控制台
- /swagger-ui.html / openapi.json   API 文档泄露 → 枚举业务接口
- /graphql                 GraphQL 端点无认证/内省（introspection）开启
- /api/v1/export           CSV/Excel 导出无权限校验
- /api/third-party/*       第三方对接接口无鉴权（可越权调用对方能力）
```

**检测：** 用字典枚举端点 + 观察未登录态是否 200；重点看"内部/运营/管理/导出/导入/回调"类路径。

### 4.4 逻辑组合链（IDOR + 逻辑 + 支付）

**组合链才是高危放大器，示例链：**

```
链 1：IDOR 支付确认 → 0 元购
  下单(100元) → 找到 /paySuccess?orderNo=<订单号> 无鉴权确认端点
  → 遍历他人订单号批量标记已支付 → 0 元购 + 越权破坏他人订单

链 2：越权改价 + 竞态 → 无限提现
  找"订单金额可改"接口（管理端 IDOR）→ 把订单金额改成 0.01
  → 退款时按订单金额退 → 并发退款 N 次 → 余额暴增 → 提现

链 3：优惠券 IDOR + 兑换竞态 → 批量薅券
  优惠券绑定接口 IDOR（可把他人券绑到自己）→ 绑定后并发兑换
  → 同一券兑换 N 次

链 4：注册逻辑 + 邀请奖励 + 竞态 → 刷量
  注册"新用户送红包" → 并发领取 + 大小写/空格绕过唯一性校验注册多个
  → 邀请码自邀闭环 → 批量红包

链 5：GraphQL 嵌套 + 越权 → 拖库
  内省查询发现 nested relation → 多层嵌套查询跨对象拉取（如 order.user.profile.paymentInfo）

链 6：审批流跳步 + 垂直越权 → 大额订单免审
  审批状态机"待审→通过"由前端参数控制 → 直接 POST 通过状态
  → 或调用管理端审批 API（BFLA）→ 自审自批
```

**组合链测试要点：** 每个单点漏洞单独看可能只是"低危"（如轻微越权），组合后要重新评估影响（资金损失/账户接管/数据泄露），并按组合后危害定级。

