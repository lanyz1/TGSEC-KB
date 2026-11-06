---
name: covering-tracks
description: Use when 拿到 shell 后要清痕或对抗取证。证据源清单+顺序+边界。
---

# 痕迹清除 / 反取证（授权主机）

**先枚举证据源，再动手。** 清痕的最大风险不是没清干净，而是**清痕动作本身产生新日志**（服务创建、账户修改、大量文件时间戳一致变更、卷影被删）。

## 铁律

1. **先问能不能恢复**：改密码、删日志、写后门 —— 数据可还原 ≠ 审计痕迹可清。动手前先答这个问题。
2. **先枚举，后执行**：`wevtutil el` / `Get-WinEvent -ListLog *` / `ls /var/log` 先列全，再决定动哪些。
3. **默认最小动作**：优先「不动原系统」（内存执行/无文件），其次「事后清」，不要为了干净而制造更多异常。
4. **顺序**：先清最容易被实时上报的（进程/命令行/网络），再清静态留痕（日志/文件/时间戳）。
5. **恢复原状是交付要求**：临时账号/服务/计划任务用完删除，改过的配置改回。

## 关联

- 落地执行面：`edr-bypass-re`（AMSI/ETW/ACG/AppLocker）
- 持久化留痕：`windows-persistence` / `linux-post-exploit` / `admin-backdoor-persistence`
- 对抗视角（知道自己被怎么看）：`incident-response` / `digital-forensics`

## Windows：证据源清单（先看，再决定动不动）

| 证据源 | 位置/命令 | 清痕代价 |
|---|---|---|
| 事件日志 | `wevtutil el` 列表；`wevtutil cl <log>` 清；`Clear-EventLog` | 清空 = 明显异常（EID 1102），优先**单条删**（`wevtutil qe` 定位 recordId）|
| PowerShell 日志 | `Microsoft-Windows-PowerShell/Operational`(4104 脚本块) | 少用 `-enc`，用 `-Command` 前台执行噪声更低 |
| 安全日志 | 4624/4625/4688/7045/4698 | 服务与计划任务类留痕，用完即删实体 |
| 预取 | `C:\Windows\Prefetch\*.pf` | 删除/占位会破坏目录一致性，不如一开始就别在盘上落地 |
| Amcache / ShimCache | `Amcache.hve`、注册表 AppCompatCache | 同时改注册表与文件 = 二次造假，风险更高 |
| USN Journal | `fsutil usn queryjournal C:` | `fsutil usn deletejournal` 本身留痕 |
| SRUM | `SOFTWARE\Microsoft\Windows NT\CurrentVersion\SRUM` | 网络/进程统计，EDR 常上报 |
| 注册表取证键 | RunMRU、UserAssist、MUICache、RecentDocs、Shellbags | 逐键清理，别整个 hive 删 |
| 文件时间戳 | `timestomp`(.NET/时间伪造工具) | 批量一致的时间戳反而像伪造，优先保持原样 |
| LNK / JumpList / 回收站 | `%APPDATA%\Microsoft\Windows\Recent`、`$Recycle.Bin` | 用户目录清理属于高危动作 |
| 卷影副本 | `vssadmin list shadows` / `delete shadows` | 一删就被判定为勒索行为特征 |
| RDP/终端痕迹 | `Default.rdp`、Terminal Server 日志 | 会话类日志常被集中采集 |
| Sysmon / EDR 遥测 | 先确认上报层（`Get-Service Sysmon*`、EDR 进程） | **远端已收到的撤回不了**：先想清楚哪些动作会上报 |

## Linux：证据源清单

| 证据源 | 位置 | 备注 |
|---|---|---|
| 认证日志 | `/var/log/auth.log`、`secure`、`wtmp`、`btmp`、`lastlog` | `last`/`lastb`/`who` 交叉验证 |
| 系统日志 | `/var/log/syslog`、`messages`、`journald`(`journalctl --vacuum-time`) | 集中转发后本地清无效 |
| auditd | `/var/log/audit/auditd.log`、`auditctl -l` 规则 | `service auditd stop` 本身就是事件 |
| 命令历史 | `~/.bash_history`、`~/.zsh_history`、各用户 HOME | 中途 `HISTFILE=/dev/null` 优于事后改 |
| 文件时间戳 | `touch -r/-t`、`debugfs` 改 crtime | ext4 有 inode 备份，深挖能还原 |
| 包管理/系统变更 | `dpkg.log`、`yum.log`、`/etc/passwd` 变更 | 新增账号必留痕 |
| 容器场景 | docker/podman 事件、kubelet 日志 | 走 `container-security-testing` 的清理纪律 |

## 常见坑

- **清日志 = 自曝**：`wevtutil cl`/`Clear-EventLog` 产生 EID 1102；能用单条删就别整清。
- **时间戳批量归零**：`copy /b` 或统一 `touch` 会让 MFT/预取与文件时间对不上，取证一挖一个准。
- **远端遥测不可撤**：Sysmon/Wazuh/EDR/日志服务器的副本清不掉；先判断「这件事会不会被实时上报」再决定做不做。
- **恢复原状 > 抹干净**：临时账号/服务/计划任务/配置改动要能还原（用户交付要求），比擦日志更重要。

## 服务级抹除（清库 / 拆服务 / 锁入口）—— 只在用户点名时做

清痕（本卡正文）之上还有一层更响的动作：**把业务本身抹掉**。它不属于隐蔽操作，属于破坏性处置，
**必须用户明确要求**（如「清库＝拉满」「不要入口」）；动手前先把 `库名 / 账号清单 / 表清单` 落盘，供复位与报告。

| 动作 | 做法 | 复盘/确认判据 |
|---|---|---|
| 锁入口（先做） | 应用后台：只留自控账号 + 停用他人（`prohibit_login`/`disabled`）+ 吊 token + 关注册/OpenID；DB：`ALTER ROLE x NOLOGIN`、改自控账号口令、`pg_hba` 只放可信网段 | 改完立刻自测：他人账号登不进、自控账号能进 |
| 清库 | `DROP DATABASE <业务库>`；带自有库的服务（Gitea、面板）要连它的库一起处理 | 库列表为空；应用报「库不存在」 |
| 拆服务 | 删数据目录（PG：`base/ pg_wal/ global/` + 配置）→ 进程仍在但连不上，报 `FATAL: could not open file "global/pg_filenode.map"` | **端口仍开但握手即失败** = 服务已废（比「端口不通」更有说服力）|
| 别做 | 改服务的**运行用户**（如 PHP-FPM `user=root`）去换执行权限：常见结果是把服务弄挂，而且这不算提权 | — |

**交付口径**：破坏性动作与「是否可复原」分开写 —— 数据可还原（有备份/可重建）≠ 审计痕迹可清；
用户问「能不能恢复」时先答这个（见本卡铁律 1）。

## 最小工作流

1. `wevtutil el` / `journalctl --list-boots` / `ls -la /var/log` —— 枚举。
2. 判断哪些证据源**已经**被集中采集（转发远端的一律不动）。
3. 按「实时上报 → 静态留痕」顺序处理；能不动就不动。
4. 收尾：删临时实体、还原配置、记录改过什么（写进交付报告的风险项）。
