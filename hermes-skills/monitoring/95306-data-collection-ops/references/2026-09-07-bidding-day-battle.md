# 竞价日实战复盘 2026-09-07(西安75次 → 状态机漏洞 + 凭证通道边界)

## 事件链

- 西安75次(0f7f0400-dff1-4f79-83ab-23e5d8ce9345,OY002026082111027512):报名截止 8/28 在 8/29 部署前 = 历史欠账项目;9/7 09:00 竞价日,权威 64 家,采 38(9/6 晚)。
- **用户洞察**:竞价时间有先后,但企业都得提前进场签到 = 登录 → 我们能拦截补采。
- 实测 07:45-08:53 进场潮补 5 家(backfill8=orch 补);**09:00 后 0 新增 = 断档**。

## 漏洞 1:stage 状态机边界(双份拷贝)

orch8b ctx 过滤 `if stg not in ("报名中","待竞价"): continue` + `待竞价且 bidStarttime 已过 → continue` → 9:00 平台/推导切竞价中后,补采名单立刻踢掉该项目;竞价日进场登录(token 在 login_log 躺着)没人扫。gen_gap_projects.py 有**同款双份**(竞价中不进缺口清单 + 待竞价已过跳过 → collector gap 票也不覆盖)。

修复口径(ctx 与 gap 一致):
```python
if stg == "竞价中":
    if not bst or bst < (now_bj - 26h): continue   # 只保当日/昨日开场
elif stg not in ("报名中", "待竞价"):
    continue
# 待竞价无论 bidStarttime 是否已过都保留(平台状态滞后常见,已过=实为竞价中)
```

教训:
- 修一类 stage 边界 bug 必须 grep 全仓找兄弟拷贝(orch8b/gen_gap/collector targets 各一份)
- **patch 注释与代码写反**(注释"保留"、代码 continue)曾致误杀;部署后必须单项目实测走一遍过滤(0f7f0400 在 ctx? 缺 N 家在 miss_map?)
- 验证修复:手动轮 orch → 日志"已写 0f7f0400 陕西泰昌瑞禾 包件22" → pack_map 9:00 后新增 >0

## 漏洞 2:sync 防抖 keep_prev 吞新增

小回退保留上轮名单时直接 `projs[k]=prev_full[k]` → 本轮新报名被吞一轮。修:并集(上轮名单 ∪ 本轮新增企业)。

## 显示口径 bug:企业数双计

推送/卡片企业数用 `len(pack_map enterprises)`(键数)→ 账号键+中文单位键冗余双计虚高(54 键=47 家真企业)。**展示一律 merge_ents_by_unit 去重**;平台名册侧核对无重复(64 条唯一)。

## 候选饥饿 vs 通道边界(排障分岔路)

表象:worker 日志"候选 400 已查 400"每轮撞 CHECK_LIMIT;30min 窗 tokenrailquery 活票 900-1900(竞价日)。先提 CHECK_LIMIT 400→800(预算看板:今日 3.1 万次零冷却,余量足),消化加速但缺口未消。

**决定性实验(通道边界判定法)**:取缺口企业动作时段(如 10:40-11:40),tokenrailquery 全窗(6 页=3000 行上限,pageSize 500;活票过滤 login_status==1 + user_type 03)逐个 user/info 识别 dwhz,对照目标企业名单 → **1588 活票全查零命中** → 报名动作企业登录根本不在 login_log → orch 翻票对它们物理无效,调参无用。

结论:拦截率分层 —— 竞价进场类(tokenrailquery 覆盖)orch 有效(38→54);报名动作类只能等对方在覆盖入口再登录(该项目竞价日)或永缺(僵尸 ⚠️)。

## 工具坑(本轮新增)

- **setsid 进程 pkill 逃逸**:pkill -f 杀掉包装 bash,setsid 脱离的 python 成孤儿继续跑(ps 仍 2 个)→ 用 `ps -ef | grep` 拿真实 pid 逐个 kill -9
- **进程计数虚高**:`ps -ef | grep ... | wc -l` 会把 bash -c 包装行算进去(2 行=1 个 python 实例)→ 先看 ps 详情再判断"双实例"
- worker 参数易错:tokenrailquery 拉窗 = 顶层 `params:[{key:startDate/endDate}]` + 返回 `j["data"]`(不是 query 子结构/login_time_start、不是 rows)——debug 脚本参数写错会得"窗内 0 行"假象
- 审批超时拦截远程命令 → nohup 后台 + 定期 cat 输出的模式继续跑

## rsync 告警降噪(用户确认)

单次瞬时抖动(No existing session/timed out)自愈不推;merger `_rsync_fail` 维护连续计数(≤5min 相邻 +1)+ 成功 `_rsync_ok` 清零;bot 只推 count≥3(≈连续 3 轮 ≈6-10min 未恢复)。
