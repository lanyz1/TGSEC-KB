# 平台接口字段边界 + 探针四坑（2026-10-09 实测）

## 1. 数据平台 findList 的边界（实验结论，勿再猜）

- 端点 `https://cg.95306.cn/proxy/dataplatform/api/findList`
- 行字段 **只有 9 个**：`bidder_name / bulletin_reldate / buy_time / proj_business_type / proj_business_type_name / proj_code / proj_name / proj_type / un_social_cr_code`

## 2. funcId 家族与参数（均为实验结论）

- **funcId 家族只有这一个**：13 个兄弟名（`…result` / `…package` / `…proj` / `…projlist` / `…notice` / `…detail` / `…win` / `…deal` / `…bid` 等）**全返 `code=-1 不存在的功能`**
- **参数只认 `startDate`/`endDate`**：`proj_code` 被忽略（rows=0）⇒ 只能按时间窗扫、再本地过滤 proj_code
- 同一 `(proj_code,bidder_name)` **会返回重复行**（实测 buy_time 差 30 秒）⇒ 消费侧必须按 bidder_name 去重取 `max(buy_time)`
- **无包件、无审核状态、无登录账号** ⇒ 「每企业通过/驳回包件矩阵」不可能从平台公开面拿到，只能靠企业自己的活票
- 反之 **企业名单 + 统一社会信用代码 + 报名时刻可免 token 拿全** ⇒ 这是需求①「平台权威名单完整度对账」的正解

## 3. `buy_time` = 一次必然登录（战术价值）

报名（买标书）必过登录 ⇒ `buy_time` = 「该企业曾登录」的权威时刻。
实测铁工锻造：平台 `buy_time` 10-02 15:18 → 我方表 `报名时间` 10-02 15:56 ⇒ **一次会话内完成「报名 + 提交包件」，且该会话 ≥38 分钟**。
⇒ 接住登录即可在同一会话拿到包件+审核状态；缺口收网窗口 = 竞价开始前（本项目 `2026-10-14 09:00~10:24`，它们必然再登录）。
⇒ **独立确认账号↔企业映射**：在 `[buy_time-20min, buy_time+20min]` 窗内扫 rail：① 已知账号是否在场 ② 登录时刻最贴近 buy_time 的候选账号 + `user/info` 回显企业名 ⇒ **可发现未知账号**（如上海海富华）。

## 4. 探针四坑（本轮新踩，都会让实验白跑）

1. **`rail_rows()` 返回 `(rows, fail)` 元组** —— 写成 `rows = w.rail_rows(a,b)` 再迭代，会把内层 list 当行 ⇒ `'list' object has no attribute 'get'`，探针秒崩。
2. **采集机上 `import master.bk_worker` 走 `/opt/v6/current` 旧树**，不是生产运行体（症状：`force_accts=0`）。生产 backfill 腿真跑 **`/tmp/bk_worker.py`**，orch 腿跑 `tools/gap_once.py` ⇒ 探针要显式指定 `/tmp/bk_worker.py`。
3. **票龄符号**：`lt - (utcnow+8h)` 得到的是「距现在」的负值；过滤 `age<0` 会把样本全丢（v2 的 TTL 档汇总因此为空）。正写 `age = (utcnow+8h) - lt`。
4. **「只取最新 N 个账号」永远只测到 0~2 分钟票龄**（rail 45 分钟窗 1200+ 行、最新票龄恒 1~2 分钟）⇒ 测 token TTL **必须按票龄分档取样**。

## 5. P1e 排序契约的实测自证（2026-10-09，真实 rail 数据 + 生产代码）

`p1e_order_test.py` 在 shard0 上跑（零写入：只读 rail + 内存排序）：

```
force=['m168988','SXXHFS888','d168988','hcxd<PHONE-REDACTED>','qikai1989']
fresh_since=2026-10-09 09:26:36  check_limit=1500  recheck_quota=0.15  user_types=('03','3')
GAPFIRST shard0: 新377 复查0 额度377
T1 PASS  合成新鲜缺口票 5/5 全在最前
T2 PASS  合成陈旧缺口票最靠前位置=376（被 372 条新鲜票压后）
```

⇒ 契约确认：**新鲜缺口票 rank 0 最先查；陈旧缺口票 rank 3 反被新鲜票压后**（P1d×P1e 自洽：不把额度浪费在死票上）。

## 6. 本轮被证伪的方法（别再走）

1. **「按 `buy_time` 就近匹配账号」= 噪声** —— 平台 40 分钟窗内有 722~1404 个账号登录（≈30 登录/分钟），任意时刻附近 1~12 秒内必然一堆账号 ⇒ Δ=1s 无身份含义。此法**无法**做账号↔企业确认；映射只能靠我方历史采集表的 `登录账号` 列（且 P1e 只改排序、企业名由活票 `user/info` 决定 ⇒ 无污染风险）。
2. **「按 userid 去重能大幅提升额度覆盖率」= 想当然** —— 实测 776 行/722 账号、1500 行/1349 账号 ⇒ 去重收益仅 **1.07~1.11×**，不值得改代码。
3. **「票龄越新 token 越活」= 不成立（至少不单调）** —— 实测 0-10 分钟 53%、10-30 分钟 53%、30-60 分钟 7%、60-120 分钟 60%、>120 分钟 0% ⇒ **死亡不是纯时间驱动**（疑被后续登录顶掉/会话超时）；唯一可靠结论 = **>2 小时必死**。
4. **「rail 行延迟 2-3h」= 不适用于 rail** —— 实测最新票龄 1~2 分钟、45 分钟窗 1200+ 行 ⇒ rail 实时。

## 7. 缺口快线（B 方案：已就绪、未启用；C 决策=10-13 再启用）

背景：6 家缺口只能靠活票收；它们必然在 **2026-10-14 09:00~10:24 竞价**时再登录（已 armed：P1e `force_accts` 排 rank 0）。

- 检测器 `gapfast.py`（**纯只读**，跑在**采集机**）：拉最近 `--win` 分钟 rail → 命中名单账号且 `user/info` 活 ⇒ 打印 `HIT <acct> | <企业名> | 票龄 X 分`、`rc=2`
- 自测姿势：`--dump-ids N`（看窗内最新账号/活跃度）、`--probe --force-test a,b`（用临时名单验证）⇒ **实测 6/6 HIT、rc=2**（真靶子 hengtonggroup 等，票龄 2~5 分）
- 包装 `gapfast_cron.sh`（主控侧 `*/3`）：ssh 采集机检测 ⇒ 有 HIT 才触发**一次既有生产补采腿**（`v6m.py backfill`，flock 保护），同账号 600s 冷却 ⇒ **不新增收割逻辑**，复用 P1e
- 启用/停用命令写在脚本尾部（停用=`crontab -l | grep -v gapfast_cron.sh | crontab -`）
- ★ 检测器**必须跑采集机**（主控直打 rail 报 `appId不存在`）；主控→采集机免密 ssh 已有
- 时段事实：BJ 凌晨 1 点仍有零星登录，2~5 分钟票 **6/6 全活**；白天 0-10 分钟档仅 53% ⇒ 存活率随时段/负载变化，不是固定 TTL 曲线

### 7.1 已安装（2026-10-11，用户「需要」点头）

- 采集机 shard0：`/root/gapfast.py`（md5 `04cb32c0b31a…`、compile OK）＋ `/tmp/gapfast.py` 同 md5
- 主控：`/opt/v6/gapfast_cron.sh`（md5 `afd505498017…`、`sh -n` OK），crontab 新增：
  `*/3 * * * * cd /opt/v6 && flock -n /tmp/v6_gapfast.lock bash /opt/v6/gapfast_cron.sh >> /tmp/gapfast_cron.log 2>&1`
- **回滚一行**：`crontab /root/crontab.bak_20261011_gapfast`（28 行基线）
- 触发链测试钩子：`GAPFAST_ARGS="--probe --win 30 --force-test a,b" bash /opt/v6/gapfast_cron.sh`
- 状态：冷却标记 `/tmp/gapfast_hits/<acct>`（mtime 600s）＋ 命中流水 `/tmp/gapfast_hits/log.txt`
- 双层锁：外层 `/tmp/v6_gapfast.lock`（防包装重叠）＋内层 `/tmp/v6_backfill.lock`（与 `15,45` 正班轮互斥）
- ★ 坑：本地 scratch **根目录**文件会被 prune 清掉（子目录存活）⇒ 交付物放子目录（`cache/scratch/v6_95306/`）或服务器 `/root`
- **触发链已实测（2026-10-11 05:43 UTC）**：4 个真靶子（`ZTWGDKJFWJT` 等，票龄 0.3~0.5 分）⇒ `log.txt` 记录 + 4 个冷却标记 ⇒ **05:43:20 生产补采腿进程启动**（`ps etime` 反推，命令与正班轮完全一致）
- cron 自身已确认在跳：`/tmp/gapfast_cron.log` 每 3 分钟一行 `检测: rows=NNN 命中账号=0/5`（白天 20 分钟窗约 250 行）
- ★ **日志前缀坑（连坑两次）**：编排腿（`2-59/5`）与补采腿（`15,45`）**都打 `[orch HH:MM:SS]` 前缀** ⇒ **不能按前缀判腿**。判腿只能按**排程**：`:15/:45`=补采腿、`2-59/5`=编排腿、其它分钟=**快线触发**。
- **快线触发轮完整实测（2026-10-11 05:43 UTC）**：命中 05:43:18 → `[orch 05:43:19] 名册：缺企业 178…` 起轮 → 05:43:32~05:44:50 扇出 12/12 → `05:52:49 DONE 12 回写 12 新增包件 0（超时 0 台）`，整轮 9.5 分钟。
- 冷却分支已加诊断行 `[冷却中] <acct>`（早期版本静默，易误判为故障；实测 `[ 3 -lt 600 ] → continue → 空触发文件 → exit 0` 为正确行为）。
- 测试痕迹处置：`/tmp/gapfast_hits/log.txt` → `log_test_20261011.txt`；合成冷却标记宜删。
- 线上 crontab 位置：`*/3` 行在 `# <<< v6master <<<` **之外** ⇒ 不会被 `deploy/master_deploy.py` 重生成吃掉。




