# 95306 通道健康复核与审核状态获取现状(2026-09-01)

接渗透报告 2026-08-28 的通道清单,复核 8/31 平台变更后的可用性。**结论:getBuyPackageList 是唯一活通道,业务表全受限。**

## 通道现状表(逐条实测)

| 通道 | 8/28 报告时 | 现状(9/1 实测) | 说明 |
|---|---|---|---|
| getBuyPackageList?projId=(企业票) | ✅ | ✅ **唯一活通道** | 企业→包件+bidderCheckStatusName;待竞价项目已积累"通过 40/拒绝 3"实证,机制活着 |
| biddingandsellingsupplier(findList 无锁企业名单) | ✅ 可用 | ❌ **code=0 但 total=0 全空** | 8/31 起业务表全受限,仅 auditlog/sysfunc 例外;接口不报错、返回空 data——别被"活着"骗了 |
| biddingregistrationsupplier / centralizedbidsuppliers | ✅ | ❌ total=0 | 同上,业务表受限 |
| aggregation_bfwz_bfwzpackage_a(已结束包件含 pack_id) | ✅ | ❌ code=-1 "处理异常" | 同上 |
| 审计日志解析审核操作 | 未探索 | ❌ 证伪 | 审计只有"变更审核通过/复核审核通过"(企业资质变更),**无报名包件审核操作** |
| 审计票角色 | — | 全 `roles:["supplier"]` | 无审核员/管理员票 → 无法用审核员视角拉全量审核状态 |

## 审核状态获取的语义(回答"进行中项目审核状态可获取吗")

- **可以获取,但被动**:审核状态 = 企业自己的票调 getBuyPackageList 返回的 `bidderCheckStatusName`(未审批/通过/拒绝)。只有**该企业再操作产生新 ST** 时才能刷新。
- **"报名中项目全未审批"≠ 数据池坏了**:报名截止未到,审核员还没开始审——业务正常。
- **验证机制是否活的**:统计**待竞价项目**(报名已截止)的审核状态分布,出现"通过/拒绝"= 通道活着(实测通过 40 + 拒绝 3)。
- **修复方向**:对报名截止/待竞价项目的已识别企业,保留"企业→ST"映射,在票 TTL(30min)内周期重拉;票过期只能等新票——被动架构天花板。

## 接口调用陷阱(实测)

- **所有 bfwz 接口必须走 `/business-proxy/business` 前缀**:`/user/info` 裸路径 → 404(报告里的 `/business/user/info` 旧路径 8/28 后已失效)。403 是裸路径典型,404 是 Spring Security 隐藏接口存在性——都要加前缀重试。
- `/user/info` 返回:`{"code":null,"success":true,"data":{"userid","username","dwhz","dwdm","token","roles":["supplier"]}}` — **roles 是字符串数组**,用 `r.get("roleName")` 会 AttributeError。
- findList 业务表探测:`code=0 + total=0` 且无报错 = 表被限制(不是没数据),区分"接口死"与"数据空"看 code/msg。
