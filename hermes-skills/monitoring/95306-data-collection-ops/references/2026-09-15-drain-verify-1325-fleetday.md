# 2026-09-15 13:2x drain 修复「全队当日」终验 + 三个新坑

## 一、结论:drain 修复(去 `_my_acct` 二次分片)当日全队生效,四路证据同时成立

1. **跨机同键(主证据,§9-14 口径)**:当日 16 个入队账号键中 **11 个跨多台入队**。
   - 12 台全中(6 键):`hnss455590759`(08:39:52-08:43:12)、`LS537150006`、`gengen169`、`hezehangmo`、`laimin`、`liushuanji9999`(均 00:0x-01:0x)
   - `sxtyljb012001` 11 台、`schjxc003` 6 台(sh0/1/2/3/6/11)、`hbyutie` 3 台(sh5 09:12:59 / sh6 10:23:07 / sh1 12:57:16)
   - 2 台:`Chenyan123456`(sh5 12:02:39 + sh0 12:32:03)、`LZYSC147369`(sh0 12:49:03 + sh10 12:55:19,相隔 6min)
   - 旧版 `hash(acct)%N` 下同键最多出现在 1 台 ⇒ 账号级二次分片确已移除。
2. **当日计数(全 12 台,当日-only)**:`drain 入队` **102 次 / 158 项目**,`📦 榨干队列` **57 轮 / 158 项目**。
   逐台:sh0 14/6、sh1 9/5、sh2 8/5、sh3 8/5、sh4 7/4、sh5 9/5、sh6 10/4、sh7 7/4、sh8 7/4、sh9 7/5、sh10 8/5、sh11 8/5。
   **与 monitor EVID 末行 `入队=x 榨干=y` 逐台完全一致(12/12 对账通过)** ⇒ monitor 的 EVID 段可信,可直接引用。
3. **`跳过(分片)` 当日全 12 台 = 0**(journald ∪ 文件两路各查;该分支是死代码,不能单独当判据,见 §9-14)。
4. **版本一致**:全 12 台 `md5(/opt/v6/collector.py)=525edd501d603159528b8cd13f567f6d`(较 §9-14 的 v9.32 `f8f3e26d…` 又更新过),
   mtime `2026-09-14 15:44:36`(sh0)→`15:45:57`(sh11),`ExecMainStartTimestamp` = mtime + 1s(逐台递增=逐台部署),`MYACCT=2`(仅剩定义+注释)。

## 二、当轮(13:05-13:25 窗)状态 = 纯 idle

- 12/12 `SSH_OK`,无 `ERR/TIMEOUT/refused/denied`;loop 364-490s(<1800 无 `LOOP_LAG`)。
- 窗内 `drain 入队 | 榨干队列 | 识别 [1-9] | 跳过(分片)` **全 12 台合计 0 条**;
  各机仍按 ~90s 周期跑 `审计 ST 371-375, 新 126-184` → `↳ 候选 39-64(new_t …) → proc 40 (新40/重试0)` → `轮询完成 新企业包件 0, 识别 0`
  ⇒ **候选>0 全是账号冻结期的 churn(§6/§8),不是新票**。末次入队仍停在 sh1 12:57:16 / sh10 12:55:19 / sh0 12:49:03 / sh6 12:23:34 / sh5 12:02:39,其余 7 台 08:39-08:43。
- **队列分布(13:23 逐台实测 state,acct=len(drain) / proj=Σall / pend=待榨 / SEEN=len(seen_st))**:

  | 机 | acct | proj | pend | SEEN | cooldown_until(北京) |
  |---|---|---|---|---|---|
  | sh0 上海 | 30 | 57 | 1 | 514 | 13:30:16 |
  | sh1 杭州 | 19 | 34 | 1 | 1017 | 13:28:51 |
  | sh2 广州 | 22 | 36 | 0 | 1068 | 13:31:08 |
  | sh3 成都 | 25 | 42 | 0 | 1032 | 13:23:49 |
  | sh4 上海2 | 28 | 44 | 0 | 800 | 13:34:48 |
  | sh5 成都2 | 23 | 36 | 2 | 771 | 13:23:53 |
  | sh6 青岛 | 18 | 31 | 6 | 794 | 13:31:48 |
  | sh7 深圳 | 22 | 40 | 0 | 774 | 13:22:46 |
  | sh8 上海3 | 34 | 61 | 0 | 439 | 13:27:48 |
  | sh9 武汉 | 19 | 35 | 0 | 454 | 13:36:00 |
  | sh10 乌兰察布 | 23 | 40 | 0 | 453 | 13:29:42 |
  | sh11 河源 | 19 | 41 | 0 | 441 | 13:28:24 |

- 全队 pend=10,集中在 sh6(6:`hbyutie`1/`ylxyix`1/`henanhuaque`4)、sh5(2)、sh0(1 `Chenyan123456`)、sh1(1 `hbyutie`)。
  **滞留原因 = 机器级冷却(`cooldown_until` 滚动在 +5min 内)+ 账号级冻结(日志 `🧊 冷却升级(…): 冻结到次日 09-16 00:10(北京)`)**,非 drain bug(§8)。→ 09-16 00:10 北京解冻后这批会自动榨干。
- 口径:任务描述「8 台 SHARD0-7」过时,实为 **12 台 SHARD0-11**(脚本 `SHARD_NUM=12`)。

## 三、本次新踩的坑(必须记住)

1. **cron 归档 md 只保留头 ~3 行输出** ⇒ 用 §11 的 `grep -h -o "EVID …" $(ls -t *.md|head -3)` 做「全队跨轮 delta」时,
   **sh3-sh11 在 md 里根本没有**(只 sh0/sh1/sh2 存活),会误判成「no EVID on one side」。
   → 全队跨轮 delta **必须**自己重跑当日 sweep,或用窗口脚本 `D:\tmp\_fleet_win_*.py`(`journalctl --since "… 13:05:00"`,sh8-11 走 `tail -40000 /opt/v6/v6_run.log | awk` 按 `[MM-DD HH:` 过滤)。
2. **主服 sshd 会被本机高频 sweep 短时拒连**:13:13/13:14/13:15 连跑三轮全 12 台 paramiko 跳转后,13:16 出现
   `TimeoutError [WinError 10060] ... 128.241.245.73:12971`(ssh 也报 `connect to host ... port 22/12971 timed out`),**等 ~90s 单连即恢复**。
   → 一轮 sweep 只用**一条** master 连接做内部跳转,台间 `sleep ≥1.5s`,**不要连跑三轮**;若监控 cron 恰在此时跑会误报 `ERR`,需分清「本机自致限速」vs「机器失联」。
3. **`scripts/_drain_fleet_sweep.py` 源选择缺陷(本次已修)**:原「journalctl 输出非空 → 用 journald」在 sh9/sh11 上 journald 非空但无应用行 ⇒ 误报 `入队=0 榨干=0`(实际 7/5、8/5);
   且 `DRAIN=` 用内嵌双引号 `python3 -c` 静默失败(只输出空的 `DRAIN=`)。修法:**journald ∪ 文件 → 去 journal 前缀 → `sort -u` 去重**,state 用 heredoc 读并自动搜索 `/tmp/v6_state.json` 等路径,新增 `KEYS=`(当日入队键集合,直接看跨机同键)。

## 四、复现命令

```bash
# A. monitor 全量原文(12 行)与逐行 EVID
cat "C:/Users/Administrator/AppData/Local/hermes/profiles/123/cron/output/e93ac7f7b11a/monitor_last_output.txt"
# B. 全队当日 sweep(入队/榨干/跳过 + 版本 + 队列/待榨/冷却)
cd "C:/Users/Administrator/AppData/Local/hermes/profiles/123/skills/monitoring/95306-data-collection-ops/scripts" && python _drain_fleet_sweep.py
# C. 跨机同键判定(把 B 的 LASTQ 逐台收集后按 key 归并)
python D:/tmp/_fleet_enq_sweep_1311.py     # 输出 D:\tmp\_fleet_enq_1311.json
# D. 指定时间窗原文(查「本轮有无新入队」最直接)
python D:/tmp/_fleet_win_1325.py
```
