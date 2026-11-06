# 路由表白盒审计法 — 实操配方

## 1. 定位路由注册文件

```bash
grep -rln "func RegisterAdminRoutes\|func SetupRouter\|router\.Group\|\.GET(\"" --include=*.go .
```

Gin / Echo / Express / Nest 都是集中注册，一份文件 = 全站 API 地图。
常见位置：`internal/server/routes/*.go`、`routes/*.go`、`router.go`、`app.js`。

## 2. 划出鉴权边界

读 `.Use()` / `app.use()` 的**位置**，然后看哪些路由注册在它之前：

```go
// 裸注册：在任何鉴权中间件之前 = 无鉴权面
v1.GET("/plugin-ui/:token/*path", h.Admin.Plugin.ServeUIAsset)

// 鉴权组：之后的全部路由继承 adminAuth
admin := v1.Group("/admin")
admin.Use(gin.HandlerFunc(adminAuth))
{ /* 300+ 路由全部需要 admin */ }
```

Express：`app.use('/admin', requireAdmin)` 之前的 `app.get('/admin/x')` 是裸的。

把「鉴权组之前的路由」逐条列出 —— 这就是待测清单，通常 1~5 条。

## 3. 拼真实 path

规则：`根前缀 + Group 前缀 + 路由字符串`，**路由字符串为空 = 就是 Group 前缀本身**。

```go
v1 := r.Group("/api/v1")            // 根
user := authenticated.Group("/user") // Group
user.PUT("", UpdateProfile)          // 空 → PUT /api/v1/user
keys := authenticated.Group("/keys")
keys.POST("", Create)                // → POST /api/v1/keys
```

## 4. 顺 handler 读密钥来源

```bash
grep -rn "func.*Handler\|Verify\|Signature\|Sign\b" --include=*.go internal/handler/ | head
grep -rn "signingKey\|SecretKey\|encryptionKey\|Getenv" --include=*.go internal/service/
```

顺着 `handler → service → 密钥来源` 追一层，把猜测变成判据（见 SKILL.md 表格）。

注意「同一把 key 复用于多处」的情况：例如同一把 encryptionKey 既做某令牌 AES-GCM
又做另一处 HMAC —— 泄露任一即可跨用途复用，判死路时要一并写明。

## 5. 建立基线与对照

```bash
# 1) 用自己拥有、且已失效的旧对象拿 200 基线
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"out_trade_no":"<我自己的旧单号>"}' "$BASE/api/v1/payment/public/orders/verify"

# 2) 用乱填值拿 404 对照
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"out_trade_no":"<随机>"}' "$BASE/api/v1/payment/public/orders/verify"
```

两条一起才构成证据链：证明端点无鉴权 + 证明它是个有效性 oracle。

## 6. 输出三列表

| 路由 | 鉴权归属 | 结论 |
|---|---|---|
| `POST /payment/public/orders/verify` | **无中间件** | 匿名 IDOR（存在性 oracle）；泄露字段不含金额/用户 |
| `GET /api/v1/user` | jwtAuth | mass assignment 已排除：白名单序列化，只持久化白名单字段 |
| `POST /auth/oauth/*/start` | 无 | 死路：`OAUTH_DISABLED` |
| `GET /plugin-ui/:token/*path` | 无中间件，但 token 是 AES-GCM 能力令牌 | 死路：无密钥不可伪造 |

外加一组「需新输入」：需要什么凭据 / 需要现开新单（旧的已超时）/ 需要哪个配置值。

## 7. 附带产出：哪些面根本没碰

审完路由表顺手就能列出未覆盖面，比凭记忆可靠：
退款流、邀请返利、旁站、某个需要凭据的内部服务。
