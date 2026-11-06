<!-- archived from /root/.hermes/skills/security/ransomware-defense-ir-recovery/SKILL.md on 2026-10-21 -->

---
name: ransomware-defense-ir-recovery
description: "Use when 处置勒索/勒索演练:家族指纹、YARA、备份不可变、恢复。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/ransomware-defense-ir-recovery`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ransomware-defense-ir-recovery/…')`，不要相对 `references/legacy/` 解析。

# 勒索软件防御 / 应急响应 / 恢复

只做**防御 · 处置 · 恢复**。进攻侧演练见 `authorized-ransom-lab`、`ransomware-builder`；取证方法论见 `digital-forensics`、`traffic-analysis-pcap`；样本逆向见 `malware-analysis`。

## 触发场景

- 发现文件被批量改名/加密、出现勒索信（`README.txt`、`RECOVER-*-FILES.txt`、`info.hta`、`_readme.txt`）。
- Windows 卷影副本/备份目录被删（`vssadmin delete shadows`、`wbadmin delete catalog`、`bcdedit /set {default} recoveryenabled no`）。
- 需要判断"能不能解密""要不要付款""先恢复哪个系统"。
- 需要评估备份能否扛住勒索（不可变/WORM/离线/air-gap、3-2-1-1-0、演练）。
- 勒索事件复盘、RTO/RPO 实测与行动项。

## 工作流（6 步）

1. **确认与分级**：确认是否为勒索（扩展名 + 勒索信双向确认，见参考卡 §1）；同步确认是否有外传（数据泄露勒索）。分级：全站停摆 / 关键业务停摆 / 少数主机。
2. **遏制**（先断网再决策关机，见参考卡 §5）：
   - 逐台断网（拔网线/禁网卡/交换机端口 shutdown），**不要全部断电**（内存证据）。
   - 立即停用备份作业与复制任务，冻结不可变/离线副本时间点。
   - 禁用涉事账号（不删除）、切断 RDP/VPN/共享/带外管理，收敛备份管理面。
3. **证据保全**（只读、另存）：勒索信、一个 <1MB 加密样本、EVTX 原文件、Sysmon/EDR 日志、`vssadmin list shadows` 输出。
4. **判定与解密评估**：ID Ransomware → NoMoreRansom / Emsisoft 解密器（见参考卡 §6）；无解则明确写"依赖备份/重建"。
5. **恢复**：先认证地基（AD/DNS/KMS）→ 备份系统自身 → 安全设备 → 关键业务数据 → 外围；在隔离网络先验一台再批量；从**最干净**恢复点起（详见参考卡 §7 与 `references/backup-resilience.md`）。
6. **复盘**：7 段骨架（时间线/初始访问/影响面/检测与响应指标/恢复表现/根因/行动项），见参考卡 §8。

## 命令速查

```bat
:: 备份面 / 卷影面检查（Windows，优先在取证副本上跑）
vssadmin list shadows
vssadmin list shadowstorage
wbadmin get versions
wbadmin get status
bcdedit /enum {default}
wevtutil qe Security /q:"*[System[(EventID=1102)]]" /f:text /c:5
net share & net use
```
```powershell
Get-SmbShare | Select-Object Name,Path,Description
Get-WmiObject Win32_ShadowCopy | Select-Object InstallDate,DeviceObject
Get-Service VSS | Select-Object Name,Status,StartType
# 备份平台（Veeam 为例；cmdlet 参数以 Get-Help 为准）
Get-VBRJob; Get-VBRBackupSession; Get-VBRBackupRepository | Format-Table Name,Type,ImmutabilityPeriod
```
```bash
# 备份挂载点是否在生产主机（加密半径）内
mount | grep -Ei 'nfs|cifs|backup'; findmnt -t nfs4,cifs -o TARGET,SOURCE
# 对象存储不可变
aws s3api get-object-lock-configuration --bucket <b>
aws s3api list-object-versions --bucket <b> --prefix <p>
# 检测规则
yara -r rules.yar <target>
```

## Pitfalls

- **别删勒索信、别跑"批量改扩展名"脚本**，别在原盘上试解密（先副本）。
- **别重启/"重启试试"**：丢内存证据，可能触发启动阶段载荷。
- **上传样本去 ID Ransomware 前先判断保密要求**（样本含业务数据/路径时先脱敏或走内部渠道）。
- **一个文件确认不了家族**：ALPHV/BlackCat 等扩展名与勒索信名按受害者配置生成，扩展名不通用。
- **"备份成功"≠"可恢复"**：必须实测恢复 + 恢复点勒索信扫描，保留期要长于发现时间。
- **不可变只开 GOVERNANCE 等于没开**；备份仓别挂在生产主机上；备份控制台别暴露且要核对 build（CVE-2024-40711 类）。
- 检测规则**先观察模式**再阻断（运维脚本会误报）。
- 上游（Hi-FullHouse，2026-02 快照）情报**不可直接采信**：本次已核出其 ASR 规则 GUID、NIST 文档编号标注、Veeam 不可变 cmdlet 参数均有错误，逐条以参考卡中的【L1】/【未验证】标注为准。

## 参考文件

- `references/ransomware-detection-response.md` — 家族指纹、4 条实测 YARA 规则、Sigma/Sysmon 检测点、真实排查命令、隔离 trade-off、解密评估、恢复核查清单、复盘骨架。
- `references/backup-resilience.md` — 3-2-1-1-0 落地、S3/Azure Object Lock、Veeam Hardened Repository、Rubrik、备份被攻陷路径、RTO/RPO 与演练、健康监控、失效清单。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
- 交叉引用：`incident-response`（通用 IR 流程）、`host-ir-check`（主机应急）、`digital-forensics`（镜像/时间线/内存）、`traffic-analysis-pcap`（外传取证）、`malware-analysis`（样本分析）。
