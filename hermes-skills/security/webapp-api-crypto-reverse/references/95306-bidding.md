# 95306 竞价系统(cg.95306.cn)专属侦察笔记

逆向对象:国铁采购平台竞价系统(business-view 前端 + business-bidding 网关)。2026-08-30 侦察。

## 数据平台 findList(无鉴权,但 2026-08-27 16:57 后整体停更)

接口:`POST /proxy/dataplatform/api/findList`,body `{"funcId":..., "appId":"system", "pageNum":1, "pageSize":1000, "params":[{"key":"start_time","value":"YYYY-MM-DD"},{"key":"end_time",...}]}`

已验证 funcId(2026-08 数据量):
- `bid_project_business23` — 项目表(705):id(proj_id UUID)/bid_starttime/create_time/project_explain/status
- `bid_package_business23` — 包件表(2,185):id(pack_id)/proj_id/pack_code/pack_name/end_time/outbid_date/bid_min_bidder
- `bid_notice_business23` — 公告表(2,247):id(noticeId)/proj_id/proj_code/not_title
- `bid_package_bidder_business23` — 报名表(8515 增量来源):proj_id/pack_id/buy_time/status,企业字段(bidder_id/dwcode/phone/person/address)全 null,condition 通道不通只能走 params
- `auditlog` — 审计(唯一实时源):operation_details 含 serviceTicket=ST,按时间降序滚动日志(500 条/1.5 天)

**结论:数据平台只能作历史源(8/27 前),实时唯一依赖审计 ST 链路。西安局69次(f4d6e6e2)在所有表都查无记录(数据平台不覆盖)。**

## selectSelfSellList — 全量在网项目发现(实时!)

`POST /business-proxy/business/bidProject/selectSelfSellList`(带 ST + Referer: bfwz-view)

status 过滤(关键!混合拉取会被 1118 个已结束项目淹没,按 status 分页才拿得全):
- 13 = 竞价中(极少)
- 19 = 发布中/未开始(169)
- 22 = 待竞价/报名中(468)
- 30/31 = 已结束(965/128)
- 14 = 成交(1118+)

body: `{"projName":"","dwhz":"","projChar":"","status":"19","createWay":"","jtgsCode":"","wajorDomain":"","projType":"","fulfillmentStatus":"","projCategory":"","bidType":"02","pageVo":{"pageNum":1,"pageSize":100},"orderField":"","orderType":""}`

要点:按名称搜 `projName="26081507"` 能命中任何项目(即使翻 15 页找不到)——排序混乱,必须 status 过滤。测试项目过滤:projName 含"测试"/"test"。

4 台采集机分片:proj_id(去横线 hex) % 4 == SHARD_ID,每台 ~160 项目。

## business-view 前端 JS 逆向结果

- 入口 `/business-view/`,webpack runtime 在**内联 script**
- chunk URL:`/business-view/js/chunk-<名>.<版本号>.js`(版本号如 1787574513567,**不是 hash**,无版本号 404)
- 业务 API 全在巨型 chunk `chunk-65b3177a`(2.3MB,127 个接口)
- 请求封装模块 `b775`(在 app.js):urlType→baseURL 映射 + encryption 注入
- 加密模块 `ed08`(在 app.js):sm4encryptEcb/sm4decryptEcb = SM4-ECB + PKCS7 + base64

## SM4 密钥(2026-08-30 实测)

```
v = YYYYMMDD(北京时区,如 20260830)
b = "$e9s20@2o4u^r2"
key = (v + b)[:16] = "20260830$e9s20@2"   ← 每日动态,跨天变
p = "memberserver"(memServer 专用 key 材料,g = (v+"+"+p)[:16])
```

请求:`GET /business-proxy/business-bidding/<接口>?data=<base64(SM4-ECB(JSON params))>`
- params 必须带 `r`(时间戳+随机,JS: `(new Date).getTime()+Math.random()`)
- 响应:裸 base64(SM4 密文,无 JSON 包装)

Python 纯实现已过国标向量(key=pt=0123456789abcdeffedcba9876543210 → ct=681edf34d206965e86b3e94f536e4246)。

## 关键接口(bidRoom 竞价系)

- `bidRoom/packTable`(GET,加密)— 项目包件表 ← 报名期提前拿包件 ID 的主接口
- `bidRoom/packDetail`(GET,加密)— 包件详情
- `bidRoom/initProjInfo`(GET,加密)— 竞价房间初始化
- `bidMonitor/packTable`/`packInfo`(GET,加密)— 竞价监控
- `buy/bidRoom/offer`(POST,加密)— 出价
- `notice/redirectEnrollUrl?noticeId=`(GET,明文)— 报名跳转,返回 business-view centralizedBid URL
- `supplierPackage/getBuyPackageList?projId=`(GET,明文,ST)— 企业报名包件(采集机在用)
- `supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02`(GET,明文,ST)— 企业全部已报名项目

## 未完成项(2026-08-30 状态)

1. **packTable 响应密文解不开**(所有 key 变体/参数组合返回固定 80B 密文)→ 怀疑 Authorization 头格式不对:JS 里 token getter 是模块 `5f87`(`headers[k]=Object(a["a"])()`),定义未找到,可能不是裸 ST(带前缀/签名)
2. 数据平台 8515 CSV 来源 funcId 未找到(可能是跳板机侧数据库直查,非 findList)
3. centralizedBid/centralizedList(集中采购列表)接口参数未测通(500)
