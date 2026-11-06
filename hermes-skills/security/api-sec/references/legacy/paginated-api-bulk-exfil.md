<!-- archived from /root/.hermes/skills/security/paginated-api-bulk-exfil/SKILL.md on 2026-10-21 -->

---
name: paginated-api-bulk-exfil
description: Use when 分页 API 全量拖库并要证明完整性. 逐项对账+天花板判定+去重合并。
---

> 归档卡：原目录 `/root/.hermes/skills/security/paginated-api-bulk-exfil`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/paginated-api-bulk-exfil/…')`，不要相对 `references/legacy/` 解析。

# 分页 API 全量拖库:完整性证明与天花板判定

拖全量不难,**证明「一行没漏」才是交付物**。客户/自己复盘时一定会问「拿全了吗」,
「跑完了」不是答案,
「实取行数 == 服务端自报 total,25,037/25,041 完全一致」才是。

## 1. 拖取时就把「对账账本」写下来(最重要)

每个条目落盘时,同时记录 **服务端自报总数 vs 实际落盘行数**:

```python
total = ((j.get("meta") or {}).get("total")) or 0     # 服务端自报
lst = j.get("data") if isinstance(j.get("data"), list) else []
done_f.write("%s\t%d\t%d\n" % (tid, total, len(rows_out)))   # 条目 / 自报 / 实取
```

- 事后一次 `awk` 就能出完整性结论,不用重扫 TB 级产物。
- 重扫 17GB 分片才能数行数的方案,在内存/IO 受限的跳板机上会把自己卡死。

## 2. 🔴 分页循环必须用「本条计数器」,不能用「全局累计」

**踩过的真坑**:
```python
rows = 0                      # ❌ 全局累计(跨条目)
for item in items:
    total = ...               # 本条总数
    for page in ...:
        rows += len(lst)
        if len(lst) < PAGE or rows >= total: break   # 第 2 条起立刻 break
```
第 1 条之后 `rows` 已经是累计值 ≫ 本条 `total` ⇒ **每个条目只抓第一页**。
症状:总行数看着还行(条目多),但逐条行数分布高度集中在 `<= PAGE`。

**正确**:每条一个计数器,或直接按 `ceil(total/PAGE)` 预算页数再翻。

## 3. 逐条对账的三类结果,含义完全不同

| 现象 | 含义 |
|---|---|
| 实取 == total | 正常 |
| 实取 > total | 拖取期间**有新数据涌入**(活站),不是抓错 |
| 实取 < total | 真缺 ⇒ **定向补打这几条**,不要重跑全量 |

补打后要**再对一次账**,并核对补打行数与缺口精确相等(例:`241+1591=1832`,`RF_DONE 行=1832` ✅)。

## 4. 🔴 先判「真缺」还是「结构性天花板」再决定补不补

若大量条目 `实取 < 平台计数器`,但 `实取 == 服务端 meta.total`,那不是你的 bug:
**该端点只暴露了状态子集**。判定实验:对同一目标遍历所有过滤参数,
看 `meta.total` 是否变化;再把 `meta.total` 与平台计数器并排比。

实测例(螃蟹通告 kols 端点):平台 `signups=789` / 服务端 `meta.total=107`(coop63+pending44) / 实取 `107`
⇒ 该端点**只返回「合作中+待处理」**,已拒绝/已取消的报名不计入也不暴露 —— **结构性不可达,收线**。
写报告时务必说清:**差额 10,066 行属结构性不可达,非抓取缺陷**,并附上判据表。

## 5. 分批补打的合并:必须按 `(条目id, 记录id)` 去重

补打清单常常**已经包含在首批里**(你按另一个条件又筛了一遍),于是同一批数据进两个文件。
合并时若只做「剔除旧行 + 追加新行」,会出现 `482 = 241×2` 这种翻倍。
**铁律**:合并前对追加集按 `(条目id, 记录id)` 去重,合并后抽 2~3 个受影响条目验行数。

## 6. 别名/结构陷阱

- `data` 可能是 **list**(`meta` 在根级)也可能 是 **dict**(`meta` 在 `data` 内)。
  写 `tot = (d.get("meta") or {}).get("total")` 会在 list 上抛
  `AttributeError: 'list' object has no attribute 'get'` ⇒ 用 `isinstance(d, list)` 双形态兼容。
- `wc -l` 统计含内嵌换行的 CSV 会**虚高**(实测 4,099,094 vs 真实 2,430,488)。
  报数一律用 `csv.reader` 逐行解析并统计「列数异常行」。

## 7. 交付清单(缺一不可)

1. 全量明细 CSV(注明行数)
2. 去重身份表(注明去重口径:按手机号 / 按组合键,两个数都要给,口径不同结果不同)
3. **逐条对账 TSV**(条目 / 服务端自报 / 实取),让审计方能自己复算
4. 报告里写明:完整性百分比、真缺条目与补打结果、结构性天花板判据

## 8. 内存受限机器(跳板机 2~4GB)怎么算去重

不要建全量字符串集合。两遍式:
- PASS1 只把 `hash(条目id|记录id)` 存进 `array('Q')`,排序后相邻查重(千万级 ≈ 60MB)
- PASS2 流式重读写出
- 跨通道合并时,把索引侧(较小的一侧)整体载入 dict,大侧流式扫,不要双向载入
