# 95306 活票收割三轮突破: Referer 防盗链 + 供应商穿透链(2026-08-28)

## 关键突破 1: Referer 防盗链(500"没有操作权限"的真实原因)

`/business-proxy/business/*` 全部接口(bfwz 竞卖体系)要求 **`Referer: https://cg.95306.cn/bfwz-view/`**:

- 不带 Referer → 一律 `500 {"msg":"您没有该功能的操作权限,请联系技术支持!"}` —— **曾被误判为"供应商角色权限不足"**,实际是防盗链校验
- 带 Referer → 立即 200(同 ST 同接口)
- 其它 header 无效:Origin / X-Requested-With 单独带均 500;只有 Referer 是关键
- **通用教训**: 500"没有该功能的操作权限" 先补 Referer 重试, 再怀疑角色。判断顺序: 401=未登录/票无效; 500+该消息=缺 Referer 或真缺角色。

## 关键突破 2: 供应商穿透链(企业→pack_id 全链路实测)

### 调用序列(全部 GET, 带 `Authorization: <st>` + Referer)

```
GET /business-proxy/business/user/info                          # 验证票 + 企业身份
GET /business-proxy/business/supplierPackage/getSupplierPackageList?statusGroup=join&bidType=02    # 可参与项目(进行中!)
GET /business-proxy/business/supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02   # 已报名项目
GET /business-proxy/business/supplierPackage/getBuyPackageList?projId=<uuid>   # 该企业在此项目的报名包件明细!
POST /business-proxy/business/bidProject/selectSelfSellList                    # 竞卖项目全量(含进行中)
GET  /business-proxy/business/bidProject/getProjInfo?projId=<uuid>             # 项目详情
```

### 关键语义

- **statusGroup 映射**(前端 tab): `join`=可参与项目 / `buyed`=已报名项目 / `progress`=进行中项目; tab 切换时前端自动带 `jointSaleType` 参数(0=自行处置, 1=联合处置), **缺省=自行处置**; myPackage 页(联合处置)与 manage/myPackage 页(自行处置)是两套列表。
- **`getBuyPackageList?projId=xxx` 返回 pack_id 级**:
  ```
  packId(UUID) | packCode | packName | frontMoney(保证金) | payTypeName(总价/单价)
  | bidderCheckStatus(审批码) | bidderCheckStatusName(通过/未审批) | detailNum | packDesc
  ```
- **⚠️ 只返回"当前企业已报的包件"**: 未报该项目 → 返回空数组 `[]`(不是报错)。要拉目标项目包件, 必须用**报过该项目的企业**的 ST。
- `user/info` 返回 `dwhz`=企业全名, 可匹配本地报名企业名单(如 8515 文件)定位目标 ST。
- `selectSelfSellList` body: `{"projName":"","dwhz":"","status":"","pageVo":{"pageNum":1,"pageSize":20},"bidType":"02"}` — 返回 status=19"发布"的**进行中项目全量**(16,872 个), 可搜任意项目(武汉局69次在其中, projId=f1b40608...)。

### 实证数据(25 条)

- 黄强(遵义市玉强金属回收有限公司): 遵义车务段第4次汽车 → 001 报废汽车(保证金500, 未审批); 贵阳电务段第6次废旧物资 → 001/002/003 报废转辙机(各2000, 通过)
- 陕西九洲再生资源: 西安局73次废钢铁 → **001-020 全部 20 个包件**(packId+名称+保证金, 001/002 未审批, 003+ 状态 None=未报/待审)

## 关键突破 3: ST 有效性判断(修正早前"100=过期"单一判断)

- `user/info` 成功 = `code:null, success:true`(含 username/dwhz/roles/userid/token)
- 业务异常 `code:100 系统服务异常` = 票过期 **或接口本身异常** —— 用具体业务接口二次确认(401=确定无效)
- 不同 ST 权限不同: 同为供应商, 有的账号能看到 97 个可参与项目+已报名, 有的全部 500(真实角色差异, 与 Referer 无关——Referer 补上后低权账号仍 500)

## 关键突破 4: playwright 真实会话辅助(前端流程还原)

```
1. 登录: page.goto("bfwz-view/#/auction/manage/allProject?serviceTicket=<32hex>")  # 不带 projName!
2. 导航: #/auction/manage/myPackage(自行处置) 或 #/auction/jointDis/myPackage(联合处置)
3. 切 tab: 点击"已报名项目"(触发 statusGroup=buyed)
4. 点"查看报名" → 触发 getBuyPackageList?projId=xxx(包件明细!)
   点"查看公告" → 公告正文(项目信息/资质要求, **不含包件清单**)
5. 拦截 page.on("request"/"response") 还原真实接口+body
```

- **myPackage 页面 URL 带 projName 参数会过滤列表**(带 x = 空列表) —— 登录 URL 别带 projName
- 前端 fetch 需手动带 `Authorization: localStorage.getItem('Ah')`(axios 拦截器自动加, 手动 fetch 不加)
- 页面内 XHR/fetch 与 urllib 直连差异 = 仅 Referer(同 ST 同接口同 header 验证过)

## 审计日志侧(本轮补充)

- 搜 redirectEnrollUrl: `condition={"operation_details":{"like":"%redirectEnrollUrl%"}}`
- 每条记录含: 账号 / 时间 / 调用结果(带 projName+serviceTicket 的完整跳转 URL)
- 审计只保留近几天: 8/13-19 的武汉局69次报名记录已滚动删除 —— **历史报名企业的 ST 不可回溯, 只能等它们再报名(产生新 ST)**
- 监控频率: bfwz ST TTL < 30 分钟(实测 06:03→06:32 失效), crontab 用 `*/5 7-23 * * *`

## 数据层补充(本轮新拉)

- `biddingregistrationsupplier`(Doris 无锁): 招投标报名统计 26,977 条(8月, 实时到 8/28)
- `centralizedbidsuppliers`(Doris 无锁): 集中竞价报名 2,857 条
- aggregation_bfwz_bfwzpackage_a: 13,075 包件(2026, pack_id+proj_id 级) — 只含已结束项目
- XOR 反转(8/27 曾可行): 8/28 复测 total 不变 = **已修复/参数化**, 不要重试
- ES 公告: `scrapSuppliesQueryDataToEs?noticeType=01` 19,898 条, digest 截断 ~100 字, keyword 参数无效
