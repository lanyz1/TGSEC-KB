# 95306 Session 28 — 项目生命周期状态机(用户 9 步流程 → stage 五状态)

日期:2026-08-31(数据平台限流后,session27 续)

## 1. 用户权威业务流程(9 步,原话整理)

```
1. 新项目审核员审核后公示;公示期间~报名截止均可报名
2. 报名入口: bfwz-view/#/auction/manage/myPackage?tab=join → 点"我要参与报名"
3. 跳转 myBag?projid=<projId>(projId=项目唯一 id)→ 上传资质 → 点报名 = 报名成功
4. 报名成功 → myPackage?tab=buyed(等待审核;查看报名/查看公告两个按钮)
5. myBag?projld=<projId> → 项目编号+审批/报名情况(未审批/通过/未报名包件/驳回 4 态)
6. 审核通过 → 等竞价室打开(项目开启时间),通过的项目进竞价室
7. 所有包件竞价结束 → 竞价室关闭
8. 项目出现在 myPackage?tab=progress(结束待发布)
9. 审核员人工点发布结果 → myPackage?tab=over(已发布)
10. 查看结果: bfwz-view/#/auction/noticeResult?projId=<projId>(查看结果/查看报名/查看公告三按钮)
```

## 2. stage 五状态划分(merger classify_all + index.json 字段)

```
报名中(公示~报名截止,可报名) → 待竞价(报名截止~竞价开始)
→ 竞价中(竞价室开~关) → 待发布(竞价室关~审核员发布结果) → 已发布(结果公示)
```

判定规则(_stage_of,按优先级):
```python
now_s = _fmt_ts(now)
sell  = _fmt_ts(info.get("sellEnddate", ""))   # 报名截止
bt    = _fmt_ts(info.get("bidStarttime", ""))  # 竞价开始
max_end = _max_end(pid)                        # 包件清单最大"竞价结束"
st    = str(info.get("status", ""))
if sell and now_s <= sell: return "报名中"      # join 项目才有 sellEnddate
if st == "14":            return "已发布"       # 终态优先(历史项目都靠它)
if max_end:
    if now_s >= max_end:  return "待发布"
    if bt and now_s >= bt:return "竞价中"
    return "待竞价"
if bt: return "竞价中" if now_s >= bt else "待竞价"
return "历史"
```

实测分布(21,219 项目):报名中 5 / 待竞价 45 / 竞价中 7 / 待发布 413 / 已发布 20,747 / 历史 2。

## 3. status 字段语义(selectSelfSellList 全量,实测)

- `14` = 已发布/终态(20,747 个,含所有历史)——**stage 判定的主依据**
- `19` = 进行中(69 个,报名中+待竞价+竞价中)——**不随报名截止更新**(郑州13次 8/26 截止仍 19)
- `22` = 流标/招投标类(391 个,含非竞卖项目)——不可当"竞价中"
- 空 = 无状态(12 个,新项目信息未同步)
**结论:状态划分必须以时间为准(status 只做 14 终态/兜底),不能信 19/22 当进行中。**

## 4. sellEnddate 数据源差异(关键坑)

- **join 列表**(getSupplierPackageList?statusGroup=join)返回 sellEnddate → 报名中项目有
- **selectSelfSellList**(全量 16,875)不返回 sellEnddate → 已截止/历史项目该项目信息.json 无此字段
- 结果:非 join 项目 stage 判定只能靠 bt/max_end/status(不影响正确性,报名中判定天然只对 join 项目生效)

## 5. 性能优化:_max_end 优先读合并目录

```python
def _max_end(pid):
    # 1) 优先 /data_pool/<pid>/包件清单.json(主服合并产物,1 次 IO)
    # 2) fallback 扫 RAW_DIR 4 个采集机目录(兼容未合并)
    # 3) 全空 → 返回 ""(历史项目直接 status 判,不做 listdir)
```
**为什么**:build_index 要给 21,000+ 历史条目补 stage,若每条都扫 4 个 RAW_DIR
目录 = 84,000 次 listdir,分钟级卡顿;读合并目录只有有目录的项目才 IO。

## 6. build_index 的历史条目补 stage 模式

build_index 只更新"有 项目信息.json 目录"的实时项目(~130 个);21,000+ 历史条目
(旧 index 里的,无目录)stage 保持空 → **第二轮循环专门补**:
```python
for pid, oinfo in idx["projects"].items():
    if not oinfo.get("stage"):
        oinfo["stage"] = _stage_of(pid, oinfo)
```
classify_all 的 by_stage 分组 + 分类/按流程.json + 分类总览.json 每轮自动刷新。

## 7. 输出物

- /data_pool/index.json:每项目加 `stage` + `sellEnddate` 字段
- /data_pool/分类/按流程.json:5 状态分组(名称/编号/竞价时间/包件数/企业数)
- /data_pool/分类/分类总览.json:各分类计数
- bot"实时项目"可用 stage 分组展示(待做:用户已确认方向,未落地)
