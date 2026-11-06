# atomicredteam 与检测验证工具链

## 为什么用它

单条 TTP 原子化执行 → 看**检测侧**是否命中 → 不命中就补规则。这是紫队循环的最小闭环，
也是"防守有日志、有告警"的唯一实证方式。

## Windows（Invoke-AtomicRedTeam，最常用）

```powershell
# 安装（PowerShell 5+/7，管理员）
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)
Install-AtomicRedTeam -getAtomics                      # 下载 atomics 仓库到 -PathToAtomicsFolder

# 查询与执行
Invoke-AtomicTest T1059.001 -ShowDetailsBrief          # 看有哪些测试编号
Invoke-AtomicTest T1059.001 -TestNumbers 1 -CheckPrereqs
Invoke-AtomicTest T1059.001 -GetPrereqs                 # 缺依赖时按需装
Invoke-AtomicTest T1059.001 -TestNumbers 1              # 执行（先确认检测已就绪）
Invoke-AtomicTest T1059.001 -TestNumbers 1 -Cleanup     # 清理（必做）
Invoke-AtomicTest T1059.001 -TestNumbers 1 -TimeoutSeconds 120
Invoke-AtomicTest All -ShowDetailsBrief | Select-String T1059   # 按关键词找
```

## Linux / macOS

```bash
# 官方 atomics 仓库里的 bash/sh 原子可直接跑（先读源码再执行）
# 社区跨平台包装：atomic-operator（pip），跑 YAML 格式原子，参数以 --help 为准
pip install atomic-operator
atomic-operator run -t T1059.004 --help
```

## 检测侧（跑完原子看这些会不会响）

| 工具 | 用途 | 例子 |
|------|------|------|
| Sigma + pySigma | 规则跨平台转换 | `sigma convert -t splunk -p splunk_windows rule.yml` |
| Chainsaw | EVTX 批量狩猎 | `chainsaw hunt evtx/ -s sigma/ --mapping mappings/sigma-event-logs-all.yml` |
| Hayabusa | 快速时间线 | `hayabusa csv-timeline -d ./logs -o out.csv` |
| DeepBlueCLI | 安全日志速判 | `powershell -f DeepBlueCLI.ps1 -log Security.evtx` |
| Sysmon/EDR | 进程树、命令行、网络 | 原子执行时看是否产生遥测（没遥测=最大缺口） |
| 云侧 | Stratus Red Team | AWS/Azure/GCP 的 TTP 原子 |

命令行以各自 `--help` 为准（版本间参数会变）。

## 演练排期模板

```text
每轮：选 3-5 个 T-ID（优先无告警的阶段）→ 原子执行 → 记录
  {T-ID, 主机, 时间, 命令, 是否产生遥测, 是否告警, 规则来源}
不命中 → 补 Sigma/EDR 规则 → 下一轮回归同一条原子（回归才算修好）
产出：覆盖矩阵（战术 × 有遥测 × 有告警）+ 缺口清单
```

## 坑

- 原子会真改主机（新建账号/计划任务/服务/注册表）：只在靶机/授权窗口跑，跑完 `-Cleanup`。
- 杀软会直接拦原子：被拦也记录（这本身是有效检测）。
- 网络类原子（T1071/T1105）会外连测试域名，需允许出网或记录"未执行"。
- Atomic 仓库更新快，旧博客里的 `-TestNumbers` 可能已变：以 `-ShowDetailsBrief` 为准。
