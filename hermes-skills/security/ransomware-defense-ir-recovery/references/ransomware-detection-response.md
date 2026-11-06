# 勒索检测与应急处置参考（ransomware-defense-ir-recovery）

> **定位**：本卡只覆盖**防御 / 处置 / 恢复**。取证方法论见 `digital-forensics`、`traffic-analysis-pcap`；样本逆向见 `malware-analysis`；授权进攻演练见 `authorized-ransom-lab`、`ransomware-builder`。
> **证据分级**：【L1】官方文档/厂商公告原文核实；【L2】公开威胁报告；【上游】来自 Hi-FullHouse CyberSecurity-Skills（2026-02 快照），未独立核实；【未验证】未核实，使用前自测。

## 1. 家族指纹（扩展名 / 勒索信 / 来源年份）

| 家族 | 加密扩展名 | 勒索信文件名 | 来源（年份） |
|---|---|---|---|
| LockBit 2.0/3.0 | `.lockbit` | `<Ransomware ID>.README.txt`；附带改桌面壁纸/图标行为 | 【L2】CISA AA23-075A（2023） |
| ALPHV / BlackCat | 7 位随机字符扩展名（每个受害者不同） | `RECOVER-<7位扩展名>-FILES.txt` + 同名 `.png` 壁纸；变体 `GET IT BACK-<扩展名>-FILES.txt` | 【L2】CISA AA23-353A（2023-12）、Emsisoft（2023）、pcrisk |
| Conti | v1 `.CONTI`；v2/v3 为随机 5 位大写字母扩展名 | `CONTI_README.txt`、`Conti_readme.txt`、`CONTIm.txt`、`R3adm3.txt`、`readme.txt` | 【L2】Cybereason（2021）、pcrisk |
| Ryuk | `.RYK` | `RyukReadMe.txt` + `RyukReadMe.html`；另有 `UNIQUE_ID_DO_NOT_REMOVE.txt` | 【L2】HHS（2020）、CERT-FR（2021）、MITRE S0446 |
| Phobos | `.phobos` 及多套变体扩展名 | `info.txt`、`info.hta`；重命名规则 `<原名>.id[<ID>].[邮箱].<扩展名>` | 【L2】CISA AA24-060A（2024-02） |
| Akira | `.akira` | `akira_readme.txt` | 【L2】SentinelOne/Trend Micro（2023+，ChaCha20） |
| Cl0p / Clop | `.Clop`、`.C_I_0P`、`.CIIp` | `ClopReadMe.txt`、`!Cl0pReadMe.txt`、`README_C_I_0P.TXT` | 【L2】公开家族表（2019+） |
| STOP/Djvu | 数十种（`.djvu`、`.stop`…） | `_readme.txt`（含 "$980 / $490" 报价与 personal ID） | 【L2】Emsisoft 解密页（2026-06 查阅 URL，报价文本未逐字复核） |

判定要点：
1. **文件名 + 扩展名双向确认**；`readme.txt` / `README.txt` 属通用名，多家族共用，单看名字会误判。
2. 勒索信原文 + 一个 <1MB 加密样本，才能让 ID Ransomware 给出可信判定（见 §6）。
3. 【L2】ALPHV/BlackCat 的扩展名与勒索信名由**每个受害者独立的配置**决定（JSON，含 RSA 公钥、跳过目录、要终止的服务清单），同族不同受害者扩展名不同——只背扩展名会漏判。

## 2. YARA 规则（4 条，已用 yara-python 4.5.4 实测编译通过）

```yara
rule Ransomware_LockBit3_Behavior_And_Note
{
    meta:
        description = "LockBit 3.0 behavior + note strings (source: CISA AA23-075A, 2023)"
        reference   = "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-075a"
        source_year = "2023"
    strings:
        $note = ".README.txt" ascii wide nocase
        $n1   = "LockBit" ascii wide nocase
        $n2   = "all your files" ascii wide nocase
        $c1   = "vssadmin delete shadows" ascii wide nocase
        $c2   = "wbadmin delete catalog" ascii wide nocase
        $c3   = "bcdedit /set {default} recoveryenabled no" ascii wide nocase
    condition:
        uint16(0) == 0x5A4D and filesize < 20MB and
        $note and ($n1 or $n2) and 1 of ($c*)
}

rule Ransomware_Phobos_Note_And_Evasion
{
    meta:
        description = "Phobos: info.txt/info.hta note + firewall/shadow/BCD destruction (CISA AA24-060A, 2024-02)"
        reference   = "https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-060a"
        source_year = "2024"
    strings:
        $note1 = "info.hta" ascii wide nocase
        $note2 = "info.txt" ascii wide nocase
        $name  = /id\[[A-Za-z0-9]{6,14}\]\.[A-Za-z0-9._-]{3,40}@[A-Za-z0-9.-]{4,40}\.[A-Za-z]{2,6}/ ascii
        $c1    = "netsh advfirewall set currentprofile state off" ascii nocase
        $c2    = "netsh firewall set opmode mode=disable" ascii nocase
        $c3    = "wmic shadowcopy delete" ascii nocase
        $c4    = "bcdedit /set {default} bootstatuspolicy ignoreallfailures" ascii nocase
        $c5    = "wbadmin delete catalog" ascii nocase
    condition:
        uint16(0) == 0x5A4D and filesize < 10MB and
        $note1 and $note2 and 2 of ($c*) and $name
}

rule Ransomware_ShadowCopy_Backup_Destruction_Toolset
{
    meta:
        description = "Generic ransomware prep: shadow copy deletion + backup catalog wipe + recovery disable"
        source_year = "2024"
    strings:
        $v1 = "vssadmin delete shadows" ascii wide nocase
        $v2 = "vssadmin resize shadowstorage" ascii wide nocase
        $v3 = "wmic shadowcopy delete" ascii wide nocase
        $v4 = "Get-WmiObject Win32_ShadowCopy" ascii wide nocase
        $b1 = "wbadmin delete catalog" ascii wide nocase
        $b2 = "wbadmin delete systemstatebackup" ascii wide nocase
        $b3 = "wbadmin delete backup" ascii wide nocase
        $d1 = "bcdedit /set {default} recoveryenabled no" ascii wide nocase
        $d2 = "bcdedit /set {default} bootstatuspolicy ignoreallfailures" ascii wide nocase
        $f1 = "netsh advfirewall set allprofiles state off" ascii wide nocase
    condition:
        filesize < 5MB and 1 of ($v*) and 1 of ($b*) and 1 of ($d*) and $f1
}

rule Ransomware_ALPHV_BlackCat_Note_Naming
{
    meta:
        description = "ALPHV/BlackCat note naming RECOVER-<ext>-FILES.txt (CISA AA23-353A, 2023-12)"
        reference   = "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-353a"
        source_year = "2023"
    strings:
        $n1 = /RECOVER-[A-Za-z0-9]{6,10}-FILES\.txt/ ascii wide
        $n2 = /GET IT BACK-[A-Za-z0-9]{6,10}-FILES\.txt/ ascii wide nocase
        $t1 = "STRONGLY encrypted" ascii wide nocase
        $t2 = "Data includes:" ascii wide nocase
    condition:
        ($n1 or $n2) and 1 of ($t*)
}
```

用法与注意事项：
- 编译/扫描（实测可用，Windows Git-Bash + yara-python 4.5.4）：`yara -r rules.yar <target>` 或 `python -c "import yara; yara.compile(filepath='rules.yar')"`。
- 规则 1/2 要求 `uint16(0)==0x5A4D`（PE），对**脚本载荷**（`.bat/.ps1`）不命中；脚本场景用规则 3。
- 规则 2 的 `$name` 正则匹配 Phobos 重命名后的文件名，只在样本内出现该字符串时命中；建议同时对**文件名列表**做同一正则扫描。
- 【L1】上述 4 条为本次根据 CISA 公告公开特征**自撰并实测编译**（非 CISA 原文规则）；规则 3 已用含 `vssadmin delete shadows /all /quiet`、`wbadmin delete catalog -quiet`、`bcdedit /set {default} recoveryenabled no`、`netsh advfirewall set allprofiles state off` 的合成证据文件实测命中。
- 误报来源：合规审计脚本、备份运维脚本、补丁/迁移工具常含同类命令。**先在生产环境以"仅告警"模式跑 2 周再阻断**。

## 3. Sigma / Sysmon 检测点

| 数据源 | 事件 | 匹配点 |
|---|---|---|
| Sysmon EID 1 / Security 4688 | 进程创建 | CommandLine 含 `vssadmin delete shadows`、`vssadmin resize shadowstorage`【上游】、`wmic shadowcopy delete`、`wbadmin delete catalog`、`bcdedit /set {default} recoveryenabled no`、`netsh advfirewall set allprofiles state off`；父进程为 Office / `wscript` / `mshta` / `powershell -enc` |
| Sysmon EID 11 | FileCreate | TargetFilename 命中勒索信命名：`*.README.txt`、`RECOVER-*-FILES.txt`、`info.hta`/`info.txt`、`RyukReadMe.txt`、`_readme.txt`、`ClopReadMe.txt`、`akira_readme.txt`；同一 Image 在 60s 内新建 >200 文件（按自身基线调阈值） |
| Sysmon EID 11 + 原文件改名 | 加密写入速率异常 | 同进程短时间内在多目录产生"同名不同扩展名"文件，且原文件被重命名/删除；写速率（文件数/分钟）突增 10x 以上 |
| Sysmon EID 13/14 | 注册表 SetValue | `HKCU\Control Panel\Desktop\Wallpaper` 被改写（LockBit/ALPHV 换壁纸）；`DisableAntiSpyware`、`AmsiEnable=0`【上游】 |
| Sysmon EID 10 | ProcessAccess | LSASS 异常访问（前置凭据窃取阶段）【上游】 |
| Security 1102 | 审计日志被清空 | 反取证动作，出现即视为高可信入侵 |
| Security 4698 / 7045 | 计划任务 / 服务创建 | 持久化与载荷投递【上游】 |
| Security 5140 / 4624 LogonType=3 | 共享访问 / 网络登录 | 横向移动与备份面访问痕迹【上游】 |
| System 日志 VSS 相关事件 | 卷影副本删除 | 【上游】称 `Event ID 33` 为卷影删除——**未验证**；可靠证据以 Sysmon EID 1 抓到 `vssadmin`/`wmic shadowcopy` 命令行 + VSS 服务日志交叉确认为准 |

补充：
- SigmaHQ 有同族规则（名称：`proc_creation_win_shadow_copies_deletion.yml`，公开仓库，未逐字校验），上线前用 `sigma convert -t <backend>` 自行转换。
- 【上游】管线里的 Sigma 骨架 `id` 为占位 UUID（`12345678-1234-1234-1234-123456789001/002`）+ detection 列表 `vssadmin delete shadows` / `vssadmin resize shadowstorage`：**检测逻辑可吸收，占位 id 必须换成真实 UUID** 才能入库。
- 备份/EDR 侧告警也要接：备份作业被删/被禁、EDR 策略被改、`rclone`/`MEGA` 等外传工具执行（ALPHV 案例使用 Mega/Dropbox 外传）。

## 4. 真实排查命令（备份面 / 卷影面 / 恢复面）

Windows 主机（加密后**优先在取证副本/镜像**上跑，避免污染）；命令为标准 Windows 命令（2026 仍在用）：
```bat
vssadmin list shadows
vssadmin list shadowstorage
wbadmin get versions
wbadmin get status
wbadmin get items -version:01/01/2026-06:00   :: 版本串以 get versions 输出为准
bcdedit /enum {default}
bcdedit /enum all
wevtutil qe Security /q:"*[System[(EventID=1102)]]" /f:text /c:5
wevtutil epl System C:\evidence\System.evtx
net share
net use
```
```powershell
Get-SmbShare | Select-Object Name,Path,Description
Get-WmiObject Win32_ShadowCopy | Select-Object InstallDate,DeviceObject
Get-ScheduledTask | Where-Object {$_.TaskPath -notlike "\Microsoft\*"} | Select-Object TaskName,TaskPath
Get-Service VSS | Select-Object Name,Status,StartType
```
Linux / ESXi 与备份挂载面：
```bash
mount | grep -Ei 'nfs|cifs|backup'          # 备份/共享是否直接挂在生产主机上（加密半径内）
findmnt -t nfs4,cifs -o TARGET,SOURCE
df -hT
smbclient -L //<backup-host> -N             # 备份机共享暴露面探测（受权范围内）
```
云侧（读侧证据，写侧详见 `references/backup-resilience.md`）：
```bash
aws ec2 describe-snapshots --owner-ids self
aws s3api list-object-versions --bucket <bucket> --prefix <prefix>
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteSnapshot
```
- ESXi：检查数据存储内 `.vmdk/.vmx` 是否被改名/加密（ESXiArgs 2023 系特征）；【未验证】具体 `esxcli` 命令未核实，勿照抄。

## 5. 隔离与遏制：拔网线 vs 关机

**决策树（按优先级）**
1. **加密仍在进行**：先**断网络**（拔网线/禁用网卡/交换机端口 shutdown/隔离 VLAN），再决定是否关机——断网可即时阻断 SMB/域内横向与备份写入。
2. **保留内存取证价值**：若需要内存中的密钥/注入进程证据，**不要直接断电**。条件允许时先做内存镜像（`winpmem`、Belkasoft/FTK Imager 内存导出，工具清单见 `digital-forensics`），再关机。
3. **必须立刻断电的场景**：加密速度极快、无法在数分钟内定位源头主机、且机房无法逐台断网 → 断电优先（代价：内存证据丢失）。
4. **已经停止加密**：保持开机取证（易失性数据 + 日志），仅做逻辑隔离（禁用网络、禁用账号、停用备份作业），不要重启。

**必做**
- 立刻切断所有备份作业/复制任务（`Disable-VBRJob`、备份控制台停作业），**防止被加密数据覆盖干净备份**。
- 冻结/保护干净副本：把不可变策略、离线副本标记为只读/锁定，登记副本时间点。
- 禁用而非删除**涉事账号**（保留取证），视情况重置域管凭据（`krbtgt` 双次重置安排在恢复阶段，避免打断取证）。
- 保全：勒索信（含"每个目录一份"）、<1MB 加密样本、EDR/AV 日志、EVTX 原文件、Sysmon 日志；用 `wevtutil epl` 导出而不是原地清理。
- 断掉 RDP/VPN/共享/管理端口（含备份管理口、iDRAC/iLO/ESXi 管理面）。

**禁止**
- 不要删除勒索信、不要跑"批量去掉扩展名"脚本（可能二次破坏/覆盖可恢复内容）。
- 不要在未验证备份干净前执行批量恢复（会把加密版本同步回生产）。
- 不要在原盘上做解密尝试（可能覆盖可恢复的头部/明文残片）；先在副本上试。
- 不要"重启试试"——会丢内存证据且可能触发启动阶段载荷。

## 6. 解密可行性评估流程

1. **保全样本**：复制勒索信 + 一个**小于 1MB** 的加密文件（不要就地操作，另存到 U 盘/证据目录）。
2. **识别家族**：上传到 **ID Ransomware** `https://id-ransomware.malwarehunterteam.com/`（返回家族与可用解密器）；离线初判 `strings note.txt | head -20` 与 §1 表格比对。
3. **查可用解密器**：
   - NoMoreRansom 解密工具库 `https://www.nomoreransom.org/en/decryption-tools.html`
   - Emsisoft 免费解密器总览 `https://www.emsisoft.com/en/ransomware-decryption/`；STOP/Djvu 专用 `https://www.emsisoft.com/en/ransomware-decryption/stop-djvu/`
4. **可行性判据**（任一成立才值得投入）：
   - 存在官方/厂商解密器（覆盖对应版本）；
   - 【L2】执法或厂商释放过主密钥（如 REvil/Sodinokibi 主密钥解密器，公开报道 2021）；
   - 加密实现有缺陷（公开案例：Clop 2019 Linux 版"flawed encryption"有解密器）；
   - 变体属**部分加密**：只加密文件头/尾部追加（可用截断类工具抢救部分内容）——【未验证】须先在副本上验证该变体行为，勿假设。
5. **验证与再验证**：任何解密器先在**副本**上跑；成功后将解密输出与备份/原始副本做哈希比对，确认非"用另一份密钥换文件"的骗局。
6. **记录决策**：无解密器时明确写"不可自主解密，依赖备份/重建"，并把结论与依据（家族、版本、解密器覆盖情况）写进报告；不要模糊表述为"正在尝试解密"。

## 7. 恢复顺序与恢复后核查清单

**恢复顺序（先地基后业务）**
1. 认证与地基：域控/AD、DNS/DHCP、KMS/证书、带外管理；
2. 备份系统自身（先修好"救命的"）；
3. 核心网络与安全设备（EDR 管理端先于终端上线，避免"未受管终端"被二次打）；
4. 关键业务数据/应用（从**最干净的时间点**恢复）；
5. 外围/办公/共享；
6. 数据回灌 + 全量扫描 + 变更审计。

**恢复前后必须核对的项**
- 备份是否干净：备份作业历史里有无"被删除/被禁用/异常空洞"；加密时间窗与备份时间窗重叠的副本一律降级为可疑。
- 先在**隔离网络/clean room** 里恢复一台做验证：文件能打开、应用能起、哈希比对通过，再批量。
- 恢复后核查：本地/域账号（新增管理员、`point`/`point2` 类可疑账号）、计划任务、服务、WMI 事件订阅、GPO（壁纸/登录脚本被改）、RDP 与防火墙规则、VSS 是否被关闭、备份作业与不可变策略是否被改、EDR 策略、密码复用面（域管/备份/ESXi/iLO）、证书与私钥泄露面。
- 【L1/L2】域控被控时按"AD 林恢复"流程处理：DSRM 密码、权威恢复与全体凭据重置同步推进（`digital-forensics` 与 AD 专项卡配合）。
- 恢复完成后再开放共享与 VPN；观察期内保留日志（避免 EVTX 被覆盖导致复盘取证断链）。

## 8. 复盘报告骨架（7 段）

1. **时间线**：初始访问 → 权限提升 → 横向 → 外传 → 加密 → 发现 → 遏制 → 恢复（每步给时间戳与证据来源）。
2. **初始访问向量**：VPN/暴露面/钓鱼/凭据复用/第三方（写清"已证实"vs"未证实"）。
3. **影响面**：加密主机数与数据量、外传证据、业务停摆时长。
4. **检测与响应表现**：MTTD / MTTR、告警是否命中、规则缺口（对应补 §3 的检测项）。
5. **恢复表现**：实际 RTO/RPO vs 目标值、失败环节（备份被污染/挂载点在生产侧/不可变未开）。
6. **根因与系统性问题**：技术 + 流程 + 权限模型（不做人身归因）。
7. **行动项**：责任人 + 截止日期 + 验收方式（含"定期恢复演练""不可变副本覆盖率""备份管理面收敛"）。
