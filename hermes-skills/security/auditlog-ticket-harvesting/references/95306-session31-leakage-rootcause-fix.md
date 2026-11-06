# 95306 v6 漏采三层断裂根因 + 四管齐下修复(2026-09-01, session31)

## 漏采实锤(最终真相)

**真漏采项目 = 十堰 5d75257d**(不是乌鲁木齐 d74a341a)。证据链:
- f1dd4a3c950c 完整 ST 解出 = Ajt3211(丹阳市江腾再生资源有限公司),其 `getSupplierPackageList?statusGroup=buyed` 列表**明确含 5d75257d**,但项目 pack_map 里没有它。
- **enroll_ops 记录的是"打开报名页"(redirectEnrollUrl 跳转)≠ 提交成功**。此前误判"乌鲁木齐 3 家漏采"即因此——d74a341a 三家(ACE666/shd5688/yjh_248248)只有跳转记录,getBuyPackageList 全 ST 池试调零命中 = 没真提交。
- 4b7aa2c2 公告映射矛盾定案:`readNoticeInfo?noticeId=4b7aa2c2-ffd7-4906-8fcc-c44eb920c3bd` 实锤 projId=d74a341a(乌鲁木齐 OR002026083111263589),notices_map 映射**正确**。之前"时间戳与 5d75257d pack_map 一致"只是同批审计日志。

## 根因:三层断裂(全链路)

1. **collector.py `if st in seen: continue`(630 行)吞票**:企业登录产生的 ST 早已在 seen_st 里;后续报名操作同 ST 再出现 → 被跳过。`enroll_st` 延迟补拉入队代码在 seen 检查**之后**,永远执行不到 → 报名数据永不补拉。
2. **notices_map.json 是 8/30 一次性静态文件(72 条),无任何代码更新**:报名审计只记 `noticeId=xxx`(跳转 URL 只带 noticeId 不带 projId);不在映射表 → merger 归入"待确认缺口" → **不告警不处理**。
3. **merger `check_gaps` 只写 gaps.json 不补采**;且 bot 告警签名只比对"项目包件缺口+企业报名缺口+采集机告警",**待确认缺口不算变化 → 永远不推**。

## 四管齐下修复(全部实装验证)

### ① 存量补映射:187 待确认 → 0
- 30 个未映射 notice 从各采集机 `_enroll_ops.json`(key 前缀 `notice:`)找回**完整 36 位 UUID** → `readNoticeInfo?noticeId=<full>` 逐个反查 `data.bidNoticeResultVo.projId` → 写回映射。
- **readNoticeInfo 必须完整 UUID,8 位前缀必失败**;完整 UUID 从 enroll_ops 恢复(29/30 上海找到,1 个在杭州)。
- 结果:notices_map 72 → 905 条;待确认缺口 187→0;企业报名缺口 76→263(历史报名归位,进入告警池)。
- 反查示例:`{"bidNoticeResultVo": {"id","key","projId","projCode","notTitle","pubTime",...}}`。

### ② seen_st 吞票根治(collector.py,4 台)
- 补丁:`proc` 循环**之前**、遍历**全部 tickets**(不只 proc 名额内 15 个):`if _t.get("enroll") and _t["st"] not in state.get("enroll_st",{}): 入队`。
- 删除 proc 内旧入队块(seen 检查之后那段)。
- 验证:重启后日志出现 `🔁 延迟补拉成功: henanyuye 3 项目 / Ajt3211 2 项目 / a<PHONE-REDACTED> 10 项目 / cuidongxu 7 项目 / Xzh112211 1 项目`——**之前永远触发不了的队列真的在工作**。

### ③ merger 自动维护 notices_map
- 采集机:每 30 分钟用最新 ST 拉公告清单 → `_notices_map.json`(随 rsync 回主服)。参数:`POST /notice/queryBusinessNoticeList`,body `{"projType":"02","notTitle":"","noticeType":"01","dateType":"","pageVo":{"pageNum":pg,"pageSize":100},"isjtgsCode":0,"validOr":"1","orderField":"","orderType":"","onweb":"","jointSaleType":"","noticeStatus":""}`,返回 `data.result[]`(字段含 id/projId/notTitle)。**必须带 Referer:https://cg.95306.cn/bfwz-view/**,否则 500。
- merger:check_gaps 里 NMAP 加载后合并各采集机 `_notices_map.json` + **扫描数据池已有 `包件清单.json` 的 公告id→projId(零请求兜底)**;变化才写回。
- 效果:日志出现 `notices_map 自动更新: 904 条`。
- **注意公告清单只覆盖近7天/02类型/validOr=1**——更早公告映射不到,属正常;靠 readNoticeInfo 存量反查补。

### ④ 告警闭环
- bot `check_gaps_alert()` 在 `health_checker` 线程每 5 分钟跑;签名(sig/ent_sig/alert_sig)变化才 `broadcast`。**待确认缺口原本不进签名 → 修复后映射归位成企业报名缺口才进告警**——这本身是设计漏洞,已通过①消除。

## 部署/运维陷阱(本次实踩)

- **4 台采集机**:上海 8.133.188.178(SHARD0)/ 杭州 121.43.97.73(SHARD1)/ 广州 8.138.236.124(SHARD2)/ 成都 47.108.152.60(SHARD3)。**打补丁必须 4 台全同步**——只打一台会漏。
- 三层部署模式:本地 paramiko → 主服(Ed25519Key `C:\Users\Administrator\.ssh\v6_master_key`,`username="root"` 用 pkey **不是 password**)→ scp 补丁脚本到采集机 → 执行 + `systemctl restart v6collector` + `systemctl is-active` 验证。
- **merger 单实例 flock 锁**:cron 持有锁时手动 `python3 merger.py` **静默 sys.exit(0) 零输出**——不是没跑,是被锁。验证用 gaps.json 的 `time` 字段是否刷新,或 sleep 90s 等 cron 下一轮。
- **Python 作用域陷阱**:collector.py 里 `now_ts = datetime.now()` 在第 3 节才定义,第 2 节(目标发现后)插入补丁引用 now_ts 会 NameError——补丁内用局部 `_dt = datetime.now()`。
- **paramiko 嵌套三引号**:外层 `r'''...'''` 内再嵌 `'''` 会提前终止字符串(lint 报 SyntaxError);外层改 `r"""` 内层 `'''` 即可。
- 采集机 `v6_state.json` 是**轮询结束才 save**——中途设置的 state 字段(如 notices_map_ts)当轮读不到,属正常。
- 上海采集机日志 `grep '公告映射表|延迟补拉' /tmp/v6_collect.log` 是验证补丁生效的最快方式。

## 同类问题排查清单(通用)

1. 有"已见票去重"的地方,检查关键操作(报名/提交/审核)的处理是否在去重之后 → 必吞。
2. 有静态映射表的地方,检查是否有代码写入它;报名跳转只带短 ID 的平台,映射表断链 = 静默漏采。
3. 告警签名是否覆盖所有缺口类型——"不告警的缺口"= 没人知道的漏采。
4. 审计日志记录的是**跳转 URL**(redirectEnrollUrl)不是业务提交——区分"打开页面"与"完成操作",以最终业务状态为准(证据规则:运行行为 > 日志记录)。
