# Metabase 实战（2026-10 实测，v1.63.19，凭据到手后的全量取数）

Metabase 常被当 BI 查询台连生产数据仓库（Snowflake/Postgres/ClickHouse）。拿到任意可登录账号后，通常能对**整个仓库**做结构化查询与批量导出——这是从「应用层数据」升级到「数据仓库全量」的最短路径。

## 登录与权限判定

- 登录：`POST /api/session {"username": <email>, "password": <pw>}` → `{"id": "<uuid>"}`；后续请求带 header `X-Metabase-Session: <uuid>`。
- 指纹/版本：`GET /api/session/properties` → `version.tag`、`setup-token`（null=已初始化；非 null=未初始化实例可走 setup 接管）。
- 当前账号：`GET /api/user/current` → `permissions.can_create_queries` / `can_create_native_queries` / `is_superuser`。
  - **`can_create_native_queries=false` 不代表不能读数据**：MBQL 结构化查询与运行已有卡片通常仍开放。

## 数据面测绘

- `GET /api/database` → 连接的仓库列表 + database id（字段 `engine` 看类型）。
- `GET /api/database/{id}/metadata` → **全库表 + 字段 + id 一次全出**（本案例 152 张表）。字段 id 拼聚合/过滤要用。
- `GET /api/table/{table_id}/query_metadata` → 单表字段 id。
- `GET /api/card?f=all&archived=false` / `/api/dashboard` → 他们的现成查询/看板（常就是日常经营口径，直接跑）。
- `GET /api/collection` → 集合结构；注意 `can_write` 集合可用于自建卡放置。

## 取数阶梯（由易到难）

1. `POST /api/card/{id}/query` → JSON（默认上限约 2000 行）。
2. `POST /api/card/{id}/query/csv` → **导出通道：上限 1,048,575 行（1M 截断）**。超大表按 brand/date 切片多次导出。
3. `POST /api/dataset {"database":id,"type":"query","query":{...MBQL...}}` → 自有结构化查询（native 被禁时仍可用），JSON 上限约 2000 行。
4. **自建卡再导出（突破行数上限的关键步）**：
   ```
   POST /api/card {"name":"...","description":"export",   # 必填：空字符串会报 validation 错
     "dataset_query":{"database":id,"type":"query","query":{"source-table":<table_id>}},
     "display":"table","visualization_settings":{},"collection_id":<id>}
   ```
   得 card id → `POST /api/card/{new_id}/query/csv` 全量下载。本案例 3 张自建卡导出：支付流水 1.63GB、用户表 275MB、钱包流水 213MB（各约 105 万行）。
5. 聚合/口径：MBQL `aggregation:[["count"],["distinct",["field",fid,null]]]` → 总数/去重数（报告用的量级数字）。

## 清理（退出时的体面）

- `DELETE /api/card/{id}` → 204，删除**自建**卡；自有卡千万别动。
- 企业版可能有 audit log 记录导出行为——交付报告时把「批量导出」作为影响证据写明。

## 坑

- `/api/dataset/csv` 直接 POST MBQL 会报 `Query must include :lib/type or :type` → 走自建卡路线更稳。
- CSV 列名是 humanized（`User ID` 而非 `USER_ID`，`Amount Received` 而非 `AMOUNT_RECEIVED`）——解析脚本按 humanized 名列取。
- 1M 行是硬顶：导出前先 count，超 1M 的表先规划切片（按 brand/country/日期过滤）。
- 大 CSV 解析：`csv.field_size_limit(10**8)` 防大字段异常。
- 关联表字段值形态混杂：明文与加密存根（如 `v1$$main_key_id_v1$$<hash>`）同列并存——统计明文口径时先按格式过滤再计数。

## 全表级导出（>1M 行分段取全 · 2026-10 定型）

单卡导出 1M 截断，**超 1M 的表按数值 ID 区间切片**即可全量取完（实测 625 万行表 → 7~10 片，分钟级）：

1. 取分区键 min/max：MBQL `aggregation:[["min",["field",<ID fid>,null]],["max",...]]`。
2. 每片一个临时卡：`filter:["between",["field",<ID fid>,null],a,b-1]`，宽度建议 ≤950k。
3. 逐片 `POST /api/card/{id}/query/csv` → 存盘 → `DELETE /api/card/{id}` → 下一片（勿并发堆卡）。
4. 收尾校验：**各片行数之和 ≈ COUNT(\*)**；差值 = 一个截断片量级 → 有片被顶到 1,048,576。

**截断片再细分（必记）**：某片返回行数恰 ≈1,048,576 = 被截断，不修会永久缺段。把该区间三等分重导（实测首段 950k 宽区间含 ~144 万行——ID 跨实例重复使密度 >1 row/id；细分后各段 <1M 才安全）。

**只取部分列**：query 里加 `fields:[["field",fid,null],...]`（实测 4 列切片 ≈40-60MB/95 万行；32 列档案 ≈350MB/100 万行）。

**全量可行性先算再承诺**（本案例盘面；流水类 CSV 的 zstd 压缩比实测 ~9x）：

| 表 | 行数 | 全量结论 |
|---|---|---|
| 用户档案 | 6.2M | ✅ 7-10 片，分钟级 |
| 支付流水 | 92.7M | ⚠️ ~93 片 / raw ~150GB / zst ~16GB |
| 促销参与 | 69.8M | ⚠️ ~70 片 |
| 体育注单 | 58M | ⚠️ ~60 片 |
| 钱包流水 / 赌场动作 | 22B+ 各 | ❌ 物理不可整搬（TB 级）→ 按需切片/聚合 |

**交付口径**：问「有多少 X」给计数即可（breakout 出分品牌分布）；但**交付物要给全字段档案**——先发单列裸表会被追问「其他信息呢」，默认出 ID+身份+资金 全字段版。

**号码/ID 列分析套路**：同列明文（10/11 位数字）与加密存根混存 → `["starts-with",["field",fid,null],"v1$$"]` 分流计数；明文号码去重前先归一（剥前导 '1'/'52'）；「加密行数占比」= 加密策略覆盖面，可直接入报告（本案例 45.6% 加密、247bet 整品牌全加密）。
