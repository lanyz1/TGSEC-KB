# REPORT — endpoint-os-hardening-baseline 抽取台账

产物目录：`D:/skills4redteam/out/endpoint-os-hardening-baseline/`
- `references/os-hardening-baseline.md`（240 行，上限 240 ✅）
- `references/container-endpoint-audit.md`（136 行，上限 180 ✅）
- `DRAFT-SKILL.md`（70 行，正文上限 120 ✅；frontmatter 仅 name/description ✅）
- `REPORT.md`（本文件）

## 1. 上游读取清单

上游根：`D:/skills4redteam/HiFullHouse-CyberSecurity-Skills/`

### 全文精读（14 个）
| 文件 | 字符数 | 用途 |
|---|---|---|
| `27-操作系统安全-OSSecurity/skills/Linux安全加固与基线检查-LinuxHardeningBaseline.md` | 10,861 | os 基线 Linux 主体 |
| `27-…/Windows安全加固与基线检查-WindowsHardeningBaseline.md` | 10,131 | os 基线 Windows 主体 |
| `27-…/macOS安全评估与加固-macOSSecurityHardening.md` | 11,008 | os 基线 macOS |
| `27-…/国产操作系统安全加固-DomesticOSSecurity.md` | 12,463 | 国产 OS / 等保 / 国密 |
| `37-端点安全-EndpointSecurity/skills/端点加固与合规基线-EndpointHardeningComplianceBaseline.md` | 11,372 | 端点合规清单、Windows 策略项、Defender/ASR |
| `37-…/EDR部署与检测规则-EDRDeploymentDetectionRules.md` | 12,074 | EDR 遥测与调查 |
| `37-…/文件less恶意软件与LOLBins检测-FilelessMalwareLOLBinsDetection.md` | 14,746 | Sysmon + LOLBins 检测 |
| `37-…/移动设备安全与MDM-MobileDeviceSecurityMDM.md` | 11,768 | 判为范围外（丢弃） |
| `33-容器安全-ContainerSecurity/skills/容器运行时安全-Falco-ContainerRuntimeSecurityFalco.md` | 11,462 | Falco 规则要点 |
| `33-…/容器镜像安全与漏洞扫描-ContainerImageSecurityScanning.md` | 8,581 | trivy/grype/cosign |
| `33-…/Kubernetes RBAC与安全策略-KubernetesRBACSecurityPolicy.md` | 13,381 | K8s RBAC/PSP/NetworkPolicy |
| `33-…/容器逃逸检测与防御-ContainerEscapeDetectionDefense.md` | 14,050 | gVisor/Kata 运行时加固 |
| `14-安全审计-SecurityAudit/skills/配置安全审计-ConfigSecurityAudit.md` | 4,676 | 配置核查项 |
| `14-…/容器安全审计-ContainerSecurityAudit.md` | 6,613 | 容器主机审计（含 docker-bench-security） |

### 只读结构/命令级浏览（3 个）
| 文件 | 处理 |
|---|---|
| `27-…/Linux攻击与权限维持技术-LinuxAttackPersistence.md` | 仅取标题与命令行：长期权限维持、capabilities 滥用、eBPF 逃逸 —— **全部丢弃**（攻击面，库内已有 linux-privilege-escalation） |
| `27-…/Windows攻击与横向移动技术-WindowsAttackLateralMovement.md` | 仅取标题：域枚举、Kerberos、NTLM 中继、ACL、ADCS —— **全部丢弃**（库内已有 active-directory / windows-lpe） |
| `14-…/等级保护合规审计-ClassifiedProtectionAudit.md`（用户清单外，主动补充浏览） | 取等保 2.0 测评流程与检查点（`auditpol /get /category:*`、`systemctl list-units` 等），用于 §4 等保映射；其余章节丢弃 |

## 2. 逐条 吸收 / 丢弃

### 2.1 `Linux安全加固与基线检查`（吸收为主）
- 吸收：CIS 落地流程（定版本/分级/先扫后改）；Lynis、OpenSCAP（`oscap info` → `xccdf eval --profile/--results-arf/--report`、`xccdf generate report`）、Chef InSpec（`inspec exec`）命令；`/etc/sysctl.d/99-security.conf` 网络与内核片段；sshd_config 项；PAM（`pwquality.conf`、`login.defs`、`pam_faillock`/`pam_tally2` 辨析）；auditd 规则集与 `augenrules --check/--load`、`ausearch`；SUID/SGID 盘查、`chmod`/`chattr +a`；rsyslog 远程日志。
- 修正（标注在参考文件里）：`secedit`/`Protocol 2`/`ClientAliveCountMax 0` 见下；`kernel.exec-shield` 在主流内核不存在（上游 Ansible 片段会整任务失败）。
- 丢弃：与攻击面混编的「提权/后门」段落（库内已有专卡，避免重复）。

### 2.2 `Windows安全加固与基线检查`（吸收 + 大量修正）
- 吸收：`secedit /export /cfg` 思路与 `[System Access]` 等保项名；`auditpol` 策略面；`wevtutil sl` 日志容量/保留/自动备份；`Set-SmbServerConfiguration -EnableSMB1Protocol $false`；PowerShell 三条日志注册表键；事件转发 `wecutil cs`。
- 修正：① `secedit /export /cfg x.cfg | Select-String ...` 不成立（secedit 不写 stdout，本机实测）；② 导出文件是 UTF-16LE，须 `-Encoding Unicode`；③ 把 `MinimumPasswordLength`/`LockoutBadCount` 当注册表路径是错的（来自 secedit 导出）。
- 丢弃：无（该文件内容基本全数进入参考文件）。

### 2.3 `macOS安全评估与加固`
- 吸收：SIP/FileVault/Gatekeeper/ALF/XProtect/kext 检查、`systemsetup -setremotelogin off`、`sysadminctl -guestAccount off`、`profiles -P`、TCC.db 查询、mSCP 基线来源。
- 补充/加标：osquery 跨平台核查；`xprotect check` CLI 存在性存疑 → 标 ⚠ 未验证。
- 丢弃：渗透测试章节（攻击面，非本卡定位）。

### 2.4 `国产操作系统安全加固`（选择吸收 + 大量证伪标注）
- 吸收：等保 2.0 三级条款→核查项映射思路；登录超时 `TMOUT`；auditd 复用；强制访问控制标记读取（`ps -Z`/`ls -Z`）；openEuler `isula`、secGear 提示。
- **标注为「未验证，勿当事实」**：`kylin-security-toolkit --set-password-policy`、`kylin-security-config --set-level high`、`/etc/sysconfig/kysec/security-level`、`kysec-tools --set-subject-label/…`、`uos-security-center --…`、`dde-security-tools --…/dde-sandbox run`、`uos-audit-tool --enable/--query`。理由：这些厂商专有 CLI 名称在不同麒麟/UOS 小版本上极不一致，本机为 Windows 无法实测，且上游卡片由生成式流程产出、无出处。参考文件改为给「存在性探测（`command -v` / `rpm -qf` / `dpkg -S`）→ 再执行」的兜底流程。
- 国密：`gmssl sm3sum`、Nginx 双证书重复 `ssl_certificate`、`trust list | grep sm2`、`gmtls_server` 标 ⚠ 未验证；**但 SM2/SM3/SM4 本身在本机 OpenSSL 3.5.5 实测可用**，故改为可复现命令（见 3.1）。
- 丢弃：紫金桥数据交换平台相关小节（与 OS 加固无关，属数据平台渗透）。

### 2.5 `端点加固与合规基线`
- 吸收：端点合规核查清单/检查面（补丁、账户、口令、审计、日志、防火墙、暴露面、加密）；Windows 策略基线工具链（SCT/LGPO/PolicyAnalyzer）、DSC/Ansible/等保三级 Windows 专项思路。
- 修正：① `Set-MpPreference -LowfiThreatLevel Default_Action Quarantine` → 真实为 `-LowThreatDefaultAction Quarantine`（本机 `Get-Command` 实测不存在前者）；② `-AttackSurfaceReductionRulesIds/-Actions` → 真实 `-AttackSurfaceReductionRules_Ids/_Actions`（带下划线）；③ 上游 ASR「GUID→名称」表错位（详见 3.2），已按 Microsoft Learn 权威页替换其中可核对的条目，并改为「先 `Get-MpPreference` 枚举、再按官方页逐条添加」的稳妥做法。
- 丢弃：合规框架条文罗列（SOC2/ISO27001 等与命令无关的段落）、移动端 MDM（见 2.7）。

### 2.6 `EDR部署与检测规则` + `文件less恶意软件与LOLBins检测`
- 吸收：Sysmon 安装与事件 ID 语义（1/3/7/8/10/11/15/17/18/22）、狩猎组合（lsass ProcessAccess、CreateRemoteThread、Temp 落可执行、Office 父进程链）；PowerShell 4103/4104 遥测读取；LOLBins 清单与「命令行+父进程+执行路径」判读原则；Defender 调查命令。
- 修正/加标：`Get-Service -Name Sysmon` 不可靠（`Sysmon64.exe` 装的服务是 `Sysmon64`）；CrowdStrike RTR / Velociraptor / KAPE 命令本机无环境 → 标 ⚠ 未验证，并给出「参数按管理台/安装目录现取，不要写死」的用法说明。
- 丢弃：免杀/绕检测手法（进攻面）、具体厂商许可与采购建议。

### 2.7 `移动设备安全与MDM`
- **整篇丢弃**。理由：iOS/Android MDM、设备注册、应用白名单与本卡「端点=服务器/桌面操作系统 + 容器」的基线核查定位不同；且任务书未把移动端列入输出范围。

### 2.8 容器三卡 + `容器安全审计` + `配置安全审计`
- 吸收：`docker info`（Security Options/Runtimes/Cgroup/Default Runtime/Live Restore）判读；`docker inspect --format` 模板（Privileged/User/Mounts/CapAdd/Userns/Readonly/PidMode/NetworkMode）；容器内 `CapEff/CapBnd` 自查；dockle/trivy/kube-bench/docker-bench-security/grype/cosign/docker scout 命令面；K8s `kubectl auth can-i --list --as=…`、clusterrole/clusterrolebinding 盘点、NetworkPolicy；Pod Security Admission 三档与 restricted 合规要点；Gatekeeper/Kyverno/Falco/tracee/Tetragon 要点；gVisor/Kata 运行时加固；配置安全审计的核查维度。
- 修正：① 上游 RBAC 卡里的 `security.kubernetes.io/podsecuritypolicies` ClusterRole 是旧 API（PSP 1.25 已移除，API 组 `policy`）；② 上游 Falco 规则片段把 list 命名为 `str_miner_procs` 又写同名 macro 且自引用（`proc.name in (str_miner_procs)`）→ 会循环报错，参考文件给出正确 `- list:` + `items:` 形态；③ `daemon.json` 中 `"no-new-privileges"` 不是合法键（真实形态 `docker run --security-opt no-new-privileges`）；④ `trivy config` 不接受 `--no-progress`。
- 丢弃：镜像构建/供应链进攻细节、容器逃逸利用链（库内已有 docker-security / cloud-k8s）。

### 2.9 `容器逃逸检测与防御`
- 吸收：gVisor/Kata 运行时作为纵深防御的落地命令（`runsc install`、`--runtime=runsc|kata`）。
- 丢弃：逃逸手法（socket 挂载、`--privileged`、`nsenter --target 1` 等）——进攻面，已有专卡；仅在参考文件里保留「判读要点」用于审计发现。

## 3. 本机实测（✅）与未验证（⚠）清单

### 3.1 实测通过（作为 ✅ 证据写入参考文件）
- 主机：Windows 11 build 26200、PowerShell 5.1.26100；Docker 29.6.2（Docker Desktop/WSL2，端点 `npipe:////./pipe/dockerDesktopLinuxEngine`）；OpenSSL 3.5.5。
- Windows：`auditpol /get /category:*`（中文乱码 → `chcp 65001` 修复）；`secedit /export /cfg` 导出文件结构与 UTF-16LE 事实；`net accounts` 实际取值；`wevtutil gl Security` 字段；`HKLM\…\Policies\System`(EnableLUA/ConsentPromptBehaviorAdmin/PromptOnSecureDesktop)、`HKLM\SYSTEM\CurrentControlSet\Control\Lsa`(restrictanonymous/restrictanonymoussam/LimitBlankPasswordUse/NoLmHash/RunAsPPL/RunAsPPLBoot/disabledomaincreds) 与 `Lsa\MSV1_0`(NtlmMinClientSec/NtlmMinServerSec)、`Terminal Server\WinStations\RDP-Tcp\UserAuthentication` 实测值；`Set-MpPreference`/`Add-MpPreference` 真实参数名；`Get-MpComputerStatus` 属性名；`MpCmdRun.exe -?` 命令集；`Get-LocalUser`/`Get-NetFirewallProfile`/`Get-BitLockerVolume`/`Get-HotFix` 可用；PowerShell 三条日志键未配置。
- 容器/K8s：`docker info`、`docker inspect --format` 模板、容器内 `CapEff/CapBnd`；dockle 真实输出（CIS-DI-0001/0005/0006/0008）；`trivy config`（27 检查项、`DS-0001` 失败）；`trivy image` 因代理未起导致漏洞库下载失败（失败原因记录）；kube-bench v0.16.0 `version` 与 `run --targets node`（含 FAIL/PASS 项）；`--version` 非合法参数；docker-bench-security 失败原因；`kubectl` 存在；4 个扫描镜像可拉取。
- 国密：OpenSSL 3.5.5 支持 SM4-CBC/ECB/CFB/CTR、SM3、SM2 curve。

### 3.2 权威外部核对
- Microsoft Learn（ASR rules reference / overview，2026-09 版）逐条核对上游 ASR GUID↔名称，确认上游映射错位（例：`26190899-…` 官方为 Block Office communication application from creating child processes；`5beb7efe-…` 官方为 Block execution of potentially obfuscated scripts，而非上游所写的 "Block executable files from email"，邮件那条实为 `be9ba2d9-…`）。参考文件采用官方名称。

### 3.3 未验证（参考文件已逐条标 ⚠）
- 未安装/无环境：lynis、oscap、inspec、ansible、falco、sysmon、velociraptor、grype、syft、cosign、docker scout、kube-hunter、CIS-CAT、SCT/LGPO/PolicyAnalyzer、macOS 全部命令（本机为 Windows）、麒麟/UOS 厂商专有 CLI、`trivy image` 联网漏洞库、气隙 DB 预置方式。
- 语义存疑但已给出判据：`xprotect check` CLI 版本差异；TCC `auth_value` 语义与表结构随 macOS 版本变化；`netsh advfirewall` 未在本次实测（改用 `Get-NetFirewallProfile` 实测）。
- 参考文件中所有 ⚠ 项均要求「先探测存在性（`command -v`/`Get-Command`/`rpm -qf`）再执行」，未写成可直接照抄的事实。

## 4. 来源归属

- **纯上游**：CIS 落地流程、Linux sysctl/sshd/PAM/auditd/文件权限片段、secedit 策略项名与 auditpol/wevtutil 命令、macOS 检查命令、国产 OS 与等保映射思路、端点合规核查维度、Sysmon 事件表与 LOLBins 清单、K8s RBAC/NetworkPolicy/PSA 要点、Falco/Gatekeeper/Kyverno/gVisor-Kata 要点、`docker inspect` 模板与扫描工具清单。
- **上游 + 本机实测修正**：secedit stdout/UTF-16LE、auditpol 中文乱码、Defender 参数名与 ASR GUID、Sysmon 服务名、auditd `-ts` 取值、ssh 三项语义、Falco 规则结构、PSP API 组、daemon.json 非法键、trivy/dockle/docker-bench-security 实际行为。
- **本卡补充（上游没有或上游写错后重给）**：注册表实测点位表与目标值、auditpol 子类别 GUID 用法、Microsoft Learn ASR 对照与 MITRE 式狩猎查询示例、`docker info`/`docker inspect` 判读要点、`trivy config` 离线可用性与规则 ID 出处、kube-bench 版本/KUBECONFIG 注意点、OpenSSL 3.x 国密实测命令、`等级保护合规审计` 文件的等保检查点、以及全套 ⚠/✅ 验证标记体系。
