<!-- archived from /root/.hermes/skills/security/supply-chain-infra-hop/SKILL.md on 2026-10-21 -->

---
name: supply-chain-infra-hop
description: 主站加固打不动就打供应商运维栈(Gitea/Harbor/ES)→日志库拖库。
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, supply-chain, vhost, gitea, harbor, elasticsearch, kibana, minio, logstore, data-exfil]
    related_skills: [admin-console-discovery, docker-image-extraction, cloud-credential-leak-exploitation, middleware-unauth-family, recon-discriminators, vcs-repo-exposure, userdata-grab]
---

> 归档卡：原目录 `/root/.hermes/skills/security/supply-chain-infra-hop`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/supply-chain-infra-hop/…')`，不要相对 `references/legacy/` 解析。

# 供应链横切：应用面打不动，去打供应商的运维栈

## When to Use

- 主站应用侧已穷尽(SQLi/IDOR/竞态/JWT/回调/路径/Host 全阴)，而交付诉求是**数据**不是"打穿这台站"
- 目标形态是**规模化运营体**(账号工厂/发卡/接码/白标/代付)⇒ 一定有代码库、镜像库、日志库、监控
- 同一 IP 上挂着多个 vhost(产品站 + 后台 + 仓库 + 镜像 + 日志)

一句话：**应用是壳，运维栈是仓；要的数据在日志库里，不在业务库里。**

## 核心链(四段，每段都有只读产物)

```
A 横向找门   同IP vhost 枚举 → 挖出运维栈        (判据复用 recon-discriminators §1)
B 逐个只读   Gitea / Harbor / ES-Kibana / MinIO / Uptime / 自研 → 各自能出什么
C 凭据回灌   镜像内配置 / 厂商公开仓库配置 / 员工默认口令 → 交叉复用，不爆破
D 落数据     日志库接管 → 按字段锚定拖业务数据
```

纪律：B 段全程只读(pull / `_search` / 浏览)；写动作(push 镜像、改仓库、调运维停机口)一律不做，
只记录"可调用未调用"。

## A. 横向找门(成本最低、收益最高)

- 裸 IP + `Host:` 头逐词打；词表 = 英文 5000 + **中文拼音 470**(`gongju/git/hub/es/kb/up/oss/ip/tools/yun/monitor/pan`)——
  中文团队自建运维服务的子域几乎全是拼音或缩写，纯英文词表挖不到。
- 判定标尺 / catch-all vs `return 444` 型 / 泛域名证书下 CT 全盲 —— 照 `references/vhost-infra-enum.md`
  与 `recon-discriminators` §1，别重造。
- 关键信号：扫到 **git / hub / es / kb / up / oss / ip** 这一组名字 = 你打到的是**运维栈**，不是业务站。

## B. 七个门各自能出什么

| 服务 | 只读判据 | 能出什么 |
|---|---|---|
| Gitea | `/user/login` + `/api/v1/version` | 员工口令(团队默认口令复用) → 内部仓库 + 厂商框架源码 |
| Harbor | `/api/v2.0/projects`(另试 `/api/v2.0/search`，给得更全) | public 项目 → 匿名 pull 镜像 → 部署态配置 + `.pdb` |
| Elasticsearch | `401` + `security_exception` | 集群凭据 → 全量日志拖库 |
| Kibana | 与 ES 同口令 | 可视化确认索引名/字段名(省猜字段) |
| MinIO | `/minio/health/live`、S3 XML 错误体 | 桶可读 → 业务导出物 |
| Uptime Kuma | 登录页 | 内网主机清单 + 时区(指纹) |
| 自研 IP 归属/QQWry 服务 | 公开 | 内网网段与出口 |

逐项命令、指纹、"拿到后第一件事"见 `references/vendor-infra-service-matrix.md`。

## C. 凭据回灌(先读出来，不要先猜)

性价比顺序：镜像内 `AdmSettings.json` / `SeedData/*.json` > 厂商公开仓库 `appsettings.*.json` >
员工口令跨服务复用 > 日志里未打码的 URL(bot token / webhook)。

**厂商把生产连接串提交到公开仓库是产品线通用缺陷** ⇒ 同一厂商/同模板的其它站点共享同款默认配置与默认密钥，
一把凭据可以横向打一整个产品线。方法与口令派生反推见 `references/vendor-repo-credential-mining.md`。

## D. 落数据：日志库拖库

日志索引常把**全量 API 流量**(`requestBody`/`responseBody`/`headers`)落库 ⇒ **等同数据库镜像**，
比打业务库短得多，且明文口令/JWT 一并到手。流程、多栈迁移矩阵、去重对账见 `references/logstore-dump.md`。

## 厂商框架级后门(.NET Furion / NetAdmin 系)

硬编码 `GlobalStatic.SecretKey` = **万能验证码** + `/probe/exit|offline?token=` **运维停机口** + AES 密钥；
`#if DEBUG` 另有 `8888` 后门；`AdmSettings.json` 带默认 JWT/验证码密钥。
打**同栈**站点可直接复用；目标未沿用默认值(端点 404 / 伪造 401)就立刻写"厂商侧缺陷、目标不适用"，别反复试。
见 `references/netadmin-furion-stack.md`。

## Pitfalls

- **主站穷尽 ≠ 无路**。应用加固只证明"应用写得好"；运维栈常是完全另一拨人建的，配置水准差一个数量级。
- **打到 ES/Harbor 不等于交付**。证据必须来自业务字段(账号/订单/流水/资金)，集群健康 JSON 不是成果。
- **日志响应体常被截断/转义/按天分片**。不许用"字段没看见"推断"数据没有"；先枚举 `_cat/indices` 全量索引。
- **内网地址在源码里 ≠ 能连**。`172.16./8.x.x.x:5858` 常年 filtered；先在**能到的资产**上试凭据复用(ES/MinIO/Redis)，别在防火墙前耗。
- **只读边界写进报告**：哪些接口调用过、哪些只记录未调用；碰过的业务对象(异常订单等)单独列教训。
- **接手别人报告**：把每条"已验证"当待验证假设，差分复现过再引用。

## 支持文件

- `references/vhost-infra-enum.md` —— 同 IP vhost 枚举：拼音词表、七门命名、批量命令、判据交叉引用
- `references/vendor-infra-service-matrix.md` —— Gitea/Harbor/ES/Kibana/MinIO/Uptime 逐服务探测与只读产出
- `references/vendor-repo-credential-mining.md` —— 厂商公开仓库/镜像挖生产凭据 + 口令派生反推
- `references/logstore-dump.md` —— 日志库接管拖库(ES/Kibana/ClickHouse/Loki/SLS) + 字段锚定 + 去重对账
- `references/netadmin-furion-stack.md` —— .NET9+Furion NetAdmin 框架族主密钥/后门/默认钥利用卡
- `references/gmail168-account-shop-case.md` —— 账号商城案例(脱敏)：完整链 + 死路清单 + 复现命令
