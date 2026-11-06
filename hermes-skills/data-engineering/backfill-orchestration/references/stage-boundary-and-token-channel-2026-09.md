# stage 状态机边界 + 凭证通道覆盖边界(2026-09-07 类级教训)

> ⚠️ 更正指针:本文件修正并取代 `references/orch8b-scope-input-stale-2026-09.md` 第 1 节的旧口径
> ("竞价已开始,不再补" —— 2026-09-07 竞价日实战证明该逻辑错误,详见下方及 95306-data-collection-ops `references/2026-09-07-bidding-day-battle.md`)。

## 1. 补采 ctx 的 stage 过滤:三个状态都要收,别按"时间已过"剔除

错误史(两次迭代才修对):
1. 只补 `stage=="报名中"` → 报名截止后转待竞价即放弃 → 截止前扎堆报名的漏采永久遗留;
2. 补 报名中+待竞价,但 `待竞价且 bidStarttime<now → continue`(认为"竞价已开始,不再补")→ **竞价日 9:00 切竞价中后补采全停,进场签到潮(企业必登录)= 历史欠账项目最后补采窗口被整段丢掉**(9/7 西安75次实测:进场潮 07:45-08:53 补 5 家 → 9:00 后 0 新增 → 断档 1.5h)。

正确口径(orch8b ctx 与 gen_gap 缺口清单一致):
```python
if stg == "竞价中":
    bst = str(info.get("bidStarttime") or "")[:16]
    if not bst or bst < 平台时间系now-26h:   # UTC+8,勿用服务器UTC直比
        continue   # 只保当日/昨日开场
elif stg not in ("报名中", "待竞价"):
    continue
# 待竞价不按 bidStarttime 剔除:平台状态滞后常见,"已过"=实为竞价中,保留
```

过程教训:
- **修一类 stage 边界 bug 必须 grep 全仓找兄弟拷贝**——同一过滤在 orch8b(ctx)/gen_gap(缺口清单)/collector(targets)各写一份,只改一处 = 漏洞残留一半;
- **patch 注释与代码写反**(注释"保留"、代码 continue)曾致新一轮误杀 → 部署后单项目实测(该项目在 ctx?缺口企业在 miss_map?)再收工;
- 竞价日修复后验证:手动轮 orch → 日志"已写 <pid> <企业> 包件N" → pack_map 当日新增 >0。

## 2. 翻票通道的前提是"动作=登录=留痕"——先验证通道覆盖,再调参

症状分级(按成本从低到高):
1. worker 日志"候选 N 已查 N"(每轮撞 CHECK_LIMIT)→ 消化延迟,提速上限即可(先看预算看板:实测零冷却才有余量;存量/每轮上限 = 需要轮数);
2. 提速后缺口不动 → **别再怀疑队列**,做通道边界实验:
   - 取缺口企业动作时段(名册 buy_time)→ tokenrailquery 全窗拉取(6 页=3000 行上限;活票过滤 `login_status=="1"` + `user_type` in (03,"3"))
   - 窗内活票逐个 user/info 识别 dwhz,对照 ctx 漏采名单
   - **零命中 = 该动作类型根本不在此日志**(物理边界),调 CHECK_LIMIT/seen/排序全部无效
3. 实测结论:tokenrailquery/login_log 只记录部分登录入口(竞价进场签到等);报名动作(business 域/持续会话)不产生新行。同一权威名单可能两拨企业:覆盖入口登录的(通道有效,补得到)vs 报名动作的(通道无效 → 等对方在该项目竞价日进正规入口,或永缺=僵尸 ⚠️)。

## 3. 接口参数照抄 worker 生产代码,别凭记忆

tokenrailquery 拉窗正确形态:顶层 `params:[{"key":"startDate","value":..},{"key":"endDate","value":..}]`(不是 query/login_time_start 子结构),返回取 `j["data"]`(不是 rows),字段 login_status/user_type/token/login_time。debug 脚本参数写错会得到"窗内 0 行"假象(全平台 40 分钟无人登录不可能)。

## 4. 进程管理坑(编排重启场景)

- **setsid 脱离进程 pkill 逃逸**:pkill -f 杀掉包装 bash,setsid 的 python 成孤儿继续跑(ps 仍显示 2 个)→ 用 ps -ef 拿真实 pid 逐个 kill -9;
- **进程计数虚高**:`ps -ef|grep|wc -l` 把 bash -c 包装行算进去(2 行 = 1 个 python 实例)→ 判断"双实例"前先看 ps 详情;
- 单实例锁被并发轮误 rm 会放两个编排实例进窗 → 撞轮时(日志"已有实例")让 cron 轮跑完,别 rm 锁抢跑。

## 5. 展示口径:键数 ≠ 企业数

pack_map enterprises 键含账号键+中文单位键冗余(同企业双键)→ 展示层(推送卡片/菜单统计)一律按单位去重(merge_ents_by_unit),否则虚高且"修复后数字变小"会误导用户以为倒退。权威侧(平台名册)核对无重复后再谈缺口。
