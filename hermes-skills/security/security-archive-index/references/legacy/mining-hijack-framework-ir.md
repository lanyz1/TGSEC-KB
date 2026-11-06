<!-- archived from /root/.hermes/skills/security/mining-hijack-framework-ir/SKILL.md on 2026-10-21 -->

---
name: mining-hijack-framework-ir
description: "Linux 挖矿劫持框架(icc/nvpmgr 类)解剖·检测·清除与技法复用。触发:挖矿排查/清矿。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/mining-hijack-framework-ir`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/mining-hijack-framework-ir/…')`，不要相对 `references/legacy/` 解析。

# 挖矿劫持框架（icc / nvpmgr 类）— 解剖 / 检测 / 清除 / 技法复用

针对**长期运营、自动化、自愈型 GPU 挖矿劫持框架**（代号 `icc`，主伪装名 `nvpmgr`，冒充 NVIDIA 电源管理守护）。
处置任何「主机被挖矿占着 / GPU 被吃满 / 删了又回来」的场景时用本卡。

## 真源

- `references/framework-anatomy.md` —— 三件套组件、四层持久化、guard.py 反竞争者逻辑、antirival.rules 指纹库、GPU 利用率健康探针、画像与致命弱点。
- `references/eviction-playbook.md` —— 取证 → 斩 L1 → 清 L2/L3 → 多轮 kill/换键 → 静置复检 的完整命令序列 + 边界判定。
- `scripts/icc_triage.py` —— 只读布点排查探针（不 kill、不改文件）。
- `scripts/selftest_icc_triage.py` —— 自带 mock 靶机自测（5 例）。

## 一、判型要点（别只看单个文件）

框架的识别不靠某一个文件，而靠**命名规律 + 四个层面同时出现**：伪装成系统守护的进程 + 字典序末尾的持久化文件 + 应用数据目录下的 `.mgr` + 矿机二进制黑名单。
**只命中一项不够定性**；`cron + systemd timer + .mgr 目录 + 矿机名` 中命中 ≥2 类即可按本卡处置。

## 二、一票命中信号（探针 check ↔ 现场现象 ↔ 所在层）

| check | 现场现象 | 层 |
|-------|----------|----|
| `cron_zz_prefix` | `/etc/cron.d/` 下 `zznvpmgr`/`zzantirev` 类 **zz 前缀**文件（字典序末尾，规避按名排序的人工审查） | L2/L3 |
| `cron_miner_keyword` | cron 内容含 `nvpmgr`/`antirival`/`/.mgr/`/`stratum`/`--pool`/矿机名 | L2/L3 |
| `cron_pipe_shell` | cron 内容是 `curl … \| sh` 型下载执行 | L2/L3 |
| `systemd_unit_framework` | `nvpmgr*` / `antirival*` 单元（伪装系统守护） | **L1** |
| `timer_high_frequency` | `OnUnitActiveSec` ≤ 120s（约 45s 的**真正的复活引擎**） | **L1** |
| `systemd_restart_always` | 可疑 ExecStart + `Restart=always`（kill 秒级复活） | L1 |
| `mgr_dir` | `~/.local/share/<app>/.mgr/`（伪装应用数据目录） | L2/L3 |
| `framework_trio` | 同目录同时存在 `boot.sh` + `guard.py` + `antirival.rules` | L2/L3 |
| `payload_masquerade` | `<cache>/.v3/gl_blob_*.dat`（伪装 Mesa 着色器缓存） | L2/L3 |
| `framework_evidence` | `evidence_<artifact>.<unix-ts>`（框架给它自己/对手留档） | L2/L3 |
| `miner_in_profiles` | `profiles/p<随机hex>/<矿机名>`（路径动态化） | L2/L3 |
| `miner_binary_name` | 文件名命中矿机黑名单（krig-miner/xmrig/nbminer/lolminer/trex/srbminer/peakminer/miner2/xmr-stak…） | 任意 |
| `authorized_keys_framework` | key 注释/内容含 `nvpmgr`/`heal`/`antirival`（自建 key 固化） | **L4** |
| `authorized_keys_recent_write` | `<10min` 被改写（**LOW 噪声**：装自己 key / ansible 也会命中，只提示不定性） | L4 |

补充现场信号（探针在真实主机上给提示行，不在文件树里）：

- **进程伪装**：`ps` 里出现 `nvidia-persistenced --pool …` —— 真 NVIDIA 守护**没有 `--pool` 参数**，带 `--pool` 就是矿机。
- **被污染成 no-op 的落脚文件**：`/tmp/python`、`/var/tmp/python`、`~/.ssh/<tunnel>.sh`、`/usr/local/bin/frpc` 内容是 `#!/bin/sh\nexit 0` ⇒ 有挖矿框架在清场（**是劫持信号，不是自己的清理**）。
- **GPU 被抢占**：`nvidia-smi --query-gpu=utilization.gpu` 长期 ≥40% 但机主没跑任务；渲染/训练进程被外力 kill。

## 三、跑探针

```bash
# 真实主机（只读；退出码 0=未发现 10=有命中 2=参数/路径错）
python3 scripts/icc_triage.py --root / --json --out /tmp/icc_triage_$(date +%s).json
python3 scripts/icc_triage.py --root / --only cron_zz_prefix,systemd_unit_framework

# 靶树/mock 验证探针本身
python3 scripts/selftest_icc_triage.py
```

**自测记录表**（本机 Windows + python3.14，`python3 scripts/selftest_icc_triage.py`）：

| 用例 | 结果 | 证据 |
|------|------|------|
| 例1 感染靶树（etc/cron.d/zz*、nvpmgr-heal.timer 45s、.mgr 三件套、gl_blob_*.dat、profiles/p*/krig-miner、key 注释 nvpmgr） | PASS | rc=10，hits=22，命中类=14 |
| 例2 干净靶树（标准 cron.d/ssh.service/普通 key，mtime 已老化） | PASS | rc=0，hits=0 |
| 例5 仅 LOW 噪声（干净树 + authorized_keys 刚改写） | PASS | rc=0，hits=1/强命中=0（**不定性**，只列提示） |
| 例3 `--root` 不存在 | PASS | rc=2 |
| 例4 `--out` 落盘并读回 | PASS | JSON 读回 hits=22 |

设计纪律：**定性只认 HIGH/MED**，LOW 只列不断言 —— 避免把「刚装完自己 key 的运维动作」写成「已被劫持」。

## 四、清除：顺序不能反（详见 `references/eviction-playbook.md`）

```
① 取证(只读) → ② 斩 L1: stop+disable+rm unit → systemctl daemon-reload
→ ③ 清 L2/L3: cron.d(z) + crontab → ④ 多轮 kill 进程 + 删 .mgr/载荷
→ ⑤ 重置键(只留自己的) → ⑥ 静置复检 ≥60s(超过 45s timer 周期) → ⑦ 二次复检
```

四条反面教训（本卡存在的主要理由）：

1. **只删 cron 无效** —— 真复活引擎是 systemd timer，删完 cron 秒级重建。
2. **只 kill 进程无效** —— `Restart=always` 秒级拉活；要**多轮** kill（跑在重建窗口里）。
3. **只删文件无效** —— 任一钩子存活即重建目录。
4. **不静置就下结论 = 误判** —— 静置 >timer 周期才算清完。

**致命弱点可反向利用**：复活链最终收敛到 systemd timer 单点 —— 先斩它，其余层自动失去再生能力。

## 五、可复用技法（攻防双向）

| 技法 | 攻方用法 | 守方检测点 |
|------|----------|------------|
| 持久化主引擎用 **systemd timer** 而非 cron | 更隐蔽、更顽固、`Restart=always` 配合 | `systemctl list-timers --all` 里周期 ≤60s 的陌生单元 |
| 多层冗余互为备份（timer→cron→crontab→key） | 任一层存活即重建全链 | 四层**同时**出现命名规律 |
| 持久化文件用**字典序末尾前缀**（zz） | 规避按名排序的人工审查 | `/etc/cron.d/` 下的 `zz*` |
| 进程名伪装成系统守护（`*-persistenced`） | 混在 `ps` 里难分辨 | 真守护**没有** `--pool` 参数 |
| 目录伪装成应用数据/缓存（`.local/share`、`.cache/.v3`） | 人工翻目录时被略过 | `.mgr` 目录 / `gl_blob_*.dat` |
| **污染而非删除**对手落脚文件（写 no-op） | 对手重启也白搭 | 落脚脚本内容是 `#!/bin/sh; exit 0` |
| **指纹库 + 跨主机同步**（antirival.rules） | 持续识别竞争者、情报闭环 | 库内能反查对手钱包/worker/IP |
| 反向识别对手 **wallet/worker/IP** | 跨机关联同一攻击者 | 拿库即得一份对手 IOC（注意别把对手 IP 当成恶意 C2） |
| **GPU 利用率**做健康探针（非进程存在性） | 识别「进程在但没干活」的假活 | GPU 占用与机主任务不符 |
| 判定假活后**强杀全部 GPU 计算进程** | 抢回算力（打断机主业务） | 训练/渲染进程被外力 kill |

## 六、强制与边界

1. 只在**已授权**主机上跑；探针默认只读，绝不 kill/改文件。
2. 清除属**处置动作**（stop/disable/rm/kill）：多步骤部署型任务先出计划再动手；`kill -9` GPU 计算进程会**打断机主正常业务**，必须先确认授权。
3. **别误清自己**：清场前先盘自己的家当（自己的持久化马/key/隧道脚本），见 `attacker-eviction-hardening`；`authorized_keys` 里非预期 key 可能是运维平台 key。
4. 处置前先答「**能不能恢复**」：`boot.sh`/`guard.py`/`antirival.rules` 与 `evidence_*` 先备份再删（清场者身份判定、跨机溯源都靠它们）。
5. 该框架目标是**算力不是数据**：清完按 `host-ir-check` 复跑常规后门面（ld.so.preload / 隐藏 uid0 / 监听口），确认没有被顺手安装其它持久化。
6. 同团伙常**同批同构机器**都有布点 ⇒ 清一台要顺手扫同批（同 IP 段/同镜像/同跳板来源），否则会被邻居的同步逻辑重新布点。

## 七、交叉

- `host-ir-check`：通用 Linux 应急响应（隐藏用户 / ld.so.preload / 监听口 / 登录时间线）——本卡只管挖矿劫持这一族。
- `attacker-eviction-hardening`：踢攻击者 + 堵入口 + 加固（**先堵入口再清后门**的顺序原则同源）。
- `detection-engineering-sigma-attack` / `yara-rule-authoring`：把本卡 IOC 与命名规律写成检测规则。
- `operator-attribution`：用对手 wallet/worker/fleet-tag 做跨机同一运营方判定。
- `covering-tracks`：本方作业后的痕迹与反取证纪律。
