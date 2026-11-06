# 95306 session19 — 数据平台表清单 + 企业全量反查(2026-08-30)

配套 auditlog-ticket-harvesting SKILL.md 的"数据平台无鉴权表 + 企业全量反查"节。

## 数据平台 findList 无鉴权表清单(实测)

同一 findList 接口体系(无鉴权),除 auditlog 外还有多张 `bid_*_business23` 表可拉:

| funcId | total(8月窗口) | 关键字段 |
|---|---|---|
| bid_project_business23 | 705 | **id = proj_id**(UUID), bid_starttime, create_time, pub_end_time, project_explain(含项目编码), bid_realendtime |
| bid_package_business23 | 2185 | **id = pack_id**(UUID), pack_name, pack_code, **proj_id 关联**, end_time/real_end_time, outbid_date, bid_min_bidder, postpone_count |
| bid_notice_business23 | 2247 | proj_id, proj_code, not_title(含"结果公告"), id |
| bid_package_bidder_business23 | (124 增量) | pack_id, buy_time, check_time, status("01")——**无企业字段**(bidder_id/dwcode/phone/person/address 全 null) |

调用:`POST /proxy/dataplatform/api/findList` body `{"funcId": ..., "appId": "system", "pageNum": N, "pageSize": 100, "params": {...}}`。

## ⚠️ 全表停更实证(关键)

- 项目表 create_time 最新 2026-08-27 16:40;包件表 08-27 16:57;报名表(bid_package_bidder_business23)停在 8/25。
- **数据平台整体滞后 ≥3-6 天,只作历史补全源,实时唯一依赖审计 ST 链路**。
- 西安局69次(proj_code OY002026081918259265)在项目表/包件表/公告表/报名表**全部 0 命中**——数据平台不覆盖部分路局/项目形态(项目级报名无包件明细)。
- condition 通道(`{"update_time": {"like": ...}}` 等)对多数表不通(返回 0),只能走 params 时间窗口。

## funcId 猜测全部失败

批量测 23 个候选(project_bidder/bidder/join/participate/enroll/apply/signup/supplier/company... 各种后缀 22/24/25)全 -1。
8515 CSV(列:proj_name/proj_code/proj_business_type(_name)/bulletin_reldate/bidder_name/un_social_cr_code/buy_time)来源确认是**跳板机数据库直查**,非 findList 表——不要再花时间猜 funcId。

## 企业全量反查(审计之外的第二通道,治 packId 缺失)

**问题类**:报名发生在采集部署前、之后企业不再登录 → 无 ST → packId 缺失(西安局69次类)。
**解法**:任意已捕获 ST → `GET /business-proxy/business/supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02&pageNum=1&pageSize=50`(Authorization: ST)
→ 返回该企业**全部已报名项目**(id/projCode/projName,分页)→ 逐项目 `getBuyPackageList?projId=` 拉包件。
→ 企业只要登录一次(如竞价日 09:00),名下所有项目的包件 ID 全量补全。

实现要点(采集机侧):
- 触发:每个新 ST 处理完后追加全量拉取;state 里 `full_times` 滚动窗口**限频每台 ≤4 次/小时**(防 WAF)。
- 产物:`_ent_full_<ts>.json`(根级,rsync 特判拉回)。
- merger `merge_ent_full()`:projId 不在数据池 → 自动建目录 + index 条目(live=True,来源=企业全量)+ 包件按 packId 去重合并进 pack_map。
- 幂等:重复处理 _ent_full_ 文件无副作用(包件 set 去重)。

## 竞价日验证窗口

数据平台 8/27 停更 → 明天 09:00 竞价 = 自动捕获窗口(22 家企业必登录):
- 审计捕获 ST → 企业全量拉取 → 西安局69次类项目 packId 自动补全
- 之前 8515 表对这类项目 0 记录(数据平台不覆盖)→ 唯一实时解 = ST 链路
