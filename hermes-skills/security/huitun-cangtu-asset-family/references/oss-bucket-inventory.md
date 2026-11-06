# OSS/S3 桶盘点与读取的通用坑（含归档解冻）

## 1. 归档对象列得出、读不了（InvalidObjectState）
`ListObjects` 会把 **Archive / ColdArchive / DeepColdArchive** 存储类型的对象照样列出（键名、大小都对），但直接 `GetObject` 返回：

```
403 InvalidObjectState  The operation is not valid for the object's storage class
```

⇒ **不是权限问题，是存储类型未解冻**。别误读成「策略不允许读该对象」而放弃整桶。

处置：
- `head_object` / 桶信息看 `x-oss-storage-class` / `StorageClass`；
- 读前必须 **RestoreObject（解冻）**：Archive 标准解冻约 1 分钟，加急/Bulk 档不同；ColdArchive / DeepColdArchive 是小时级；
- **解冻计费且不可逆（会通知桶主）** ⇒ 批量解冻前先算账，优先挑最小对象验证格式与可读性；
- 先统计整桶 storage class 分布再决定解冻范围（很多桶只有部分前缀是归档）。

**同一 STS、同一桶可混装多种存储类型**：实测同桶同前缀下 `yyy.zip`（标准）直接 GET 成功，而 `*.sql.gz` 报 InvalidObjectState。⇒ **一个对象下载成功 ≠ 整桶可读**，按前缀/存储类型分别判定。

## 2. 用键结构当情报，比下载更快定性
备份类桶的键名本身就是覆盖面证据，无需下载即可得结论：
```
<backup-id>/full/<snapshot>/datamove/<db>/<table>/<part>
```
`ObjectIterator` 聚合（按 `<db>.<table>` 计数＋累加 size）⇒ 一次列桶就得到「表 × 分片 × 体量」全表清单，直接回答「全库能不能拿」。
同理：`<rds-instance>.mysql.rds.aliyuncs.com:3306/`、`实例N/`、`pc-*/`、`sls_log/<service>/` 这类目录名可直接映射到内网 RDS / PolarDB / 微服务，用于测绘。

## 3. 列举要防超时
百万级对象的桶全量 `ObjectIterator` 会跑十几分钟以上（工具侧/会话超时）。做法：
- 用 `delimiter="/"` 逐前缀列举（快，能立刻拿到顶层结构）；
- 需要精确总量/大小时把脚本 **detach 到远端跑**（`setsid nohup ... > log 2>&1 &`），本地只轮询 log，并设**硬上限**（如达到 cap 个请求即打印 TRUNCATED）；
- 已知大盘的桶优先复用既有清单文件，不要重复扫描。
