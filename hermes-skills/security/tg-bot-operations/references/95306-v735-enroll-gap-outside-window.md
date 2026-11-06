# 95306 v6 报名跟踪盲区:竞价窗口外项目的新报名漏采(2026-09-01)

## 用户现象
菜单B"已拦截竞价未结束"分组项目,报名企业和包件详情不增加。用户要求三选一判定:
**没更新 / 没采集到 / 企业还没报名**。

## 判定结论
**② 没采集到(漏采)**。不是 bot/merger 没更新,也不是平台没企业报名——
审计日志(enroll_ops)明确记录了新报名,但采集机没抓回来。

## 证据链(可复用判定流程)

### 第1步:数据池是否在更新(排除"没更新")
- 主服 index.json 的 mtime vs pack_map.json 的 mtime:merger 每 3min 重建 index,
  pack_map 由采集机写入、merger 合并。两者都在动 = bot 侧没问题。
- **index.ent vs pack_map.ent 不一致时**:index 是 3min 前重建的,pack_map 更新
  晚于 index → 下一轮 build_index 会跟上,不是 bug。检查 mtime 先后再下结论。

### 第2步:平台是否真的有人报名(排除"企业没报名")
- 采集机 state `/tmp/v6_state.json` 的 **enroll_ops**(报名操作记录,审计日志抓取):
  `{"notice:<noticeId>": {"账号": "报名时间"}}`,即每个公告下报了哪些账号、什么时间。
- 这是"谁报名了"的**权威证据**,比 pack_map 全——审计日志记了所有报名跳转操作,
  而 pack_map 只含采集机实际轮询抓到的企业。
- **notice→项目映射技巧**:enroll_ops 的 key 是 noticeId 而非 projId。把 notice 下某
  账号的报名时间 vs 数据池 pack_map 里该账号的时间逐字比对(如 ACE666 都是
  `2026-08-31 21:32:32`)→ 时间一致 = 同一笔报名 = 该 notice 就是该项目公告。
  (数据池搜 noticeId 往往搜不到,公告文件里不一定存 noticeId 字段。)

### 第3步:采集机是否在抓(判定"没采集到")
- 查各采集机 `state.targets` 是否含该 projId:
  `ssh 采集机 "python3 -c 'import json;st=json.load(open(\"/tmp/v6_state.json\"));tgs=st.get(\"targets\",{})'"`
- 4 台机(上海176/广州146/成都162/杭州160)全部不含 = 不在轮询范围。

## 根因:discover_targets 只有 48h 竞价窗口
`discover_targets(st)`(collector.py:155)只收录**竞价开始 48h 内**的项目。项目掉出
窗口后:
- 窗口期内报名的老企业(如 ACE666 8/31)已被抓住 ✓
- 窗口期后新报名(shd5688 9/1 09:36、yjh_248248 9/1 10:46)**无自动反查** ✗

即:**审计日志知道谁报名了(enroll_ops),但采集机只用当前 targets 里的 ST 轮询,
不会针对"已报名但未入库"的账号做补采**。这是"getBuyPackageList 单企业视角"
结构性缺口的实锤案例(企业视角:每个 ST 只能查自己报名的包件)。

## 关键接口/字段速查
- 审计日志:`POST /auditLog/page` 无需 ST;字段是 **operation_details /
  operation_account / operation_time**(不是 detail/logDetail,用错返回 0 条);
  分页 payload `{"funcId":"auditlog","appId":"system","pageNum":n,"pageSize":100}`。
- ST 提取:`re.search(r'serviceTicket=([0-9a-f]{32})', det)`;
  报名识别:`"redirectEnrollUrl" in det or "Enroll" in det or "报名" in det`。
- bfwz 业务接口:`GET {B}/business-proxy/business{supplierPackage/getBuyPackageList?projId=}`
  ,Header `Authorization: <ST 裸值>`(不带 Bearer)+ `Referer: https://cg.95306.cn/bfwz-view/`。
- 目标发现失败兜底:ST 过期/发现失败时 `targets = state["targets"]` 用上次兜底,
  心跳里写 `audit_overflow`(60s 内 ≥100 条 = 审计窗口溢出)。

## 修复方向(未实施)
merger 侧加"报名反查补采":比对 enroll_ops 报名账号 vs 该项目 pack_map 已有账号,
缺口 → 用该账号 ST 主动调 getBuyPackageList 补回包件。审计日志既是告警源也是补采触发器。

## 顺带验证通过
- fdaa139b(郑州铁路科技)pack_map 曾出现同一企业两条 key(单位名 key + 账号 key,
  henanyuye=河南省昱叶贸易有限公司)→ **merger 283-310 归一化已正确去重**
  (nk = ev.get("账号") or ek,时间取较新),主服当前文件干净,无需再修。
- 8515 快照链路 8/30-9/1 全程健康(详见 v734 reference),"8/31 停更"是接口
  瞬时全空被误判为限流;CHANGED=0 只是去重。
