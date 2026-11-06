# 备份韧性与恢复参考（ransomware-defense-ir-recovery）

> 证据分级：【L1】官方文档核实；【L2】厂商资料/公开报告；【上游】Hi-FullHouse CyberSecurity-Skills（2026-02 快照），未独立核实；【未验证】未核实，使用前自测。
> 定位：只写"备份能不能活下来 + 能不能恢复"。勒索检测/遏制见 `references/ransomware-defense-ir-response`（同目录 `ransomware-detection-response.md`）。

## 1. 3-2-1 与 3-2-1-1-0 落地

| 要素 | 含义 | 落地检查项 |
|---|---|---|
| 3 份副本 | 生产 1 + 备份 2 | 生产与备份**不同信任域/不同凭据**；备份系统独立账号体系+独立 MFA |
| 2 种介质 | 至少两种介质/技术栈 | 磁盘 + 对象存储/磁带；避免"同一存储同一故障域"（含同一超融合/同一 NAS） |
| 1 份异地 | 或"离线/不可变" | 异地机房或对象存储跨区；离线=磁带/拔线盘 |
| +1 份离线或不可变 | 3-2-1-1 | 该副本**攻击者在网络内无法删除**（WORM/硬仓库/磁带） |
| +0 错误恢复 | 3-2-1-1-0 | 定期**演练并验证**恢复点可完整恢复（"0 error"指验证无错） |

- 【上游】"3-2-1 策略引擎 + 不可变校验"的思路可吸收，但**上游未给出可执行的合规校验脚本**（其代码为伪实现），不要直接引用其判定逻辑。
- 【L2】Rubrik 对 NCSC 3-2-1 的解读把"1"明确成"异地离线 **或** 通过在线方式实现不可变"——即**不可变副本可替代异地磁带**，这是 3-2-1-1 落地的实用口径。
- 保留期必须**长于发现时间**：保留期 < 入侵驻留期时，干净副本会被轮换掉（经典失效，见 §7）。

## 2. 不可变 / air-gap 实现（真实配置要点）

### 2.1 对象存储 WORM（S3 / Azure Blob）
```bash
# S3 Object Lock：必须先开启版本控制，否则 put-object-lock-configuration 报错
aws s3api put-bucket-versioning --bucket <bucket> --versioning-configuration Status=Enabled
aws s3api put-object-lock-configuration --bucket <bucket> \
  --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Days":14}}}'
aws s3api get-object-lock-configuration --bucket <bucket>
aws s3api head-object --bucket <bucket> --key <key> --query '{Mode:ObjectLockMode,Until:ObjectLockRetainUntilDate}'
```
- `COMPLIANCE` 模式：**任何账号（含 root）都无法在保留期内删除**；`GOVERNANCE` 需特殊权限即可移除 —— **给备份桶用 COMPLIANCE**，GOVERNANCE 等于留了后门。
- 【L1】Azure：容器级不可变策略必须先有容器（且默认对 blob 版本生效需启用版本级不可变）：
```bash
az storage container immutability-policy create --resource-group <rg> --account-name <acct> --container-name <c> --period 10
az storage container immutability-policy lock --account-name <acct> --container-name <c> ...   # 锁定后不可缩短；具体 --if-match 参数【未验证】
az storage container legal-hold set --account-name <acct> --container-name <c> --tags hold1
```
- 【L1】账号级开关：`az storage account create --name <acct> --resource-group <rg> --enable-alw --immutability-period-in-days 90 --immutability-state unlocked`（`--enable-alw` = 支持版本级不可变）。

### 2.2 Veeam Hardened Repository（Linux 加固仓库）
- 形态：Linux 服务器（XFS 支持 reflink 更省空间）+ **单次使用凭据（single-use credentials）**，Veeam 仅在挂载瞬间用 SSH 登录，事后无法再 SSH 进去 → 攻击者从备份服务器侧**无法 SSH 删除**不可变数据。
- 【L2】典型流程（Veeam 12；参数名以 `Get-Help Add-VBRBackupRepository -Full` 为准）：
```powershell
Add-VBRLinux -Name <linux-host> -SSHTempCredentials   # 单次使用凭据
Add-VBRBackupRepository -Type Hardened -Server <linux-host> -Folder /mnt/backup \
    -EnableBackupImmutability -ImmutabilityPeriod 21
Set-VBRBackupRepository -Repository <repo> -ImmutabilityPeriod 30
Get-VBRBackupRepository | Format-Table Name,Type,ImmutabilityPeriod
```
- 【上游】给出的 `Set-VBRJob -Job $job -EnableImmutability $true -ImmutabilityPeriod 14` **未验证/疑有误**：不可变周期在仓库（repository）层，不在作业层；请以官方 cmdlet 帮助为准。
- 加固要求：备份服务器与域控/生产**不同管理边界**（独立本地账号、禁 RDP、最小化共享）、补丁跟踪、EDR 部署、SSH 仅限备份服务器 IP。

### 2.3 Rubrik / 其他一体化平台
- 【L2】Rubrik 的关键点：append-only 文件系统（写入后不可改）、**Retention Lock 两人规则**（改保留策略需双人）、Intelligent Data Lock（检测到异常删除时延长回收站保留）、逻辑 air gap（NFS/SMB 只对平台自身暴露）、Cloud Vault 隔离副本、Proactive Recovery Testing（DR 演练自动化）。
- 具体 CLI/API 调用【未验证】——Rubrik 以 GUI/SLA Domain 策略为主，口令式命令建议按其 REST/GraphQL 文档现查。

### 2.4 磁带 / 真离线
- LTO 轮换 + 磁带库不带网（或停机保持离线）；恢复速度是唯一代价，但对"网络内不可达"最强。
- 演练必须包含**从磁带恢复一个完整系统**（只验证"磁带写入成功"不算数）。

## 3. 备份系统自身被攻陷的路径与防护

| 攻击路径 | 真实案例/依据 | 防护要点 |
|---|---|---|
| 备份管理面暴露（未认证 RCE） | 【L2】CVE-2024-40711 Veeam B&R 未认证反序列化 RCE（CVSS 9.8，影响 ≤12.1.2.172，修复 12.2.0.334；CISA KEV 2024-10），Akira/Fog/Frag 用它建本地管理员账号（`point`/`point2`）后**先删备份再加密**；另有 CVE-2023-27532（凭据泄露，被 FIN7/Cuba 利用） | 备份服务器不暴露到互联网/不跨信任域开放；及时打补丁并**核对实际 build**：`(Get-Item "C:\Program Files\Veeam\Backup and Replication\Console\veeam.backup.shell.exe").VersionInfo.ProductVersion`；`Test-NetConnection -ComputerName <vbr> -Port 9401` 自测可达性 |
| 凭据复用 | 【上游/L2】域管理员同时是备份管理员；备份目标共享用同一域凭据 → 一处沦陷两处通吃 | 备份系统独立目录/本地账号 + 独立 MFA；禁止用域管操作备份控制台；服务账号只允许登录备份主机 |
| 备份目录挂在生产主机上 | 备份仓以 SMB/NFS 挂到生产机（`mount \| grep -Ei 'nfs\|cifs'`），勒索进程遍历挂载点即可连带加密备份 | **方向反转**：只允许备份服务器访问生产，不允许生产挂载备份仓；确需挂载则只读 + SMB 签名 + ACL 拒绝写入 |
| 备份作业被"合法"删除/篡改 | 攻击者用备份控制台或 API 停作业、改保留期、删副本 | 备份配置变更单独告警（含"保留策略被缩短""作业被禁用"）；关键配置变更需审批/双人 |
| 备份服务器被横向 | 生产失陷后用备份软件的服务账号横向到备份机 | 备份主机入独立 VLAN，仅允许备份端口出站到仓库；主机层 EDR + 日志外送（日志不能只留在被攻陷的主机） |

## 4. RTO / RPO 测算与恢复演练

**测算输入**：数据总量、全量/增量比例、备份链路带宽、恢复通道并发数、恢复目标（单文件/单 VM/整站）、人工排障时间。
- RPO 目标 ← 决定**备份频率**与"可接受丢失窗口"；若发现时间 > 保留粒度，实际 RPO 可能等于"上一个干净点"，写报告时用**实际值**不用设计值。
- RTO 目标 ← 决定恢复**并行度与优先级**：先恢复认证与地基，再业务（顺序见检测响应卡 §7）。
- 常见结论：RTO 目标 4h 但只有单条 1GbE 恢复通道 + 500TB 数据 = 不可能，需要预置恢复硬件/即时挂载（Rubrik Live Mount、Veeam Instant Recovery）。

**演练步骤（可执行）**
1. 选一个**不可变/离线**恢复点（不是最新点，故意选 7~30 天前），记录时间戳。
2. 在**隔离网络**恢复：Veeam `Start-VBRSureBackupJob`（SureBackup 验证作业，直接在 Datalabs 虚拟实验室起机并跑验证脚本；cmdlet 名随版本略有差异，用 `Get-Command -Module Veeam*Backup* | ? Name -like '*SureBackup*'` 确认后再用）；Rubrik 用 Proactive Recovery Testing / Live Mount 到 iRE。
3. 验证项（逐条打勾，缺一不可）：系统能引导 → 应用能起 → 数据能读（关键表/文件哈希比对）→ AD 场景跑 `dcdiag`、`repadmin /showrepl` → 恢复点里**没有勒索信/异常扩展名**（对恢复点做一次勒索信文件名扫描：`RECOVER-*-FILES.txt`、`*.README.txt`、`info.hta`）。
4. 计时：从"发起恢复"到"业务可用"的墙钟时间 = 实测 RTO；对比目标值写进复盘（检测响应卡 §8）。
5. 归档演练报告与失败项，把失败项转成行动项（含责任人/截止）。

## 5. 备份健康监控与告警要点

- **作业成功率与失败原因**：`Get-VBRJob`、`Get-VBRBackupSession`、`Get-VBRBackup`（Veeam 侧）；平台侧看 SLA/策略合规率（Rubrik）。
- **RPO 缺口**：最近**成功**恢复点距今时长（不是"最近作业启动时间"）；
- **容量与保留**：仓库剩余空间、不可变副本到期时间、保留策略是否被缩短；
- **篡改类告警**：备份作业被禁用/删除、保留策略变短、仓库凭据/SSH 配置变更、备份服务器新增管理员、VSS 状态异常（`vssadmin list shadowstorage`）；
- **告警通道独立**：备份告警不要只走被攻陷域内的邮件/IM；异地日志 + 独立监控（`zabbix` 等，见上游工具清单【上游】）。

## 6. 常见备份失效原因清单（逐条自查）

1. 备份与被加密数据用**同一域凭据**，域控一失陷全通。
2. 备份仓/共享**挂载在生产主机**上，加密半径覆盖备份。
3. 不可变未开启，或只开 `GOVERNANCE`（可被有权者移除）。
4. 备份控制台**未打补丁且可达**（CVE-2024-40711 类）；备份服务器 build 未核对。
5. 保留期短于驻留/发现时间，干净副本已被轮换替换。
6. 只备份数据，不备份**配置与密钥**（AD、证书私钥、KMS、数据库账号），恢复时卡在依赖。
7. 用**快照当备份**：快照可被删除（ALPHV 会用 ESXi API 删快照），且与生产同故障域。
8. 备份**作业被篡改**但无人监控（作业被禁用数周无人发现）。
9. 从未做过**完整恢复演练**，副本损坏在上线那天才发现（"备份成功"≠"可恢复"）。
10. 恢复能力无冗余：单条恢复通道/单一恢复硬件，RTO 目标无法达成。
11. 备份服务器无 EDR/无独立日志，横向后无迹可查。
12. 离线副本（磁带）从未校验，读取失败率高。
