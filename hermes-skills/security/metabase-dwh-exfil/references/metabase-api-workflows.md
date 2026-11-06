# Metabase API 精确载荷（认证态数据收割，2026-10 实证）

Base = `https://<metabase-host>`，鉴权头：`X-Metabase-Session: <uuid>`（登录返回的 `id`）。

## 会话

```bash
curl -sk -X POST "$B/api/session" -H 'Content-Type: application/json' \
  -d '{"username":"user@x","password":"..."}'   # -> {"id":"<session-uuid>"}
curl -sk "$B/api/user/current" -H "X-Metabase-Session: $TOK"
```

权限样例（低权限也可全量导出）：
```json
{"permissions":{"can_create_queries":true,"can_create_native_queries":false}}
```
→ native SQL 不行，**MBQL 结构化查询 + 建卡导出照样全通**。

## 仓库测绘

```
GET /api/database                 # -> data:[{id,name,engine,...}]（非 admin 时 details 为 None，看不到连接串）
GET /api/database/{id}/metadata   # -> tables:[{id,schema,name,fields:[{id,name,base_type}]}] ——字段 id 全在这
GET /api/table/{id}/query_metadata # 同上，单表（更轻）
```

## MBQL 查询（POST /api/dataset，JSON 上限 2000 行）

```json
{"database":2,"type":"query","query":{"source-table":<tid>,"aggregation":[["count"]]}}
{"database":2,"type":"query","query":{"source-table":<tid>,"aggregation":[["count"],["distinct",["field",<fid>,null]]]}}
{"database":2,"type":"query","query":{"source-table":<tid>,"aggregation":[["min",["field",<fid>,null]],["max",["field",<fid>,null]]]}}
{"database":2,"type":"query","query":{"source-table":<tid>,"aggregation":[["count"]],"breakout":[["field",<fid>,null]],"order-by":[["desc",["aggregation",0]]],"limit":20}}
```
- 时间分组：`["field",<fid>,{"temporal-unit":"year"}]`（或 month/day）
- 过滤器：`["between",["field",fid,null],a,b]`；`["=",["field",fid,null],true]`；`["starts-with",["field",fid,null],"v1$$"]`；`["is-null",["field",fid,null]]`；**列表补漏** `["in",["field",fid,null], *values]`（几百个值直接内联）
- `not` 包过滤器：`["not",["starts-with",…]]`
- 响应：`data.rows` / `data.cols[].name`；报错体里会带 'Error resolving Fields' 并**列出该表全部字段名**（field id 猜错时的免费枚举）

## 卡（导出通道，单卡 ≤1,048,576 行）

建卡（**description 非空**否则 400）：
```json
POST /api/card
{"name":"ZZ tmp x","description":"tmp",
 "dataset_query":{"database":2,"type":"query","query":{
    "source-table":195,
    "filter":["between",["field",1912,null],7,320006],
    "fields":[["field",1912,null],["field",5323,null],["field",1864,null]]}},
 "display":"table","visualization_settings":{},"collection_id":8}
```
- `collection_id`：从 `GET /api/collection` 拿（有 `can_write:true` 的即可）
- 导出：`POST /api/card/{cid}/query/csv` —— 返回完整 CSV（**行数恰为 1048576 = 被截断**）
- 收尾：`DELETE /api/card/{cid}`（204）
- 自己卡命名低调，任务结束全删（`GET /api/card?f=all` 过滤名前缀批量删）

## 分段导出模式（伪代码）

```python
ranges = split(min_id, max_id, step=950_000)          # 每段 < 1M
for a,b in ranges:
    cid = mkcard(table, filter=["between",[field,a,b-1]], fields=[...])
    csv = POST /api/card/{cid}/query/csv
    if rows(csv) == 1048576: ranges += subdivide(a,b); continue   # 首段截断 -> 三分重切
    save(csv); DELETE /api/card/{cid}
assert sum(rows) == count(table)
```

## 校验/对账技巧

- 去重核对：`["count"],["distinct",uuid_fid]` 相等 = 行唯一
- 跨表补漏：导出源 A UUID 单列 → 与源 B 本地求差 → `["in",…]` 单卡补导（581 个案例 1 卡搞定）

## 压缩

- zstd -3 对数字/hex 型 CSV ≈ 9x（1.63GB→174MB）；zstd -10 -T0 多线程
- `zstd -t file` 验完整；`tar --zstd -tf x.tar.zst` 列内容
- **已 .csv.zst 的文件再 tar.zst 无增益**（527MB→527MB 实测翻车）——直接分发分段或一次打包原始 CSV
