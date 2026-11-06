# 95306 数据源字段能力图谱 + 报名证据判定(2026-09-01 实测)

采集机真实 ST 逐个接口实测。用途:菜单字段可行性评估、缺口误报筛选、补采字段设计。

## 1. 接口→字段全景(权威实测)

### /user/info(GET,需 ST)
| 字段 | 语义 |
|---|---|
| userid | 登录账号(如 Ajt3211) |
| username | **联系人姓名**(注册经办人,如 盛利良) |
| dwhz | **企业全称**(如 丹阳市江腾再生资源有限公司) |
| dwdm | 单位代码(如 MA7MH4JJ-X01) |
| token | 当前 ST |

### /notice/readNoticeInfo?noticeId=(GET,需 ST)
- **结构化时间字段多为空**:`applicationDeadline`/`bidStartTime`/`bidEndTime`/`realStartTime` 等基本都是 None → **必须解析 notCont HTML**
- `notCont` HTML 含全部权威时间文本:
  - `公告日期：2026年09月01日`(也有 pubTime 字段 `2026-09-01 12:00`)
  - `报名截止时间：2026年09月07日 10时00分`
  - `竞价开启时间：2026年09月11日 15时00分`
  - `包件内容：`段落(第001包名称/文件售价/竞卖保证金/开启结束时间)
  - `联系方式：`= **销售方电话,不是企业电话**
- 其他:createTime 公告创建、pubTime 公告发布、notStatus/notStatusName、fileList(附件)

### /supplierPackage/getBuyPackageList?projId=(GET,**必须用报名企业自己的 ST**,他人 ST → code 100 无权限)
- 返回企业自己的报名包件数组,字段:packId(UUID 精确 id)/packCode/packName/packDesc(描述详情)/detailNum/payType/payTypeName(单价/总价)/frontMoney(保证金)/**bidderCheckStatus/bidderCheckStatusName(审核状态,如 未审批)**/status 等
- 无电话、无联系人

### /supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02(GET,企业视角)
- 企业已报名项目列表;projs 元素 = `{projId, name, bidStart}` —— **bidStart(竞价开启时间)直接可用**
- statusGroup=join = 报名中项目列表

### /proxy/dataplatform/api/findList(POST,无 ST,appId=system)
- funcId=`auditlog` 可用(审计日志);其余 funcId(supplier/supplierInfo/company/enterprise 等 18 个猜测)全部"不存在的功能"
- 审计字段:operation_details(含跳转 URL + 参数 JSON)、operation_username/operation_account(账号)、operation_ip、operation_time、first_menu='公告报名按钮'、operation_function='公告报名'

## 2. 权限边界(实测死路,别再试)

- **企业电话:接口层拿不到**。user/info 无电话字段;supplier 详情类接口(supplier/info、getApplyInfo、getSignInfo、registerInfo 等 12 个)全部 500 无权限;findList 无供应商库 funcId;审计无电话;公告 HTML 只有销售方电话
- 供应商注册信息类接口全部 500
- **getBuyPackageList 权限按 ST 归属**:只有报名该项目的企业 ST 能查;要枚举多企业包件详情必须用各企业自己的 ST

## 3. 报名提交证据判定(误报筛选核心方法论)

**问题**:审计日志只记录 `redirectEnrollUrl`(打开报名页跳转,44/44 条全是),**系统根本不审计"提交报名"接口** → 审计侧无法区分"打开页面"与"真实提交"。

**唯一权威判定**:企业自己的 ST 调 `getSupplierPackageList?statusGroup=buyed` / `getBuyPackageList?projId=` —— 提交报名必有包件记录,只打开页面则无。

**实施链路(四步)**:
1. **collector 增量扫 buyed 矩阵**(每 30 分钟,同公告映射表节奏):遍历 ST 池(st_times,历史 ST 时效宽松,8/30 票 9/1 仍有效),调 buyed 列表 → `_buyed_matrix.json` = `{ST: {acct, unit, tm, n_proj, projs:[{projId,name,bidStart}]}}`
2. **merger 证据分流**:企业报名缺口按项目提交证据分类——项目在矩阵证据集且账号单位命中提交单位 → 真缺口(告警);否则移入"疑似仅打开页面"(不告警)
3. **账号级精确判定**:账号→单位映射从数据池所有 pack_map 构建;缺口账号单位 ∈ 该项目提交单位集合才告警(示例:263 条缺口 → 账号级判定后 0 真缺口,69 条疑似全剔除)
4. **merger 去重**:4 台采集机 enroll_ops 重复导致缺口 ×4,按账号+项目去重

**实测效果**:263 条缺口只有 3 个账号是真提交(其余 43 个项目 = 仅打开页面 = 误报);全量 222 历史 ST 扫描出 4 家有真实报名(共 18 个项目)。

**坑**:
- buyed 扫描路径必须带 `/business-proxy/business` 前缀,否则返回空 dict 被误判"ST 无效/无报名"
- 补采脚本 Python for 循环变量泄漏(m 用了最后一个 ST 的值)→ 账号字段空、单位写错;循环内用独立变量名
- 核对 pack_map 用完整 UUID 路径,不要用 8 位前缀(目录是完整 UUID)
