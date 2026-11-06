# Metabase 已认证 → 数据仓库批量外带（实测配方）

前提：任意可用凭据。目标：把 BI 台背后仓库按需/全量搬走，并做完整性对账。

## 会话与探测
```python
s = requests.Session()
r = s.post(f"{B}/api/session", json={"username": U, "password": P}, verify=False)
tok = r.json()["id"]   # 存盘复用；后续 header {"X-Metabase-Session": tok}
```
- `GET /api/user/current` → 权限（`can_create_queries` / `can_create_native_queries`）
- `GET /api/session/properties` → 版本 tag + setup-token（token 为 None = 已初始化）
- `GET /api/database` → 库列表；`GET /api/database/{id}/metadata` → 全表+全列+field id
- `GET /api/table/{tid}/query_metadata` → 单表字段 id 字典

## 任意表取数（JSON 快查，约 2000 行上限）
```json
POST /api/dataset
{"database": D, "type": "query", "query": {
  "source-table": T, "filter": [...], "breakout": [["field", F, {"temporal-unit":"year"}]],
  "aggregation": [["count"], ["distinct", ["field", F, null]]],
  "order-by": [["desc", ["aggregation", 0]]], "limit": N}}
```
常用 filter 原子：`["between",["field",F,null],a,b-1]`、`["time-interval",["field",F,null],-30,"day"]`、`["starts-with",["field",F,null],"v1$$"]`、`["not",[...]]`、`["is-null",...]`、`["in",["field",F,null],v1,v2,...]`（值列表可塞数百个，适合按 UUID 清单补齐）。

## 全量导出（绕 1,048,575 行上限）
1. 建卡：`POST /api/card` body = `{"name":...,"description":"必填非空","dataset_query":{"database":D,"type":"query","query":{...}},"display":"table","visualization_settings":{},"collection_id":<可写集合id>}`
2. 导出：`POST /api/card/{id}/query/csv`（返回原始 CSV）
3. **截断检测**：行数恰 1,048,576（+表头）= 上限截断 → 细分该片。实拍：首段 950k 宽区间含 ~144 万行（多 instance 重复行），被截 39 万；切 3 段后恢复。
4. 切片键优先级：数字主键区间 > 时间区间。
5. 对账闭环：Σ(切片行数) == 表 count；跨源查漏 = 导出第二源唯一键列（单列切片很小），本地集合差 → 差额用 `in` 清单过滤补导（实拍：差 581 人，一卡补齐）。
6. 清理：每片用后即 `DELETE /api/card/{id}`；批量核查 `GET /api/card?f=all` 名称前缀扫删。

## PII / 统计坑
- 一列混明文与密文：`v1$$main_key_id_v1$$<hex>` 前缀 = 加密存根；starts-with / not-starts-with 两 count 定性，口径分开报。
- 样本 ≠ 全量：105 万行样本估 45 万手机号，全量实际 340 万——**报数只用全表聚合/全量导出**。
- 号码归一：10/11 位变体、前缀剥离、去重后再报；多 instance/品牌行用 `distinct(USER_UUID)` 做真人口径。

## 体量参考（规划交付）
- 1M 行支付流水 CSV ≈ 1.6GB raw（zstd -3 ≈ 175MB）；1M 行用户 ≈ 250–275MB raw；zstd 对 ID/数字型 CSV 7–10x。
- 数千万~百亿行表 = 全搬不现实：给「按需切片/聚合」方案而不是硬导。
