---
name: source-audit-authz-gaps
description: "源码审计找授权/校验缺失(路由/注解中间件差分、fail-open、网关单闸门)。触发: 差异法, 权限覆盖率, 越权审计。"
---

# 源码审计: 找授权与校验缺失

适用: 在源码里找「应该校验却没校验」的洞(越权/IDOR/未授权访问)。
**不适用于内存破坏类** —— 那类走 fuzzing, 本技能不碰。

## 铁则零: 先核实「我有没有资格审」—— 在网第三方服务一律转源码面

收到一个**在网第三方服务**(有付费客户 / 商业套餐)的渗透请求时, 先做 3 个事实核查(成本 1 分钟):

1. **归属**: WHOIS/crt.sh + 是否有商业订阅 → 判定是不是自家资产
2. **授权面**: `SECURITY.md` / VDP / Bug Bounty / GitHub Security Advisories 是否存在
   (`curl -s -o /dev/null -w '%{http_code}' https://raw.githubusercontent.com/<org>/<repo>/main/SECURITY.md`)
3. **开源面**: 若 AGPL/MIT 开源, **线上不可动但源码可审** —— 成本最低、产出最高的落点

判定为「非自有 + 无公开授权渠道」时: 只做 **源码静态审计 + 自建实例上的差分 PoC**,
不对线上发任何利用/压测请求; 交付改走**负责任披露**路径(报告里附披露邮件草稿)。

**自建实例是这类任务的标配靶场**(也适用于用户自有的自部署系统):

```bash
docker run -d -p 8080:8080 <官方镜像> serve --env production --hostname 0.0.0.0 --port 8080
```

官方 Docker 镜像 = 与线上同版本代码 ⇒ 漏洞能否成立在**真进程**上验, 而不是只在脑内推。
需要「来源 IP 属于某网段」才能触发的洞(CDN/CF 网段判定类), 用
`docker network create --subnet <目标CIDR>` + 客户端容器静态 IP 复现 —— 不必碰真实 CDN。

## 铁则一: 按 CVE 数量选目标, 别碰被审透的

被审计强度直接决定出洞概率。开审前先查目标已知 CVE 数:

| 目标特征 | 动作 |
|---|---|
| CVE 几十条(大厂基础设施) | **跳过** —— 专业团队在盯 |
| CVE 1~2 条且是几年前, 但用户量/装机量很大 | **首选** —— 用户量大=影响面大, CVE 少=被审少 |

已知 CVE 的**类型**是线索: 历史上都是 Improper Authorization, 就优先审授权。

## 铁则二: 差异法 —— 找「同类都做了, 这几个没做」

**不要看到"没检查"就报。** 先证明检查模式存在:

1. **确认模式** — 看同组件/同类型的多个 handler 怎么做校验(Go 里形如 `s.iamManager.CheckPermission(ctx, permission.X, user, workspaceID, projectID)`)
2. **建对照组** — 找到"确实做了校验"的那些, 它们证明项目**有**权限模型
3. **找例外** — 脚本化列出全部 handler, 逐个看函数体内是否调用校验函数
4. **排合理例外** — Login/Signup/Refresh/Logout/健康检查本就不需要权限, 逐个人工筛
5. **追数据流** — 确认被漏掉的资源 ID / 路径真的来自请求, 而不是内部常量
6. **分级交付** — 「强候选(证据链完整, 未实测)」与「确认漏洞(已复现)」**绝不能混写**

**为什么必须先建对照组**: "没做校验"极可能是设计如此(公开接口), 也可能校验在别处(中间件/store 层/拦截器)。只有"模式存在 + 这个例外"同时成立才是漏洞 —— 只看单点会产出大量误报。

```bash
python <skill_dir>/scripts/audit_perm.py <源码根>   # API handler 权限覆盖率
python <skill_dir>/scripts/audit_go.py  <源码根>   # 危险模式扫描(宽匹配, 宁多报)
```

**实测命中(两个 Go 数据库管理端各一条)**:
- 路由层只挂认证中间件、该功能组无权限中间件 + handler 全程不取用户身份
- handler 不调 CheckPermission + 资源 ID 直接来自请求未校验归属

两条都拿"同文件另一个函数做了校验"当对照。

## 高价值位置: 「业务上不该发生」的功能

记录/统计/日志/报表/导出类功能 **必然把外部数据写进库或读出来**, 是注入与越权的双重候选; 而且越权读的**载荷**往往比普通列表接口敏感得多(如审计日志里的 request/response 原文)。开审时把这类功能单列一份清单。

## 中间件绑定载体: 绑在哪决定你扫哪(扫错位置=全量误判)

先花一分钟定位「中间件挂在哪」, 再开扫:

| 载体 | 典型形态 | 扫描入口 |
|---|---|---|
| 全局配置 | `config/autoload/middlewares.php` 按组名(如 `jsonrpc`/`http`)挂 | 读配置 —— 若某组只有 locale/日志中间件 ⇒ **该层零鉴权**, 认证全在上一层(网关) |
| 路由文件 | `route/admin.php` 逐条或分组 `->middleware([...])` | 解析路由文件 —— 组中间件常写在**组关闭行**, 必须「先建组树、再回填」, 否则整组误判为未保护 |
| 控制器注解 | `@ApiVersion(version=...)` + `@Middleware(X::class)` / `@Middlewares({...})` (Hyperf/apidog 系) | 扫控制器 docblock —— 对外 URL = `/{version}/{path}`(如 `/admin/integral/goods/list`) |

两个必查前提:
- **默认路由是否开放**: 框架开了 `url_route_must=true` 时未登记路由直接 404 ⇒ 不能用「路由未登记」当漏洞; 开放时未登记路由可直达 controller, 漏网面要按 controller action 全集算。
- **服务层零鉴权 = 上层唯一闸门**: 多服务并列仓库里每个服务的组配置都只挂 locale/日志中间件 ⇒ 一把钥匙开全部租户, 审计优先级最高。

**中间件按语义分三类, 每类都可能单独成洞**:
1. **拒绝型**(失败 `return 401`) —— 该挂未挂即未授权。
2. **注入型**(`if (checkAuth($t)) { $ctx->set('uid',...) }` 无 else 分支) —— 校验失败**不拒绝**, 只跳过赋值; 它单独存在时路由依旧是未授权 ⇒ 逐域检查是否另挂拒绝型中间件(有成对才安全)。
3. **密钥相等型**(`env('SECRET') != $req->getHeaderLine('server-secret')`) —— 语义是「知道常量即管理员」; 立刻读 `.env*` 取实值, 并核 dev/prod 是否同值(同值 = 低环境泄露直接升级为生产影响), `!=` 松比较另查 type juggling 余地(数字串/类型混用)。

**输出用「中间件组合频次」而不是只看零中间件**: `Counter(tuple(sorted(mws)))` 的**孤例与缺环**就是嫌疑 —— 单闸门 `['AdminMiddleware']`、缺 Permission 的 `['Admin','Login','Log']`、正常域一致而某控制器为空列表。拿到嫌疑后逐个列出其可写路由(`create/update/delete/grant/send/settlement/create`)再定级。

## Pitfalls

- **`Host` 头驱动鉴权分支是通病**: `guard headers[.host].first(where: { $0.contains("域名字符串") }) else { …直接处理并 return }` 这种「本机/自建便利分支」一旦用**客户端可控头**判定, 等于把限流/配额/容量限制做成可开关。**审计时优先 grep `headers[.host]` / `contains("` / `starts(with:`** —— 顺带查用 `contains`/`starts(with:)` 替代 `==` 造成的开放重定向与子域校验绕过(`Host: api.官方域.attacker` 同时满足两个条件)。
- **`Referer`/`Origin` 做唯一鉴权 = 无鉴权**: 形如 `validateAllowedReferer()` 的函数用 `curl -H 'Referer: https://<官方域>/'` 直接验; 并确认该分支是否**在鉴权代码之前就 return**(Host/路径分支最容易绕过后面的 `authorizeXxx()`)。
- **配额桶键绝不能取自 HTTP 头**: `slot = headers["X-Some-Header"].first?.hashValue` 型代码 = 每个头值一个新桶 = 配额归零; 且 Swift `String.hashValue` 是**每进程随机种子**, 配额还会跨重启丢失。
- **权限拒绝的错误码 ≠ 授权检查**: `CodePermissionDenied` / HTTP 403 可能来自 **license/付费功能开关**(`IsFeatureEnabled`)、配额、业务前置条件。**必须追到那行错误的来源函数再下结论** —— 只查 license 的分支披着 PermissionDenied 的外衣, 极易被误判成"这里有权限控制"。
- **gosec 会漏 `Sprintf`+`Raw` 拼 SQL**: 同一项目 gosec 零 SQL 注入告警, 人工却扫出多处 —— 该组合不在它规则模式里。**gosec 只当候选池的一半**。
- **gosec 在非原生平台跳过 SSA**: 扫 Linux 项目时报 `skipping SSA analysis`。基于 AST 的规则仍有效, **依赖数据流的规则全漏** → 结果只当下限, 完整结果需在目标平台跑。
- **Windows 上编不了 Linux-only 项目**: 用了 `syscall.Kill`/`Setpgid`/`sysconf` 的包 `go build` 直接挂。**解法: 把目标函数(纯字符串/逻辑类)原样复制到独立程序验证行为** —— 对不依赖平台的函数这样验证有效(行为完全由代码逻辑决定)。
- **浅克隆做不了补丁差分**: `--depth 1` 只有 1 个 commit, `git show <fix>` 全废。**替代: GitHub API 按文件查历史** —— `GET /repos/<org>/<repo>/commits?path=<file>` 拿列表, 再 `/commits/<sha>` 拿 diff 原文。比 `git fetch --unshallow` 拉几 GB 快得多。
- **`go` 是原生程序**: `GOPATH` 必须写 `D:/gopath` 而非 `/d/gopath`(MSYS 路径不认)。`GOPROXY=https://goproxy.cn,direct` + `GOSUMDB=off` 大幅加速依赖下载。
- **下载慢别归因于"本机限速"**: 同一台机器不同源的速度能差一个量级, **瓶颈通常在目标服务器**。取大文件优先官方 CDN/国内镜像, 别硬磕 GitHub release。
- **要能自证审计过的 clone 未改动**: 加过的占位/测试文件单独列出; 用 `git diff --numstat` 区分"内容改动"与"仅行尾符(CRLF)差异" —— Windows 上后者会让 `git status` 显示 `M` 但内容零变化。
- **写明审计版本的 commit hash**: 否则厂商修了之后无法证明"当时那版确实有问题" —— 这是提 CVE 的基本要求。

- **路径白名单是「按路径」不是「按路由」** —— 中间件里 `strings.Split(ctx.Request.RequestURI,"?")[0] == "/x/y"` 型白名单, 对**该路径上注册的每一个 HTTP 方法**生效(gin 里 `r.HEAD/GET/PUT/DELETE("/x/y")` 四个 handler 全部免登录)。发现白名单后立刻枚举这条路径挂了几种 verb, 再逐个进 handler 看二次校验 —— 判决随 verb 分化: 读方法可能仍有 ACL 复查, 写/删方法可能完全没有。只看白名单就下结论会同时漏掉写面和误报读面。
- **鉴权失败后不判空 ⇒ nil 解引用 panic, 不是写原语** —— 中间件把 `checkLogin` 置 false 跳过 401 后, handler 直接 `IsSuperAdmin(user.UserId)` / `user.AuthStatus` ⇒ 未登录请求变 500。判定「未授权写」之前必须读 handler 有没有 nil 检查; 有 nil 风险的要报「可用性/逻辑缺陷」而不是写原语, 且**绝不在线上试写/删**去验证。
- **硬编码密钥 + 哨兵值绕过校验** —— 请求派生字符串(桶名/对象名/uid)经 `fmt.Sprintf("%s$$%s$$%d", ...)` 拼接后加密成令牌是国产 SaaS 的常见设计。审这类校验器只看三点: ① 密钥/IV/模式是否写在源码 ② 明文是否含用户可控字段 ③ 有没有哨兵短路(`exp != -1 && now > exp` 里的 `-1`、空串、`0`、`MaxInt`)。三点齐 = 可伪造永久令牌; 用 `openssl enc -aes-128-cbc -K <hexkey> -iv <hexiv> -nosalt` 本地复现算法成本极低, 报告里写清 mode/key/iv/编码。
- **JWT 密钥泄露 ≠ 可伪造会话** —— 先读验签路径: 「无状态 JWT」才值得跑密钥伪造矩阵; 若是「JWT 只带随机 uuid + Redis 会话查找」(`UserTokenKey+uuid`, TTL 30 分钟), 拿到密钥也过不了鉴权。先花一分钟读 token 生成/校验函数, 再决定要不要跑伪造矩阵。
- **同一厂商源码 ≠ 同一代线上栈** —— 写「产品级未授权链」前先给线上做代际指纹: 源码里独有的路由在线上是否 404、两边的路由名集合是否交集为空。交集空(本次线上栈完全没有源码里的业务路由)⇒ 只能报「源码级发现, 对当前线上不适用」, 不能写成线上可利用。厂商域名/IP 也一起验: 源码配置里的部署域名常已 NXDOMAIN、IP 已不可达。**入口归属也要验** —— 同一域名 :443 可能已被别的产品占用(看页面 title / `window.X` 全局变量 / SPA base path 即可判)、候选域可能是第三方主体的站 ⇒ 这种情况按「归属失败 / 无攻击面」写进交付, 不得当漏洞上报。

- **全局中间件先于路由中间件执行 ⇒ 参数错误会掩盖鉴权结果**: 「空参 → 400 参数错误」**不能**当作穿越鉴权的证据(校验层可能先拦)。证明未授权必须挑**参数可选的只读 GET** 路由, 让 401/403 与 200 的差异唯一归因于鉴权, 并在同域另取一条**确定受保护**的路由作对照(仍 401/403 才说明差异来自路由而非环境)。
- **禁止为证明「可达」而执行写/结算/发卡类端点**: `.../statement/create`、`.../settlement/create`、`grant`、`send` 这类路由一旦真的跑通就是真实业务副作用。先读源码 `@Query/@FormData rule` 确认必填参数, 只证明未授权可达时改用**同控制器里的读路由**(注解组合相同 ⇒ 鉴权面相同), 取证优先级永远是读接口。
- **鉴权扫描要先定载体再开扫**: 用路由文件的解析器去扫注解式框架、或用「只看零中间件」的思路去找漏挂, 都会得到看似合理、实则全量的错误结论 —— 先确认绑定载体(见上节表), 再选扫描入口。

## 交付物: 报告怎么写

- **状态要分级说清**: 「强候选(证据链完整, 未实测)」不是「确认漏洞」。静态证据再硬也只算候选。
- **每条候选附完整证据链 + 对照** —— 单点"它没检查"说服力不够, 要配上"同项目其它函数检查了"。
- **长文档分段写**: 先 `write_file` 写主体(控制到几 KB), 再用 `patch` 逐段追加。一次性塞超长内容会被**静默截断**(只落几百字节)且不报错 —— 靠回读文件大小发现。
- **用 `patch` 在锚点前插入时, 必须把锚点原文写回 `new_string`** —— 否则那一行被静默删掉(表现是章节标题凭空消失), 极易连踩多次才察觉。插入后扫一眼章节标题是否还齐。
- **锚点必须是全文唯一的行**, 先 `read_file`/`search_files` 确认, 不要凭记忆写锚点。

## References

- `references/auth-middleware-and-token-validation.md` — 认证中间件白名单(按路径≠按路由)、handler 二次校验、JWT 会话查找 vs 无状态、下载令牌本地复现配方、线上代际指纹检查表、**注解式框架的中间件覆盖差分 + 未授权实证的差分设计与证据阶梯**(均附可 grep 的代码形态与判决规则)
- `scripts/audit_apidog_mw.py <app/Controller 目录> [域关键字]` — 注解式控制器的鉴权覆盖差分: 中间件组合频次 / 零中间件+可写路由 / 单闸门 / 缺环四张清单

## Verification

- [ ] 目标已按 CVE 数量筛过, 不是随手选的
- [ ] 找出了至少一个对照组 handler(证明权限模型存在)
- [ ] 每条候选都追到了数据源(资源 ID 确实来自请求)
- [ ] 合理例外已逐个人工排除, 留下的候选数得过来
- [ ] 报告里「强候选」与「确认漏洞」分开写, 未实测的没写成确认
