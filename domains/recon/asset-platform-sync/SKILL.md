---
name: asset-platform-sync
description: "要把外部资产平台的域名、子域、IP、端口、站点、应用批量导进自己的资产图时加载：用 MCP 数据源（地址加 X-API-Key）对接，按项目或任务维度翻页拉取，把主机名、记录类型、记录值、解析 IP、页面标题、状态码、应用指纹、图标哈希映射成内部资产字段，按公司域名、IP 段、ICP 主体范围归并，按唯一键去重防止产生副本，续跑做幂等校验，并判定密钥失效、分页截断、资产类型不识别三类失败。"
sources: art-content, operator_experience
---

## 定位

把一个外部平台（下称 Scopesentry 类资产平台）已扫出的域名、子域、IP、端口、站点、应用灌进本地资产图，按公司范围归并去重，让覆盖度统计与探索入口直接可用。

## 对接模型

- 数据源是一行 http 传输的 MCP 记录：`name` 取平台默认名（schema 预置占位行，URL 与密钥为空、未启用），`url` 填该平台的 `/mcp` 端点，`env` 被当作逐请求 HTTP 头，API Key 放 `{"X-API-Key":"ssk_..."}`，Bearer 形态放 `{"Authorization":"Bearer ssk_..."}`；自签证书置 `insecure=true`。
- 控制面五个方法，前缀 `/api/sync/scopesentry/`：`GET status` 返回 exists/configured/enabled/reachable/tools；`POST datasource` 收 `{url, api_key}`，两者齐备才置 enabled；`GET projects?page&size&search`；`GET tasks?page&size&search`；`POST sync`。
- 保存时 `api_key` 传空串只改地址、旧 Key 保留；保存成功即做一次工具发现（30 秒窗口），工具清单回填 `status.tools`。
- `POST sync` 请求体：`dimension` 取 `project` 或 `task`；`targets` 是项目 ObjectID 数组或任务名数组；`asset_types` 缺省 `["subdomain","service","app"]`；`create_company` 布尔；`page_size` 缺省 100，≤0 或 >500 一律按 100。
- 维度语义：`project` 走 `filter.project=[ObjectID]`，`task` 走 `filter.task=[任务名]`；ObjectID 取自 `list_projects_data` 的 `result.All[].id`，任务名取自 `list_tasks` 的 `list[].name`。`filter.project` 填 ObjectID，填项目显示名查不到数据。
- 平台侧类型枚举：`asset_type` 用 `subdomain` / `asset` / `app`（平台另有 `RootDomain`、`UrlScan`、`IPAsset`、`vulnerability`，本同步只吃前三类）；映射为 `subdomain→subdomain`、`service→asset`、`app→app`，表外类型进 warnings `未知资产类型，已跳过: X`。
- 平台的 `search` 是自有 DSL：`==` 全等走索引、`=` 转 regex 模糊、`^` 前缀走索引，`project` 拼进 search 无效；同步只用 `filter`，不拼 search。
- 分页拉取：`list_assets{asset_type, pageIndex, pageSize, filter}`，pageIndex 从 1 递增；信封 `{list:[...]}` 无 total，返回条数少于 pageSize 即停；单 target 单类型 5000 条封顶，命中即截断并记 warning；整次同步 10 分钟超时，项目列表与任务列表各 60 秒。
- `create_company` 打开时逐项目调 `get_project{id}`：`name` 建公司（同名折小写去重），`target` 按换行拆成根域名写入公司范围，reason 记 `scopesentry:<公司名>`；同步收尾再跑一次归属重算。

## 字段映射

- subdomain 行：`host`→`domain`（折小写、去尾点）；`type`→`record_type`；`value[]`→`record_value[]`；`ip[]`→逐条 `ip` 资产并把 `host` 并进 `bound_domains`。平台列表字段叫 `host`，搜索语法里叫 `domain`，两处名不同。
- app 行：`name`→`app_name`；`category`→`category`；`description`→`app_description`；`icp`→`app_icp`。
- service 行·HTTP 分支（`service=="http"` 或 `url` 非空）：`url`→`url`（scheme 与 host 折小写、裸根去尾斜杠）；`products[]`→`technologies[]`；`status`→`status_code`；`title`→`page_title`；`icon`→`favicon_mmh3`；`ip`→`ip` 与 `c_segment`（IPv4 取 /24、IPv6 取 /48）；`domain`、`port`、`service_name` 从 URL 反解，`http` 补 80、`https` 补 443 与 `HTTP`/`HTTPS`。
- service 行·非 HTTP 分支：`domain`、`ip`、`port`（字符串转 int 后入库）、`service`→`service_name`（折小写）。
- 副产物：每写一条 service 触发 `linkHostAssets`，根域名补一条 `root_domain` 资产、非 apex 域补一条 `subdomain` 资产；带 `ip` 时补 IP 资产与端口条目。

## 归并与去重

- 唯一键（PG 部分唯一索引，去重的落点）：`root_domain` 用 `(domain)`；`ip` 用 `(ip)`；`subdomain` 用 `(domain, COALESCE(record_type,''))`；`app` 有 `bundle_id` 用 `(bundle_id)`、无则用 `(app_name)`；HTTP service 用 `(url)`；非 HTTP service 用 `(COALESCE(domain,''), COALESCE(ip,''), port, service_name)`；endpoint 用 `(url, method)`。
- 公司范围归并：`company_scope.kind` 为 `domain`/`ip`/`cidr`/`icp`/`keyword`；写入时按根域名全等（长度降序、company_id 升序取首条）→ `net >>= ip`（masklen 降序）→ ICP 归一化全等（去全部 Unicode 空白、折小写）三段顺序命中即止，`keyword` 不参与归属。命中写 `company_id` 与 `company_source='scope'`。
- 同实体多来源：同一 IP 被多条子域解析到则 `bound_domains` 累加；同一 URL 被项目维与任务维各拉一次仍是单行，`task_ids` 取并集；同一端口被两条 service 报到只留一条。
- 冲突取值优先级：`company_source='explicit'` 的行，公司归属不被同步覆盖；标量走 `COALESCE(新值, 旧值)`，新值非空即覆盖、空值保留旧值；数组走并集去重（`bound_domains`、`record_value`、`technologies`、`task_ids`、`auth` 按元素文本）；`open_ports` 按 `port` 去重、同端口优先带 service 名的条目；endpoint `params` 按 `(location, name)` 去重。
- 字段级顺序并不统一：IP 资产的 `c_segment` 取旧值优先（首次定值后不再改），subdomain 的 `ip` 取新值优先，`root_domain.icp` 同样新值优先。

## 增量同步与幂等

- 源码没有游标、时间窗、since 参数：每次同步都从 pageIndex=1 全量重拉，靠唯一键 + `ON CONFLICT ... DO UPDATE` 落成同一行。
- 幂等判据：第二遍跑同一组 `targets`，各类型 `count(*)` 不变；`created_at` 保持，`last_seen` 每次写刷新为 `now()`。
- 返回体 `synced` 是「成功 upsert 次数」而非新增行数——计数照涨、表行数不变，即幂等成立。
- 同步写入的资产 `task_ids` 为空数组（落库不带 TaskID），不自动进任务范围；范围要另用 `task_scope` 的 `company`/`root_domain`/`subdomain`/`ip`/`cidr`/`icp` 行锚定，`uq_task_scope_v2` 让重复范围行被忽略。
- 项目维不打开 `create_company` 时，归属在每条写入即时解析，不做全表重算；打开时收尾统一重算，新入图资产才认领到公司。

## 入图后的用途

- 资产图与覆盖度：`GET /api/tasks/{id}/coverage` 给 `denominator`/`tested`/`pct`/`by_type`，`GET /api/tasks/{id}/coverage-graph` 给力导图节点；分母是命中 `task_scope` 的资产，已测是锚到该 exploration `fact` 节点的资产（`exploration_anchors`）。
- 探索入口：公司关联任务拿公司资产做上下文（`coverage.host_count`），`add_task_scope` 补范围，`list_untested_assets` 看未测存量；`coverage_enabled=false` 时 `coverage` 块隐去、`list_untested_assets` 从工具面摘除，范围行保留。
- 清理：`delete_assets_by_host` 按 host 全等硬删（跨任务全局，不可逆），传根域名连带子域、服务、接口。

## 失败模式与判据

- Key 失效：`status.configured` = URL 非空且 env 有非空值，`enabled` 与之同构，`reachable` 靠 12 秒内 `tools/list` 成功；项目列表与任务列表失败回 502 并带 `list_projects_data 失败: ...`，同步内单类型失败进 `errors`、文本 `<类型>(<target>) 拉取失败: ...`，整次调用仍回 200。判据顺序：`reachable=false` 先修地址与 Key，`reachable=true` 而 projects 报错则看错误里的工具名。
- 分页截断：warning 文本 `<类型>(<target>) 达到 5000 条上限，已截断`；空页即止；`page_size` 请求超 500 被压回 100，翻页深度按 100 重算。
- 类型不识别：warning `未知资产类型，已跳过: X`；`dimension` 非 `project`/`task` 回 400，`targets` 空回 400，`asset_types` 空则三类全开。
- 空字段静默丢弃：subdomain 缺 `host`、app 缺 `name`、HTTP 分支缺 `url`、非 HTTP 分支 `port` 为 0——该条不入库、不进 `errors`、不进 `synced`。
- 归因告警：`ip` 列解析失败的资产在 `RecomputeAttribution` 被 `try_inet` 跳过，日志记 warning 并列样本 id；公司创建失败记 `<公司> 创建失败: ...`。

## 与既有卡衔接

- 公司主体与范围设计接 `corporate-intel-deepdive`、`recon-and-methodology`。
- 资产图扩张与外部线索并图接 `fraud-network-asset-expansion`、`bucket-content-artifact-mining`。
- 同步进来的站点与接口做版本比对接 `component-vuln-intel`。
- 覆盖度与证据链落地接 `evidence-hygiene`、`finding-traffic-evidence-chain`；攻击路径编排接 `attack-chain`。
