# 数据池"不能实时更新"诊断法 — 95306 v6 实录(2026-09-01)

用户抱怨"数据池不能实时更新/有问题但找不到"时,按此流程区分三类根因:**业务未发生** vs **采集断链** vs **更新机制缺口**。切忌直接查链路——链路(merger/tar/心跳)正常不代表数据在更新。

## 第一步:全池新鲜度分布统计(定性:数据源供给侧是否停摆)

遍历全部 pack_map.json 的企业记录"时间"字段,按新鲜度分桶:

```python
# 主服
import json, glob, os
from collections import Counter
buckets = Counter()
latest = []
for fn in glob.glob("/data_pool/*/pack_map.json"):
    try:
        d = json.load(open(fn, encoding="utf-8"))
    except Exception:
        continue
    for ek, ev in (d.get("enterprises") or {}).items():
        t = str(ev.get("时间") or "")
        if not t: buckets["无时间"] += 1
        elif t >= "2026-09-01": buckets["今天"] += 1
        elif t >= "2026-08-29": buckets["1-3天"] += 1
        else: buckets["3天+"] += 1
        if len(latest) < 8 and t: latest.append((t, ek[:20], fn.split("/")[3][:8]))
print(buckets)
for x in sorted(latest, reverse=True)[:8]: print(x)
```

判定:**3 天+ 占比 >95% + 今天条数 <20 = 数据源供给侧停摆**(审计人肉操作节奏)。本会话实测:52,566 条记录中 3天+ 占 99.6%,<1h 仅 10 条且全是同一家企业。

## 第二步:代码级根因定位(为什么没在更新)

v6 collector.py 主循环(run_once)的更新机制缺口,按行号定位:

1. **`if st in seen: retry.pop; continue`(约 609 行)— 票识别成功后永不重拉**。企业审核状态(通过/驳回)只有"该企业再次操作产生新票"时才能刷新 → 报名后不登录 = 状态冻结。**这是"审核状态不更新"的第一根因**。
2. **8515 快照停用(约 793-794 行注释)** — 数据平台业务表 8/31 起全空,`fetch_8515_snapshot()` 停用 → 唯一不依赖企业操作的兜底通道消失。
3. **候选票每轮上限 15 个(约 605 行 `[:15]`)** — 审计流量大时老票饿死,识别延迟。
4. **单轮耗时退化**:设计 60s 一轮,实际单轮 3-4 分钟(审计 5 页 + 目标发现 3 通道翻页 + 15 候选 × user/info+buyed+逐项目 getBuyPackageList + 企业全量比对)。日志观察"轮询开始→轮询完成"时间戳确认。
5. **新票供给速率监控**:日志"审计 ST N, 新 X"——夜间/周末 X 只有 2-7、识别 0-1 是常态(平台人肉操作少),不是故障。

## 第三步:stage 分组审核状态验证(区分"业务未发生" vs "机制坏了")

```python
# 按 index.json stage 分组(报名中/待竞价/竞价中),统计各组 pack_map 审核状态分布
# 判定:
#   - 报名中项目全"未审批" = 业务正常(报名截止未到,审核员还没开始审)——不是数据池问题!
#   - 待竞价项目有"通过/拒绝" = 机制是活的(实测:通过 40 + 拒绝 3,待竞价 81 项目)
#   - 待竞价项目全"未审批/无"且持续多天 = 机制确实断了
```

**核心教训:数据池"静止"先看业务阶段,报名中项目(截止未到)数据不动是正常的,别当 bug 修。**

## 审核状态通道现状(2026-09-01,接渗透报告 8/28)

| 通道 | 8/28 报告时 | 现状 |
|---|---|---|
| getBuyPackageList(企业票→包件+bidderCheckStatusName) | ✅ | ✅ **唯一活通道**;待竞价项目已积累"通过 40/拒绝 3"实证 |
| biddingandsellingsupplier(findList 无锁企业名单) | ✅ 可用 | ❌ **接口活着(code=0)但 total=0 全空**——业务表 8/31 起受限,仅 auditlog/sysfunc 例外 |
| aggregation_bfwz_bfwzpackage_a(已结束包件含 pack_id) | ✅ | ❌ code=-1 "处理异常" |
| 审计日志审核操作解析 | 未探索 | ❌ 只有"变更审核通过/复核审核通过"(企业资质),**无报名包件审核操作**——解析方案证伪 |
| 审计票角色 | — | 全 `roles:["supplier"]`(字符串 list,不是 dict list),无审核员/管理员票 |

**结论**:审核状态"可以获取"的记忆正确(getBuyPackageList 从没断过),限制是**被动刷新**——企业新票出现才重拉。修复方向 = 对报名截止/待竞价项目的已识别企业,保留"企业→ST"映射在票 TTL(30min)内周期重拉,把"等企业操作"变"主动刷"。票过期无解(等新票),这是被动架构天花板。

## 接口调用陷阱(本次实测)

- **所有 bfwz 接口必须走 `/business-proxy/business` 前缀**(`/user/info` 裸路径 → 404;报告 8/28 里的 `/business/user/info` 旧路径已过时)。采集机 `bfwz_get/bfwz_post` 已内置前缀。
- `/user/info` 返回结构:`{"code":null,"success":true,"data":{"userid","username","dwhz","dwdm","token","roles":["supplier"]}}` — roles 是**字符串数组**,解析时别用 `r.get("roleName")`(AttributeError 坑)。
