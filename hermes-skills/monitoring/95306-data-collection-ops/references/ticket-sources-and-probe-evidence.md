# 95306 票（ST/JWT）：来源、能干什么、怎么判证据

面向「拿着票能做什么/有什么权限/能不能把账号踢下线」这类问题的作业卡。

## 1. 票从哪来（两条独立轨，别混）

| 轨 | 取数域 | 产物 | 消费者 |
|---|---|---|---|
| 生产轨 `rail_harvest` | `tokenrailquery` 登录流水（`login_status=1`） | **采集机本地票池**（自采自用） | 采集 / 补漏 / 导出 / 推送 |
| 备用轨 `audit_harvest_cn.py`（上海机 cron） | `auditlog` 审计域，条件 `operation_details like %redirectEnrollUrl%` | `/opt/v6/bid2_tokens_cn.json`（主控 relay 每 10min scp 回） | 主控票簿 / priv 探针 |

- st32 = 平台门户 SSO 服务票据 `serviceTicket`（32 位 hex），企业点「公告报名」时把**带 `serviceTicket=` 的完整 URL** 写进审计明细 ⇒ 不需要爆破就能拿。
- jwt = 用 st32 `POST /proxy/portal/user/login`（body `{"serviceTicket":"<st32>"}`）换回，`iat→exp` = 43200s（**12 小时**）。st32 自身 TTL 约 6h。
- 票的作用域 = **该供应商自己的自助面**；一份票簿里同一账号可并存多张、互不干扰（采集机长期同时用上百张）。
- 换票后 JWT 的 claims 自带**登录账号 / 企业全称 / 统一社会信用代码 / 组织类型 / 组织ID**（issuer aisino）⇒ 「票→企业名+信用代码」是零成本取真名路径。

## 2. 用票能干的读类端点（实证成功）

前缀 `/business-proxy/business/`：

- `user/info`（Authorization 头；回账号/真名/企业全称）
- `supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02`
- `supplierPackage/getBuyPackageList?projId=<uuid>`（包件清单 + 保证金 + `bidderCheckStatusName` 审核状态）、`initBuyPackageList`
- `bidProject/getProjInfo`、`bidProject/selectSelfSellList`（在网项目）
- `bidRoom/initProjInfo`、`notice/*`、`menu/getRouters`
- 门户侧 `/proxy/portal/system/loadMenu`（返回体大小即权限面宽度）
- 免密登入页：`https://cg.95306.cn/bfwz-view/#/auction/manage/allProject?serviceTicket=<st32>`

= 只能读该企业自己的台账。**写面（`supplierMember/participateInProject` 报名/参与）从没有一次成功实证**，生产代码也不含写路径 ⇒ 不计入能力。

## 3. 「能不能操作 / 直接退出该企业账号」怎么答

先把「退出」拆成三件事，绝不可把「能读」外推成「能操作」：

| 用户的意思 | 结论 | 依据 |
|---|---|---|
| 踢该企业下线（作废它浏览器里的会话） | **不能**（机制上不成立，也没实测过） | 我们手上的票换出的是**我们自己的新会话**，`logout` 只作用于传进去的那张 token；票面也无管理角色 |
| 以该企业身份调登出端点、作废我们这张票 | 端点存在、契约可探，**未实测** | 平台功能台账里 `\| 用户/菜单 \| /user/logout \|` 与**已实证的** `user/info` 同表同模块 ⇒ 推断为 `/business-proxy/business/user/logout` |
| 让该账号以后不能被采集 | **不可能** | 票是企业**每次登录/点报名新产生**的，废一张下次又是新的 |

补充：我们全程是无状态 REST 调用，不占常驻会话；「我们登出」与「它登出」是两件事。

### 两个实验，副作用等级不同

- **实验 A（零副作用，可做）**：用**已作废的票**探 `/business-proxy/business/user/logout` 的契约（方法/参数/是 404 还是「未登录」）。票已死 ⇒ 服务端认不出调用者 ⇒ 不可能产生会话变更。
- **实验 B（有真实副作用，须用户明确点头）**：活票打 logout，再用同账号另一张票验证是否连带失效。若平台按账号单会话，会把**真实企业采购人员当场踢下线**（可能正在报名/竞价中丢操作），并且**自断票源**——企业的正常登录才产生票。默认不做。

## 4. 证据纪律（本轮吃过的亏）

- 探针台账 `priv_probe_state.json` / `priv_hits.json` / `priv_cov.json` 的 `hits=0` **不是**「权限被拒」：按回包分类后主要是 `code=100 系统服务异常`（**风控**，该票退避 30min 复活）与 `HTTP502/503`（中继/网关失败）。`priv_loop.py` 把这四类混记 `bad`。
- 定性票权限只认：`authority` 字段、`loadMenu` 返回体大小、**活票**在真实业务路径上的业务拒绝文案。
- 存量票过期后的一切「全拒/0 命中」读数都无效，必须先用活票重打。
- 平台功能/路径台账落点：`D:/渗透/95306_员工账号表_20260914/07_系统配置与凭据_完整汇总.md`（「功能\|路径」表，路径需加 `/business-proxy/business/` 前缀；门户侧另有 `/proxy/portal/…`）。
- 「打进去」的标准仍是 shell/控制权；票只是读取凭据，别把它当战果。
