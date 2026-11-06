---
name: app-metrics-api-surface-recon
description: "Use when an app's own /metrics leaks its route table."
version: 1.0.0
license: MIT
platforms: [linux, macos]
tags: [metrics, 零鉴权, API面, 路由重建, health, actuator, ASP.NET Core, Prometheus, 接口清单]
---

# 业务自带 /metrics → 完整 API 面重建

> 业务服务自己开的 `/metrics`（不是 Prometheus/Grafana，是应用同端口上的那个）默认零鉴权，
> 而它给每条 HTTP 路由打了 **controller / action / route 标签** —— 这不是指标，这是**后端接口清单**。
> 一次 curl 拿到全站 action 名（含前端从不调用、文档里没有、目录爆破扫不出的隐藏接口），
> 成本比 fuzz 低一个量级，命中率高一个量级。

## 触发

- 业务端口直接回 Prometheus 文本格式（`http_request_duration{...}` / `*_requests_total{route=...}`）；
- ASP.NET Core 的 `/health` 回连接池清单；Java 的 `/actuator/metrics`、`/actuator/mappings` 可读；
- 已经拿到一个业务节点但 API 文档缺失，正在考虑目录爆破 / JS 挖接口 —— **先做这个再 fuzz**。
- 多节点同代码部署（一 IP 一域名一节点）时，每个节点各拉一遍。

与 `monitoring-plane-unauth-recon` 的区别：那张卡打的是**运维监控栈**（Prometheus 9090 / Grafana 3000 / exporter），
拿拓扑与库凭据；本卡打的是**业务应用自身的可观测端点**，拿 API 面。两者常同时存在，各拿各的。

## 第 1 步：dump 落盘，按 label 归集

```bash
curl -sk -m 60 https://<node>/metrics -o m_node.txt
wc -c m_node.txt                     # 实测常见 0.9–1.1 MB
```

**别在 stdout 里灌全量**，落盘后按标签聚合：

```python
import re, collections
routes = collections.Counter()
for line in open('m_node.txt', errors='replace'):
    m = re.search(r'route="([^"]+)"', line)
    if m: routes[m.group(1)] += 1
for r, n in sorted(routes.items()):
    print(n, r)
```

也把 `controller=` / `action=` / `endpoint=` / `method=` 各自 grep 一遍 —— 不同插件的标签名不一样，
有的只打 `route`，有的分开打 `controller` + `action`。**独立出现的 `action=` 往往比 `route=` 更全**。

一次能拿到的字段：controller 名、action 名、真实 route 字符串、HTTP 方法、状态码分布、延迟直方图。

## 第 2 步：把 `route=` 重建成可打的 URL（★三个坑，全部实测咬过人）

### 坑 1：大小写不一定能直接拼
框架层通常不区分大小写，但**实际部署可能按字面字符匹配**：

```
GET /api/VipUser/GetConfigByStyle   -> 404
GET /api/vipuser/GetConfigByStyle   -> 200   ← controller 段全小写才通
```

⇒ 每次拼测**两种形式都打**：`route=` 原文，和「controller 段强制小写」。
同一家族里不同节点可能不一样，别拿一个节点的结论套另一个。

### 坑 2：`route=` 里的 `{x}` 是路径参数，不是装饰
`Manage/GetAppVersion/{version}` 这类必须把值填进去；空着或当查询参数打都回 404/422。
先把模板里的 `{...}` 列出来，逐个给一个类型正确的值。

### 坑 3：同一个 action 可能只吃一种方法
实测同一批脚本 POST 全 405、改成 GET 全 200（`GetByImageType`、`GetFinancialVipUserDetail/{x}` 一类）。
⇒ **每个 action 跑一遍 GET + POST 两种载体**，别用一种的结果断言「接口不存在」。
405 和 404 要分开记：405 = 路由在、方法错，这是**正向信号**。

## 第 3 步：`/health` 当库拓扑图

ASP.NET Core 的 `/health` 零鉴权时直接列**连接池名**：

```
ActiveSystemAuthDb / ActiveSystemLogicDb / LoginLogConnection / ...
```

读法：池名 → 这服务管几套库、哪套是认证、哪套是业务、有没有独立登录日志库。
连接串本身常被剥掉密码，只剩 `Server=` / `User ID=` / `Port=` / `Database=` —— 也够定内网库地址（常是 172.16/10.x 私网）。
拿到私网库地址后下一步是找 SSRF 落地，不是硬连（见 `ssrf-verification-and-escalation`）。

## 第 4 步：多节点取并集

同代码多节点部署时**路由数量会不一样**（实测同一个站：一个节点 101 条、另一个 71 条）。
逐个 dump、取并集，才是完整 API 面。少拉一个节点就可能漏掉整组 action。

## 第 5 步：逐条打鉴权状态

**`route=` 存在 ≠ 零鉴权。** route 表只证明路由挂了，鉴权是另一回事：

- 先按「名字像零鉴权的」优先打：`GetConfig*` / `GetAppVersion` / `GetPaymentMethodConfig` / `GetStyles*` / `Get*List`
- 再打「名字像高危的」：`Register` / `Login` / `BindPhone` / `ChangePwd` / `DisableAuthenticator` / `SendMessage`
- 剩下的按 controller 分组批量打，记录状态码分布（401/403/200/5003）

错误码族本身是信息（实测一套站：`1001` 服务器异常、`1002` 参数校验、`1004` 数据不存在、`1041` 版本太旧、`3001` 账号密码错、`5003` 登录过期）。
**先建立错误码字典，再解释结果** —— 不然会把「参数错」误判成「无权限」，把「版本闸」误判成「接口死」。

## 高价值 action 名先验（拿到 route 表先扫这几个词）

| 关键词 | 为什么值钱 |
|---|---|
| `Register` / `OneClick` / `LoginRegister` | 注册口常无验证码、无频率限制 |
| `BindPhone` / `ChangePhone` / `ChangePwd` | 只认 token 里的身份时 = 账号接管面 |
| `DisableAuthenticator` / `EnableAuthenticator` | 2FA 开关，改名不验旧凭据就是接管 |
| `SendMessage` / `SendCode` | 短信口 = 短信轰炸 + 验证码 oracle |
| `GetConfig` / `GetAppVersion` / `GetStyle` | 常零鉴权，泄全租户配置与下载地址 |
| `Export` / `Backup` / `Download` / `GetReport` | 直接数据出口 |
| `InviteCode` / `Subordinate` / `Promotion` | 代理/推广树，越权重灾区 |

## 坑

- **别把 `/metrics` 里出现过的 action 写进报告当「已发现接口」**：只证明路由注册，不证明可达。
  报告口径写「路由表存在，鉴权状态如下表」。
- **别用单个节点的 route 表当全家族结论**：多节点取并集（第 4 步）。
- **404 有三种原因**：路径前缀错、大小写错、controller 未在该节点注册。按这个顺序排除，别一上来就换接口。
- **指标正文里可能夹凭据**：连接串、`pool_name=`、job label 里的 DSN。grep `Server=` / `User ID=` / `Password=` / `key=` 一遍再走。
- **零鉴权 `/metrics` 本身也是拒绝服务面**：只做小范围读，别把对方 metrics 当自己的数据源跑聚合。

## 支撑文件

- `references/pay-family-metrics-case-20261029.md` — 一次完整实战：101 条路由的隐藏 action 清单、大小写 404 实录、多段登录状态机。
