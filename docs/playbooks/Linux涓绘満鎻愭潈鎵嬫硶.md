---
title: "Linux主机提权手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# Linux主机提权手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/linux-privilege-escalation/SKILL.md`

## 汇总内容

### linux-privilege-escalation

来源：`/root/.hermes/skills/security/linux-privilege-escalation/SKILL.md`

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
A  receive parser 在 strp->stopped 仍为 false 时被放入（strp_data_re

…（截断，全文见来源卡）
