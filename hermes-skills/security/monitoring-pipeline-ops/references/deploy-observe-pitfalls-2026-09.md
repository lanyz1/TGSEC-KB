# 部署验证与观察纪律实战(2026-09-03,菜单B抖动修复验证轮)

案例:菜单B 23↔21 抖动修复(pack_map 原子写 + 3925 unpack 修复)后的验证轮。
三个教训,均在本轮实测踩出。

## 1. 观察器假阴性:grep 输出静态 ≠ 修复没生效

背景:修复部署+重启后,后台观察器每 60s 抓一次 `grep -n "菜单B监控\|启动\|异常" pixbot.log`,
输出**连续 5-8 次几乎一模一样**(同一条 `[菜单B监控异常] too many values to unpack` 反复出现),
误判"修复没生效,异常每 3 分钟还在刷"。

真相:观察器 grep 只匹配监控关键词;06:40 重启后新增日志主要是**用户 CB 操作行**(不匹配 grep 模式),
日志文件增长慢 → 每次 check 输出的都是**同一段历史窗口**(含重启前旧进程的异常),
行号 56/58/60 < 启动行号 64/66 → 异常其实在启动记录**之前** = 旧进程遗留历史。

**判定纪律**(修复后验证必做):
1. `ps -eo pid,lstart,cmd | grep bot` → 进程启动时间是否晚于部署时间(排除"还在跑旧代码")
2. `ls -l 日志文件` mtime 是否持续增长(排除"日志根本没在写")
3. **拉全量日志不带 grep 过滤**,按时间顺序读,确认"重启标记之后"有没有新异常
4. 观察器 grep 模式漏掉的信息(用户操作等)会让输出冻结——别把"输出不变"当"系统没变"

结论:06:40:09 重启后异常 0 次,最后一条异常是 06:21 旧进程(3925-bug)的历史日志。
观察器把历史当新异常,虚惊一场。**验证修复是否生效,以"重启时间戳之后"的日志段为准。**

## 2. 补丁通道等级(远程 python 改文件)

- heredoc/内嵌 exec_command:引号不可靠(已有记录)
- **base64 嵌入远程 python 同样翻车**:本地 write_file → 本地 python 解析 → base64 → 远程解码,
  每层把 `\n` 系列转义再解一次。实测:NEW 字符串里的换行经多层后变成**字面 `\n`(反斜杠+n)**
  写进 ai_query.py → `SyntaxError: unexpected character after line continuation`。
  修复时要用 `chr(92) + "n"` 构造坏串才能反向替换——纯属自找麻烦。
- **最稳通道 = 本地 write_file 写纯 python 源码(真换行)→ paramiko SFTP put 到 /tmp → ssh python3 /tmp/x.py**:
  零转义层。远程脚本内:
  - `src.count(old) == 1` 校验(多 0 少都 ABORT,不落盘)
  - 每步 print tag + 结果
  - 全部改完 `py_compile` 两个文件
  本轮 11 处 patch 一次全过,零返工。

## 3. kill 后 setsid nohup 启动的 exec 读 stdout/stderr 必超时

paramiko `exec_command("setsid nohup python3 x.py & echo UP")` 后读输出 → PipeTimeout。
**超时是假象**(setsid 子进程持有 channel 不释放),启动命令实际已发出。
处置:忽略该超时,另起一条 exec `ps -eo pid,lstart,cmd | grep '[x].py'` 验证启动时间 + 单实例。
KILL 侧用 `pkill -f '[p]ix_bot_server.py'`(方括号防自杀),kill 后独立 exec 验证残留 0 再 start。

## 附:菜单B验证结论(2026-09-03)

- 根因(非原子写竞争)与修复详见 `packmap-reader-race-oscillation-2026-09.md` 与 v738 记录
- 验证通过:原子写 + 3925 unpack 修复部署后,监控线程零异常、零假推送;
  06:41 推 `审核通过 24→26; 十堰车务段 (✅4→6)` 为**真实审核变化**(明细推送正常生成 = 修复副作用验证)
- bot 重启模式:kill/start 分两个 exec;START exec 读超时用 ps 验证
