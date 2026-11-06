# Airflow 管理面实战（Airflow 3.x；betmaster/bmhub 案例验证于 3.1.8）

目标形态：`airflow[-dev].<corp>` 公网暴露（常在管理子域群中发现）。本流程基于 3.1.8 实测；2.x API 完全不同（`/api/v1`、会话/基本认证），先读版本再选路。

## 0. 指纹与版本
- `GET /api/v2/version` → `{"version":"3.1.8",...}`（**本案例 prod 实例此端点免鉴权**）。
- `GET /api/v2/openapi.json` 拿全量端点与 securitySchemes（部分部署未鉴权可读）。
- dev / prod 常是两套实例（`airflow-dev` 与 `airflow`）：dev 门禁更弱、凭据常与 prod 复用，先打 dev。

## 1. 登录（API 令牌）
- Airflow 3 JSON 令牌登录：`POST /auth/token`，body `{"username":"admin","password":"..."}` → `access_token`；后续 `Authorization: Bearer <access_token>`（以实例 openapi 的 securitySchemes 为准）。
- 凭据来源优先级：上游元数据平台泄露（OpenMetadata `pipelineServices` 的连接 login/password 面）→ 配置文件/事件日志 → 默认 admin 一发。本案例即用上游元数据平台泄露的凭据登上 dev。
- **没 DAG ≠ 没价值**：本案例 DAG 列表为空，但 connections / variables / eventLogs 全在。

## 2. 凭据面（admin 令牌）
- `GET /api/v2/connections?limit=...` → 全量连接（本案例 79 条）：conn_id / conn_type / host / login / schema 明文；**password 恒 mask `***`**。价值：内网主机名、外部服务地址（FTP / MySQL / Snowflake 主机）、用户名清单。
- `GET /api/v2/variables` → 全量变量（本案例 148 条）。**掩码是名字型的**：名字含 secret / token / password / apikey / access_key / secret_key / mypass → 值 mask `***`；不含的（host / user / db / 普通名、仅含 `key` 的名字）明文。摸规则：自己建几条变量（一条名字带 secret、一条不带）读回对比即知。
- **改名绕掩码 = 死路（实测堵死，别耗）**：`PATCH /api/v2/variables/{key}` 要求 body 的 `key` 与 URI 参数一致——改名返 `400 Invalid body, key from request body doesn't match uri parameter`；不带 value 返 `422`。掩码值取不到时走两条正路：① 事件日志翻老明文（下条）② 上游元数据平台（OpenMetadata）admin 面重拉同一凭据（见 openmetadata.md §3）。
- `GET /api/v2/eventLogs` → **最大单表（本案例 59 万条），也是老数据的明文库**。掩码是后加的版本/时间行为——旧事件存着加掩码之前的明文（实测：2025-04 的 `variable.create` 事件里 access key 明文，同批 secret key 已 mask）。另可**恢复被后人覆写/删除的变量原值**：本案例从早期 `patch_variable` 事件恢复出 `CLICKHOUSE_HOST` 原值 `http://link-main-databases.vpn.svc:8123/?query=`（后被别人改成 webhook.site）。事件类型速查（本案例量级）：`variable.edit`（257）/ `patch_variable`（67，extra 带值，最肥）/ `connection.edit`（53）/ `cli_users_create`（47，口令已 mask）/ `connection.create`（30）/ `variable.create`（26）/ `cli_variables_set`（1）。按 `event=` 过滤 + 分页捞；结果落文件再读回，分批续跑。
- **前任测试残留 = 免费情报**：`i24xxx` / `pt*` 系列变量/账号是上几轮测试者的探针——本案例靠 `i24168_*` 系列直接反推出掩码规则；事件日志里还能看到前任的尝试（如 `xCLICKHOUSE_SECRETx` 改名试探）。
- `POST /api/v2/connections/test`、`config` 端点在部分部署被关（本案例连接测试不可用）——试一发即止，别耗。
- API 层 mask 别硬撬：同一批连接若上游元数据平台（OpenMetadata 等）也持有，其 admin 读面**不 mask**（见 openmetadata.md §3）。

## 3. 横向与利用
- 连接清单的 host/login/schema 直接做凭据复用（跨库/跨服务/跨 dev-prod 先试）。
- 变量里的内部主机名（ClickHouse host、Vault 地址等）→ 配合 SSRF 探针（openmetadata.md §5）打内网。本案例变量明文给全了 host/user/db（`link-main-databases.vpn.svc:8123` / `analytics` / `eventslog`），只差 mask 的口令——先翻事件日志老明文（§2），别对服务盲爆。
- 无 DAG 且无写面时，不要纠结「上传 DAG 跑代码」；凭据面 + 事件日志挖掘才是主产出。

## Pitfalls
- 3.x 与 2.x 完全不兼容：路径（/api/v2）、令牌 JSON、参数名都不同——先读 openapi.json 再动手。
- `***` 是 API 层掩码行为，别把 `***` 当「已获取」写进报告；也别在「改名绕掩码」上耗时间——实测堵死（§2）。
- 事件日志含大量运营噪音，先按事件类型/关键字过滤，避免把 59 万条整表翻到底。
