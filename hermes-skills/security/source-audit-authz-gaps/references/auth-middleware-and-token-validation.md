# 认证中间件 + 令牌校验:审计检查表(Go/Gin 血统为主)

适用: 拿到一套后台/对象存储/多租户 SaaS 源码, 要快速定位「未授权可达面」与「令牌可伪造面」。
按下面 5 个检查点顺序走, 每点都是可 grep 的形态 + 判决规则。

## 1. 认证中间件:白名单是按「路径」匹配的

```go
// 典型形态(gin)
checkLogin := true
if strings.Split(ctx.Request.RequestURI, "?")[0] == "/api/oss/bucket/object" {
    checkLogin = false                     // ← 路径白名单
}
authUser, _ := security.CheckAuthUser(ctx)
if authUser == nil {
    if checkLogin { 401; ctx.Abort(); return }
}
if checkLogin && authUser.Status != constant.NORMAL_STATUS { 601; Abort() }
ctx.Next()
```

要点:
- 比较的是 **URI(去 query)**, 不是路由对象 ⇒ **同一路径上所有 verb 一起免登录**。
- 白名单条目通常是硬编码字符串, 直接 `grep -n 'checkLogin\|whiteList\|excludePath\|RequestURI'` 就能捞出来。
- 拿到白名单路径后, 去路由文件里枚举该路径注册的**全部方法**:
  `grep -n '"/<同样的路径>"' app/router/*.go` —— HEAD/GET/PUT/DELETE 往往都挂在同一字符串上。
- 杂项: 探活/监控端点常带静态令牌守卫(`middleware.HasStat()` + `stat.token`), 它**不是认证** —— 令牌在源码/配置里 ⇒ 等于公开。

## 2. handler 层的二次校验:决定「读面」还是「写面」

读方法常常在 handler 内再判一次 ACL:

```go
checkLogin := true
if bucket.ACL == "public_read" { checkLogin = false }
if ossFile.ACL == "public_read" { checkLogin = false }
if fromShare { checkLogin = false }
// ... 后面才 IsSuperAdmin/bucket.UserId != tokenUser.UserId
```

⇒ **结论**: 桶级/文件级 `public_read` = 任何人知道「桶名+对象名」即可下载任意对象。
这解释了实测中大面积「对象存储匿名可读」——**是配置默认值/误配 + 设计, 不是临时漏洞**, 报告里要这么写。

写/删方法往往没有 ACL 逃生口:

```go
tokenUser := security.GetAuthUser(ctx)                   // 未登录 = nil
if !utils.IsSuperAdmin(tokenUser.UserId) && ...          // ← nil 解引用 ⇒ panic ⇒ 500
```

⇒ 报「可用性/逻辑缺陷(未认证即 500)」, **不是未授权写**; 且**不要为了验证在线上发写/删**。

## 3. 令牌设计:无状态 JWT vs 会话查找

```go
type SysUserClaim struct { Uuid string; jwt.RegisteredClaims }   // claims 里只有随机 uuid
token, _ := jwt.NewWithClaims(jwt.SigningMethodHS256, a).SignedString([]byte(config.Data.Token.Secret))
dal.Redis.Set(ctx, rediskey.UserTokenKey+a.Uuid, &UserTokenResponse{...}, 30*time.Minute)  // 真状态在 Redis
```

判定:claims 里只有 `uuid/iat/nbf/iss` 且伴随一次 Redis/DB 写入 ⇒ **会话查找式**。
⇒ 密钥泄露只能让你签出一个「指向不存在会话」的 token; 伪造矩阵跑再大也没用。
**先读 `app/token/*.go` 的 `GenerateToken` 与 `GetAuthUser`, 再决定要不要跑密钥矩阵。**

## 4. 下载/分享令牌:本地复现配方

形态: 明文 = 用户可控字段拼接, 加密后作为 URL 参数; 校验函数里带哨兵短路。

```go
text := fmt.Sprintf("%s$$%s$$%d", bucket.BucketCode, ossFile.ObjectName, expiredTime)
downloadToken, _ := aes.Encrypt(text, aes.AesKey)
// 校验:
if expiredSeconds != -1 && time.Now().Unix() > expiredSeconds { 失效 }   // ← 传 -1 永久有效
```

本地复现(Windows git-bash 自带 openssl):

```bash
printf '%s' "<bucket>\$\$<object>\$\$-1" | \
  openssl enc -aes-128-cbc -K $(printf '%s' "$KEY" | xxd -p) -iv $(printf '%s' "$IV" | xxd -p) -nosalt | xxd -p -c 200
```

交付时写清: 算法(mode/padding)、key/iv 来源(源码文件:行)、明文拼装格式、编码(hex/base64)、绕过点(`-1`)。

## 5. 代际指纹:这套源码到底对不对得上线上

开写利用链前花 5 分钟做三件事:

1. **路由交集**:源码里独有的业务路由(挑 2–3 个特征名) 在线上 `curl` 一发 —— 若全 `404 page not found`(Go text/plain 18B), 高度怀疑不是同一代。
2. **反向特征**:线上前端 bundle 里有没有源码中不存在的路由(本次线上有 `/api/buckets/GetBuckets` 这类名字空间路由, 源码里完全没有) ⇒ 代码库不同代。
3. **资产活性**:源码配置里的域名/IP —— `test.xx.com` 常已 NXDOMAIN, 部署 IP 常已不可达; 官网域名可能只是 CDN 落地页(`/api/*` 全 404)。

⇒ 结论写成「源码级发现(未在线上验证 / 对当前线上不适用)」, 不要写成线上可利用。
若该产品是**商业售卖的多买家产品**, 其他买家部署属于越界面 —— 只登记, 不主动探测, 等显式授权。

## 6. 注解式框架的中间件覆盖差分(Hyperf/apidog 系)

中间件写在控制器 docblock 里, 所以「路由 × 中间件差分」= 扫控制器注解, 不是解析路由文件。

```bash
# 1) 找中间件真正被谁挂载
grep -rn "Middleware::class" app config | grep -v "^app/Middleware"
# 2) 取样看注解形态(version 决定对外前缀)
sed -n '1,45p' app/Controller/<域>/<X>Controller.php
python <skill_dir>/scripts/audit_apidog_mw.py <app/Controller 目录> admin
```

```php
/** @ApiVersion(version="admin")          // ⇒ /admin
 *  @Middleware(AdminMiddleware::class)    // 单闸门 */
/** @ApiVersion(version="admin.v2")         // ⇒ /admin.v2
 *  @Middlewares({ @Middleware(AdminMiddleware::class), @Middleware(AdminLoginMiddleware::class),
 *                 @Middleware(AdminPermissionMiddleware::class), @Middleware(AdminLogMiddleware::class) }) */
```

判决规则:
- 零中间件的 Admin 域控制器 = **完全未授权**(连密钥都不需要); 它带 `create/statement/settlement` 路由时是最高危面。
- 只有 `AdminMiddleware` 的 = 取决于它校什么: 若是与 `.env` 常量比相等 ⇒ 知道常量即管理员 API 全量(含写)。
- 有 Admin+Login+Log 而缺 Permission = **垂直越权**(任意登录用户可打该域)。
- 注入型中间件(`if (checkAuth) { set uid }` 无 else) 单独出现 = fail-open, 必须找到配套拒绝型中间件才算安全。

## 7. 未授权实证的差分设计与证据阶梯

每条结论一对请求, **唯一变量是鉴别因素**:

| # | 请求 | 预期 |
|---|---|---|
| 1 | `GET <只读路由>` 不带鉴别头 | 401/403 |
| 2 | 同路由 + 鉴别头(密钥/伪造票/任意 scene 值) | 200 + 业务数据 |
| 3 | 同域一条确定受保护路由 | 仍 401/403(证明差异来自路由而非环境) |

- 只选**参数可选**的读路由(`list/info/page/detail`), 否则被全局参数校验层提前拦下, 无法归因。
- 频率低(≥0.7s/发)、经跳板、可随时停。
- 证据阶梯(按此定级, 不许越级): ① 源码确证(读完分支) → ② 入口确证(域名/端口/路径命中且是本产品指纹) → ③ 未授权确证(上表差分) → ④ 影响确证(读回的**业务字段**, 不是状态码)。
- 停在 ①/② 必须在报告里写「需内网/入口前提」; 入口验证失败(403、异产品、内网 ingress 独占)同样是交付结论 —— 写「归属失败/无攻击面」, 而不是省略。
