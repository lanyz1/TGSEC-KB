# 「来源」字段体系 + 菜单B 展示排序 — 95306 v6 实录(2026-09-02)

## 一、数据池「来源」字段全貌(实测 52,572 条)

位置:pack_map.json → enterprises.<企业>["来源"](企业级),`记录[].来源`(记录级),
项目信息.json["来源"](项目级),index.json 顶层 `source`(全局标记)。

| 取值 | 数量 | 占比 | 含义 | 写入方 |
|---|---|---|---|---|
| `01三态+映射链` | 49,010 | 93.2% | 旧采集链路(报名三态接口 + 账号→企业映射链) | 早期采集脚本(历史遗留) |
| `公示包成交人` | 2,412 | 4.6% | 结果公告(公示包)提取的成交企业 | 公示包导入 |
| `8515项目级` | 908 | 1.7% | 8515 快照按项目粒度导入 | import_8515.py |
| `8515` | 231 | 0.4% | 8515 全量导入(记录级) | import_8515_all.py |
| `公告成交人` | 11 | 0.02% | 公告流成交人提取 | 公告导入 |
| `企业全量` | (项目级) | — | 全量企业快照(新项目实时采集打标) | merger.py |
| `报名企业来源` | (透传) | — | 接口原始字段透传 | import_history.py |

关键事实:
- **现行 collector.py(8 台)已完全不写来源字段**——来源由主服 merger/import 脚本维护
- `01三态+映射链` 49010 条全是历史导入产物,现行实时采集打 `企业全量`
- merger 合并 pack_map 时:旧 key(单位名)→新 key(账号)归一化、`时间` 新者胜、包件按 packId 去重、来源随条目保留不丢
- 用户问"来源字段"时 = 上述体系;先查取值分布再答,别只答一两个值

查法(主服):
```python
import json, os
from collections import Counter
cnt = Counter()
for root, dirs, files in os.walk("/data_pool"):
    for fn in files:
        if not fn.endswith(".json"): continue
        try: d = json.load(open(os.path.join(root, fn), encoding="utf-8"))
        except Exception: continue
        def walk(o, p=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("来源", "source") and isinstance(v, str): cnt[v] += 1
                    walk(v, p + "/" + k)
            elif isinstance(o, list):
                for x in o: walk(x, p)
        walk(d)
print(cnt.most_common(10))
```

## 二、菜单B 可拦截项目排序逻辑(用户问"为什么全是08-31"的答案)

- 列表 📅 显示 = **公告发布日**(`proj_pub_day`:pubtime_map 优先,缺则从 projCode 正则 `0020(\d{6})` 推导)
- **排序键 = bidStarttime(竞价开始时间),不是公告日**!`blockable_projects()` 三组均按 bidStarttime 升序
- 后果:08-31 公告的项目竞价集中在 09-10~09-11,09-01 公告的项目竞价在 09-11~09-15,两者混排 → 最新公告(09-01)埋在第 3 页以后,用户以为没采集到
- 判读:总分组数 🔵/🟢/🟡 是权威,翻页看日期;数据缺失先查 stage 分布 + pubtime_map 最新日期,别直接下"没采到"结论
- 优化选项(用户可选):按公告日倒序排 / 组顶部加日期统计行

## 三、关联

- 心跳/时区陷阱、index.json 原子写:见 monitoring-pipeline-ops 其他 references
- skipJoinPage 排除、新ST 判读:见 lowcode-dataplatform-pentest references/95306-data-channel-matrix.md
