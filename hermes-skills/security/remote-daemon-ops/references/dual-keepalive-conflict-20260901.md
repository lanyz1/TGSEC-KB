# 双保活冲突实录:systemd 服务 vs 遗留 setsid 守护(2026-09-01)

## 现象
4 台采集机每台同时有 2 个 collector 进程:
```
168036  1  bash -c cd /opt/v6 && setsid nohup ./collect_daemon_fast.sh > /dev/null 2>&1 < /dev/null & echo STARTED
168037  168036  /bin/bash ./collect_daemon_fast.sh
168039  168037  python3 /opt/v6/collector.py          ← 守护脚本子进程(PATH 解析)
168367  1  /usr/bin/python3 /opt/v6/collector.py      ← systemd 托管(绝对路径)
```

## 根因(两套保活互不认识)
- 8/29 部署时代:SSH 会话里 `setsid nohup ./collect_daemon_fast.sh`(while 循环守护,挂了 30s 拉起)
- 8/31 引入 systemd 服务 `v6collector.service`(`ExecStart=/usr/bin/python3 ...`, `Restart=always`, `RestartSec=5`, 注入 `V6_SHARD` 环境变量)
- 切换 systemd 时**旧守护脚本进程没清理** → 两台保活各拉一个 collector → state 互相覆盖、请求翻倍、守护侧进程缺 `V6_SHARD` 可能跑错分片

## 排查弯路(浪费时间最多处)
- 把 `PPID=1` 的 systemd 进程误判为"孤儿/隐藏启动源" → 跑了一整串杀-等-复现实验(stoptest/fixproc/proc2/orphan/cronfind)
- 真相:systemd 环境里服务进程 PPID=1 是**正常形态**;"杀后 150 秒又出现"就是 `Restart=always` 的 5s 自动拉起,根本不是隐藏启动源
- cron/systemd timer/at 全查过 = 干净,佐证没有第三方启动源

## 正路诊断(一次到位)
1. `ps -eo pid,ppid,etimes,cmd | grep '[c]ollector'` — 看 PPID + cmd:绝对路径 vs PATH 解析
2. `systemctl cat v6collector.service` — ExecStart + unit 修改时间(8/31 = 新机制)
3. `ls -la /opt/v6/*.sh` — 守护脚本时间戳(8/29 = 遗留机制)
4. `systemctl status` — ActiveEnterTimestamp 与 ps 的 etimes 对齐

## 修复(保留 systemd 单一管理)
```bash
for p in $(pgrep -f 'collect_d[a]emon'); do kill $p; done        # bash -c + bash 守护
for p in $(pgrep -f '^python3 /opt/v6/collector.py'); do kill $p; done  # ^锚定:不误杀 /usr/bin/python3
sleep 2; for p in $(pgrep -f 'collect_d[a]emon'); do kill -9 $p; done
```
杀 bash 守护**不会**杀其子 collector(会变孤儿继续跑)——必须连子一起杀。
验证:`systemctl status` MainPID == ps 唯一 collector PID,cmd 以 `/usr/bin/python3` 开头,4 台全部一致。

## 附带发现:V6_SHARD 环境变量只由 systemd 注入
守护脚本直接 `python3 collector.py` 没有 `V6_SHARD` → 非 systemd 启动的进程可能全跑 shard 0。进程 cmd 的 `python3` vs `/usr/bin/python3` 差异同时是"有无环境变量注入"的标志。

## 预防
- 任何"切换保活机制"的部署,必须显式杀光旧机制进程链(含子进程)再启用新机制
- 迁移后 5 分钟复核:进程数=1、systemd active、MainPID 匹配、日志在跑
