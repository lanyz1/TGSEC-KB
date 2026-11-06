---
name: attck-ttp-and-atomic-validation
description: 映射 ATT&CK TTP / 验证检测规则时用：attck+atomicredteam。
---

# ATT&CK TTP 映射与 Atomic 检测验证

两用：**进攻**——把已打下的行为映射成 T-ID，出战术链报告；
**防守**——用 atomicredteam 原子化执行 TTP，验证检测/告警真的会响。
触发词：ATT&CK、TTP、战术、演练报告、原子测试、atomicredteam、Sigma、检测规则验证、紫队。

| 档 | 成立 | 不算 |
|----|------|------|
| primitive | 命令 ↔ T-ID 对应 | 只写“用了一些红队工具” |
| L2 | 每条 TTP 有执行证据（命令/日志/回连） | 臆测的战术链 |
| L3 | 检测侧有可见证据（规则命中/告警截图） | 只跑不验 |

## 两段工作流

```text
① 映射：现场行为 → T-ID → 战术阶段 → 缺口（哪段无日志、哪段无告警）
② 验证：atomicredteam 单个原子跑一遍 → 看检测是否命中 → 不命中就修/补规则
```

| 内容 | 参考 |
|------|------|
| 14 战术与高频 T-ID | `references/attck-14-tactics.md` |
| atomicredteam 部署与命令 | `references/atomic-red-team-usage.md` |
| Sigma/检测规则验证闭环 | `references/sigma-detection-validation.md` |

## 立刻跑

```bash
# 把现场证据（命令行/日志片段）映射成 T-ID，输出战术链与缺口
python3 scripts/ttp_map.py --in evidence.txt --out ttp.md
python3 scripts/ttp_map.py --selftest
```

```powershell
# atomicredteam（Windows，检测验证用）
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)
Install-AtomicRedTeam -getAtomics
Invoke-AtomicTest T1059.001 -ShowDetailsBrief
Invoke-AtomicTest T1059.001 -TestNumbers 1 -CheckPrereqs
Invoke-AtomicTest T1059.001 -TestNumbers 1      # 跑之前先确认检测已就绪
Invoke-AtomicTest T1059.001 -TestNumbers 1 -Cleanup
```

## 纪律

- 原子测试会**真的**改主机状态（本机/靶机为主），跑前告知、跑后 Cleanup，生产环境只在明确授权窗口内做。
- 报告里 T-ID 必须附**证据单元**（命令、时间、主机、检测命中），否则不写。
- 映射不追求数量：只写实际执行过的，一条 TTP 比十个“可能用到”有价值。

## 交接

| 认到 | 走 |
|------|-----|
| 事件处置与定级 | `incident-response` |
| 攻击链规划 | `attack-chain` · `attack-router` |
| 免杀/EDR 对抗 | `evasion` · `edr-bypass-re` |
| 溯源画像 | `attacker-tracing-and-counterstrike` |

## 真源

- `references/attck-14-tactics.md` · `references/atomic-red-team-usage.md` · `references/sigma-detection-validation.md`
- 探针：`scripts/ttp_map.py`（含 --selftest）

## BAS 平台（2026-09 上游收割补充）

- `PurpleSharp`（Windows 行为模拟）、`Stratus Red Team`（AWS/云场景）、`SCYTHE` / `Nighthawk`（商业 BAS/C2）
- 纪律：检测规则仍以 atomic-red-team 逐条验证为准；BAS 一把梭噪声大、映射含糊，只能当覆盖度参考
