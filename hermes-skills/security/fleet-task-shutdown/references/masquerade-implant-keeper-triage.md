# 伪装系统组件的植入体 + 双 keeper 结构:识别与处置

停机/收网时最容易被漏掉的一类"任务进程":它不叫 spray/scan/watch,名字像系统组件,
还带 systemd 单元 + 用户态守护双保活。单个 kill 必然白干,必须按"先摘单元 → 隔离 keeper → 再杀 client"的顺序。

## 实测样本(2026-10-22,本机 <IP-REDACTED>)

```
/usr/bin/ipv4_addrconf          21MB 静态 strip ELF,伪装系统网络组件
  fd 8/9/10 -> /memfd: (deleted)          运行时解密,磁盘上看不到载荷
  1/2      -> /tmp/ipv4_addrconf.log      日志故意丢 /tmp,不在 /var/log
  ESTAB    <IP-REDACTED>:39900 -> 18.143.196.108:443   (AWS 新加坡,C2/monitor)
  /proc/<pid>/environ 含 VGLD_ID=vgld-48aae1dc         自愈标记
/etc/systemd/system/vgld-48aae1dc.service   Description=Vigil client watchdog
  Restart=always / RestartSec=5 / KillMode=process / ExecStart=/bin/sh <watch.sh>
/root/.cache/.vgld-48aae1dc/watch.sh        5s 轮询,client 不在就拉起来(带 pidfile 防重叠)
```

一个 **21MB 的 stripped ELF 出现在 /usr/bin 且文件名像内核网络组件**(ipv4_addrconf、netconf、route-helper 之类),
基本可以按植入体处理:Ubuntu 的 `ipv4_addrconf` 不该是 21MB 静态二进制。

## 识别四看(30 秒出结论)

1. `file /usr/bin/<name>` — `statically linked` + `stripped` + 体积十几 MB = Go/Rust 植入体特征,系统小工具不长这样。
2. `ls -l /proc/<pid>/fd` — 出现 `memfd: (deleted)`,或大量 socket+memfd 组合 = 运行时解包。
3. `tr '\0' '\n' < /proc/<pid>/environ` — 私有变量(`VGLD_ID=...`)= 自愈/多实例标记,不是系统服务的写法。
4. `ss -tnp | grep <pid>` — 单一常驻 443 外连(尤其云厂商 IP),没有对应业务进程 = beacon。

配套: `ls -la /root/.cache /root/.[a-z]*` 找同名隐藏目录;`ls -l /etc/systemd/system/*.service` 找**同分钟创建**的手写单元(包管理单元在 `/usr/lib/systemd/system`)。

## 处置序列(顺序错就复活)

```bash
# 1. 摘 systemd 层(它才是 Restart=always 的根)
systemctl disable --now vgld-<id>
systemctl is-enabled vgld-<id>; systemctl is-active vgld-<id>   # disabled / inactive

# 2. 隔离用户态 keeper(不删,可还原)
mkdir -p /root/stop_sweep/quarantine
mv /root/.cache/.vgld-<id> /root/stop_sweep/quarantine/

# 3. 再杀 client + 全体子孙(TERM -> 复查 -> KILL)
bash scripts/kill_sweep_pids.sh

# 4. 复查:ps 空 + 端口空 + 等 30-40s 再扫一遍确认没复活
sleep 40; ps -eo pid,cmd | grep -E 'vgld|ipv4_addrconf|watch\.sh' | grep -v grep
```

`systemctl mask` 若被本机 approvals.deny(`*systemctl mask *`)拦下:**不要重试、不要加 --force 换写法**。
`disabled + inactive` 已经保证下次开机不自启,报告里注明一句即可。

## 预装 vs 本役:靠时间戳判,别靠名字

- `systemctl show <u> -p ActiveEnterTimestamp -p UnitFileState` 和单元文件 mtime,
- 与**本役开工时间**比:早于本役 = 预装/前科(如本轮 `warp-watchdog.timer` Oct 19 就装好,属出口,保留);
- 晚于本役 = 自己或队友今天加的,该摘。

名字越像系统件,越要看时间戳和 `Restart=`——"Vigil client watchdog" 这种描述是给自己看的伪装,
不代表平台自带。**判不了就在报告里点名让老板认**:是自装监控就留着,不是就是别人在这台 VPS 上留的后门。

## 报告里怎么写

一段"已停"里单列它,给出:二进制路径、单元名、`Restart=`、外连 IP:port、隔离路径、以及一句结论——
「伪装系统二进制 + memfd + 系统级保活,是藏的手法,不是正经监控的做派;不是老板装的就等于有人留了东西」。
