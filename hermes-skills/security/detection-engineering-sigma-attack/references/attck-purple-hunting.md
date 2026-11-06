# ATT&CK 映射与紫队验证参考（ATT&CK v19.2 / Sysmon / Atomic Red Team / Caldera / Navigator）

> 上游来源：`HiFullHouse-CyberSecurity-Skills/24-红蓝对抗-RedBlueTeam/skills/*.md`（5 张）+ `28-威胁狩猎-ThreatHunting/skills/*.md`（4 张）。
> 标注：**【实测】**=已核对官方文档/仓库原文（2026-09 抓取）；**【上游】**=上游原文保留未复测；**【未验证】**=命令形状未在本机跑通，落地前须复测。
> 边界：只做映射/验证/覆盖度，不含规避手法（见同目录 `attack-view-reuse.md`）；攻击链编排见本库 `attack-chain`、`attack-router`。

## 0. 版本前提：ATT&CK v19.2 已重编号（不核对就会整表错位）

当前站点 content v19.2 / website v5.1.0【实测】。旧卡里的号必须迁移，再写进规则或报告：
- T1562 Disable or Modify Tools → **T1685**（旧号废弃）；子技术：**T1685.001** Disable or Modify Windows Event Log、**.002** 云日志、**.003** Modify or Spoof Tool UI、**.005** Clear Windows Event Logs【实测】
- T1070.001 Clear Windows Event Logs → **T1685.005**；T1070 现存子技术仅 .003/.004/.005/.006/.007/.008【实测】
- 战术：TA0005 Defense Evasion → **Stealth**；新增 **TA0112 Defense Impairment**（破坏日志/采集管道/工具）【实测】
- Enterprise 15 战术：TA0043、TA0042、TA0001、TA0002、TA0003、TA0004、TA0005(Stealth)、TA0112、TA0006、TA0007、TA0008、TA0009、TA0011、TA0010、TA0040

铁律：写规则前开 `attack.mitre.org/techniques/<ID>/` 核一次；引用必带版本号；旧 Navigator 层先跑升级向导，否则 T1562 系格子渲染不出来。

## 1. 战术/技术 → 数据源 → 检测点 → 事件 ID 映射表

| Tactic | Technique ID | 数据源 | 检测点（可直接写成 Sigma/SIEM 条件） | Sysmon / Windows EventID |
|:---|:---|:---|:---|:---|
| Execution | T1059.001 PowerShell | Sysmon 1 + PowerShell 双日志 | `-enc/-EncodedCommand`、`IEX`+`DownloadString`、Office 或 wmiprvse 拉起 powershell、`-WindowStyle Hidden` | Sysmon 1；**4104** ScriptBlock、4103 Module（PowerShell/Operational）；4688 |
| Execution | T1059.003 Windows Command Shell | Sysmon 1 | `cmd /c` 超长命令行、管道接 powershell、`del`/`vssadmin` 组合 | Sysmon 1；4688 |
| Execution | T1047 WMI | Sysmon 1 + WMI 日志 | `wmic process call create`；父进程 `wmiprvse.exe` 拉子进程 | Sysmon 1；WMI-Activity/Operational 5857/5861【上游事件号，未验证】 |
| Persistence | T1547.001 Registry Run Keys | Sysmon 注册表事件 | Run/RunOnce 值写入、Startup 目录新文件 | Sysmon **13**、11；4657（需注册表 SACL） |
| Persistence | T1053.005 Scheduled Task | 任务计划程序 + 任务日志 | 任务动作带 `-enc`/UNC/临时目录；Tasks 目录直接落 XML | 4698/4699/4700/4702；TaskScheduler/Operational 106/200/201；Sysmon 11 |
| Persistence / PrivEsc | T1543.003 Windows Service | 服务控制管理器 | ImagePath 指向 temp/用户目录；`sc create` 后立即 start | **7045**（System）；Sysmon 13；4697 |
| Persistence | T1546.003 WMI 事件订阅 | Sysmon WMI 三件套 | filter+consumer+binding 三事件同主机短时出现 | Sysmon **19 / 20 / 21**（多数配置默认未开） |
| Stealth | T1685.001 禁用/篡改事件日志与审计 | Sysmon 服务态 + 审计策略 | Sysmon 服务停止/配置重载、`auditpol` 改策略、`wevtutil cl` | Sysmon 4、16；**4719**、1102 |
| Stealth | T1685.005 Clear Windows Event Logs | 安全日志 | 出现 1102（旧系统 System 104）；同机 1102 后 4688 计数断崖 | **1102** |
| Stealth | T1070.004 File Deletion | Sysmon 文件删除 | 批量删暂存/载荷；删除后紧跟远程会话断开 | Sysmon **23**（归档）、**26** |
| Stealth | T1218.011 Rundll32 | Sysmon 进程 + 镜像加载 | `rundll32` 带 `javascript:`、远程 UNC、未签名 DLL | Sysmon 1、7 |
| Credential Access | T1003.001 LSASS Memory | Sysmon 进程访问 / SACL 句柄 | 非系统进程打开 `lsass.exe`，GrantedAccess `0x1010`/`0x1410` | Sysmon **10**（GrantedAccess、CallTrace）；4656/4663（需 SACL） |
| Credential Access | T1003.006 DCSync | 目录服务访问 | 非 DC 主机发起 DS-Replication-Get-Changes* | **4662**（需开目录服务访问审计） |
| Credential Access | T1558.003 Kerberoasting | Kerberos 票据请求 | 单账号短时大量 4769 且加密类型 RC4 `0x17` | **4769**；4771/4776 关联 |
| Lateral Movement | T1021.001 RDP | 登录事件 + 终端服务 | LogonType=10 来源非管理网段；异常账号越权 | 4624(Type 10)、4778/4779；TerminalServices 1149 |
| Lateral Movement | T1021.002 SMB/Admin Shares | 共享访问审计 | ADMIN$/C$ 访问后紧跟服务创建或计划任务 | **5140/5145**（需详细文件共享审计）；Sysmon 3 |
| Command and Control | T1071.001 Web Protocols | Sysmon 连接 + 代理/Zeek | 非浏览器进程固定周期外连 443、UA/SNI 与进程不匹配 | Sysmon **3**（官方文档明示默认关闭，须显式启用）、22；代理 http.log |
| Command and Control | T1071.004 DNS | DNS 查询 + DNS 服务器 | 高熵长子域、TXT 查询、固定周期解析同域 | Sysmon **22**；Zeek dns.log；DNS 服务器日志 256【上游事件号，未验证】 |
| Command and Control | T1197 BITS Jobs | BITS 客户端日志 | `bitsadmin /transfer`、`Start-BitsTransfer` 拉外部载荷 | Bits-Client/Operational 3/59/60【上游事件号，未验证】；Sysmon 1 |
| Exfiltration | T1041 Exfiltration Over C2 | 代理 / NetFlow | 单会话出站字节远超同进程基线、上传到新注册域 | Zeek conn.log `bytes_out`、代理日志；Sysmon 22 |
| Impact | T1486 数据加密 for Impact | 文件事件 + 进程 | 短时大量文件重写/改名、扩展名批量变更、前置卷影操作 | Sysmon 11、23、26；Sysmon 1 |
| Impact | T1490 Inhibit System Recovery | 进程命令行 | `vssadmin delete shadows`、`wbadmin delete`、关闭恢复 | Sysmon 1（须采集命令行）；System 104【上游】 |

## 2. 狩猎假设生成法：4 类来源 + 可落地查询

上游（28-001/28-003）的 4 类来源，必须钉死「技术号 + 数据源 + 时间窗 + 判定标准」，否则狩猎会退化成翻日志：
1. **威胁情报驱动**：新报告用了某技术 → 假设本环境存在同技术行为（例：报告用 T1003.001 → 查非系统进程访问 lsass）。
2. **数据基线异常驱动**：某指标偏离基线（DNS 查询量 +300%、夜间登录占比突变）→ 假设存在隧道/自动化。
3. **已知漏洞驱动**：某 CVE 在野 → 假设内网有扫描与利用尝试（查 4625/4688/Web 访问日志的利用特征）。
4. **红队反馈驱动**：已打穿的技术 → 假设真实攻击者走同一条路，优先补检测（闭环最短）。

假设卡片字段（可直接落 YAML）：`id / title / source / mitre_technique[] / hypothesis / data_sources[] / indicators[] / time_window / validation_query / 判定标准 / status`【上游模板 + 判定标准】。
```spl
# A. T1059.001 PowerShell 远程下载执行（Sysmon 1 为主，4104 交叉验证）
index=windows EventCode=1 (Image="*\\powershell.exe" OR Image="*\\pwsh.exe")
 (CommandLine="*Net.WebClient*" OR CommandLine="*DownloadString*" OR CommandLine="*Invoke-WebRequest*" OR CommandLine="*-enc *" OR CommandLine="*Start-BitsTransfer*")
| table _time host User ParentImage CommandLine
# B. T1003.001 非系统进程访问 lsass（高信号低噪声）
index=windows EventCode=10 TargetImage="*\\lsass.exe" GrantedAccess IN ("0x1010","0x1410","0x1438","0x1fffff") | stats count values(CallTrace) by host SourceImage User
# C. T1558.003 Kerberoasting：单账号短时大量 RC4 票据
index=windows EventCode=4769 TicketEncryptionType="0x17" | stats dc(ServiceName) as svc count by TargetUserName IpAddress | where svc>5
# D. T1685.005 日志被清（1102 近零误报，直接 P1）+ 基线类：同源 IP 多账号登录
index=windows EventCode=1102 | table _time host user
index=windows EventCode=4624 | stats dc(Account_Name) as users by IpAddress | where users>5
```

```bash
# 高熵长子域（T1071.004 DNS 隧道）：先确认字段存在再上规则
curl -s -X POST "localhost:9200/winlogbeat-*/_search" -H 'Content-Type: application/json' -d '{
 "query":{"bool":{"filter":[{"term":{"event.code":"22"}},{"range":{"@timestamp":{"gte":"now-24h"}}}]}},
 "aggs":{"d":{"terms":{"field":"dns.question.name","size":50}}}}' | jq '.aggregations.d.buckets[]|{q:.key,n:.doc_count}'
```

索引名/字段名与 Sysmon 事件号以现场 mapping 为准，上面查询全部【未验证】。

## 3. Atomic Red Team 真实用法

**安装**（模块在 PSGallery）与路径【实测官方文档】：

```powershell
Install-Module -Name invoke-atomicredteam -Scope CurrentUser -Force
Import-Module "C:\AtomicRedTeam\invoke-atomicredteam\Invoke-AtomicRedTeam.psd1" -Force
```

默认 atomics 路径：Windows `C:\AtomicRedTeam\atomics`（`<HOMEDRIVE>\AtomicRedTeam\atomics`）、Linux/macOS `$HOME/AtomicRedTeam/atomics`；全局改路径用 `$PSDefaultParameterValues = @{ "Invoke-AtomicTest:PathToAtomicsFolder" = "C:\AtomicRedTeam\atomics" }`【实测】。
**上游勘误**：上游写 `-Path "C:\AtomicRedTeam\atomics"` 参数名错误，真实参数是 **`-PathToAtomicsFolder`**；上游 `-TimeoutSeconds` **未验证**（旧版参数列表无此项，用 `Get-Help Invoke-AtomicTest -Full` 核）。

```powershell
Invoke-AtomicTest T1059.001 -ShowDetailsBrief   # 列测试号+名字，选号用，不执行
Invoke-AtomicTest T1059.001 -ShowDetails        # 详列攻击命令/输入参数/前置条件
Invoke-AtomicTest T1059.001 -ShowDetails -anyOS # 忽略平台过滤
Invoke-AtomicTest T1218.010 -TestNumbers 1,2    # 指定测试号（短写 -1,2）
Invoke-AtomicTest T1564.001 -TestNames "Create a hidden file"
Invoke-AtomicTest T1003.001 -TestGuids <auto_generated_guid>  # 编排脚本首选
Invoke-AtomicTest T1059.001 -GetPrereqs | Invoke-AtomicTest T1059.001 -CheckPrereqs
Invoke-AtomicTest T1059.001 -TestNumbers 3 -Cleanup           # 不收尾会在靶机留残留
```

atomics 目录与 YAML 键【实测】：

```text
atomic-red-team/atomics/T1059.001/
├── T1059.001.md      # 人读版（红蓝对照）
├── T1059.001.yaml    # attack_technique / display_name / atomic_tests[]
└── src/              # 测试依赖脚本与载荷
# atomic_tests[] 每条：name / auto_generated_guid / description / supported_platforms /
#   input_arguments / dependency_executor_name / dependencies[] / executor{name,command,cleanup_command,elevation_required}
```
**紫队闭环 6 步**：`ShowDetailsBrief 选号 → GetPrereqs → 记录开始时间戳 → 执行 → SIEM 按 主机+时间窗+命令行 查证 → Cleanup`。每条测试号单独记：技术号 T1059.001 的 1 号检出、3 号未检出，只能记「部分覆盖」。
**跨平台**：`atomic-operator`（Python，仓库是 **swimlane/atomic-operator**，非 redcanaryco）【实测】：

```bash
pip install atomic-operator
atomic-operator run --atomics-path "~/_Swimlane/atomic-red-team" --techniques T1059.004,T1560.001 \
  --check_dependencies True --get_prereq_command True --cleanup True --command_timeout 40 --debug
# --select_tests 交互选测试；--kwargs '{"filename":"x.py"}' 传参；超时默认 20s
```

上游 `atomic-operator run T1059.004` 形状不对（缺 `--techniques`）且归属写错；`--check_dependicies`（原文拼写）与 `--check_dependencies` 在官方文档同时出现，落地前跑 `atomic-operator run --help`。

## 4. Caldera 部署与操作
现状【实测】：仓库已从 `mitre/caldera` 迁至 **`apache/caldera`**（Apache-2.0），文档仍在 `caldera.readthedocs.io`；要求 Linux/macOS + Python 3.10+。

```bash
git clone --recursive https://github.com/apache/caldera.git
cd caldera && pip install -r requirements.txt
python server.py --insecure          # 默认 8888，无 TLS
python server.py --insecure --build  # 首次/插件变更后构建前端（magma 需 Node.js）
# Docker 分 full / slim；slim 不含 emu、atomic 数据，启用时按需下载
```

- 紫队常用默认插件：**Sandcat**（默认 agent）、**Manx**（shell/反连）、**Stockpile**（TTP 与 adversary profile 库）、**Atomic**（引入 Atomic Red Team TTP）、**Magma**（前端）、**Debrief**（结果分析）、**Compass**（ATT&CK 可视化）、**GameBoard**（红蓝同框）【实测插件清单】。
- 登录：默认 `red` 用户，口令见 `conf/local.yml`；`--insecure` 模式读 `conf/default.yml`【实测文档原文】。
- **Agent 部署（文档 5 步，已核实）**：① `red` 登录 → ② Agents 页点「Click here to deploy an agent」→ ③ 选 **Sandcat** + 目标平台，核对 `app.contact.http` 与服务端监听一致 → ④ 在受害机执行页面生成的命令（需高权的 ability 用提权 shell）→ ⑤ Agents 列表确认上线。**agent one-liner 由 UI 按服务端地址生成，本文不写未验证的手抄版本**。
- **跑操作**：Operations 页 → 选 group（专设 `bas` 组便于回收）→ 选 adversary profile（`Discovery`/`Hunter` 为官方建议起步档）→ start。**导出**：operation 模态「Download report」(JSON) +「Download event logs」(JSON，结束时自动落盘)【实测】。
- **API**：REST 基址 `http://<host>:8888/api/v2`，鉴权头 **`KEY: <api_key>`**，`POST /api/v2/operations` body `{"name":...,"adversary":{"adversary_id":...},"group":"bas","autonomous":1}`【上游 24-004，**未验证**：字段名以 UI 的 API Docs 与 `conf/local.yml` 的 `api_key_*` 为准】。
- 纪律：只在授权靶场；一套操作一套 group + 一套 agent，跑完立即销毁 agent 与目标侧残留。

## 5. ATT&CK Navigator：图层 JSON 结构与导入流程

图层是 **v4.5 格式 JSON**，一份文件只属一个 domain；规范原文 `mitre-attack/attack-navigator` 仓库 `layers/spec/v4.5/layerformat.md`【实测】。

| 字段 | 必填 | 说明 |
|:---|:---:|:---|
| `versions.attack` | 否 | 你分析的 ATT&CK 版本（如 `19.2`）；`versions.layer` 须为 `"4.5"`，`navigator` ≥ `4.9.0` |
| `name` / `domain` | **是** / **是** | 图层名；domain ∈ `enterprise-attack`/`mobile-attack`/`ics-attack` |
| `techniques[]` | 否 | `techniqueID`（**大小写敏感**，子技术 `T####.###`）、`tactic`（短横线短名如 `lateral-movement`，子技术跨战术时必填）、`score`、`color`、`comment`、`enabled`、`metadata[{name,value}]`、`showSubtechniques` |
| `gradient` / `legendItems` / `filters` / `sorting` / `hideDisabled` | 否 | `gradient{colors,minValue,maxValue}` 决定配色；`filters.platforms` 只显示 Windows；`sorting` 0–3 |

```json
{
  "name": "2026Q3 检测覆盖度", "domain": "enterprise-attack",
  "versions": { "attack": "19.2", "navigator": "5.1.0", "layer": "4.5" },
  "description": "原子测试验证结果：score=覆盖级别，comment=证据ID",
  "techniques": [
    { "techniqueID": "T1059.001", "tactic": "execution", "score": 50,
      "comment": "4104 采集✓；测试#1 检出 / #3 未检出（部分覆盖）" },
    { "techniqueID": "T1003.001", "tactic": "credential-access", "score": 0,
      "comment": "缺口：Sysmon 10 未开、4656 无 SACL", "color": "#fc3b3b" }
  ],
  "gradient": { "colors": ["#ffffff", "#ffe766", "#8ec843"], "minValue": 0, "maxValue": 100 },
  "legendItems": [{ "label": "已验证检出", "color": "#8ec843" }], "filters": { "platforms": ["Windows"] }
}
```
**导入流程**：Navigator（`mitre-attack.github.io/attack-navigator/`）→ **Open Existing Layer → Upload from local** 选 JSON（或 Create New Layer 手工建）→ 顶栏核对 **domain 与 ATT&CK 版本**与生成时一致 → 打开「show annotated techniques only」只看有标注的格子。多域分别建层。批量生成可用 `mitreattack-python` 读 STIX 或离线 `attack-stix-data`，但**不要用它替代一次人工核对**（技术号会随版本迁移）。

## 6. 紫队覆盖度评估流程与补测优先级

**覆盖级别（自定，必须写进 comment）**：`0` 无采集 → `1` 有日志无规则 → `2` 有规则未验证时效 → `3` 规则 + 告警 + 可复现检出（含 MTTD 与证据 ID）。
**流程（逐条走，不许批量盖章）**：
1. 定范围：从 Navigator 层挑技术（优先红队/RAT/勒索报告里的高频项），写明 ATT&CK 版本。
2. 逐条跑原子测试，记 `开始/结束时间戳 + host + test number + 完整命令`。
3. 查 SIEM/EDR：按 `host + 时间窗 + 命令行特征`；**只看 EDR 弹窗不算**，要拿到 SIEM 里的事件。
4. 记结果：`detected(t/f)`、`MTTD`、`命中 rule id`、`原始事件 ID`；缺证据不算检出。
5. 回填图层：`score`=覆盖级别，`comment`=证据 ID + 缺口原因（哪一路数据源没开）。
6. 补测后**重跑同一个 test number** 回归，通过才闭环；失败回退状态。

**判定铁律**：一条技术有任一测试号未检出，只能记「部分覆盖」；「装过 EDR」≠「SIEM 有覆盖」；「日志里有该事件类型」≠「有检测规则」。
**补测优先级**：`优先级 = 真实使用频率 × 影响面 ÷ 补测成本`，成本阶梯 `补采集/开审计 < 写 Sigma 规则 < 上 EDR/内存检测`。最该先补的「默认没采集」低成本缺口：Sysmon 3 与 22 未开、4104 未开、4688 未含命令行、4656/4663 无 SACL、4662 目录服务访问审计未开、5140/5145 未开、Linux auditd 未配 execve、云审计未接入 SIEM。
**度量（上游 24-003/24-005 口径）**：覆盖率（≥2 级视为覆盖）、MTTD、误报率、评估频率、缺口转规则平均时长；上游参考目标为覆盖率 >85%、MTTD <15min、FP <10%【上游】。
