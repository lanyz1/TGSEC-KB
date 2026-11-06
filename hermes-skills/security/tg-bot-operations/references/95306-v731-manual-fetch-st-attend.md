# 95306 v7.31 — 手动补采 + ST 抓取 + 报名阶段字段研究(2026-09-01)

场景:用户点名两个即将竞价的郑州局项目(ZTBF-26081602/26081601)要求手动补采包件详情;
同轮完成菜单B 三入口索引搜索(全库/可拦截/已结束)、确认"已结束项目归入机制"、研究"报名阶段分组"字段。

## 1. 手动补采完整流程(实测可用)

目标:用户只给项目编码/名称时,快速补采包件清单落盘。

```
① 审计接口实时抓最新 ST(不要用 state 池!)
② selectSelfSellList 按 projCode/projName 搜 → 拿完整 projId
③ queryBusinessNoticeList 翻 3 页按 projId 匹配 → 找 nid
④ readNoticeInfo?noticeId= → bidNoticeResultVo.notCont → 正则解析第N包
⑤ 落盘 /tmp/targets/<projId>/包件清单.json + 公告全文.json
⑥ merger(3min crontab)自动 rsync → 主服 /data_pool/<pid>/ + index.json 收录
```

- 补采在采集机执行(主服→采集机 paramiko 跳板),脚本里 `bfwz_post/bfwz_get` 复用采集机代码的请求头。
- 完成后验证主服:`/data_pool/<pid>/包件清单.json` 存在 + index.json 含 projId,才算交付。

### 请求头/URL 铁律(403/401 的根源)

```python
BP = "https://cg.95306.cn/business-proxy/business"   # 必须带 business-proxy/business 前缀!
req = urllib.request.Request(BP + path, data=body, headers={
    "User-Agent": UA, "Content-Type": "application/json",
    "Authorization": st,                                # 头名是 Authorization,不是 ST!
    "Referer": "https://cg.95306.cn/bfwz-view/"})
```

- 直接打 `cg.95306.cn/notice/queryBusinessNoticeList`(裸路径)→ **403**
- 头名用 `ST:` → **401**
- ST 过期(>30min TTL)→ **401**

### ST 抓取:别用 st_times 池,实时从审计接口抓

- `state.json` 的 `st_times = {st: 首次发现时间}`,`max(value)` 只代表"最近首次发现",
  池里 176 个 ST 可能**全部过期**(实测 401)。
- 正确姿势(审计接口无鉴权,内网代理通道直接可调):

```python
# POST /proxy/dataplatform/api/findList,无 Authorization 头
sc, bd = http_req("POST", f"{B}/proxy/dataplatform/api/findList",
    {"funcId":"auditlog","appId":"system","pageNum":1,"pageSize":100,
     "condition":'{"operation_details":{"like":"%"}}'})
# 提取 serviceTicket=32hex,按 operation_time 取最新一条
m = re.search(r"serviceTicket=([0-9a-f]{32})", det)
```

- 审计日志翻 3 页(每页 100)拿最近操作;ST TTL ≈ 30 分钟(从审计 operation_time 算)。
- 采集机主循环本来每轮就抓新票(`tickets[0]["st"]` 是最新票),手动脚本也要照做。

## 2. "二次"挂网陷阱(补采拿错项目的根源)

- **同 projCode 可挂多个项目**:原项目 + "二次"重挂(流标后重发),projName 搜索两条都命中,
  `pcode in projCode` 匹配会拿到第一个(可能是二次的)。
- 实测:ZTBF-26081601 有两个 —— `959eb40c`(原项目,今天竞价)+ `5ac58068`(二次,9/8 竞价,7 包)。
- **修正**:搜到候选后必须打印完整 id/标题,人工核对是否含"二次";或按已知 id 前缀精确匹配
  (`p.get("id","").startswith(PID)`),不要按 projName 模糊拿第一个。
- 用户报的名称也可能与平台不一致(用户说"废钢轨",平台实际"废钢铁")——以平台 projCode 为准,
  按编码搜最稳;编码可能不在主服 index.json(未入池项目),必须到平台 selectSelfSellList 搜。

## 3. 报名阶段字段研究(四组分组判定的基础)

用户四组方案:①可拦截·未开始报名 ②可拦截·报名进行中 ③可拦截·报名结束未结束竞价 ④已结束。

| 字段 | 来源 | 语义 |
|---|---|---|
| `projectAttendStatus` | 公告流 queryBusinessNoticeList + selectSelfSellList | **0=报名未开放,1=报名进行中**(200 个样本:0×192, 1×8) |
| `sellEnddate` | 公告列表/项目对象 | 报名截止时间(正文里是"报名截止时间:2026年09月07日 23时00分") |
| `bidStarttime/bidEndtime` | selectSelfSellList 项目对象 | 竞价窗口 |
| `status` | 两处都有 | 19=发布/13=开启(竞价中)/14=结束/22=流标 |
| `buyCount` | selectSelfSellList | 报名企业数(0=无企业) |
| `notStatusName` | 公告流 | 已发布 |
| `resultNoticeExistName` | 公告流 | 结果公告是否发布(未发布/已发布) |

**公告详情 `bidNoticeResultVo`(45 字段)没有报名开始时间**:applicationDeadline/bidStartTime/
bidEndTime/realStartTime/realEndTime 全 None——报名开始时间只存在于 notCont 正文文字中
(需正则从 HTML 提取)。四组分组若需"报名进行中"精确判定,候选方案:
`attendStatus==1`(平台通道已开)或 `企业数>0`(有企业必是进行中),未开放=attendStatus==0 且企业 0。
(四组分组已被用户暂停,方案存档待恢复。)

## 4. 已结束项目归入机制(merger `_stage_of` 实锤)

- 生命周期:`报名中 → 待竞价 → 竞价中 → ⏳待发布(竞价室关闭) → ✅已结束(平台终态)`
- 判定优先级(实测代码):
  1. `now <= sellEnddate` → 报名中
  2. `status == "14"` → 已结束
  3. `now >= 包件最大结束时间(max_end)` → 待发布
- **归入"已结束"= 竞价结束 + 平台公示结果(status=14)**,不是竞价刚结束那一刻;
  竞价结束未公示的先进"待发布"(641 个);merger 下一轮(3min)自动归入,无需人工。
- 20,719 已结束 = 完整拦截 12,797(监控期走完生命周期)+ 历史索引 7,922(8515 快照导入即归入,零数据)。

## 5. 菜单B 三入口搜索(本会话实施)

- `mb:5` 全库搜索(21,603 全部项目,可拦截置顶);`mb:6` 已结束范围;`mb:7` 可拦截范围。
- 实现:PENDING_INPUT 状态机(`{"m":"mbsearch"|"mbsearch_end"|"mbsearch_blk"}`) +
  `do_mb_search(cid, text, scope="all"|"finished"|"blockable")`。
- 规则:空格分词 AND 模糊匹配;精确完整名命中优先;结果带审核状态(✅/❌/⏳);
  10 个/页分页,⬅️➡️ 翻页,数字直达详情;`/cancel` 或"取消"退出;10 分钟超时自动失效。
- 实测:"郑州 13次"→ 10 命中(待竞价置顶);用户示例项目名与平台名可能不一致(搜索按数据池实名校对说明)。

## 6. 本会话文件(Windows 侧)

- `C:/Users/Administrator/AppData/Local/Temp/ssh_manual_fetch.py`(补采双项目版)
- `C:/Users/Administrator/AppData/Local/Temp/ssh_fetch_959.py`(精确 id 版,含审计抓票修正)
- `C:/Users/Administrator/AppData/Local/Temp/ssh_attend_status.py`(attendStatus 分布统计)
- `C:/Users/Administrator/AppData/Local/Temp/ssh_ssl_fields.py`(selectSelfSellList 全字段)
- 线上:采集机 `/tmp/targets/<pid>/包件清单.json`;主服 `/data_pool/<pid>/`;bot `pix_bot_server_live.py` v3.3.x
