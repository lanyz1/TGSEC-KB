# 发布上线 + 生产侧验证(主控 + 12 台采集机)

改造完成 ≠ 上线;上线 ≠ 生效。**闸口输出不算发布成功,生产侧的「消费者证据」才算。**

## 三条铁律(每次发布都适用)

1. **deploy 工具自报的 `verify OK` / `activate OK` 只证明「文件到位」,不证明「新代码在跑」。**
   每条改造都必须到**它自己的输出侧**取证:新模块的**自有日志前缀**、产物时间戳、下游读到的东西。
2. **跨源时间戳对齐**:生产端把「本产物生成时刻」写进日志/产物,消费端读到后原样打出 ⇒ 两端同一个时间戳 = 链路真通。
3. **发布前先写出回滚点**(上一版 rel 名 + `activate.<ts>.json` 记录文件名),发布完一起报。

## 8 关发布链(本机 `/d/95306c` 起,主控收口)

① 本机 verify(不过不许打包):

```bash
cd /d/95306c && mkdir -p logs_rel && python deploy/verify_release.py > logs_rel/verify.txt 2>&1 && echo VERIFY_OK || echo VERIFY_FAIL; tail -22 logs_rel/verify.txt
```

② 打包 `ST=$(date +%Y%m%d%H%M) && python deploy/build_release.py --out dist --stamp $ST` ⇒ 记 tar sha / 文件数。
   **★文件数必须核**:改 N 个文件、其中新建 M 个 ⇒ 新 tar 文件数 = 上一版 + M。对不上就是漏打或多带(`*.bak`/`__pycache__`/`*.pre_split_*` 不得随包发出)。
③ 传包 + **双端 sha 对齐**(本地 `sha256sum` vs 主控 `sha256sum`)+ 字节数。
④⑤ **必须在主控上跑**(fleet_deploy 要读主控 `/opt/v6/jumpers.json`):

```bash
cd /opt/v6/current && python3 deploy/fleet_deploy.py --tar /tmp/<rel>.tar.gz --sha <sha> --stage
python3 deploy/fleet_deploy.py --rel <rel> --activate --yes   # 不带 --yes 拒跑;带 = 必定 systemctl restart v6collector
python3 deploy/fleet_deploy.py --rel <rel> --verify           # 只读:12/12 active + NRestarts=0
```

   `--activate` 的备份是 `cp -a` **覆盖式、非幂等** ⇒ 同一台只激活一次,别重跑。
⑥⑦ 主控割接 `master_deploy.py --stage` → `--activate --yes`;`--activate` **不重启常驻**(bot 必须手动重启)。
⑧ `master_deploy.py --verify --status` + 记 `activate.<ts>.json`。

**回包纪律**:长跑命令把输出重定向到远端文件再 `tail`,ssh 只取摘要 —— 大段 CJK 输出直传会被截断。

## bot 静默重启(动运行中进程前先拿用户点头)

- **kill 与 start 永不同一个 exec**;停完先核**残留 0 + 锁已释放**,再起。
- 停:`pkill -TERM -f "v6m[.]py bot"`(方括号防自匹配);核查 `P=v6m; ps -ef | grep "$P[.]py bot" | grep -v -e grep -e bash`。
- 起:`cd /opt/v6 && setsid nohup flock -n /tmp/v6_bot.lock python3 -u /opt/v6/v6m.py bot >> /opt/v6/pixbot.log 2>&1 < /dev/null &`。
  ssh 会因后台常驻进程挂住 ⇒ **exec 超时(124)属正常**,改用 `ps` 复核。
- **双 bot 不能同跑**(409 互顶 getUpdates offset)⇒ 起完必须确认只有一个实例。
- 用户偏好:**静默重启,不推上线公告**。

## ★重启后「零日志」≠ 挂了 —— 按内核/状态证据判活性

守护进程可能长时间一行不打(只在事件时才打日志)。**不要用「等日志」判活性**,按这套取证:

```bash
readlink /proc/<pid>/fd/1 /proc/<pid>/fd/2   # stdout/stderr 是否真指向日志文件
ss -tnp | grep <pid>                         # 有没有 ESTAB 到目标(例 TG 149.154.166.110:443)
ps -o pid,nlwp,etime,time,stat -p <pid>      # 线程数 / CPU 时间是否在长
stat -c "%y" <游标文件>                       # offset/cursor 类状态文件 mtime 是否在推进 ← 最强
```

游标文件 mtime 持续推进 = 消费者真在消费队列,比日志强。

## ★日志里的 traceback 要先「定代次」再归因

append-only 日志里的报错可能是几代前的。**看 traceback 引用的树路径**(例 `/opt/v6/lib/v6rel_<旧戳>/…`)与现役 rel 比对:
路径 = 现役 ⇒ 本轮真错必须查;路径 = 旧 rel ⇒ 历史残留,不是本轮。
同理 `grep -i -E "error|except"` 会命中历史噪音 ⇒ 判「本轮有无新错」要**按字节/行偏移切出本轮那一段**再 grep。

## ★「日志最后一段是谁写的」用字节偏移,别用行数

`wc -l` / `sed` 在混 `\r`/`\n` 行尾或缓冲差异下会骗人;`mtime` 只说明「有人写过」,不说明是谁。

```bash
stat -c %s <log>                          # 总字节
 grep -a -bo "<启动标记>" <log> | tail -3  # 每个启动标记的字节偏移
tail -c <size-最后偏移> <log>              # 最后一段原文(= 最后一次启动写的)
```

启动标记 + 其后字节数 + 段落内的时间戳,三者对齐才能断言「这段是本次重启写的」。

## ★主控配置里的 `/tmp` 路径常是「远端路径」

派活/下发腿把名册、结果、统计、日志路径写在 job 命令里由**采集机**执行 ⇒ **主控本地不存在这些文件是预期,不是接线断了**。
判「接线断了」之前先读代码确认该路径是本地读写还是 `ssh "cat > <path>"` 到远端。
验证要在**采集机侧**做:文件与生产端同刻产物**字节一致** + 采集端 journald 打出「名单 N(生成于 <生产端时间戳>)」。

## 上线后生产侧验证清单(逐条落到数字)

- [ ] 新模块/新分支的**自有日志前缀**出现在首轮 cron 日志里(例 `[<新模块名> <ts>] …`)⇒ 新码真在跑
- [ ] 关键产物 mtime **晚于** activate 时刻(用 activate 记录文件对齐)
- [ ] 清单条数与**独立第二算法**(沙箱只读验收 / 离线量测脚本)**逐数吻合** ⇒ 三方互证
- [ ] 下游消费证据带**生产端生成时间戳**(采集机 journald / 状态文件)
- [ ] 无新 traceback(按偏移切段判)
- [ ] 回滚点已记录

**★轮转类分发别误判**:按分片/shard 轮转下发的名册,**某台机器上还是上一轮的是正常节奏**;要验证就看已走到自己窗口的那台,或等下一轮。
