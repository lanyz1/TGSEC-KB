# AI 查询层截断类 bug:95306-v739(2026-09-03)

用户问题:"平台共18家报名,采集到6家,待补10家" 6+10≠18,差 2 家 —— **AI 有问题还是数据有问题?**
结论:**数据没问题,AI 查询工具层截断 bug**。此类 bug 是 LLM function-calling 数据助手的**类级陷阱**。

## 数据源三件套(95306 对账用)

- `index.json`:顶层 `{"updated","source","projects"}`,`projects` 键 = **项目 UUID**(如 5d75257d-...),值含 projName/projCode/status/stage/enterpriseCount。搜项目:遍历 projects dict,value 里匹配 projName(注意键名不含在 value 里,遍历要带 key)。
- `/data_pool/<UUID>/`:`pack_map.json`(enterprises 键=账号,**与中文单位键并存重复!** 遍历需按单位去重)、`包件清单.json`、`公告全文.json`、`企业包件表_18列_<projCode>.csv`。
- `plat_enroll_map.json`:顶层 `{"updated","start","end","projs"}`,`projs` 键 = **平台 projCode**(ON/OQ/OM 前缀,如 ON002026083108351207,不是 UUID);值 `{"企业数","企业":[企业名...],"公告日"}`。每 30min sync 更新,报名数实时变动。

语义(用户确认):报名企业 = plat_enroll_map(平台名册,projCode 索引);报名明细 = pack_map(我们采集)。
待补 = plat 名册有 ∩ pack_map 无。orch8b 补漏无地域过滤,省外企业一样覆盖。

## 根因:列表硬截断 + 无 total 字段

`ai_query.py project_enterprises` 返回 `"pending": pending[:10]` —— 12 家待补只给 LLM 前 10 条,
名单第 17/18 位(成都收荒匠、四川和记鑫城)被切。LLM 看到 plat_total=18 + pending 列表 10 条,
自然答"待补10家",且 6+10≠18 的漏洞它**无法察觉**(工具没给它总数)。

**类级规则:LLM function-calling 查询层,凡"count 全量 + 列表截断",返回必须带 total/count 字段,
并在 SYSTEM 提示里写明"报数量一律用 total,列表只是样例"。** LLM 无法自己发现列表不完整。

最严重案例:全库最大项目 OY002026082111027512(平台 64 家报名)→ 修复前 AI 只见待补 10/59。

## 修复清单(2026-09-03,共 11 处,全部验证)

ai_query.py:
1. `project_enterprises`: `pending[:10]` → `pending[:limit]` + `"pending_total"`;加 `"ent_total"`;limit 默认 50→100
2. `search_projects` / `bid_calendar` / `deadline_alerts`:去 `if len(out)>=limit: break`(纯内存循环,21747 项目毫秒级)→ `return {"total": len(out), "rows": out[:limit]}`
3. `audit_status`: detail limit 30→100(已有 total 兜底,只扩明细)
4. `search_enterprise` 10→50、`notice_search` 10→30(IO 重函数保留 break,不包装 total,靠 schema 注明上限)
5. `project_detail`: packs[:20] 旁已有 pack_count 全量,无需改(判定:有全量 count 字段即可)

ai_agent.py:
6. `scan_watches`:消费 search_projects 原 list → 适配 dict(`rows = hits.get("rows") if isinstance(hits, dict) else hits`)
7. tool 结果回传 LLM `[:6000]` → `[:12000]`(大列表要能完整送达;64×90 字符 ≈ 5.7KB)
8. SYSTEM 加规则:"search_projects/bid_calendar/deadline_alerts 返回 {total,rows},报数量用 total,rows 不够建议导出表格"

**兼容纪律:纯列表→dict 包装会破坏直接调用方**(如 isinstance(hits,list) 检查),改返回结构必须全库 grep 消费点同步适配。schema description 也应同步(但 SYSTEM 一条通用规则比逐个 schema 改省事)。

## 验证方法

函数级直接调(不重启 bot 也能验):`python3 -c "import ai_query; ..."` 或远程 import 测试:
十堰项目(5d75257d-8fe7-4fbf-b70c-410df871d61a):plat_total 18 / ents 6(去重后)/ pending 12 全量 ✓
64 家项目(0f7f0400-dff1-4f79-83ab-23e5d8ce9345):plat_total 64 / ents 5 / pending 59 全量 ✓
然后重启 bot(ai_query/ai_agent 被 pix_bot_server import,不重启不生效)。

## 顺带发现

- pack_map enterprises 账号键与中文单位键并存(同一企业两条),遍历计数需按 `_norm(单位)` 去重,否则 ents 虚高(8 条→真实 6 家)
- 平台报名在报名截止前持续新增(十堰 12→13 家待补,成都熊雄),对账时先看 plat_enroll_map 的 updated 时间戳,别把实时变动当数据缺失
- 观察器/日志纪律见 monitoring-pipeline-ops `references/deploy-observe-pitfalls-2026-09.md`
