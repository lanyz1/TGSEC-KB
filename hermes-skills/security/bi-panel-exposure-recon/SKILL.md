---
name: bi-panel-exposure-recon
description: "Use when an exposed BI panel (Metabase, Superset) is found."
---

# 暴露的分析面板（BI）快速定性与封堵判定

适用：扫到 3000/8088/3001 之类端口，返回 SPA + `metabase.DEVICE` / `superset` 字样的服务。这类面板的价值不在自身漏洞，而在**它手里有生产库的数据源凭据**——它是到达整库的最后一段，不是终点。

## 三步定性（不要先找 exploit）

### 1. 指纹（一条 curl 就够）
```
curl -sS -i http://IP:3000/api/health
curl -sS -i http://IP:3000/api/session/properties
```
- `Set-Cookie: metabase.DEVICE=…` → Metabase
- `/api/health` 返回 `{"status":"ok"}`（无需鉴权）→ 服务活着
- 版本从 `/api/session/properties` 的 `version.tag` / 前端 `app-*.js` 取，**不要用首页 HTML 判断版本**

### 2. 取判据（唯一高价值未授权端点）
`GET /api/session/properties` 在多数版本无需鉴权，返回全量站点属性。只提取：
- `version`（定 CVE 面）
- `setup-token`（是否泄露——**泄露≠可用**）
- `has-user-setup` / `site-name` / `enable-embedding` / 公开分享相关键
把 token 与 rest 落盘但**脱敏外报**，不写入报告正文。

### 3. 判定表（照表下结论，不要探索性乱打）

| 响应 | 含义 | 下一步 |
|---|---|---|
| `POST /api/setup` → `已初始化 / already been set up` | 实例已建首个管理员，setup-token 是死资产 | **放弃 setup 路线**，转找账号 |
| `POST /api/setup/validate` 同样被拒 | CVE-2023-38646（<0.46.6）一类 setup 链全部失效 | 同上 |
| `setup-token` 存在且 `has-user-setup=false` | 真·未初始化 | 可在授权范围内建首个管理员→加数据源→读库 |
| `/api/user/current` → 401 `Unauthenticated` | 无匿名会话 | 需凭据 |
| `/api/dashboard` / `/api/card` → 401 | 无公开分享面 | 需凭据 |
| `/api/public/card/<uuid>` → 200 带数据 | 公开分享开着 | 直接读分享的查询结果 |

**版本 ≠ 漏洞**：1.48+ 已修 setup 链与 H2 注入，拿着 setup-token 反复试 `/api/setup/validate` 是纯浪费。判定「已初始化」就停。

- **schema 校验先于状态检查，400 不等于入口可用**：空 body 打 `POST /api/setup` 会回「email 必须是有效邮箱」，看着像入口活着；补齐结构合法的 body（假值即可）后才回 403「只能用来创建第一个用户」。判「能不能用」必须发一次字段齐全的 body，否则会把死入口误判成活入口。
- **setup-token 不能当会话用**：塞 `X-Metabase-Session` / `Authorization: Bearer` / cookie 打 `/api/user/current` 全是 401，别在变形上耗时。

## 拿到账号之后（才是真正价值）
顺序固定：`/api/database` 列出数据源（含主机/库名/用户）→ `/api/database/<id>` 看详情 → `POST /api/dataset` 跑 `SELECT`。
- 生产库常与 Web 应用同机内网，面板上的连接串直接给出 MySQL 主机与账号
- 只读 `SELECT count(*)` / `SELECT * LIMIT n`，不做写操作
- 面板账号体系与业务后台账号**不共用**：业务后台用户名不能直接拿来登 Metabase，反之亦然

## 找账号的唯一有效入口
Metabase 登录必须邮箱+密码，**用户名枚举与手机号都不适用**。有效材料只有：
1. 员工邮箱格式（从邮件、工单、代码仓库、错误页线索推）
2. 密码复用（业务后台/Grafana/Jenkins 同套口令）——默认口令尝试 ≤ 3 组
3. 面板自身的应用库（H2 文件 / Postgres）——需要先有另一条读文件或库的口子
拿不到就如实记「面板存在、版本 X、setup-token 泄露但不可利用」，**不要把它写成 getshell**。

## 顺带的侧信道
应用侧报错 `no such index [x]` / `Unknown database` 会直接暴露**它连的是哪个数据层**：同一套业务的两个入口报不同索引名，说明它们不是同一个 ES/库。这条比扫端口更快定位「线上真库在哪」。
