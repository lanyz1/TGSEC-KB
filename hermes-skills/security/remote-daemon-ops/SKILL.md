---
name: remote-daemon-ops
description: "部署监控daemon用: pkill自杀/setsid保活/双调度。触发: 部署监控, 跳板机, daemon。"
tags: [pkill, 自杀, 误杀, 杀自己, 进程清理, 进程管理, 保活, 部署监控, 跳板机部署, 后台进程, 把自己杀了, 杀进程, 进程别杀, 误杀自己]
---

# 远程 Daemon 部署与进程管理(Remote Daemon Ops)

## 适用场景
用 paramiko SSH 在远程 Linux 机(跳板机/采集机/主服)部署**常驻监控脚本**(while+sleep 轮询 daemon、merger 合并器、TG bot 长轮询),以及跨多台机器切换运行节奏(加速/常规)。

## 部署模板(实测可靠)

```bash
# 启动常驻 daemon(关键:setsid 脱离会话 + stdin 重定向)
cd /opt/v6 && setsid nohup python3 collector.py > /tmp/collect.log 2>&1 < /dev/null &

# daemon 本体模式(比 crontab 简单可靠)
#!/bin/bash
sleep 3                      # 错峰启动
while true; do
  python3 /opt/v6/collector.py >> /tmp/collect.log 2>&1
  sleep 60                   # 轮询间隔
done
```

## 三大坑(全部实测,必须遵守)

### 1. pkill -f 自杀
`exec_command("pkill -9 -f 'pat'; sleep 1; setsid nohup ./daemon.sh &")` — 若整条命令串里包含目标进程名的**真实字面量**(如 `./daemon.sh`、`collector.py`),`pkill -f` 会匹配到**自己的 exec shell** 并杀掉它 → 连接断开、后续启动命令不执行、daemon 被杀没重启。

`[x]` 技巧(`pkill -f '[c]ollector'`)只能防住"方括号字面量自身",**防不住命令串里其他部分的真实字面量**。

**修复:杀与启动拆成两条独立 exec_command**:
```python
ssh_run("pkill -9 -f '[c]ollect_daemon' || true; sleep 1; echo K")   # 第一条
ssh_run("cd /opt/v6 && setsid nohup ./collect_daemon.sh > /dev/null 2>&1 < /dev/null & echo OK")  # 第二条
```

### 2. setsid 保活
普通 `nohup ... &` 在 paramiko 会话/通道关闭后**可能随会话退出**(进程消失、无报错、日志停在启动行)。
**必须 `setsid nohup ... > log 2>&1 < /dev/null &`**(setsid 完全脱离会话;`< /dev/null` 防止 stdin 占用)。

验证:关闭 SSH 连接后再开新连接查 `ps aux | grep [x]`——必须仍存活。

### 3. 双调度冲突
crontab(每分钟 wrapper)+ daemon(while+sleep)同时存在 → 每轮启动 2 个采集进程 → 进程成倍堆积、请求量翻倍(触发 WAF)。

排查:`ps aux | grep [c]ollector` 看完整命令行,区分 `/bin/sh -c /opt/v6/wrapper.sh`(crontab)与 `/bin/bash ./collect_daemon.sh`(daemon)。**只保留一种调度**(推荐 setsid daemon)。

## 其他要点

- **远程请求超时设 8s**:目标 ST 过期/服务卡死时,20s 超时 × 几十个请求 = 每轮 10+ 分钟 → 下轮 daemon 又启动新进程 → 堆积。8s 超时让卡死轮快速失败。
- **进程计数陷阱**:`ps aux | grep -c '[x]'` 会把当前 exec shell 也算进去(计数 2 = 实际 1 个真进程),用 `grep -c` 前先确认实际命令行。
- **幂等采集**:目标数据"存在且非空即跳过"(如包件清单只拉一次),避免 ST 过期时重复拉取卡超时。
- **状态兜底**:发现失败时用上次状态兜底(目标列表/已处理 ST),不能因单轮失败清空。
- **加速器模式切换**(多机节奏控制):控制脚本 accel.py 通过 SSH 分步(pkill → 启动对应 daemon)切换各机 daemon 间隔(fast=sleep 30 / normal=sleep 60);状态存 JSON,bot/面板读它显示当前模式。切换命令同样要遵守"杀/启分离"。
- **大文件跨洋上传**:sftp 500MB ≈ 0.4MB/s ≈ 20 分钟——放后台跑(background + notify_on_complete),同时做其他事。

## 参考案例
- `auditlog-ticket-harvesting` 技能 references/95306-session10-v6-tgbot-v3.md — 4 采集机 + 主服 + TG bot 全量部署实录(含所有踩坑现场)。


---

## 外部库增量（2026-10-11 分享包）

## 共享跳板/多案并存的归属纪律
跳板机常被**多个并行案子共用**（root 下混着别案工具链、长跑 worker、仍在写的日志）——消费或清理任何东西前先分案：
- **读脚本头部注释定归属**：脚本首行的 `TARGET=`/`BASE=`/usage 注释 = 案子归属；归属不定就围绕其产物推理 = 白耗。
- `ps -eo pid,etime,args --sort=start_time | tail -25`：etime 以「天」计的长跑进程多为陈年别案 worker。
- **绝不动无法归属的进程**：别案可能 24/7 在跑，误杀 = 跨案互伤（杀进程前先与用户确认的全局铁律同样适用）。
- 自己的脚本放案卷专属子目录/统一前缀，并在案卷笔记里维护「本机 ↔ 跳板」文件对应表。
- **找最新产物别用 `ls | head -N`**：大目录里 head 的截断点看着像自然边界，会把「后面还有」误判成「文件不存在」——用 `ls -la | tail`、`find <dir> -newermt '<date>' -ls` 或按 mtime 排序。
- 旧笔记/摘要点名的文件先逐一 `[ -e "$f" ]` 核验再规划——摘要会带出**从未存在过的文件名**，围着幻觉清单行动就是空跑。

## 同批「写脚本 → 执行」的落盘竞态
`write_file` 与 `terminal` 同批并发时，执行命令可能先于文件落盘运行 ⇒ 报「不存在」。执行侧先等就绪：
`for i in $(seq 1 10); do [ -f ./script.sh ] && break; sleep 1; done`
