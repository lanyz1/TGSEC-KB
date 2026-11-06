# 自部署服务指纹速查（2026-10 betmaster/bmhub 战役实证）

识别 → 未鉴权面 → 判定价值 vs 死路。适用于数据/运维平台子域侦察（Grafana/Headscale/PostHog 类）。

## Grafana（/metrics 双用：信息泄露 + CVE 适用性判定器）

- 指纹：`GET /api/health` → `{"database":"ok","version":"12.x.y","commit":...}`；`/login` 是 SPA；`/metrics` 常未鉴权公开。
- **/metrics 是金矿**（未鉴权）：
  - `grafana_build_info{branch=...,edition="oss"|"enterprise",version=...}` — **edition 判定企业插件类利用链死活**（oss 上依赖 Enterprise 插件的链直接死）。
  - `grafana_feature_toggles_info{name="..."} 0|1` — **先查开关再投入 CVE**：实测 CVE-2026-27876（SQL Expressions 链 RCE，CVSS 9.1，影响 12.3.0≤v<12.3.6 等区间）因 `sqlExpressions` toggle=0 直接放弃，省一整轮研发；文档说"需要 toggle 开启"的 CVE 一律先查此项。
  - datasource 名/类型、handler 级请求计数 — 推 API 面与使用度。
- 登录面判定：`POST /login` JSON `{"user":..,"password":..}` → 401 `password-auth.failed` = **本地密码认证开着**（即便同时配了 Google OAuth）；登录页无 signup 链接 = 注册关闭；OAuth-only 且无凭据 = 门死，转 /metrics 与 datasource 名的侧信道。
- 出口：拿到 Viewer+ 会话 = 全部 datasource 凭据可达（含 DB）。**会话是一切**；无会话时本产品只做资产登记。

## Headscale（Tailscale 控制面，自建内网中枢）

- 指纹：`/swagger/v1/openapiv2.json` → `"title": "headscale/v1/headscale.proto"`；`/version` → `{version, commit, buildTime, go}`；`/key` → `capability version must be set`；`/apple` `/windows` 静态转换页；`/api/v1/health` 401。
- API 面：`/api/v1/{user,node,apikey,preauthkey,policy,...}` 全部 Bearer API key；除 health 外无匿名读。
- 历史漏洞：早期版本 `/api/v1` 认证中间件写 "Unauthorized" 后未 return → handler 继续执行并向 body 追加数据（修于 0.2x；v0.29.3 实测已堵——无 auth 时 body 恒为 12B `Unauthorized`，探测方式=看响应长度是否超此值）。
- **拿到 key 的后果 = 整个 tailnet**：apikey → 创建 preauthkey → 任意外部主机 `tailscale up --login-server <host> --auth-key <key>` 加入内网 → 直连内网数据库/服务。发现 `tskey-*` 或 headscale apikey 即最高优先级（立即去 /api/v1/node 列节点）。
- 死路记录：无 key 时穷举/头伪造/audience 绕全无效；同域 derp 中继（*.derp.*:443）只转发加密包，无凭证价值。

## PostHog（自部署产品分析）

- 指纹（摄入端未鉴权）：`/decide/` `/flags/` `/e/` `/s/` `/batch/` `/track/` `/engage/` `/capture/`。GET `/decide`|`/flags` → `{"featureFlags":{},"featureFlagPayloads":{},"evaluatedAt":...,"supportedCompression":["gzip","gzip-js"],"config":{"enable_collect_everything":true}}`；POST `/e`|`/s`|`/batch` → 400 `request missing data payload`。
- 管理/UI 面常被部署方剥离：`/login` `/signup` 404（自定义 404 页），`/api/*` → 401 `{"type":"authentication_error"}`（需 phx_ 个人 API key）。
- `/decide` 免 token：可用 distinct_id 探 feature flag 名称（recon）；写事件需项目 token（phc_ 前缀，常在主站 JS 里）。
- 价值：入口 = inst实例内容（用户行为/人群/flags 全量）；无 key 时记录，勿在摄入端空转。

## 未知子域首探清单（通用，30 秒定性）

1. `/openapi.json` `/docs` `/swagger` `/swagger/v1/openapiv2.json` — 轻框架的完整 API 表。FastAPI 形态回传接收器（实测 appsflyer 类）= `/postback/{secret}` POST + `/healthz` + `/test`：价值低（除非 secret 可猜），登记即走；Headscale 则靠 `/swagger/v1/openapiv2.json` 认出。
2. `/robots.txt` — **部署者自曝的 API 路径表**：`Disallow:` 列表常直接给出全部业务路由（实测一个内部服务的 /decide /flags /e /s /batch /track /engage /capture 全是从 robots 列表拿到的）。自定义 404 页（如 ASCII 骆驼 "where am i?"）不算指纹，别过度解读。
3. `/version` `/api/health` `/_health` `/metrics` — 版本/存活/指标（metrics 常最肥，见 Grafana 节）。
4. `/login` `/signup` `/admin` 全 404 = UI 被剥离的部署 → 门在 API 层，转找 key（见下方 token 前缀表）。

## 快速分类口诀（自部署服务通用）

- 硬 403 全路径（含 /favicon.ico）= 主机级 WAF；换出口判 per-IP vs host-wide（见 app-layer-login-ratelimit）。
- 小页 200 + `document.cookie` + reload = 主机 JS 门（Beget: `beget=begetok`）——每个请求都要带，否则全程假失败。
- 静态页 404 但 API 401 成对出现 = 服务在跑、门在 API 层：把目标从"找漏洞"切换到"找密钥/会话"——在已有 loot 里搜产品 token 前缀：`glsa_`（Grafana SA token）/ `eyJrIjoi`（旧版 Grafana API key b64）/ `phx_`（PostHog）/ `phc_`（PostHog 摄入）/ `tskey-`（Tailscale/Headscale）。
