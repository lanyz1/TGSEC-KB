# REPORT — 上游抽取与交付说明（ransomware-defense-ir-recovery）

产出目录：`D:/skills4redteam/out/ransomware-defense-ir-recovery/`
产出文件：`references/ransomware-detection-response.md`（225 行，限 230）、`references/backup-resilience.md`（106 行，限 170）、`DRAFT-SKILL.md`、本报告。

## 1. 读了哪些文件

上游根：`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills/`

| 上游文件 | 读取方式 | 体量 |
|---|---|---|
| `38-勒索软件防御-RansomwareDefense/skills/勒索软件应急响应与恢复-RansomwareIncidentResponseRecovery.md` | 全文分块读 | ~18.5k 字符 |
| `38-.../勒索软件攻击链分析与检测-RansomwareAttackChainAnalysisDetection.md` | 全文分块读 | ~17.8k 字符 |
| `38-.../反勒索软件加固与备份策略-AntiRansomwareHardeningBackup.md` | 全文读 | ~22.8k 字符 |
| `15-应急响应-IncidentResponse/skills/事件分类与优先级评估-IncidentTriage.md` | 全文读 | ~4.5k |
| `15-.../事件遏制与清除-ContainmentEradication.md` | 全文读 | ~7.8k |
| `15-.../日志收集与分析-LogCollectionAnalysis.md` | 全文读 | ~7.1k |
| `15-.../事件复盘与报告-LessonsLearnedReporting.md` | 全文读 | ~9.4k |
| `15-.../云环境应急响应-CloudIncidentResponse.md` | 全文读 | ~8.7k |
| `30-数字取证-DigitalForensics/skills/`（5 个文件） | 两轮 grep（`勒索\|ransom\|shadow\|MFT\|USN\|时间线\|Volatility\|易失`），命中 10 处；要点为 MFTECmd / USNJournal2CSV / hayabusa / log2timeline+psort / auditd+mactime 等**时间线工具链** | 未逐字精读 |

外部核验（web_search / web_extract）：CISA AA23-075A、AA23-353A、AA24-060A；Microsoft Learn ASR 规则；Emsisoft / NoMoreRansom / ID Ransomware 页面；Veeam / Azure CLI / Rubrik 官方与厂商资料；CVE-2024-40711 公告与利用报道。

## 2. 逐条处置（吸收 / 修正 / 丢弃）

### 2.1 已吸收（来自上游）
| 上游内容 | 去向 |
|---|---|
| Sigma 检测逻辑：`vssadmin delete shadows`、`vssadmin resize shadowstorage`（正文含对应 Sigma 骨架，含占位 UUID `12345678-1234-1234-1234-123456789001/002`） | 检测响应卡 §3（**逻辑吸收，占位 id 标注必须替换**） |
| 检测点：Security 4688、4698/7045、5140、4624 LogonType=3、Sysmon Event 10（ProcessAccess）、"Event ID 33 卷影删除" | §3（Event ID 33 标【未验证】） |
| 注册表侧检测：`DisableAntiSpyware`、`AmsiEnable` 值变化；`.lockbit` 扩展名指示器 | §3 / §1 |
| 卷影+备份破坏组合命令（vssadmin / wbadmin / bcdedit / netsh） | §1 YARA 规则 1/2/3、§4 命令 |
| Veeam 恢复验证思路："用 VeeamFLR 挂载备份点后做防病毒扫描" | 备份卡 §4 第 3 步（转为"恢复点勒索信扫描 + 先验一台"） |
| 备份工具面：Veeam / Azure Backup / AWS Backup / Rubrik / Cohesity / S3 Object Lock；`az storage container immutability-policy create ...` | 备份卡 §2 |
| 3-2-1 与"不可变副本"概念、云上快照/对象版本作为最后防线 | 备份卡 §1/§2 |
| 复盘"无指责 + 指标化"取向、云环境应急的账号/凭据收敛要点 | 检测响应卡 §7/§8 |
| 参考标准方向：NIST SP 800-61r2、SP 800-86、SANS FOR508/FOR500/FOR572、ENISA | 作为方向性引用（未逐条抄录） |

### 2.2 已修正（上游有错，必须改后再用）
| 上游内容 | 问题 | 处理 |
|---|---|---|
| ASR 规则 GUID 三条：`c1db55ab-c21a-4637-b3ea-a6c10f4f6e3b`（"Block ransomware behavior"）、`b2b3f03d-6a4c-4b7e-8c9d-0a1b2c3d4e5f`（"Block credential stealing from LSASS"）、`e6db77e5-3df2-4bcf-b52a-9b4d3b6b5c6a`（"Block untrusted executable from USB"） | 三条均非官方值（后两条尾部为连号式杜撰；前两组的 GUID **前缀**恰好等于真实的 `c1db55ab-…`＝Use advanced protection against ransomware、`e6db77e5-…`＝Block persistence through WMI event subscription，属拼接产物） | **整组丢弃**，不使用；如需 ASR 建议只引用规则**名称**并按 Microsoft Learn 现查 GUID |
| `Set-VBRJob -Job $job -EnableImmutability $true -ImmutabilityPeriod 14` | 不可变周期在**仓库层**（Hardened Repository），不在作业层，参数不可信 | 备份卡 §2.2 改为 `Add-VBRBackupRepository -Type Hardened -EnableBackupImmutability -ImmutabilityPeriod` + `Set-VBRBackupRepository`，并注明以 `Get-Help` 为准 |
| NIST 文档标注：`SP 800-184`＝"Ransomware Recovery"、`SP 800-209`＝"Ransomware Prevention" | 标题不符：800-184 为 *Guide for Cybersecurity Event Recovery*（2016）、800-209 为 *Security Guidelines for Storage Infrastructure*（2020） | 只保留"事件恢复/存储安全"语义，去掉错误副标题 |
| 3-2-1 "策略引擎" 伪代码、`mkdir /backup/immutable` + `chmod 700` 之类"不可变"示例 | 与真实不可变实现无关（目录权限 ≠ WORM） | **丢弃**，替换为 Object Lock / Hardened Repository / 磁带离线真实做法 |

### 2.3 已丢弃（与已有技能卡重叠或不可交付）
| 上游内容 | 丢弃理由 |
|---|---|
| 攻击链分析中的进攻 TTP 细节、初始访问利用步骤 | 本库已有 `authorized-ransom-lab`、`ransomware-builder`（进攻侧），本卡只做防御/处置 |
| 通用取证方法学（磁盘镜像、内存分析、时间线工具用法） | 已有 `digital-forensics`；`30-数字取证` 命中内容仅作方向性引用，不重复抄录 |
| 流量分析 / 样本沙箱分析方法 | 已有 `traffic-analysis-pcap`、`malware-analysis` |
| 上游的通用 IR 流程叙述（分级表格、沟通矩阵、通告模板） | 已有 `incident-response`；只吸收对勒索特化的指标（MTTD/MTTR、恢复表现） |
| 上游"事件分类与优先级/日志收集/复盘报告"的**通用**章节 | 与 `incident-response`、`host-ir-check` 重叠；复盘骨架仅保留 7 段勒索特化版 |
| 未经核实的家族-扩展名对应（含把 REvil 与 STOP/Djvu 的 `_readme.txt` 混用） | 按铁律剔除；只保留公开报告（CISA/厂商/pcrisk）能对应的条目，见检测响应卡 §1 |

## 3. 哪些来自上游、哪些是补充

**来自上游（Hi-FullHouse，2026-02 快照）**：Sigma/Sysmon 检测点清单、卷影-备份破坏命令组合、`.lockbit` 等指示器、Veeam 恢复点扫描思路、备份/不可变工具面（Veeam/Azure/AWS/Rubrik、S3 Object Lock、`az storage container immutability-policy create`）、3-2-1 与不可变概念、复盘指标化取向、参考标准方向。

**本次补充（官方/公开来源，已在文中标 【L1】/【L2】+ 年份）**：
- 家族指纹表：CISA AA23-075A（LockBit，2023）、AA23-353A（ALPHV，2023）、AA24-060A（Phobos，2024）、Cybereason/pcrisk（Conti、Ryuk）、SentinelOne/Trend Micro（Akira）、Emsisoft 页面（STOP/Djvu）。
- 4 条 YARA 规则：**自撰并实测**（yara-python 4.5.4 编译通过；规则 3 用合成证据文件实测命中），非 CISA 原文规则，已在文中声明。
- 真实命令：`vssadmin/wbadmin/bcdedit/net share/wevtutil`、`Get-SmbShare/Win32_ShadowCopy`、`mount/findmnt/smbclient`、`aws s3api put-object-lock-configuration` 等（L1/命令行标准语法）。
- Veeam Hardened Repository 的**单次使用凭据 + XFS** 机制、CVE-2024-40711（CVSS 9.8、修复 12.2.0.334、CISA KEV 2024-10、Akira/Fog/Frag 利用）与 CVE-2023-27532；Rubrik append-only / Retention Lock 两人规则 / Proactive Recovery Testing（L2）。
- 解密评估全流程与真实 URL：`id-ransomware.malwarehunterteam.com`、`nomoreransom.org/en/decryption-tools.html`、Emsisoft（含 STOP/Djvu 专用页）。
- 备份失效 12 条清单、RTO/RPO 测算口径、恢复后核查清单、隔离"拔网线 vs 关机"决策树。

**未纳入但已确认存在（可后续补）**：`https://ransomwhe.re/`（荷兰警方官方支付地址核验入口，上游提及；建议实现时作为可选参考）、SigmaHQ 同族规则 `proc_creation_win_shadow_copies_deletion.yml`（名称引用，未逐字校验）。

## 4. 遗留问题 / 使用前必读

- 参考文件中的【未验证】项：ESXi `esxcli` 具体命令、Azure 不可变策略 `lock` 的 `--if-match` 参数、Veeam `Start-VBRSureBackupJob`/`Add-VBRLinux` 的精确参数名（随版本变化）、上游所述"Event ID 33 = 卷影删除"。这些必须在目标环境自测后再落地。
- 上游 ASR GUID 不能使用（见 §2.2），是本次最重要的"排雷"结论。
- 本报告与两份参考文件均未包含任何凭据/密钥。
