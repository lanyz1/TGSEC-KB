# 95306 铁路物资平台补漏实例(2026-09)

场景:菜单B(可拦截项目:企业+精确包件ID+审核状态)漏采补齐。审计通道仅覆盖跳转式报名(~25%),直接提交式报名零审计。

## 数据源通道

| 通道 | 接口 | 覆盖 | 时效 |
|---|---|---|---|
| 审计 | findList funcId=auditlog(无鉴权) | 跳转式报名企业 | 秒级 |
| 权威名单 | biddingandsellingsupplier(无鉴权) | 100% 报名企业 | 30min cron |
| 登录日志 | findList funcId=tokenrailquery, dsid=binlog_doris | 登录过的企业 | 30min 轮 |
| 业务拉取 | /supplierPackage/getBuyPackageList?projId= | 指定项目包件 | 实时 |

## tokenrailquery 关键认知

- 调用:`POST /proxy/dataplatform/api/findList {"funcId":"tokenrailquery","appId":"system","pageNum":N,"pageSize":500,"params":[{"key":"startDate","value":"YYYY-MM-DD HH:MM:SS"},{"key":"endDate",...}]}`
- 返回字段:userid/token(32hex)/login_time/user_type(03=供应商)/return_url
- **供应商(03)token 即 bfwz ST,直接当 Authorization 用**(免换票;TTL 实测 >2h,4h 窗 295/477 有效)
- 集团/其他类型(02 等)token 调 user/info 报"无权限"——只处理 03
- **主服(海外 128.241.x.x)调 user/info 全 code=100** → 必须国内采集机出网(同 token 立即成功)

## pack_map schema(消费者契约,必须遵守)

collector/bot 生态格式(企业 key=账号):
```json
{"enterprises": {"ACCT123": {
  "账号": "ACCT123", "用户": "", "单位": "企业全称", "ST": "", "时间": "...",
  "来源": "backfill8",  // 补漏标记(可选)
  "包件": [{"packId": "uuid", "packCode": "004", "packName": "...", "保证金": 15000,
            "报价模式": "单价", "物资条数": "1", "审核状态": "未审批", "审核码": "00"}]
}}}
```
- bot 读 `ev.get("包件")`(list)+ `pk.get("审核状态")`;写 `packs`(dict)格式 bot 读不到
- 审核状态值:通过/拒绝/未审批/空(空=该包件企业未走完报名提交/无审批记录)
- merger 会把 `ent_bk8_N` 类 key 按"账号"字段归一成账号 key——补漏写入直接用账号做 key

## 接口返回结构

- `getBuyPackageList?projId=<uuid>`:data **直接是 list**(不是 {result:[]}),item 含 packId/packCode/packName/frontMoney/payTypeName/detailNum/bidderCheckStatus/bidderCheckStatusName
- 解析兼容:`d if isinstance(d, list) else d.get("result", [])`
- 需带 Referer: https://cg.95306.cn/bfwz-view/(否则 500)

## orch8b 编排要点

- 主服 cron `5,35 * * * *`;rounds=4(4 个 30min 窗覆盖 2h),8 台每窗 2 台
- seen 文件 `/tmp/bk8_seen_<shard>.json` = {token: login_time},裁剪 >6h
- worker 先拉窗内 token(6 页×500 拉满,~3000/窗)→ user/info 识别企业名(0.08-0.12s 间隔)→ 匹配漏采名单 → getBuyPackageList 拉包件
- 每台 ~6-10 分钟/轮;命中率:全量首轮 43 家/4h,增量轮 5-13 家/30min
- 残余漏采 = 报过名但窗口外未登录的企业;登录即被下轮捞到;永不登录 = 物理边界

## 展示口径(菜单B)

- 列表/详情企业数显示 `🏢已采/平台`(如 2/3),平台名单更大时分子为采集数分母为平台数;无平台数据只显已采数
- 审核统计:`✅通过 ❌拒绝 ⏳未审批 ⬜无状态`(⬜ = 空审核状态,详情页每包件标注"⬜无审批")
