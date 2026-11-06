---
name: monitoring-plane-unauth-recon
description: Use when 目标开 Prometheus/Grafana/exporter 面. 零鉴权取数+拓扑.
tags: [grafana, prometheus, 监控面, 默认口令, 弱口令, grafana默认口令, 未授权取数, exporter]
---

# 监控面未授权：从指标栈拿宿主拓扑与库凭据

> 监控栈是**运维给自己开的免鉴权后门**：Prometheus 默认无认证、exporter 默认无认证、Grafana 的 `/api/health`
> 与 `/metrics` 常漏在鉴权外。它不直接给 shell，但能一次性交出**内网拓扑 + 库身份 + 写马路径**。
> 发现任意一台主机开着 `9090/3000` 或 `9100/9104/9113/9187/9121`，先按本卡榨干读面，再谈登录面。

## 触发

- 端口/指纹命中 Prometheus(`9090`)、Grafana(`3000`)、Alertmanager(`9093`)、exporter 族；
- 响应里出现 `grafana_build_info` / `prometheus_build_info` / `node_exporter` 字样；
- 已经在打一个 Docker 化业务栈，想找侧向的读面（业务站打不动时性价比最高的第二面）。
- **业务面是加固/二开私有分支时更要先摸监控面**：加固者会把应用层收干净（参数化注入、外联收口、无文件写原语），
  却几乎不动运维栈 ⇒ 读面常常是**唯一还在漏**的出口（见 `hardened-fork-recon`）。
- **`9090` 常只在源站/内网侧开放**：从本机探到「未开放」不等于没有 —— 换出口复测（见 `ip-ban-bypass` §3c）；
  反过来，探到就把 targets 当**靶单**：加固版典型是「SSRF 只拒公网 HTTP、明放私网 HTTP」，靶单正好由 targets 给出。

判层/假阳性/负结论纪律不在本卡，见 `api-probe-layer-triage`；
**connect 成功≠端口开放**这条尤其致命，见 `probe-script-authoring` 扫面类探针第 8 条。

## 第一步：画像（每发都是零凭据、只读）

| 端点 | 拿到了什么 | 注意 |
|---|---|---|
| `GET :9090/-/healthy`、`/api/v1/status/buildinfo` | Prometheus 版本、启动时间 | 无鉴权也能过 ⇒ 这就是零鉴权栈 |
| `GET :9090/api/v1/targets` | ★**全部抓取目标 + 各 exporter 的真实内网 `IP:port` + 健康状态** | 内网网段、容器名、job 名一次到手 |
| `GET :9090/api/v1/status/config` | ★**抓取配置原文（YAML）** = 凭据产地：`basic_auth` 用户名/口令、DSN、`bearer_token_file` 路径 | `basic_auth` 说明 exporter 侧有口令；值可能被打码，但**用户名与 target 全露** |
| `GET :9090/api/v1/status/flags` | 保留期 `storage.tsdb.retention.time`、存储路径 | 判断这面有多久的指标纵深 |
| `GET :9090/api/v1/label/__name__/values` | 全指标名清单 | 用来找 `*_info`/`up` 类指纹指标 |
| `GET :9090/api/v1/query?query=up` | 哪些目标在跑、跑了多久 | 与 targets 交叉核验 |
| `GET :3000/api/health`（Grafana） | 版本 + 数据库状态，**常无鉴权** | 有的实例把 `/api/*` 整关在鉴权后，`/metrics` 却开着 |
| `GET :3000/metrics`（Grafana） | 数百 KB 指标：`grafana_build_info` 等 | 拿来验「真 Grafana 还是诱饵」 |

**exporter 端口表（去 `/api/v1/targets` 里逐个对上，别只记端口名）**：
`9100`=node（核数/内核/文件系统/内网网卡 = 最直接的主机画像）、`9104`=mysqld、`9187`=postgres、
`9121`=redis、`9113`=nginx、`8080`=cadvisor。

从 targets 一步得三样东西，直接进报告与下一步：**内网网段**（如 `10.0.x.0/24`）、**宿主 IP**、
**栈成分**（同宿主跑着 MySQL + Postgres + Redis + 网关 = 一条写马链的全部要素）。

## 从读面到 RCE 的路径（★推演，非本卡已验证结论）

零鉴权读面本身不是漏洞结论，它的价值是**缩短到 RCE 的距离**。两条常规去向：

1. **面板管理员口令 → 数据源代理执行 SQL → `SELECT … INTO OUTFILE` 写 webshell**。
   前提三条，动手前逐条核实，缺一条就换路：① 已配置 `mysql`/`postgres` 数据源（`/api/datasources`，需鉴权）；
   ② 库账号有 `FILE` 权限且 `secure_file_priv` 允许可写目录；③ 知道 webroot 绝对路径。
   拿不到 ②③ 时，**读库单独也有价值**（配置表里的 SYS_KEY / 密钥 / 管理员口令常在此）。
2. **抓取配置里的凭据复用**：`status/config` 的 `basic_auth`、exporter 连接串里的库口令，直接拿去打库/打面板。

**纪律**：写马、改库都是状态变更，属可逆性最低的动作 —— 动手前先答「能不能恢复」
（`INTO OUTFILE` 留下的文件、库里的改动），并向用户披露；用户未明确要求时，本卡只做到读面榨干 + 凭据到手。

## 登录面（面板）：口径与预算

- **锁口径先测**：同出口连发两发看是否触发锁定 —— 有的实例**无账号锁、只回 401**（可轮换出口慢打），
  有的是 per-IP 计数。判作用域（账号级/出口级/端点全局）的**单变量对照法**见 `api-probe-layer-triage`
  《登录门的第二道参数》，别在这里重推一遍。
- **默认口令先试一轮**再决定要不要靶向：`admin/admin` 是产品默认，改过再换靶向小列表。
- **匿名关（`/api/*` 全 401）不等于整面都关**：`/metrics`、`/healthz`、`/-/healthy`、`/api/health` 常是例外，
  先穷举这些**免鉴权子路径**，再谈登录。
- 面板版本号（如 `13.0.2`）拿到后去比对该版本的已知 CVE（路径穿越/插件加载/SSRF）—— 版本是免费的攻击面索引。

## 坑

- **别把 exporter 端口当「暴露的服务」写报告**：`/api/v1/targets` 列的是**内网**目标，内外网可达性不同；
  外网打不到的要写成「内网可见、外网不可达」，否则严重度虚高。
- **别只从 `up` 指标数服务**：`up=0` 的目标也在 targets 里，是「配置了但挂掉」，不是活服务。
- **指标正文可能上千 KB**：先落盘再分片 grep（`> metrics.txt` 后按需读），别在 stdout 里灌全量
  （见 `probe-script-authoring` 调用输出纪律）。
- **零鉴权 Prom 的 `query` 本身是可用性风险**：大范围 `rate()` 很吃内存，只发**小范围/单点**查询当探针，
  不要把目标 Prom 当自己的数据源跑重查询。
- **口令不是唯一进路**：`/api/health` 露版本、`/metrics` 露插件、`/public/plugins/*` 可读资源，
  都试完再回头补登录面。

<!-- abraxas-2026-10 -->
## 2026-10 Prometheus / Grafana 增量
- **Prometheus 3.15.0**: `remote_write` 的 google_iam/azuread 跨域重定向仍带 Bearer（凭据泄露）；`http_sd` 的 `__unix_socket__` 未净化 Dial（SSRF）。
- **Grafana 13.2.3**: Git Sync URLValidator 只在 admission 做 DNS（重绑定绕过）；SignUpStep2 无邀请码即加入 pending org（邀请接管）。

## Grafana Helm 默认口令 + Loki 单租户（2026-10 te-k8s 实锤）
- `admin:prom-operator`（chart 默认）直接进 → `/api/datasources` 拿 Loki uid → proxy 查全部 namespace 日志
- `auth_enabled: false` 时任何 `X-Scope-OrgID` 都能读；改密**不吊销**既有 session
- 日志明文打印 S3 AK/SK、TG Bot Token、SOCKS5 账密 → 见 `log-endpoint-secret-harvest`

## 缓存监控 = 会话与密钥金矿（2026-09 taskking 实战）
- 后台「缓存监控」页开 Redis 全命名空间 → 直接读到 14 个在线会话令牌 + 全部配置密钥明文
- 找法：`/monitor/cache`、`/system/cache`、`/admin/cache`、RedisInsight/Another Redis Desktop
- Redis 里重点 key：`login_tokens:*`、`session:*`、`*:token`、`sys_config`
- 判据：`KEYS *` 或监控页能列出业务 key（不是空白 demo）
