# Next.js(RSC) 端点表挖掘 + 守卫顺序判读（tokenweb.sbs 案，2026-09-29）

## 0. 入口形状：废弃静态旧站 → 真实业务（证书带路）

- 用户给的入口 `38.47.198.24` = **已废弃的纯静态模板页**（TRX 闪兑落地页，TG bot 链接还是占位符 `t.me/您的机器人用户名`，全路径 404，只有 21/22/80/443/888）。
- 突破口：**旧站 443 上还挂着 Let's Encrypt 证书，SAN 直接吐出 `pc.<域>` / `km.<域>`**：
  ```bash
  echo | openssl s_client -connect <ip>:443 2>/dev/null | openssl x509 -noout -text | grep -E 'Subject:|DNS:'
  ```
  → `crt.sh` 拿全子域（`tokenweb.sbs` / `admin.` / `api.` / `pc.` / `km.`）→ 现行解析指向另一台 IP。
- 真实栈：`172.245.253.248` = Caddy + Next.js（前端）/ Vite SPA（admin）/ NestJS（api），PostgreSQL 64 表（`/health` 自己报的）。
- 教训：**「入口站打空了」不等于「目标打空了」——先拿证书/子域把真站找出来再下判**。

## 1. RSC 端点表挖掘（本案例的核心突破）

```bash
# 从任意页面 HTML 取 chunk 清单并全量下载
curl -s https://<host>/login | grep -oE '/_next/static/chunks/[^"]+\.js' | sort -u |
  while read c; do curl -s "https://<host>$c" -o "chunk_$(basename $c)"; done

# 端点定义表：一次拿到「名字 + 方法 + 带参路径」
grep -oE '[a-zA-Z]+:i\("(GET|POST|PUT|PATCH|DELETE)","/[^"]+"' chunk_*.js
# → membershipByAddress:i("GET","/membership/:address")
```

产出 54 条端点，**含参名**，覆盖猜不到的模块（`/rentals/*`、`/staking/*`、`/projects-v2/*`、`/trading/triggers/oco`）。

坑与阴性项（别再耗）：
- App Router 生产构建**没有** `__NEXT_DATA__`、HTML 里**没有** `"buildId"` → 那两个 grep 空是正常，不是被加固；`/_next/data/<build>.json` 同样全 404。
- **admin 的 Vite bundle（437KB 压缩）几乎榨不出端点**（只出 `/login`、`/dashboard`、`settings/admins`）；有效目标永远是 Next.js 的 `app/<route>/page-*.js` 与共享 chunk。
- source map、Server Action ID、`/_next/image` SSRF 在本案全阴（image 有 remotePatterns 白名单，非白名单 URL 一律 400 —— 与 `hunt-nextjs` 里那条假阳性守则一致）。
- **参数位置提示**：`GET /membership/plans?address=<acct_x>` 恒回 `Invalid address`，说明该参属于**路径**（`/membership/:address`）；读端点表定位置，别逐个试 query 名。
- member address 形如 `acct_<32hex>`，对不存在的地址也回 200 + 零余额（无 404）⇒ 该面**没有存在性 oracle**，别用它枚举。

## 2. 守卫顺序判读（NestJS/Express，判决表）

执行顺序 Middleware → Guards → Interceptors → Pipes → Handler，**能走到 Pipes 就说明 Guard 已过**：

| 响应 | 读法 |
|---|---|
| `Cannot GET /api/x` | 无此 handler（路由不存在） |
| `401 未授权访问` / `Missing auth token` | 全局守卫拦住 |
| `404 <自定义文案>`（如 `管理员不存在`） | **路由在、JWT 已被接受**，只是 handler 内层查表失败 ⇒ 用它枚举整个 admin 面（本案 27 条全中） |
| `403 <属主文案>`（`Authenticated user does not own the requested address`） | 对象级鉴权**正确实现**，跳过 |
| **无凭证的 POST 回 `400 ["property X should not exist"]`** | **守卫缺口**——你已进 DTO 校验，按报错逐轮补字段 |

- 同族里 **GET 回 401 而 POST 回 400 校验错 = 守卫按模块注册（module-level drift）**：把端点表整体按 200/401/403/400 分桶，**200 + 400 那批就是攻击面**。
- handler 级 `Invalid address` / `<x> does not match signature identity` = **已越过守卫**，是写缺口/缺属主校验的落点；此处**不能收工**。
- 报错文案=免费 schema：`property X should not exist`、`must be one of the following values: a, b`、`must not be less than N` 逐轮喂进去即可重建 DTO。
- bcrypt 抛 `data and hash must be strings`（500）= 密码比对收到非字符串（object 型 password）⇒ 泄漏栈指纹（Express + bcrypt、该路由无 DTO 校验），**不是 NoSQL 注入**；admin 登录路由常缺它面向用户孪生路由有的校验。
- 不存在的 email 与错密码**回同一句** ⇒ 无账号枚举面（只有时序/状态差分可做）。

## 3. 本案判决（可直接当模板抄形状）

- **无鉴权 200**：`wallet/balance/:addr`、`wallet/transactions/:addr`、`membership/:addr`、`membership/stats/overview`、`membership/tiers/all`、`projects-v2`、`projects-v2/:id`、`projects-v2/user/:addr/{investments,pending-revenue}`、`trading/{config,market-stats,kline/:id,orderbook/:id,trades/:id}`、`wallet/deposit/options`、`admin/system/public-runtime-config`、`/health`（版本号+64 表+kline 缓存状态）。
- **401（有守卫）**：`trading/*` 的全部按地址读端点。
- **403 属主校验**：`trading/orders/user/:addr` 等 —— 与上面同级的 `wallet/*` 形成缺口对照。
- **写端点**：`POST /trading/{orders,alerts,triggers}` 无凭证也进 DTO 校验 ⇒ 守卫缺口；迭代到 handler 级 `Invalid address` 后**未能前进（未完成，别写成已利用）**。`wallet/withdraw` / `wallet/transfer` 有 signature-identity 二次校验 ⇒ 判死。
- **admin 面**：普通用户 JWT 下 27 条路由全回 `管理员不存在`；`POST /api/admin/auth/login` 与 user 登录是**两张独立表**；弱口令 19 组全灭并触发 429。
- **JWT HS256**：rockyou 全量 14,344,379 条 70s 零命中 + `alg:none` 6 变体 + 注册期 mass assignment（DTO 白名单拦下）⇒ 写「强随机密钥，伪造路径判死」。
- **写操作 IDOR 未成**：`projects-v2/:id/invest` 的 `User action address does not match signature identity` —— 身份来自签名而非请求里的地址字段（试过 header/query/body 各式均无效）。

## 4. 工程备忘
- 本机若无 `nmap`，用 python `socket.connect_ex` + `ThreadPoolExecutor` 扫端口足够（本案 5 个端口 + 高端口全扫）。
- Tor 出口在 `ALL_PROXY` 里时，`curl`/FTP 探针会走 Tor；用 `ALL_PROXY= all_proxy=` 前缀可对单条命令旁路（判 FTP banner/SSH banner 时有用）。
- FTPS 的 Pure-FTPd 回 `421 Unable to read the indexed puredb file ... Try pure-pw mkdb` = **认证库坏了**，不是密码错；任何用户名都先 `331` 再 `421`，无枚举价值。
- Next.js 站点的 CSP/robots 文案与 `meta description` 会直接说出业务定性（本案 `An AI compute investment platform` —— 入口那个“闪兑”只是引流壳）。
