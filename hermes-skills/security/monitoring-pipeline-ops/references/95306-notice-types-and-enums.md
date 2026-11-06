# 95306 公告类型枚举与报名语义(实录 2026-09-01)

来源:公告接口实测(23,202 条全量分布)+ 前端 JS 字典(主服 /tmp/bv_*.js)双证据。

## noticeType 公告类型总表(销售侧 projType=02)

| noticeType | 类型 | 存量 | 特征样本 | 发布后能否报名 |
|---|---|---|---|---|
| 01 | 项目公告(主公告) | 21,091 | "XX局2026年第N次废钢铁物资处置项目的项目公告" | ✅ 立即开放报名 |
| 02 | 变更公告 | 435 | "…处置项目的变更公告" | ❌(附属于原项目) |
| 03 | 包件级公告 | 1,432 | "本项目…007包…终止销售/修正为…" | ❌(单包件变更/补遗) |
| 05 | 结果公告 | 少量 | "…处置项目的结果公告" | ❌ |
| 07 | 结果公示 | 1,624 | "…处置项目的结果公示"(status=31) | ❌ |
| 08 | 成交公告 | 113 | "…成交公告"、"…竞价结果公告"(询价/谈判类) | ❌ |
| 09 | 终止公告 | 244 | "…处置项目的终止公告"(status=22) | ❌ |
| 04/06/10-12 | 空 | 0 | 不存在 | — |

另有**补遗公告**(`makeupCount` 字段挂靠原公告,非独立 noticeType)。

## 报名语义(回答"发公告就能报名吗")

- 只有 **noticeType=01 项目公告**发布后立即开放报名;公告列表页 JS 判断 `projectAttendStatus==0` 才渲染"我要参与"按钮
- 8/31 发布的 46 个新公告全部:noticeType=01、status=19、projectAttendStatus=0、notStatusName=已发布 → 全部可报名,报名截止=`sellEnddate`
- 变更/结果/成交/终止类公告发布后无报名入口

## 关联枚举

- **bidType**:`01`=采购(竞买)、`02`=销售(竞卖/处置)——数据池全是 02 销售侧
- **jointSaleType**:`0`=自行处置(18,749 条)、`1`=联合销售(37 条);8/31 的 46 条全是"自行处置项目"
- **status**:19=报名中、22=终止/流标、31=结果公示、14=终态

## 枚举挖掘方法(前端 JS 字典 + 接口逐值探测)

1. 前端 chunk JS 保存到主服(如 /tmp/bv_chunk-*.js,含 2.4MB 主 chunk),`grep -o` 枚举关键词:`noticeTypeName`/`projectAttendStatusName`/`bidType.code`/`jointSaleTypeName` + 中文标签(招标/竞价/询价/谈判/单一来源/结果公示)
2. 公告接口逐值探测(低频、单页):`queryBusinessNoticeList` 循环 noticeType=01..12,统计每值返回条数 + 打印前 2 条标题特征;noticeType=05 曾遇 503(限流)重试成功
3. 判定"能否报名"看 JS 渲染条件,不看接口字段名

## 采集过滤核实(公告流发现源)

- 线上 collector.py 3 处公告拉取(222/325/342 行)全部 `"noticeType":"01"` → 变更/结果/终止类不会污染目标清单(核实 4 台一致)
- 公告流发现项目落盘带 `src:"notice"` 标记,位置 `/tmp/targets/<projId>/项目信息.json`(不是 /opt/v6/targets!)
- 主服 index.json 结构:`{"updated","source","projects":{projId:{...}}}`;merger 未透传 src → 数据池看不出来源(如需按来源统计,merger 加一行透传)
- **全量入池核验**:`公告_831.json` 的 projId ∈ index.json projects → 46/46 缺失 0(双进程修复后达成;此前 39/46)

## 陷阱

- 公告接口样本字段:`notStatus`=10(已发布)/`notStatusName`、`projectAttendStatus`=0(可报名)、`resultNoticeExistName`=未发布
- grep 采集机文件前先确认路径:/tmp/targets/ 而非 /opt/v6/targets/(TARGETS_DIR 定义为准)
