# Daemon 生命周期事故实录:setsid 失效 → systemd 根治(2026-08-30)

## 事故经过
4 台采集机 daemon(collect_daemon.sh, setsid nohup 启动)在 SSH 加固后出现"重启后悄悄死掉":
- 重启后立刻检查:进程在、日志在跑(看起来成功)
- SSH 通道一关:几秒到几分钟后 daemon 被杀
- 心跳停 30 分钟后健康告警才触发 → 完美掩盖根因(用户收到的告警是延迟 30 分钟的)
- 多轮"重启成功→告警又响"循环,直到改为 systemd 才根治

## 根因
部分环境(sshd 加固/UsePAM/会话限制变化)下,setsid nohup 的后台进程在 paramiko exec_command 通道关闭后仍被清理。**ps 检查在会话内是假的"活着"**。

## 根治:systemd 服务化(4 台采集机全量切换成功)
```bash
cat > /etc/systemd/system/v6collector.service <<'EOF'
[Unit]
Description=V6 Collector
After=network.target
[Service]
ExecStart=/usr/bin/python3 /opt/v6/collector.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now v6collector
systemctl is-active v6collector   # 必须 active
ps aux | grep [c]ollector         # 进程存在
```
systemd 优势:崩溃自动重启(5s)、开机自启、完全独立会话、状态可查。**注意 ExecStart 直接跑 python(不用 while 循环包一层,Restart=always 本身就是循环)。**

## 伴生事故 1:部署脚本清空远程文件
`ssh root@ip 'cat > /opt/v6/collector.py < /dev/null'`(本意清空后 scp 上传)——**scp 因无密码交互失败**,文件留下 0 字节 → 采集机全停。教训:先 scp/上传成功再动旧文件,或上传到 .new 再 mv;清空操作与传输必须原子(传输成功前绝不截断目标)。

## 伴生事故 2:merger 多实例僵尸
多次部署脚本各起一个 merger(setsid 存活的环境反而累积):3 个 merger 同时 rsync+写 index → 互相阻塞,health.json 停止更新(表现为"采集机全部告警",实际是 merger 死了/卡住)。修复:pkill -9 -f '[m]erger.py'(分开 exec_command)+ 重启单实例 + 验证进程数=1。**多实例并发的 merger 比没有 merger 更糟。**

## 伴生事故 3:心跳验证时序
merger 每 5 分钟一轮,health.json 每轮结束才更新一次。验证"心跳恢复"必须在 merger 一轮完成后(等 2-3 分钟)再看,否则误判"拉不到心跳"。判断 daemon 活着以**心跳文件 mtime/内容持续更新**为准,不是 ps(collector.py 在 sleep 间隔期本来就不在)。

## 诊断命令速查
- 采集机 state:/tmp/v6_state.json(seen_st/last_st/targets,统计 ST 利用情况)
- 采集机心跳:/tmp/v6_heartbeat.json(machine/ts/targets/disk/waf)
- 主服 health:/data_pool 旁 health.json(updated/machines 各机 ts+gap_s)
- 时区坑:主服 UTC(health.json 时间戳 UTC),采集机北京时间(+8)——gap 计算以"采集机本地 ts 与主服拉取时刻换算"为准,先确认两端时区再判告警真假
