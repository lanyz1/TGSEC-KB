---
name: oss-deployed-app-audit
description: "Use when target runs a recognizable open-source app."
version: 1.0.0
tags: [pentest, oss, source-audit, self-hosted, cloudflare-worker]
---

# 自部署开源应用审计（认牌子 → 对版本读源码 → 靶向测）

来源: 2026-10 多案例（cloudflare_temp_email / RenewHelper / Kite / SnailJob / Gitea）。

现代中文黑灰产/企业内网大量用**开源/市售产品**搭服务（临时邮箱、续费管理、K8s 控制台、任务调度、Git）。这类目标的最优路径不是盲打，而是：

## 工作流

1. **认牌子**（指纹）：title/版本号（如 `RenewHelper v3.8.4`、`Temp Email`、`Gitea`）、特征路径（`/open_api/settings`、`/api/v1/auth/setup`）、页面里的产品名/版权/仓库链接（`github.com/xxx/yyy`、`versync.pages.dev/xxx.json`）、JS 里的包名。
2. **拉对应版本源码**：`raw.githubusercontent.com/<org>/<repo>/<tag>/<path>`；不确定路径用 GitHub API 拿 tree：
   `api.github.com/repos/<org>/<repo>/git/trees/<tag>?recursive=1`（找 auth/middleware/worker/index/admin 文件）。
   还能搜 v1.x.y 标签找精确版本；README/部署文档里往往有**样例配置值与默认口令**。
3. **读懂真实门禁**（比猜端点快 10 倍）：读路由挂载（什么路由分到哪个 auth 中间件）+ 中间件本体。记录：公开路由、各 token 名称（cookie/header）、校验顺序（先验签还是先查库）、默认 secret/口令。
4. **靶向验证**：按验证器语义构造请求——区分「路由不存在 vs 存在但門禁」（如 404 no-static-resource vs 401/500）；默认值先试样例配置里的值。
5. **没门就记录并为其它轴让路**；拿到密钥就解加密数据。

## 实战要点（已验证）

- **Cloudflare Worker 类产品**（RenewHelper/cloudflare_temp_email）：
  - 单口令门常见实现：`payload === (env.AUTH_PASSWORD || "admin")`——默认 admin 先试；改过则限速常很狠（如 5 错/15 分封 IP，键=`cf-connecting-ip`，经 CF 无法伪造→用 Tor 换出口=新配额）。
  - token 体系：HS256 + `env.JWT_SECRET`（Cloudflare secret 不可读）；部分实现写库校验 token 负载（如 payload 里的 id 必须在 DB 存在）→ **即使 secret 泄露也需有效对象**。
  - KV 配置项（settings）决定功能开关：注册/建址/换密/TG 集成常整片关闭——读 open_api/settings 一次看出整个攻击面。
- **开源框架默认密钥**：先试仓库里的默认（如 `kite-default-jwt-secret-key-change-in-production`、jeecg/jimu 系列）；失败再确认自定义后放弃——不要盲目锤。
- **鉴权分层差异**：同一套代码不同部署/镜像域名门禁可能不同（有域靠 CF WAF 挡 `/api/*`、有域裸着）→ 多域名/镜像都要过一遍。
- **拿不到源码时**（闭源市售产品同此）：用同款其他部署（demo 站/官方 SaaS/证书透明枚举出的兄弟实例）对照行为推导中间件逻辑；前端可读时优先反读 bundle 提 API（uni-app Vue2 搜 chunk 表 `"pages-x":"[a-f0-9]{8}"` 直取异步 chunk）。
- **数据/运维平台管理面暴露在子域时**（OpenMetadata / Grafana / Airflow / Jupyter / Vault / Airbyte / Metabase 等）：先读**未鉴权系统配置 API**（如 OpenMetadata `/api/v1/system/config/auth`、`/api/v1/system/config/authorizer`）与自注册开关——`enableSelfSignup=true` + 空白名单 = 任意邮箱零门槛注册；再查默认管理员邮箱（principalDomain）+ 默认口令一发。**配置类 API 常只 mask 密码**，host/端口/用户名/内网主机名照吐 → 直接得内网拓扑与上层系统凭据材料。OpenMetadata 全流程（自注册 → Base64 登录 → JSON-Patch 提权/人类号 PAT → admin 未 mask 凭据 → testDestination SSRF 内网探针）见 `references/openmetadata.md`；Airflow 3 管理面（/auth/token 登录、connections/variables 枚举、名字型掩码、改名绕掩码堵死、事件日志翻历史明文）见 `references/airflow.md`；Grafana 先无脑拉公开 `/metrics`（本案例 1.7MB：datasource 名/告警计数/用户数全泄）——**也是 CVE 适用性判定器**（`grafana_feature_toggles_info{name=..} 0/1`，先查开关再投入）与 edition 判定（oss/enterprise 决定企业插件链死活）；Headscale（Tailscale 控制面）/ PostHog 等自部署服务指纹与未鉴权面速查见 `references/service-fingerprints.md`。

## 网络层（CF/WAF 后自建面板的访问）

- CF 挑战（Just a moment）挡直连时：真实浏览器（playwright + Tor）过挑战后**页内 fetch** 打 API（凭据放请求头）；
- 判断封禁维度：直连/浏览器/curl_cffi（浏览器 TLS 指纹）全 403 → 按 IP/地区封，换出口（Tor 轮换）而非换指纹；
- CF 1015 限速触发 = 该出口被拉黑，`NEWNYM` 换出口 + 降速；
- XFF 随机化（每请求一个新 IP）可绕“按 XFF 计数”的限速器（固定 XFF 会很快进洞）。

## Support files

- `references/oss-cases-2026-10.md` — 四个案例细节（temp-mail 全关 / RenewHelper 单口令 / Kite 改密 / dev 模板默认值）。
- `references/openmetadata.md` — OpenMetadata 1.x 管理面实战：系统配置探测 → 自注册 → Base64 登录坑 → 读面（services hostPort / apps 全量 JWT）→ JSON-Patch 提权 → 人类号 PAT → admin 未 mask 凭据 → testDestination SSRF 内网探针。
- `references/airflow.md` — Airflow 3 管理面实战：/auth/token 登录、connections/variables 枚举与名字型掩码、事件日志挖凭据、dev/prod 双实例与凭据复用。
- `references/service-fingerprints.md` — 自部署服务指纹速查：Grafana（/metrics 作 CVE 适用性判定器 + edition 判定）/ Headscale（Tailscale 控制面，拿 key=整个内网）/ PostHog（摄入端未鉴权）；含 token 前缀对照（glsa_/phx_/tskey- 等）与「门在 API 层」时的应对。
- `references/metabase.md` — Metabase 凭据到手后的全量取数链：/api/session 登录、权限旗标（native 被禁≠读不了）、/api/database/{id}/metadata 全仓 schema、现成卡片直跑、**自建卡 + /query/csv 导出（1M 行硬顶 → 数值 ID 区间分段取全表）**、MBQL 结构化查询、聚合口径、建卡 description 非空坑、截断片再细分、全量可行性速算、删卡清理。
- `references/internal-panel-chains.md` — 内部运营面板链（自研 CRM/后台）：弱口令后台 → `/backup/list+download` 全库下载 → 配置表明文密钥（Slack/ClickUp/Resend 等）→ SaaS 文档库凭据档案（wiki “Accounts” 页）→ BI → 数据仓库；含慢磨纪律与收尾清理。
- 市售 IM 产品 **pop_im / 音信**（Workerman+uni-app；错误泄露 `/www/wwwroot/pop_im/`、JWT issuer `wks-webman-chat-admin`）指纹与全链 → 见 `chinese-private-im` → `references/popim-yinxin-im.md`。

## Pitfalls

- 版本 ≠ 漏洞：读到源码后用**行为**确认（状态码/错误体），不要拿源码里的函数名当已打点。
- 仓库 README 里的样例口令（如 `ADMIN_PASSWORDS=["123","456"]`、`ruoyi/123456`）值得各试一发，之后即停。
- 镜像部署可能共用同一 DB（一个 SQLi 能读另一个域名数据）——发现镜像后交叉验证。
