---
name: linux-host-ir
description: Use when a Linux host may run an implant or backdoor.
---

# Linux 主机入侵排查与处置（IR）

用户问「是不是被植入木马了」「排查进程任务」「有没有后门」时走这套。核心是**先取证、再断链、最后清理**，并且**结论先行**：一句话给有/无，再上证据。

## 铁律

1. **先取证后清理。** 清理前先把样本、watchdog、unit、`ps`/`ss` 快照、`sha256`、auth 摘录拷到 `~/ir/<日期>_implant/`。删了就没法归因，也没法回溯。
2. **先杀守护，后杀主体。** 反过来 5 秒内被重新拉起，你会误判「杀不掉、有内核层」。
3. **时间线靠两个数据源对齐**：`/proc/<pid>/environ` 里的 `SSH_CONNECTION` + 进程启动时间 vs `auth.log` 的 `Accepted password`。同一秒 = 就是那个 SSH 会话拉起的，赖不掉。
4. **root 级驻留 ⇒ 按「本机全部文件已被读取、可能已外传」报告。** 不要给「大概没读」这种安慰话；同时列出必须轮换的凭据清单。
5. 报告不写口令/密钥明文，只给落地路径（`chmod 600`），凭据本身在聊天里只出现一次。

## 流程

### 1. 只读快检（一次跑完）

直接跑 `scripts/host_triage.sh`（本 skill 自带，纯只读），它覆盖：进程表、memfd/删除态可执行、监听与外联、systemd/cron/rc.local/ld.so.preload/authorized_keys、`dpkg -V`、近期落地文件、auth.log 成功登录与爆破源 Top N。

关键判读：
- **`readlink /proc/<pid>/exe` 指向 `/memfd:` 或 `(deleted)`** → 无落地载荷，重点嫌疑。
- **`dpkg -V` 只有 `??5?????? c /etc/...`** → `c` = 配置文件被改（管理员正常改动），不是二进制替换；真替换会是不带 `c` 的行。
- **`authorized_keys` 0 字节 / `shadow` mtime 很早** → 没种公钥、没改口令，但**不代表攻击者不知道口令**。
- 监听端口必须逐个对上业务：sshd / 交付页 / 自己起的探测服务都算；**自己为渗透开的回调服务（0.0.0.0 监听）属于误暴露，顺手关掉**。

### 2. 可疑进程深挖

```bash
ls -la /proc/<pid>/cwd /proc/<pid>/exe            # 工作目录 + 真身
tr '\0' '\n' < /proc/<pid>/environ | grep -iE 'SSH_|ID=|KEY='   # 谁拉起的
ls -l /proc/<pid>/fd | grep memfd                # 无落地载荷
cat /proc/<pid>/status | grep -E 'Threads|CapEff|Seccomp'
ps -o pid,ppid,lstart,stat,args -p <pid>         # 僵尸子进程 = 执行过命令的痕迹
file /usr/bin/<suspect>; ls -la; dpkg -S /usr/bin/<suspect>   # 不属于任何包 = 高危
```

实战特征（模式识别，不要当唯一指纹）：20MB 级 .NET 单文件、`strings` 里出现 `TouchSocket`/`Dmtp`/`Hardware.Info`、伪装成系统网络工具名（如 `ipv4_addrconf`）、隐藏目录 `~/.cache/.<随机4字母>-<8位hex>/`、watchdog 脚本 5 秒轮询 `/proc/*/exe` 并用环境变量标记防重复、systemd 单元伪装成监控客户端（`Description=... watchdog` + `Restart=always`）。

### 3. 持久化六面（必须逐面看）

| 面 | 检查 |
|---|---|
| systemd | `ls -lt /etc/systemd/system/*.service`、`/etc/systemd/system/*.target.wants/`、`systemctl list-unit-files --state=enabled` |
| cron | `crontab -l`、`/etc/cron.{d,daily,weekly,hourly}`、`/var/spool/cron` |
| 启动脚本 | `/etc/rc.local`、`~/.bashrc`、`~/.profile`、`/etc/profile.d/*` |
| 动态链接 | `/etc/ld.so.preload`（有内容基本就是 rootkit）、`/etc/ld.so.conf.d/` |
| SSH | `~/.ssh/authorized_keys` 字节数、`/etc/ssh/sshd_config.d/*` 的 `PermitRootLogin`/`PasswordAuthentication` |
| 账号 | `/etc/passwd` 里新增 UID=0、`/etc/shadow` mtime、`/etc/sudoers.d/` |

### 4. 归因

```bash
grep -ahE 'Accepted (password|publickey)' /var/log/auth.log* | sed -E 's/.*T([0-9:]+).*for ([a-z]+) from ([0-9.]+).*/\1 \2 \3/' | sort | uniq -c
awk '/<出事时刻前后两分钟>/' /var/log/auth.log | grep -aE 'Accepted|Failed password'
grep -ac 'Failed password for root' /var/log/auth.log
grep -aE 'Failed password|Invalid user' /var/log/auth.log | grep -oE 'from [0-9.]+' | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

- 把成功登录按 IP 分组：常用办公/家宽 IP 是用户自己，**商业 VPN 出口（Datacamp/CDN77/M247 等）落在异常时刻 = 攻击者**。
- 几十万次失败 + 一次成功 ⇒ 定向爆破或凭据复用命中；顺手做一次离线弱口令自查（`crypt.crypt(cand, shadow_hash)` 比 30 个常见口令），能区分「默认口令」还是「复用口令」。自有主机上这是合法自查。
- `whois` 查 C2 与落地 IP 的 ASN/归属，写进报告。

### 5. 处置顺序（不可乱）

```bash
# a. 取证（见铁律 1）
# b. 停持久化：禁用 + 删 wants 软链 + 删单元文件 + daemon-reload
systemctl disable --now <unit>
rm -f /etc/systemd/system/multi-user.target.wants/<unit> /etc/systemd/system/<unit>
systemctl daemon-reload; systemctl reset-failed
# c. 杀守护 → 杀主体
kill -9 <watchdog_pid>; sleep 1; pkill -9 -x <implant_name>
# d. 删落地：二进制、隐藏目录、日志
# e. 封 C2 与入侵源（进出双向），并落盘
for ip in <c2> <src1> <src2>; do
  iptables -C OUTPUT -d $ip -j DROP 2>/dev/null || iptables -I OUTPUT -d $ip -j DROP
  iptables -C INPUT  -s $ip -j DROP 2>/dev/null || iptables -I INPUT  -s $ip -j DROP
done
iptables-save > /etc/iptables/rules.v4
# f. 观察 ≥90 秒确认不复活；再跑一次只读快检
```

坑：
- `systemctl mask` 在单元文件还存在时会失败（`File ... already exists`）—— 顺序必须是 disable/删文件，再 daemon-reload，不要指望 mask 兜底。
- **iptables 默认不跨重启**：`iptables-persistent` 常常没装（`systemctl is-enabled netfilter-persistent` → not-found）。写一个 oneshot 单元 `ExecStart=/sbin/iptables-restore /etc/iptables/rules.v4` 并 enable，比装包快且不依赖网络。
- SSH 限速用 `xt_recent` 就够，别为此改 `sshd_config`（会把自己锁在外面）：
  ```bash
  iptables -I INPUT 4 -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
  iptables -I INPUT 5 -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 8 --name SSH -j DROP
  ```
- **验证进程数不要用 `ps | grep -c <名字>`**：会把你自己的命令算进去，出现「procs=3 但实际为 0」的假阳性。用 `pgrep -x <name>` 或 `ps -eo args | grep -v grep`。

### 6. 二次排查（证明「只有这一个」）

- memfd/删除态进程复扫；全盘找同源样本：`find / -xdev -type f -size +15M -size -30M -exec sh -c 'strings -n 6 "$1" | grep -qa "<特征串>" && echo HIT $1' _ {} \;`
- `dpkg -V` 全量校验（几分钟，可以接受）
- `/tmp /var/tmp /dev/shm` 隐藏文件、`~/.cache` 下随机后缀隐藏目录

### 7. 报告形状（用户要的就是这个）

1. **第一行给结论**：「有。确认被植入木马，root 级远控，存活 N 天」或「没有」。
2. **恶意组件清单**：路径 / 大小 / 类型 / SHA256，一层一条（主体、守护、自启）。
3. **时间线**：登录成功时刻 → 落地时刻 → 持久化时刻 → 执行痕迹，全部带秒级时间与 IP，并注明证据来源（environ / auth.log / mtime）。
4. **已处置**：逐条列出做了啥，附验证结果（`Unit could not be found`、90 秒无复活、`no c2 conn`）。
5. **二次排查干净项**：明确「无第二样本 / 无公钥 / 无新用户 / 无 ld.so.preload / 监听只剩 N 个」。
6. **残留风险 + 必须人工点头的事**：改口令、关密码登录或 fail2ban、轮换凭据清单、数据外泄评估、是否重装。最后用一句话问「要我现在换口令吗」——改 root 口令会改变用户访问方式，必须他点头。
