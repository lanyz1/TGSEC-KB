## 4.1 ★ 大产物不回传:远端先聚合,只拉小结果

远端盘上一份 20–200MB 的 jsonl **不要** `gzip -c | base64 -w0` 走 exec 通道回传
(几十 MB base64 吃掉整轮预算,回显还可能被折叠成 `1 lines output`)。既定形态 = **在远端把数据压成结论**:

```python
# 远端 agg.py: 读大 jsonl -> 按 id 去重 / 分类计数 / 按主体 rollup -> 写小 CSV
ids=set(); cats=collections.Counter(); per={}
for line in open(SRC, encoding="utf-8", errors="replace"):
    d=json.loads(line)
    if d["id"] in ids: continue
    ids.add(d["id"]); cats[d.get("category","")]+=1
    r=per.setdefault(uid,[uid,nick,0.0,0,set()]); r[2]+=amt; r[3]+=1; r[4].add(cat)
```

然后只把**几十 KB 的 CSV** 拉回本机;原始 jsonl 留在远端(要细节时按 id 精确取单条)。

- **闭合判据**:分页全量拖取以「**去重后 id 数 == 服务端 meta.total**」为闭合,不以「页数跑完」为闭合。
- 本地累计行数 **>** total 时先别当重复删:前一轮落盘的文件常来自**另一个端点 / 另一个 id 空间**,
  按 id 去重后再对账,别用行数判断重复。
- **进度行**:拖取脚本每页打一行 `page=N 累计 M / total=T`。靠它才能 (a) 算剩余时间,
  (b) 判断 `timeout` 是否砍尾 —— 砍尾后用「**带已见 id 的去重续跑**」补齐,
  绝不重头跑(重头会把已完成的请求对目标再打一遍)。

