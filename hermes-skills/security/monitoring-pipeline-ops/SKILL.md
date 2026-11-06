---
name: monitoring-pipeline-ops
description: "多机采集+主服合并监控管道运维: flock/滚动日志溢出/远程补丁。触发: 采集机, merger, 监控管道。"
---

# 多机采集 + 主服合并监控管道运维

适用:多台采集机(跳板机)定时拉目标接口 → rsync/SSH 回传 → 主服 merger 合并 → bot/告警推送的监控系统。此类系统的部署与排障坑高度重复,按本节逐一规避。

## 部署与补丁(远程 Linux 服务器)

1. **先 `ps aux` 查实际运行文件名**——服务器真身文件名常 ≠ 本地副本名(案例:主服跑 `pix_bot_server.py`,本地副本叫 `pix_bot_v3.py`)。**服务器文件可能比本地新**(字节数更大)→ 永远**增量字符串补丁**,禁止整文件覆盖。
2. **paramiko 远程补丁三件套**:
   - sftp 读返回 **bytes**:`code = s.open(path,"r").read().decode("utf-8","replace")`
   - 主服文件常带 **CRLF**:先 `code = code.replace("\r\n","\n")` 再字符串匹配,否则 old_string 永远匹配不上
   - 写回后**验证**:`py_compile` + `grep -c 新函数名`。**验证用 grep 函数名,不要用文件字节数**——CRLF/UTF-8 差异会让大小对不上(26,623 vs 23,738)但内容正确。
3. **本机直连采集机超时/不通 → 全部经主服跳转**:采集机只对主服开放 SSH;本机脚本模式 = 连主服(私钥认证)→ 主服上跑 Python → 主服连采集机(口令认证)。主服连接用 Ed25519 私钥(`pkey=`),**不是口令**;采集机连接用口令。
4. **部署后必看运行日志,不能只看 py_compile**:改过的代码可能引用**后置局部变量**(`now_ts` 定义在函数后段、前段提前引用 → UnboundLocalError,部署后全部采集机静默崩)。部署完 `tail` 日志确认新代码路径真的在跑一轮。

## 并发与任务调度

- **cron 周期任务必须单实例锁**:`*/5 * * * *` + 任务耗时波动(rsync 4 台慢时可超 5 分钟)→ 前后轮重叠并发写同一数据。main 入口:
  ```python
  try:
      import fcntl
      _lk = open("/tmp/job.lock", "w")
      fcntl.flock(_lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
  except Exception:
      sys.exit(0)
  ```
- 部署新版本后**等下一轮 cron 自然跑**(不要立即手动跑,可能与在跑实例并发);验证看日志轮次时间戳。

## 告警判定(滚动日志陷阱)

- **滚动日志溢出误报**:审计/操作日志是滚动窗口(如 500 条覆盖 1.5 天),"5 页全满"是**常态**不是溢出。**溢出必须按时间窗密度判断**:第 1 页内"最近 60 秒"的记录数 ≥ 页容量才算真溢出。按页满数判定会 4 台采集机天天误报。
- 告警"变化才推":merger 写 gaps.json 时对比上一版签名(缺口列表 JSON 串),`new` 标记;bot 读签名变化才 broadcast,否则每次轮询都轰炸。
- **心跳新鲜度 hb_age 会整体翻转符号**(2026-09-10 实踩):主服 `stat -c %Y /data_raw/<台>/heartbeat.json` 与主服时钟比较,同一小时内可从 `+62..+92s` 整体翻成 `-63..-88s`(主服 NTP 回拨或 mtime 由推送方写入)。**符号翻转 ≠ 采集机异常**,绝对新鲜(|hb_age|<120s)即健康;判活必须结合日志 mtime/处理行,别单看 hb_age。
- **verify_drain_monitor.py 的 DRAIN/SEEN 口径**:`DRAIN=len(state['drain'])`(未榨干完的排队项,非 0 是常态)、`SEEN=len(state['seen_st'])`(已见 ST 累计)。队列是否失控要看 **两点差分 + 入队/榨干事件数**:如 11 分钟 13 次入队 vs 总量 +8 项 = 榨干在消费队列(健康);只涨不消才是堵。
- **报前先读本 job 的历史报告去重(2026-09-11 实踩)**:本 job(cron id `e93ac7f7b11a`)历次交付留档在 `（朋友 Hermes 工作区路径，本库对应 tools/ops/）cron/output/e93ac7f7b11a/*.md`(含当时的 monitor 输出 + 上一轮的 Response)。判「有无新事件」前先读最近 1-2 份的 Response:同一 `入队`/`识别`/`榨干` 事件若上轮已报,**本轮不得重复报**。monitor 每 10 分钟 cron、只要时间戳变就触发,若每轮都深探+重报会轰炸。判据:本轮账本(DRAIN/SEEN 逐台)与上轮**完全一致** = 无新事件 → 走 idle 一行,不必再跑深探。深探脚本留档 `scripts/_drain_cron_*.py`(经主服 128.241.245.73:12971 + `~/.ssh/v6_master_key` 免密中转,只读)。

## 采集机"没在跑"的误判(日志去向陷阱)

- 判定采集机 idle/挂掉前先确认 **unit 的日志去向**:`systemctl cat v6collector | grep StandardOutput`。
  - 无 StandardOutput 行 → 应用日志进 journald,`journalctl -u v6collector` 可见。
  - `StandardOutput=append:/opt/v6/v6_run.log` → journald 只有 systemd 的 Started/Stopped 三行,**应用日志全在文件里**。
- 2026-09-10 实踩:新加入的 4 台(sh8-11)用 file 输出,监控脚本只 grep journald → 4 台恒"无事件",差点误判为分片配置错。实际 `v6_run.log` mtime 一直在涨、处理行/入队行齐全。
- **判活三板斧**:`stat -c %y /opt/v6/v6_run.log`(mtime)、`tail -400 /opt/v6/v6_run.log`、`pgrep -af collector.py`。任一活跃即健康;`journalctl` 空不能作为判据。
- 监控脚本应对 journal 空时回退读日志文件(verify_drain_monitor.py 2026-09-10 已加);同时机队从 8 台扩到 12 台(SHARD_NUM=12),别按旧注释的"8 台"写死列表。

## 采集机状态文件与回传

- 采集机落盘:项目数据写 `/tmp/targets/<projId>/` 子目录;**跨系统小文件(告警/报名记录/全量快照)写根级文件**(`_alerts.json`/`_enroll_ops.json`/`_ent_full_*.json`)。
- merger rsync 循环:`listdir("/tmp/targets")` 按条目分派——**以 `.json` 结尾 = 根级文件直接 get 到机器目录根;否则按子目录拉**(目录内文件拼 `pid_文件名` 前缀防冲突)。
- 采集机新模块部署后,**根文件出现要等下一轮采集+下一轮 rsync**(两段延迟),验证时别急。

## 只读探针伪影与长轮次基准(2026-09-11 实踩)

- **python-subprocess 探针在个别台全零**:经主服 `ssh 采集机` 跑「python3 读 state + subprocess 调 journalctl/md5sum/systemctl」的探针,杭州 sh1 **subprocess 全部返回空**(TODAY 计数全 0、PID 空、md5=?),但 state 文件直读正常 → 曾差点误判采集中断。同一台用 **bash 脚本(base64 解码后 `bash /tmp/x.sh`)** 复核:PID/active/md5/计数全正常。**结论:判定采集机状态一律用 bash 探针;python-subprocess 探针出现"全零但 state 可读"= 探针伪影,不是故障。**
- **长轮次是周期性重活,不是卡死**:sh4(上海2,目标最多 235 个)今日有 **11 轮 >300s**,最长 23 分 18 秒,中位 57s,长轮次约**每 50 分钟一次**(02:18/03:09/03:59/04:52/05:41/06:33/07:23/08:13)——周期重活(切片/全量刷新)所致。日志形态:`轮询开始 → 公告流/目标项目 N 个 →(逐目标拉取段长时间无输出 N 分钟)→ 过滤分布 → 候选 → 轮询完成`,期间 `重试队列 0 死票 0`。**判"卡死"必须看轮次时长分布(配对 开始→完成),不能只看日志空档。**

## 限频与资源纪律

- 新增"枚举全量"类接口(一个票/会话拉企业全部数据)必须限频:state 里存时间窗计数(如每小时 ≤4 次),超限跳过。
- 每台采集机 60s 轮询 + 多页拉取 + 逐 ST 拉包件:保持 sleep 0.4-1s,防 WAF 封禁。

## 参考

- `auditlog-ticket-harvesting` 技能下 `references/95306-session20-alerts-deploy-fixes.md` — 95306 实录:数据平台表停更检测、8515 历史全量(12万条)、企业全量接口、7 类告警闭环、上述陷阱全部实踩。


---

## 外部库增量（2026-10-11 分享包）

## 合并层新鲜度:面板/bot 矛盾抖动的第一嫌疑

- 症状即定位:**面板数字与 bot 推送反复互相矛盾**(同一项 4→6 / 6→4 / 4→6)、同时刻两边还不一致 ⇒ 先查**合并层的择优键**,别先改推送或显示代码——推送只是如实复述池内翻转。
- 择优键铁律:跨机副本合并同键记录,新鲜度用**来源文件 mtime(观测时间)**并落回记录(`_obs`);用记录内的上游时间字段(各机相同)时 `>=` 恒真,胜负交给 `os.listdir` 顺序 ⇒ 必然翻转。
- 改合并层必**计时首轮**(`ps -eo etime,time,pcpu` + 日志轮次配对):赋值换合并函数会把每轮耗时放大到 机器数×主体数×子项数(实测 2–4 分钟 → 8 分钟以上),超时立刻加快路径。
- 验证要**跨轮差分**:落盘 (主体, 子项, 状态) 签名,隔 1–2 轮比对;单看某一刻的值证明不了翻转已停。
- **幂等合并不重写 ⇒ 文件 mtime / 字段缺失都不是"合并坏了"的证据**:这类合并函数是 `if changed:` 才写盘(零变更不重写),于是 index mtime 长期不动、行内可能没有来源标记字段(`src` 之类)全是正常态(实踩:据此连判两轮"增量合并从没落地"皆误)。判合并完整度一律用**行级比对**:最新上游快照的行 vs 池内条目,数出 新增/落后/更旧 三类计数。
- 细节见 `references/merger-multirow-aggregation-and-verify-patterns.md`。

## 健康表假告警(非采集机目录)与告警文件写盘坑(2026-09-13 实踩)

- **/data_raw 下任何非采集机目录会被 write_health 当成第 13 台采集机**:merger.py `write_health()` 遍历 `os.listdir(RAW_DIR)`(RAW_DIR=/data_raw),目录没有 `heartbeat.json` → 状态 `❌ 无心跳` → bot `check_health` 广播「🚨 采集机告警」。实踩:`95306_full`(2026-09-12 新建的全量收割落地目录)19:25 触发假告警广播轰炸用户。**新建任何落地目录(全量收割/快照/导出)后,必须同步把目录名加进 `NON_MACHINE_DIRS`**——两个文件都要改:`/opt/v6/merger.py` + `/opt/v6/merger_v926_stage.py` 第 13 行(先例 m_snap=v9.25b,95306_full=2026-09-13),改后 `python3 -m py_compile` 校验;merger 每轮新进程、下轮自生效**无需重启**。**注意该列表只作用于健康/告警与机队口径** —— 合并器遍历 `/data_raw` 是按目录分派读取的,新建落地目录(如 `m_snap`)照样会被合并消费;别据此怀疑"抓到了没进池"(照此排查会空转数轮)。
- **健康判定阈值(v9.24 消抖)**:心跳 gap ≥600s 且**连续 2 轮**才标 `⚠️ 异常`(streak==1 = `🕒 延迟`);`heartbeat.json` 缺失/解析失败直接 `❌`(无 streak 门槛)。bot 侧 `❌` 与 `⚠️` 都广播,恢复后下次写盘时 pop。平台限流风暴(全队 user/info code=100 退避)期间会有 **1-2 轮瞬时心跳抖动告警**,10 分钟内自愈,属正常摩擦。
- **health_alert.json 写盘坑(bot 侧 pix_bot_server.py check_health)**:文件**只在有新告警时写盘**,已恢复项虽在内存 pop 但不立即落盘 → 残留条目**抑制同名再次告警**(直到下一次任意新告警写盘才清)。复测/清理:`cp -a /opt/v6/health_alert.json{,.bak} && echo '{}' > /opt/v6/health_alert.json`。
- **验证路径**:改完等一轮 merger(数分钟,看 health.json `updated` 变化)→ `grep -o '"status": [^,]*' /data_pool/health.json | sort | uniq -c` 应 12×`✅ 正常`、无 `❌ 无心跳`。


## 全文导航（已拆分）

主卡保留前 11 节；其余 3 节在 `references/full.md`：

- 主服 IP 被平台拉黑 → 采集机中继(2026-09-13 实踩)
- 机队实体台账、断供与到期诊断
- 对拍/手搓参考

加载：`skill_view(name='monitoring-pipeline-ops', file_path='references/full.md')`

> 全文较大（31309 字符），已分 3 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
