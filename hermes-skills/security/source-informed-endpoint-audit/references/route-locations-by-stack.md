# 路由与鉴权代码位置速查

目标：一次定位到「路由注册表」和「鉴权中间件」两个文件。

| 栈 | 路由注册 | 鉴权中间件 | 备注 |
|---|---|---|---|
| Go + Gin | `internal/server/routes/*.go`、`router.go` 的 `SetupRouter` | `internal/server/middleware/*_auth.go` | group 上 `.Use(adminAuth)` 即鉴权；**group 之外注册的路由无鉴权** |
| Go + net/http | `http.HandleFunc(` / `mux.Handle(` | 包裹式中间件 | 逐个 handler 看是否被 wrap |
| Laravel | `routes/web.php`、`routes/api.php` | `app/Http/Kernel.php`、`bootstrap/app.php` | 路由组 `middleware()` 数组；空数组=无鉴权 |
| Spring Boot | `@RestController` + `@RequestMapping` | `SecurityFilterChain` 配置类 / `@PreAuthorize` | 注意 `permitAll()` |
| Express | `app.get/post/use` | passport / session 中间件、`router.use(auth)` | `router.use` 之后的路由才有鉴权 |
| FastAPI | `app.include_router`、`APIRouter` | `Depends(...)` | 逐个 endpoint 看依赖注入 |
| Django | `urls.py` | `settings.MIDDLEWARE`、`LoginRequiredMixin` | 视图上的装饰器/混入优先于全局 |
| Next.js | `app/**/route.ts`、`pages/api/*` | middleware.ts | `export const config.matcher` 决定覆盖范围 |
| Rails | `config/routes.rb` | `ApplicationController` 的 `before_action` | `skip_before_action` 是绕过信号 |

## 通用检索模式

```bash
# 路由注册（挑一个栈试，不中就换）
grep -rnE '\.(GET|POST|PUT|PATCH|DELETE|Any|Use)\("' --include=*.go .
grep -rnE 'app\.(get|post|put|patch|delete|use)\(' --include=*.js .
grep -rnE '@(Get|Post|Put|Delete|Patch)Mapping|@RequestMapping' --include=*.java .
grep -rnE 'include_router|@router\.(get|post|put|delete)' --include=*.py .
grep -rnE 'Route::(get|post|put|delete)|->(get|post|put|delete)\(' --include=*.php .

# 鉴权中间件定义
grep -rn 'func New.*AuthMiddleware\|func .*Auth(' --include=*.go .
grep -rn 'passport\|jwt\|requireAuth\|isAuthenticated' --include=*.js --include=*.ts .
```

## 读中间件时逐项记下

| 项 | 为什么重要 |
|---|---|
| 接受的凭证形态（header / JWT / query / cookie） | 决定要试几种，每种都要单独覆盖 |
| 比较原语（`ConstantTimeCompare` / `==` / 解密后比对） | 弱比较是可绕信号 |
| 密钥来源 | 判死路还是判可伪造的**唯一依据** |
| 会话绑定（IP/UA/TokenVersion） | 决定拿到 token 后能否复用 |
| 角色检查在哪一步 | 区分 401（无凭证）与 403（凭证不足） |
| 是否有空值/类型混淆跳过分支 | 常见的真实绕点 |

## 未鉴权路由的定位技巧

路由文件里，**鉴权 group 的声明位置**就是分界线：

```go
v1.GET("/capability/:token/*path", h.ServeUIAsset)   // ← 在 group 之前 = 无鉴权
admin := v1.Group("/admin")
admin.Use(gin.HandlerFunc(adminAuth))               // ← 这行之后挂的才受保护
```

发现这种行后，不要停在“未鉴权”结论上：接着读 handler，看 `:token` 是怎么签的（AEAD / HMAC / 随机串），才能判它是可利用入口还是不可伪造的能力令牌。
