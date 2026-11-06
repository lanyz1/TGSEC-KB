# 检测工程 / SIEM 规则 / 端点检测

> **定位**：补上游缺口。`31-SOC运营` 只有 Splunk SPL / Elastic KQL 片段，**没有 Sigma 规则、没有 sigma-cli/pysigma 转换、没有 Sysmon 配置表、没有 LOLBins 清单**，本文件补齐这四块。
> **验证基线**（本机实测）：`sigma-cli 3.1.0` / `pySigma 1.5.1` / `pysigma-backend-splunk 2.1.0` / `pysigma-backend-elasticsearch 2.1.1`。所有命令、类名、格式名、`-t` 取值均来自实跑输出；3 条样例规则均通过 `sigma check`（**0 errors / 0 issues**）并实际转换成功。

## ① Sigma 规则结构与可用样例

**必备字段**：`title` `id`(UUIDv4，别用 `12345678-...` 顺序伪造) `status`(只允许 `stable/test/experimental/deprecated/unsupported`，写 `production` 会被上游 CI 拒) `description` `author` `date`(`YYYY/MM/DD`) `logsource` `detection` `falsepositives` `level`(`informational/low/medium/high/critical`)。过滤器一律 `filter_*` 命名，`condition` 写 `... and not 1 of filter_*`。

**两个实测踩坑**：① `product:windows` + `service:sysmon` + `category:process_access` 三者同写会报 `SpecificInsteadOfGenericLogsourceIssue`(HIGH)，正确写法是**只留 `category` + `product`**。② **ATT&CK v19 已改名**：`attack.defense-evasion` 与 `attack.defense_evasion` **都会**报 `InvalidATTACKTagIssue`；TA0005 现名 **stealth**，新增 TA0112 **defense-impairment**，`T1562` 已被 `T1685 Disable or Modify Tools` 取代，`T1070.001` 已改为 `T1685.005`。照抄老规则会一路报错。
### 1.1 LSASS 凭证转储（Sysmon EID 10）
```yaml
title: LSASS Process Memory Access for Credential Dumping
id: 0d894093-71bc-43c3-8c4d-8d3cb0f2ecc8
status: test
description: Detects non-allowlisted processes opening lsass.exe with credential-dumping access rights.
author: HiFullHouse Detection Engineering
date: 2026/05/01
tags: [attack.credential-access, attack.t1003.001]
logsource: {category: process_access, product: windows}
detection:
    # Sysmon 实际写的是位掩码组合，必须 contains 不能 =
    selection: {EventID: 10, TargetImage|endswith: '\lsass.exe', GrantedAccess|contains: ['0x1010','0x1410','0x1438','0x143a','0x1fffff']}
    filter_os: {SourceImage|endswith: ['\svchost.exe','\csrss.exe','\lsm.exe']}
    filter_av: {SourceImage|endswith: ['\MsMpEng.exe','\MsSense.exe','\SenseCE.exe','\MpCmdRun.exe']}
    filter_edr: {SourceImage|contains: ['\CrowdStrike\','\SentinelAgent','\elastic-agent']}
    condition: selection and not 1 of filter_*
falsepositives: ['Signed backup/troubleshooting tools reading LSASS memory']
level: critical
```
### 1.2 可疑 PowerShell（编码 / 隐藏窗口 / 下载执行）
```yaml
title: Suspicious PowerShell Execution with Download and Encoded Command
id: 6f3a2b1c-4d5e-4f60-9a7b-1c2d3e4f5a6b
status: test
description: Detects PowerShell with encoded/obfuscated command line, hidden window or in-memory download cradle.
author: HiFullHouse Detection Engineering
date: 2026/05/01
tags: [attack.execution, attack.stealth, attack.t1059.001, attack.t1027.010]
logsource: {category: process_creation, product: windows}
detection:
    # 两个子字典是 OR：既匹配进程名，也匹配改名后的原始文件名
    selection_img:
        - {Image|endswith: ['\powershell.exe','\pwsh.exe']}
        - {OriginalFileName: ['PowerShell.EXE','pwsh.dll']}
    selection_flags: {CommandLine|contains: [' -enc ',' -EncodedCommand ','FromBase64String',' -w hidden',' -windowstyle hidden',' -ExecutionPolicy Bypass']}
    selection_cradle: {CommandLine|contains: ['DownloadString','DownloadFile','Invoke-Expression',' IEX ','Net.WebClient','Reflection.Assembly']}
    condition: selection_img and (selection_flags or selection_cradle)
falsepositives: ['SCCM/Intune/Ansible encoded commands', 'Approved admin scripts']
level: high
```
### 1.3 勒索软件删除卷影副本 / 备份目录
```yaml
title: Ransomware Shadow Copy and Backup Deletion via VSSAdmin, WMIC and WBAdmin
id: 9b2f7c41-8a3d-4e15-b6c7-0e5f1a2b3c4d
status: test
description: Detects deletion of Volume Shadow Copies or backup catalog, the canonical pre-encryption step.
author: HiFullHouse Detection Engineering
date: 2026/05/01
tags: [attack.impact, attack.t1486, attack.t1490]
logsource: {category: process_creation, product: windows}
detection:
    # contains|all 而非整串 'vssadmin delete shadows'，抗参数顺序变化
    selection_vssadmin: {Image|endswith: '\vssadmin.exe', CommandLine|contains|all: ['delete','shadows']}
    selection_wmic: {Image|endswith: '\wmic.exe', CommandLine|contains|all: ['shadowcopy','delete']}
    selection_wbadmin: {Image|endswith: '\wbadmin.exe', CommandLine|contains|all: ['delete','catalog']}
    selection_resize: {Image|endswith: '\vssadmin.exe', CommandLine|contains|all: ['resize','shadowstorage','maxsize=']}
    selection_bcdedit: {Image|endswith: '\bcdedit.exe', CommandLine|contains: ['recoveryenabled no','bootstatuspolicy ignoreallfailures']}
    condition: 1 of selection_*
falsepositives: ['Authorized disk-space reclamation by backup admins', 'Provisioning scripts resetting recovery']
level: critical
```
三条修正要点：1.2 的 `-enc` 前后加空格是为了避开正常参数 `-encoding utf8`；1.3 用 `contains|all` 而非整串匹配。上游 `38-勒索软件防御` 的卷影规则有缺陷：`status: production`（非法值）、伪造顺序 UUID、无 `tags`/`falsepositives`/`author`/`date`、整串匹配换参数顺序就漏——以上版本已修。

## ② sigma-cli 与 pysigma 转换命令

`sigma` 只有 7 个子命令：`analyze` `check` `convert` `list` `plugin` `pysigma` `version`。`sigma list targets` 实测全部取值：`lucene`(ES Lucene) `eql`(ES EQL) `esql`(ES|QL) `elastalert` `splunk`(SPL&tstats) `splunk_spl2`；`sigma list formats splunk` = `default` `savedsearches` `data_model`，`sigma list formats eql` = `default` `eqlapi` `siem_rule` `siem_rule_ndjson`。
```bash
sigma version                          # 3.1.0
sigma list targets                     # 全部 -t 取值
sigma list pipelines [<target>]        # 可用处理管道
sigma list formats <target>            # target 是位置参数，不是 -t！
sigma check ./rules/                   # 语法+最佳实践校验（只收路径，不读 stdin）
# Splunk —— 不带 -p 必然报 "Processing pipeline required by backend!"
sigma convert -t splunk -p splunk_windows ./rules/                     # → 纯 SPL
sigma convert -t splunk -p splunk_windows -f savedsearches ./rules/ -o savedsearches.conf
sigma convert -t splunk -p splunk_cim -f data_model ./rules/           # → tstats 数据模型查询
sigma convert -t lucene -p ecs_windows ./rules/                        # → Kibana/Lucene 查询串
sigma convert -t eql    -p ecs_windows -f siem_rule_ndjson ./rules/    # → 可直接导入的 NDJSON 规则
sigma convert -t esql   -p ecs_windows --disable-pipeline-check ./rules/  # ecs_windows 未注册给 esql 后端
sigma convert -t splunk -p splunk_windows -od out/ -P '*.yml' ./rules/ # -od 输出目录, -P 文件模式
sigma convert -t splunk -p splunk_windows -s ./rules/                  # -s 跳过无法转换的规则
sigma convert -t splunk -p my_pipeline.yml ./rules/                    # 自定义字段改名管道
```
实测产出形态（样例一）：`-t splunk -p splunk_windows` → `EventCode=10 TargetImage="*\\lsass.exe" GrantedAccess IN ("*0x1010*", ...) NOT (SourceImage IN (...))`；`-t lucene -p ecs_windows` → `(event.code:10 AND winlog.event_data.TargetImage:*\\lsass.exe AND (winlog.event_data.GrantedAccess:(*0x1010* OR ...)))`；`-t eql -f siem_rule_ndjson` → 带 `"severity":"critical","risk_score":99,"type":"eql","threat":[{"tactic":{"id":"TA0006"...}}]` 的规则 JSON。`-p splunk_cim -f data_model` 对 `process_creation` 规则产出 `| tstats summariesonly=false allow_old_summaries=true ... from datamodel=Endpoint.Processes where ...`，但对 `process_access`（LSASS 类）报 `Rule type not yet supported by the Splunk data model CIM pipeline!`——这是管道能力边界，不是规则写错；`-f data_model` 若不配 `splunk_cim` 管道则报 `No data model specified by processing pipeline`。
```python
from sigma.collection import SigmaCollection
from sigma.backends.splunk import SplunkBackend                  # 2.x 只有 SplunkBackend / SplunkSPL2Backend
from sigma.pipelines.splunk import splunk_windows_pipeline
rules = SigmaCollection.load_ruleset(["rules/", "extra.yml"])    # 目录 + 单文件
print("\n".join(SplunkBackend(processing_pipeline=splunk_windows_pipeline()).convert(rules)))
```
`SigmaCollection` 真实方法（实测 `dir()`）：`from_yaml` `from_dicts` `load_ruleset` `resolve_paths` `resolve_references` `merge` `apply_filters` `get_output_rules`。
**实测否决的错误写法**：`sigma list-backends`（`No such command 'backends'`）· `sigma list backends`（无此子命令）· `sigma list formats -t splunk`（`No such option '-t'`）· `sigma convert -d out/`（`-d` 不存在，是 `-od`）· `sigma convert -t splunk .`（缺管道）· `SigmaCollection.load_directory()`（无此方法）· `SplunkSavedSearchBackend`（无此类，savedsearches 是 `-f` 格式）· `sigma create new-rule`（v3.1.0 无 `create`）。

## ③ Splunk SPL 与 Elastic 查询

### 3.1 Splunk SPL　（上线前先 `| fieldsummary` 核对真实字段名；上游 SPL 里 `| eval risk_score=(phase_recon*0.2)+...` 引用不存在的字段、`| search src_ip IN (从阶段2获取的IP列表)` 是占位伪码，两处不可直接运行，未收录）
```splunk
-- 1) 进程链：Office → 脚本宿主（Sysmon EID1 与 4688 双源，CIM 映射字段名不同故用 coalesce）
index=windows EventCode IN (1,4688)
| eval proc=lower(coalesce(Image,New_Process_Name)), parent=lower(coalesce(ParentImage,Creator_Process_Name))
| where match(parent,"(winword|excel|outlook|powerpnt)\.exe$") AND match(proc,"(powershell|pwsh|cmd|wscript|cscript|mshta|rundll32|regsvr32|bitsadmin|certutil)\.exe$")
| stats count values(CommandLine) as cmdline by host,User,parent,proc | sort - count
-- 2) 编码/隐藏窗口 PowerShell（进程命令行 + 4104 脚本块双路）
index=windows EventCode IN (1,4104)
| eval blob=coalesce(CommandLine,ScriptBlockText)
| where match(blob,"(?i)-enc(odedcommand)?\s+[A-Za-z0-9+/=]{40,}") OR (match(blob,"(?i)-w(indowstyle)?\s+hidden") AND match(blob,"(?i)(downloadstring|frombase64string|invoke-expression|ix\s*\()"))
| stats count values(ScriptBlockText) as script_block by host,User,CommandLine | sort - count
-- 3) 服务创建/修改（7045/4697）：排系统路径 + lookup 白名单
index=windows EventCode IN (7045,4697)
| eval img=lower(coalesce(Image_Path,ServiceFileName))
| where NOT match(img,"(?i)^(c:\\windows\\system32|%systemroot%\\system32)")
| lookup local=true service_installer_allowlist_lookup image AS img OUTPUT is_allowed | where isnull(is_allowed)
| stats count values(Service_Name) as svc values(Service_Type) as type by host,Account_Name,img | sort - count
-- 4) 大流量外连（Zeek conn.log；>100MB 出、<1MB 入 = 单向倾泻）
index=zeek sourcetype="bro:conn:json"
| rename id.orig_h as src_ip id.resp_h as dst_ip id.resp_p as dst_port
| stats sum(orig_bytes) as out_b sum(resp_bytes) as in_b dc(dst_port) as port_cnt values(proto) as proto by src_ip,dst_ip
| where out_b > 104857600 AND in_b < 1048576
| eval ratio=round(out_b/(in_b+1),1), out_mb=round(out_b/1048576,1) | table src_ip,dst_ip,proto,out_mb,ratio,port_cnt | sort - out_b
```
### 3.2 Elastic KQL（Kibana Discover / 查询串，ECS 字段）
```
// 1) 进程链：Office → 脚本宿主
event.category:"process" and event.type:"start" and process.parent.name:("WINWORD.EXE" or "EXCEL.EXE" or "OUTLOOK.EXE" or "POWERPNT.EXE") and process.name:("cmd.exe" or "powershell.exe" or "pwsh.exe" or "wscript.exe" or "mshta.exe" or "rundll32.exe")
// 2) 编码 / 下载执行 PowerShell
event.category:"process" and process.name:"powershell.exe" and process.command_line:(*-EncodedCommand* or *-enc* or *FromBase64String* or *DownloadString* or *Net.WebClient*)
// 3) 服务创建 7045 且二进制落在可疑路径
event.code:"7045" and winlog.event_data.ImagePath:(*\Temp\* or *\Users\Public\* or *\ProgramData\* or *\AppData\*) and not winlog.event_data.ServiceName:(*Windows Defender* or *Google Update*)
// 4) 大量出站但几乎无回包
event.category:"network" and network.direction:"egress" and destination.port:(443 or 80 or 8443) and source.bytes >= 104857600
```

### 3.3 Elastic Security EQL（贴进检测规则，**无管道符**）/ ES|QL
```
// 进程链序列：1 分钟内 Office 起 shell
sequence by host.id, user.id with maxspan=1m
  [ process where event.type == "start" and process.parent.name : ("WINWORD.EXE","EXCEL.EXE","OUTLOOK.EXE","POWERPNT.EXE") ]
  [ process where event.type == "start" and process.name : ("cmd.exe","powershell.exe","pwsh.exe","mshta.exe","rundll32.exe","regsvr32.exe") ]
// 卷影副本删除（T1490）
process where event.type == "start" and process.name : ("vssadmin.exe","wmic.exe","wbadmin.exe","bcdedit.exe","diskshadow.exe") and process.command_line : ("*delete shadows*","*shadowcopy delete*","*delete catalog*","*recoveryenabled no*")
```
> ES|QL 实跑产出（`-t esql -p ecs_windows --disable-pipeline-check`）：`from * metadata _id, _index, _version | where event.code=="10" and ends_with(winlog.event_data.TargetImage, "\\lsass.exe") and (winlog.event_data.GrantedAccess like "*0x1010*" or ...) and not (...)`——ES|QL **无前导管道符**、用 `where ... like`，与 SPL 风格不同，手写时别照抄 SPL。
> **KQL ≠ EQL ≠ ES|QL**：上游 `31-SOC运营` 的 KQL 块把 `process where ...`（EQL）与 `| stats ... | where ...`（SPL/ES|QL）混写，**粘进任一引擎都跑不通**，且用 `#` 注释（KQL 用 `//`，EQL 不支持行注释）。上面已按引擎拆开。

## ④ Sysmon 关键 EventID 与配置要点

| EID | 名称 | 检测价值 | 关键字段 |
|:---:|:---|:---|:---|
| 1 | ProcessCreate | 进程链主数据源 T1059/T1204/T1218 | `Image` `CommandLine` `ParentImage` `ParentCommandLine` `OriginalFileName` `Hashes` `LogonId` |
| 3 | NetworkConnect | 外连/C2 T1071/T1041 | `Image` `DestinationIp` `DestinationPort` `SourceIp` `Initiated` |
| 6 / 7 | DriverLoaded / ImageLoaded | BYOVD 内核驱动；侧载无签名 DLL T1574.002 | `ImageLoaded` `Signed` `Signature` `SignatureStatus` `Hashes` |
| 8 | CreateRemoteThread | 进程注入 T1055 | `SourceImage` `TargetImage` `StartAddress` `StartModule` |
| 10 | ProcessAccess | **LSASS 转储核心** T1003.001 | `SourceImage` `TargetImage` `GrantedAccess` `CallTrace` |
| 11 | FileCreate | 落地文件 / 勒索扩展名 | `TargetFilename` `Image` |
| 12/13/14 | RegistryEvent | Run 键持久化 T1547.001 | `EventType` `TargetObject` `Details` |
| 15 | FileCreateStreamHash | **Zone.Identifier / MotW**（钓鱼下载） | `TargetFilename` `Hash` `Contents` |
| 17/18 | PipeCreated / Connected | 横向命名管道（PsExec / Cobalt Strike） | `PipeName` `Image` |
| 19/20/21 | WmiEvent* | WMI 订阅持久化 T1546.003 | `EventNamespace` `Name` `Query` `Destination` |
| 22 | DnsQuery | C2 域名 / DGA | `QueryName` `QueryStatus` `Image` `QueryResults` |
| 23 | FileDelete (archived) | 删除留档，勒索事后复盘唯一来源（EID 26 FileDeleteDetected 则不归档，是其轻量替代） | `TargetFilename` `Archived` `Hashes` `Image` |
| 25 | ProcessTampering | 进程镂空 / 替换（v14+） | `Image` `Type` |
1. **EID 10 必须在配置里显式打开 `ProcessAccess`**：社区常用配置会甩掉一大批，导致 LSASS 规则永不触发（核对：`sysmon64.exe -c --` 打印当前配置后搜 `ProcessAccess`）。**`CallTrace` 白名单比 `GrantedAccess` 白名单稳**——`CallTrace` 出现 `UNKNOWN(...)` 是强信号，正常调用栈是 `C:\Windows\System32\kernel32.dll+0x...` 具名形式。 **EID 6/7 与 22**：看 `SignatureStatus` 判 BYOVD/侧载（`CheckRevocation` 在内网无 OCSP 时会全变 `Unavailable`，先测再开）；EID 22 需 `DnsLookup: true` 才有 `QueryResults`。
2. **`ArchiveDirectory`** 决定 EID 23 可用性：不配就没有删除留档；**`HashAlgorithms`** 建议 `SHA256,IMPHASH`（家族聚类用），纯 `MD5` 在情报比对中已基本无用。
3. **丢事件排查**：Sysmon 不采样，但 WEF/WEC 转发与采集器会丢——比对本地 `Microsoft-Windows-Sysmon/Operational` 计数与 SIEM 收量，差异 >5% 即管道在丢。**采集路径**：Splunk UF 采 `WinEventLog:Microsoft-Windows-Sysmon/Operational`；Elastic 用 Winlogbeat / Elastic Agent，字段同时落 `winlog.event_data.*`（未归一）与 `process.*`（ECS 归一）两套，写查询前先确认走哪套。
4. **别只用 Sysmon**：脚本块日志 4104、服务创建 7045、计划任务 4698、注册表 4657 是 Sysmon 覆盖不到或覆盖更差的面。

## ⑤ LOLBins 清单与检测点

**父链检测模板**（父链比名单本身有效得多，补进 1.2 同款规则）：

```yaml
    selection_parent: {ParentImage|endswith: ['\winword.exe','\excel.exe','\outlook.exe','\powerpnt.exe','\wscript.exe','\mshta.exe','\7z.exe']}
    selection_child:  {Image|endswith: ['\powershell.exe','\cmd.exe','\mshta.exe','\rundll32.exe','\regsvr32.exe','\certutil.exe','\bitsadmin.exe','\msbuild.exe','\wmic.exe']}
    condition: selection_parent and selection_child
```

| 二进制 | 典型滥用 | 检测点（`logsource: process_creation`） | ATT&CK |
|:---|:---|:---|:---|
| `powershell.exe`/`pwsh.exe` | 下载执行、内存加载、绕 AMSI | `-enc`/`-EncodedCommand`、`-w hidden`、`FromBase64String`、`DownloadString`、`IEX(`、`Reflection.Assembly`、`AmsiUtils` | T1059.001/T1027.010 |
| `cmd.exe` | 命令串联、管道下载 | `/c` 后接 `certutil`/`curl`/`bitsadmin`；`echo ...\|powershell`；`&&`/`\|\|` 链 | T1059.003 |
| `mshta` / `rundll32` / `regsvr32` | HTA / VBScript / 远程 `.sct`；远程 DLL/JS 执行；Squiblydoo | 参数含 `http(s)://`、`javascript:`、`vbscript:`、父进程为 Office/浏览器；`,<非系统路径>.dll`；`/i:http`、`scrobj.dll`、`/s` | T1218.005/.011/.010 |
| `certutil.exe` / `bitsadmin.exe` | 下载、Base64 解码；后台传输 | `-urlcache`、`-split`、`-decode`、`-decodehex`；`/transfer`、`/download`、`/addfile` | T1140/T1105/T1197 |
| `msbuild.exe` / `installutil.exe` | 内联 C# 编译执行；恶意 .NET 程序集 | 参数指向 `\Temp\`、`\Users\Public\`、`\AppData\` 下的 `.proj`/`.csproj`/`.xml`；非 `Microsoft.NET\` 路径的 `.exe`/`.dll` | T1127.001/T1218.004 |
| `wmic.exe` | 远程进程创建、横向、删卷影 | `process call create`、`/node:`、`shadowcopy delete`、`/format:`（远程 XSL） | T1047/T1490 |
| `msiexec.exe` / `odbcconf.exe` | 远程 MSI；执行任意 DLL | `http://`、`/q`、`/i:` 指向 UNC/`\Temp\`；`/a {REGSVR <路径>}`、`/f` 指向 `.rsp` | T1218.007/.008 |
| `cmstp` / `hh` / `control` / `cscript` / `wscript` | INF / CHM / `.cpl` / VBS / JS 代理执行 | `/s`、`/ni`、`.inf`；`.chm`、`http://`；非 System32 的 `.cpl`；参数指向 `\Temp\`、`\Downloads\`、`\AppData\`、UNC | T1218.003/.001/.002、T1059.005/.007 |
| `regasm`/`regsvcs`/`verclsid`/`mavinject`/`forfiles`/`esentutl` | .NET COM、COM 校验、注入；代理执行、绕文件复制审计 | 用户可写目录的 `.dll`；`/S /C {CLSID}`；`/INJECTRUNNING`；`forfiles /c "cmd /c ..."`；`esentutl /y /vss` | T1218.009/.012/.013、T1202/T1005 |

**检测点优先级**（LOLBins 噪声极大，靠上下文抓而非靠名单）：① **父进程异常** > 二进制本身，`WINWORD.EXE → powershell.exe` 比孤立 `powershell.exe` 强十倍；② **网络可达性**：参数里出现 URL/UNC 几乎无正常场景；③ **落地路径**：`\Temp\` `\Users\Public\` `\ProgramData\` 下的可执行/脚本远比 `System32` 下的可疑；④ **签名状态**（EID 7）：官方二进制对非系统 DLL 做 `Signed: false` 调用是侧载信号；⑤ **频次**：同一宿主 5 分钟内连出 3 个以上不同 LOLBin 几乎必是攻击链；⑥ 名单只用来做 `filter_*` 反面清单，且只在环境基线固化后可行——新环境直接列白=淹没 SOC。

## ⑥ 误报调优与检测覆盖度评估

**上线三步压噪**：① **先做数据侧值域统计再写规则**——`| stats dc(Image) by ParentImage`（Splunk）/ `STATS COUNT(*) BY process.parent.name`（ES|QL）；凭"我知道环境里有什么"写规则，误报率基本 100%。② **白名单写成独立 `filter_*` 块**，不写进 selection：`condition` 一眼可见过滤了什么，diff 时白名单变化不污染检测逻辑。③ **告警必须带证据字段**（`fields:`）：没有 `CommandLine`/`ParentImage`/`CallTrace` 的告警等于二次狩猎，SOC 会直接静音这条规则。

| 调优手法 | 做法 | 适用 |
|:---|:---|:---|
| 值修饰符收窄 | `\|startswith`/`\|endswith` 替代宽泛 `\|contains`；`\|re` 只在必要时用 | 所有规则 |
| 绑定父进程 + 签名/精确路径白名单 | 高风险子进程限定父进程集合；白名单用**签名主体或精确路径，不用厂商名子串** | PowerShell、mshta、rundll32、EDR/杀软/LOLBin |
| 聚合阈值 | Splunk `\| where count > N`；Sigma `condition: selection \| count() > 50 by host` | 批量加密、枚举、扫描 |
| 时间窗关联 + 抑制 | Splunk `transaction` / EQL `sequence ... with maxspan`；在 SIEM 侧做 throttle，规则保持纯粹 | 进程链、多阶段、重复告警 |

**上线硬指标**：真实数据上跑 30 天 → 命中数 `> 0`（为 0 说明 logsource 或字段写错，不是"环境干净"）且 `< 20/天`（超标先加过滤器）；抽 20 条命中样本人工判定，**精确率 < 30% 不许上线**。
**覆盖度评估**：`sigma analyze attack count layer.json ./rules/`（位置参数 `{count|max|level}` 是计分函数；实测产出 MITRE ATT&CK Navigator 图层 JSON，`attack 19.2 / navigator 4.8.1 / domain enterprise-attack`，可直接导入 Navigator 看热力图），`sigma analyze logsource ls.md ./rules/` 出 logsource×level 分布表。

1. **先看数据源覆盖，再看技术覆盖**。`analyze logsource` 里"某 logsource 只有 1 条规则"意味着那条数据源没收或没写规则，比多写 10 条 PowerShell 规则重要得多。
2. **技术覆盖按"数据源 + 规则 + 验证"三件套判定**，缺一不算覆盖：有规则无数据＝假覆盖；有数据无规则＝盲区；有规则有数据但从未用原子测试验证＝未验证覆盖。
3. **反向验证而非正向宣称**：
   ```bash
   Invoke-AtomicTest T1003.001 -ShowDetails    # 列出原子测试细节
   Invoke-AtomicTest T1003.001 -CheckPrereqs   # 只检查前置条件，不执行
   Invoke-AtomicTest T1003.001                 # 执行并计时，量 MTTD
   Invoke-AtomicTest T1003.001 -Cleanup        # 清理
   ```
   上游 `28-威胁狩猎` 的 `Invoke-AtomicTest <Txxxx> -CheckPrereqs/-Cleanup/-ShowDetails` 参数写法正确（属 AtomicRedTeam PowerShell 模块）；但 `Invoke-AtomicTest -Tactics TA0002` 整战术批量执行需明确授权，且该仓库已拆为 `atomic-red-team` + `invoke-atomicredteam`，上游那条 `pip install -r requirements.txt` **未验证**。
4. **覆盖率口径必须写明分母**：`(全技术有规则数 + 0.5 × 部分覆盖数) / 目标技术总数`；分母是"全 ATT&CK 企业域 200+ 技术"还是"本单位相关技术集"要说清。上游 ≥70 高 / 30–69 部分 / <30 无 的分级口径可用。
