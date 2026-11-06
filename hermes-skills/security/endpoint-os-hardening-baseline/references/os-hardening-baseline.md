# 操作系统加固与合规基线参考
> 定位：按基线做「加固 + 合规核查」。攻击面不在此展开，见 linux-privilege-escalation / windows-lpe / active-directory。
> 标记：✅=本机实测（Windows 11 build 26200 / PowerShell 5.1.26100 / OpenSSL 3.5.5）；⚠=来自上游技能库或官方文档、本机未复现，用前先 `command -v` / `Get-Command` 探测。

## 0. CIS Benchmark 怎么落地（流程，不是命令）
1. 定版本：CIS Benchmark 按「产品+版本」发布（Windows 11 Enterprise、Ubuntu 22.04、RHEL 9…），一份通则套所有机器必然误报。
2. 分级：Level 1=低风险默认项，生产可开；Level 2=加严项（可能改功能/性能），必须灰度。
3. 顺序固定：只读扫描 → 差异清单 → 分批整改 → 复扫回归 → 出报告。先扫后改，默认值里也有已合规项。
4. 四件套：扫描器（OpenSCAP / Lynis / InSpec / CIS-CAT Pro ⚠需授权）；数据源 SCAP Security Guide（一份 datastream 内含 CIS / STIG / 等保映射 profile）；自动化（Ansible 跨平台、Windows 用 GPO/LGPO ⚠）；证据（`--results` 留 XML/ARF、`--report` 留 HTML，别只看终端 PASS/FAIL 计数）。
5. profile id 不要硬编码：各发行版/SSG 版本不一致，先 `oscap info` 现查。

## 1. Linux 基线
### 1.1 扫描（上游命令，包名随发行版变化 ⚠）
```bash
sudo apt-get install lynis && sudo lynis audit system      # Debian/Ubuntu；EL 系 yum install lynis
sudo dnf install openscap-scanner scap-security-guide      # EL 系；Debian 系 apt-get 同名
oscap info /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml            # 先列 profile
sudo oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  --results-arf results.xml --report report.html \
  /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml                     # profile id 随 SSG 版本变，以 oscap info 为准
oscap xccdf generate report results.xml > report.html      # 由已有 results 重新出报告
gem install inspec                                         # Chef InSpec
inspec exec https://github.com/dev-sec/linux-baseline      # 社区基线
```
- ⚠ 旧文档写 `apt-get install libopenscap8`，新发行版包名已变（`openscap-scanner`），照抄会装不上。
```yaml
# ansible-playbook -i hosts hardening.yml --check --diff     ⚠ ansible 本机未安装（command -v 实测 not found），未跑通
- hosts: linux
  become: true
  tasks:
    - name: 内核加固（只写目标内核确实存在的键，否则整任务失败）
      ansible.posix.sysctl: {name: "{{ item.k }}", value: "{{ item.v }}", sysctl_file: /etc/sysctl.d/99-security.conf, reload: true}
      loop: [{k: kernel.kptr_restrict, v: "2"}, {k: net.ipv4.tcp_syncookies, v: "1"}, {k: fs.suid_dumpable, v: "0"}]
    - name: sshd 关键项
      ansible.builtin.lineinfile:
        path: /etc/ssh/sshd_config
        regexp: "^#?{{ item.k }}\\b"
        line: "{{ item.k }} {{ item.v }}"
      loop: [{k: PermitRootLogin, v: "no"}, {k: PasswordAuthentication, v: "no"}, {k: MaxAuthTries, v: "3"}]
    - ansible.builtin.service: {name: sshd, state: restarted}
```
### 1.2 sysctl（内核层）
```bash
# /etc/sysctl.d/99-security.conf（上游片段）
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_source_route = 0 ; net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.all.rp_filter = 1 ; net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0 ; net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0 ; net.ipv4.conf.all.log_martians = 1
net.ipv4.tcp_syncookies = 1 ; fs.suid_dumpable = 0 ; kernel.sysrq = 0
# 其余网络/内核项按 SSG/CIS 逐项确认后再加（见下方 exec-shield 提醒）
sudo sysctl -p /etc/sysctl.d/99-security.conf
```
- ⚠ 上游 Ansible 片段里的 `kernel.exec-shield` 在主流内核**不存在**（exec-shield 是旧 Fedora 补丁，仅存在于打过该补丁的内核）。写入不存在的键报 unknown key，Ansible `sysctl` 模块会直接失败。先 `sysctl kernel.exec-shield` 确认。
- 现代补充项（⚠ 逐项在目标内核确认）：`kernel.randomize_va_space=2`、`kernel.kptr_restrict=2`、`kernel.dmesg_restrict=1`、`kernel.yama.ptrace_scope=1`、`fs.protected_hardlinks=1`、`fs.protected_symlinks=1`、`kernel.core_pattern`（避免核心转储外泄）。
- 改 `ip_forward`/`rp_filter` 前先确认是不是路由/NAT/Docker 宿主（Docker 默认需要 ip_forward=1），否则直接断业务。
### 1.3 SSH（sshd_config）
```bash
cat >> /etc/ssh/sshd_config << 'EOF'
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 3
AllowTcpForwarding no
X11Forwarding no
AllowUsers adminuser opsuser
EOF
sshd -t && systemctl restart sshd      # 改完先 -t 校验语法再重启
```
- ⚠ 上游的 `Protocol 2` 已废弃：OpenSSH 7.6+ 移除该关键字，加了出 "Deprecated option" 警告，2 本来就是唯一协议。
- ⚠ 上游的 `ClientAliveCountMax 0` 与其注释「设置闲置超时」**相反**：按 `sshd_config(5)`，0 表示服务端发 keepalive 后不会因无响应断开，等于关掉闲置超时。要超时用 1–3。
- `AllowUsers` 会立刻排除其他账号（含自动化账号），先核对 sudo/systemd 身份再上。
### 1.4 PAM / 口令策略
```bash
# /etc/login.defs
PASS_MAX_DAYS 90 ; PASS_MIN_DAYS 1 ; PASS_MIN_LEN 12 ; PASS_WARN_AGE 7
# 密码质量：RHEL 系 /etc/security/pwquality.conf；Debian 系挂在 /etc/pam.d/common-password 的 pam_pwquality.so 参数上
minlen = 14 ; dcredit = -1 ; ucredit = -1 ; lcredit = -1 ; ocredit = -1
minclass = 4 ; maxrepeat = 3 ; gecoscheck = 1
grep -E "pam_faillock|pam_tally2" /etc/pam.d/common-auth   # 登录失败锁定：先看现役模块
```
- ⚠ `pam_tally2` 在新发行版已移除，别照抄旧文档；`pam_faillock` 典型四段（preauth / authfail / authsucc + deny=5 unlock_time=900）。改 `/etc/pam.d/*` 前先在控制台留一个可用 root 会话。
### 1.5 auditd
```bash
sudo apt-get install auditd audispd-plugins    # Debian/Ubuntu；EL 系 yum install audit
cat > /etc/audit/rules.d/99-baseline.rules << 'EOF'
-D
-b 8192
-f 1
-w /etc/sudoers   -p wa -k sudoers_changes
-w /etc/sudoers.d/ -p wa -k sudoers_changes
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/group  -p wa -k identity
-w /etc/gshadow -p wa -k identity
-w /etc/ssh/sshd_config -p wa -k sshd
-w /etc/hosts  -p wa -k network
-a always,exit -S execve -k command_audit
-a always,exit -S adjtimex -S settimeofday -S clock_settime -k time_change
-w /sbin/insmod -p x -k module_insert
-w /sbin/modprobe -p x -k module_insert
-w /sbin/rmmod -p x -k module_remove
EOF
sudo augenrules --check && sudo augenrules --load      # 先 check（dry-run）再 load
sudo systemctl restart auditd && sudo systemctl enable auditd
sudo ausearch -k sudoers_changes -ts today
sudo ausearch -m avc -ts recent                        # SELinux 拒绝
```
- ⚠ 上游 `ausearch -k identity -ts 24小时前` 不成立：`-ts` 只接受 `today|yesterday|this-week|this-month|this-year|recent|boot` 或具体时间戳（`09/25/2026 10:00:00`）。
- ⚠ 上游把规则写进 `/etc/audit/rules.d/audit.rules`（与 `/etc/audit/audit.rules` 同源易冲突）；用独立文件名如 `99-baseline.rules`，避免被包升级覆盖。
- `-a always,exit -S execve` 在高并发机器量极大，先评估磁盘与 rsyslog 吞吐；`-b 8192`（上游）偏小，SSG/CIS 常用 32768 以上；`-b` 改大需重启 auditd。
### 1.6 文件权限与不可变
```bash
chmod 600 /etc/shadow /etc/gshadow ; chmod 644 /etc/passwd /etc/group
find / -xdev -perm -4000 -type f -ls 2>/dev/null       # SUID 盘点（-xdev 不跨挂载）
find / -xdev -perm -2000 -type f -ls 2>/dev/null       # SGID
find / -xdev \( -nouser -o -nogroup \) -ls 2>/dev/null # 无主文件
sudo chattr +a /var/log/auth.log /var/log/syslog       # 追加只读（⚠ 容器/overlayfs 与部分文件系统不支持）
```
- 远程日志（防本地篡改）：rsyslog `*.* @logserver:514`（UDP）/`@@`（TCP）；⚠ 同步评估合规留存期（等保三级常要求 ≥180 天）。
## 2. Windows 基线
### 2.1 策略导出与读取（实测两个坑）
```powershell
secedit /export /cfg C:\Temp\secpol.cfg        # 用 cmd 调用；路径必须是原生 Windows 路径
Get-Content C:\Temp\secpol.cfg -Encoding Unicode | Select-String "PasswordComplexity|MinimumPasswordLength|LockoutBadCount"
```
- ⚠ 坑1：secedit 把内容写进文件，**stdout 没东西** → 上游的 `secedit /export /cfg secpol.cfg | Select-String ...` 永远匹配不到。
- ⚠ 坑2：导出文件是 **UTF-16LE**，直接 grep / 默认编码 Select-String 会乱码或匹配失败，必须 `-Encoding Unicode`（Linux 侧 `iconv -f UTF-16LE`）。
- ✅ 实测导出结构：`[System Access]` 含 `MinimumPasswordAge/MaximumPasswordAge/MinimumPasswordLength/PasswordComplexity/PasswordHistorySize/LockoutBadCount/ResetLockoutCount/LockoutDuration/AllowAdministratorLockout/RequireLogonToChangePassword/ForceLogoffWhenHourExpire/NewAdministratorName/NewGuestName/ClearTextPassword/LSAAnonymousNameLookup/EnableAdminAccount/EnableGuestAccount`；`[Event Audit]` 含 `AuditSystemEvents/AuditLogonEvents`(本机=3=成功+失败)`/AuditObjectAccess/AuditPrivilegeUse/AuditPolicyChange/AuditAccountManage/AuditProcessTracking/AuditDSAccess/AuditAccountLogon`；`[Registry Values]` 格式 `MACHINE\Software\...\Value=类型,数值`；`[Privilege Rights]`=用户权限分配。
- ⚠ 上游 37-端点安全 把 `MinimumPasswordLength`/`LockoutBadCount` 写成 `HKLM\...` 注册表路径 —— 它们实际来自 secedit 策略导出，注册表里查不到。
### 2.2 账户与口令
```powershell
net accounts          # ✅实测：本机 最长42/最短0/历史None/锁定阈值10/锁定时长10/观察窗口10
net accounts /minpwlen:14 /maxpwage:90 /minpwage:1 /lockoutthreshold:5 /lockoutduration:30 /lockoutwindow:30  # ⚠需管理员
Get-LocalGroupMember -Group "Administrators"     # ✅ cmdlet 存在（Microsoft.PowerShell.LocalAccounts）
Get-LocalUser | Where-Object Enabled ; Disable-LocalUser -Name Guest   # ⚠ Guest 默认已禁用，勿误启
```
### 2.3 审计策略与日志
```cmd
auditpol /get /category:*                              :: ✅实测可用
chcp 65001 & auditpol /get /category:*                 :: ✅实测：中文 Windows 先切 UTF-8 代码页，否则表头/值乱码
auditpol /get /subcategory:"Process Creation"
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable   :: ⚠需管理员
wevtutil gl Security       :: ✅实测字段 name/enabled/type/isolation/channelAccess/logging{logFileName,retention,autoBackup,maxSize}
wevtutil sl Security /ms:1073741824 /rt:true /ab:true  :: ⚠需管理员
wevtutil sl "Microsoft-Windows-PowerShell/Operational" /ms:1073741824 /rt:true /ab:true
wecutil cs C:\subscription.xml                         :: ⚠事件转发订阅，未复现
```
- ⚠ 子类别名随系统语言变化（中文「进程创建」/英文 `Process Creation`）。跨语言脚本用**子类别 GUID**（`/subcategory:{0CCE922B-69AE-11D9-BED3-505054503030}`），先 `auditpol /list /subcategory:* /v` 取 GUID。
- ✅ 实测：`auditpol /backup`、`secedit` 需管理员；非管理员只能读。建议 `Security` 日志容量 ≥1GB 且 `/ab:true` 自动备份，避免覆盖（等保/CIS 常按留存期反推）。
### 2.4 注册表实测点位
| 项目 | 路径 → 值名 | 本机实测 | 目标 |
|---|---|---|---|
| UAC | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System` → `EnableLUA` / `ConsentPromptBehaviorAdmin` / `PromptOnSecureDesktop` | 0x1 / 0x5 / 0x1 ✅ | 1 / 2(最严) / 1 |
| 匿名/空口令/LSA/NTLM | 同上 → `restrictanonymous` / `restrictanonymoussam` / `LimitBlankPasswordUse` / `NoLmHash` / `RunAsPPL` / `RunAsPPLBoot` / `LmCompatibilityLevel` / `disabledomaincreds` | 0x0 / 0x1 / 0x1 / 0x1 / 0x2 / 0x2 / 未设置 / 0x0 ✅ | 1 / 1 / 1 / 1 / ≥2 / ≥2 / 5 / 按需(会断域外登录) |
| NTLM 会话安全 | `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\MSV1_0` → `NtlmMinClientSec` / `NtlmMinServerSec` | 0x20000000 ✅ | ≥0x20080000（含 128 位加密） |
| RDP NLA | `HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp` → `UserAuthentication` | 0x1 ✅ | 1 |
```powershell
Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force   # ⚠ 关 SMBv1（先确认无老设备）
Set-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" ConsentPromptBehaviorAdmin -Value 2
```
### 2.5 Defender 与 ASR（真实参数名以本机为准）
```powershell
Get-MpPreference                          # ✅ 实测可枚举现有 ASR 规则 ID/动作
Get-MpComputerStatus | Select AMServiceEnabled,AntispywareEnabled,RealTimeProtectionEnabled,BehaviorMonitorEnabled,IsTamperProtected,AMRunningMode
                                          # ✅ 实测属性名（本机 IsTamperProtected=False 需关注）
Set-MpPreference -CloudBlockLevel High -PUAProtection Enabled -SubmitSamplesConsent Always
Set-MpPreference -LowThreatDefaultAction Quarantine
Add-MpPreference -AttackSurfaceReductionRules_Ids "<GUID>" -AttackSurfaceReductionRules_Actions Enabled
```
- ✅ 实测 `Set-MpPreference` 真实参数名（部分）：`CloudBlockLevel`、`PUAProtection`、`SubmitSamplesConsent`、`DisableRealtimeMonitoring`、`EnableControlledFolderAccess`、`EnableNetworkProtection`、`LowThreatDefaultAction`/`Moderate-/High-/Severe-/UnknownThreatDefaultAction`、`AttackSurfaceReductionRules_Ids`、`AttackSurfaceReductionRules_Actions`。
- ⚠ **上游两处 Defender 写法是错的**（本机核对）：`-LowfiThreatLevel Default_Action Quarantine` → 不存在该参数，真实为 `-LowThreatDefaultAction Quarantine`；`-AttackSurfaceReductionRulesIds/-Actions` → 真实参数带下划线。
- ⚠ 上游 ASR 的「GUID→名称」映射错位。以 Microsoft Learn（ASR rules reference/overview，2026-09）为准的官方对照：`d4f940ab-401b-4efc-aadc-ad5f3c50688a`=Block all Office applications from creating child processes；`3b576869-a4ec-4529-8536-b80a7769e899`=Block Office applications from creating executable content；`26190899-1602-49e8-8b27-eb1d0a1ce869`=Block Office communication application from creating child processes；`5beb7efe-fd9a-4556-801d-275e5ffc04cc`=Block execution of potentially obfuscated scripts（**不是**上游写的 "Block executable files from email"，邮件那条是 `be9ba2d9-53ea-4cdc-84e5-9b1eeee46550`）；`9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2`=Block credential stealing from the Windows LSA subsystem；`c1db55ab-c21a-4637-bb3f-a12568109d35`=Use advanced protection against ransomware。
- 不要背 GUID：先 `Get-MpPreference` 查本机已配规则，未配的按官方页名称逐条 `Add-MpPreference`。
- ✅ 实测取证命令：`C:\Program Files\Windows Defender\MpCmdRun.exe`，真实命令 `-Scan` / `-GetFiles` / `-Trace` / `-RemoveDefinitions` / `-?`。
- ⚠ `Get-Service -Name Sysmon` 不可靠：`Sysmon64.exe -i` 装的服务名是 **Sysmon64**，32 位 `sysmon.exe -i` 才是 **Sysmon**；用 `Get-Service -Name Sysmon,Sysmon64 -ErrorAction SilentlyContinue`。
### 2.6 PowerShell 日志与 Sysmon
```cmd
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" /v EnableScriptBlockLogging /t REG_DWORD /d 1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging"      /v EnableModuleLogging      /t REG_DWORD /d 1
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\Transcription"      /v EnableTranscripting      /t REG_DWORD /d 1
```
- ✅ 本机查这三条返回「找不到指定的注册表项或值」= 未配置（脚本块日志关闭），本身就是待整改项。
- 开 ScriptBlockLogging（事件 4104）后 base64/混淆脚本内容才可读；转写目录是明文脚本，要落集中存储并限 ACL。
- ⚠ Sysmon 本机未安装：`sysmon64.exe -accepteula -i sysmon-config.xml`；配置用社区基线（SwiftOnSecurity / OlafHartong sysmon-modular），重点事件见 `container-endpoint-audit.md`。
### 2.7 策略基线工具（⚠ 上游给出、本机未复现）
```powershell
.\LGPO.exe /s .\baseline\GPOs\<Baseline>\DomainSysvol\GPO\Machine\registry.pol
.\PolicyAnalyzer.exe /Compare /Source "Current Policy" /Target .\baseline\GPOs\<Baseline> /Report .\compliance-report.html
```
- ⚠ 上游示例里的 zipped 基线文件名（如 `MSFT-Windows-10-1809-v4-FINAL`）与下载 URL 随 Microsoft Security Compliance Toolkit 版本变化，别写死；下载后按实际目录名填。
- ⚠ CIS-CAT Pro（`-t "Windows 10 Enterprise"`、Linux `java -jar CIS-CAT.jar -a -b <xccdf>`）依赖授权版本，未验证。
- PowerShell DSC / Ansible win_* 模块能做同样的事，但**先 dry-run**（DSC `-WhatIf`、Ansible `--check --diff`）。CIS Level2 批量落地常见翻车点：SMB 签名、NTLM 级别、凭据缓存、审计策略（会把安全日志打爆）。
## 3. macOS 基线（⚠ 全节来自上游 + 官方命令文档，本机为 Windows，未复现）
```bash
csrutil status                                                     # SIP
fdesetup status ; sudo fdesetup status -extended ; fdesetup list
spctl --status                                                     # Gatekeeper
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on --setstealthmode on --setloggingmode on
system_profiler SPInstallDataType | grep XProtect                  # XProtect 版本
kextstat | grep -v com.apple ; systemextensionsctl list            # 非 Apple 内核/系统扩展
sudo systemsetup -setremotelogin off ; sudo sysadminctl -guestAccount off
```
- 基线来源：NIST macOS Security Compliance Project（mSCP）生成 CIS/NIST 映射脚本；⚠ 上游的 `python3 assessment.py --level 1 --level 2` 是示意，参数未验证。TCC 审计（⚠ 路径/字段随 macOS 版本变动，先 `.schema access` 自查）：
```bash
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" "SELECT client,service,auth_value FROM access WHERE auth_value=2;"
# 重点服务：kTCCServiceSystemPolicyAllFiles、kTCCServiceScreenCapture、kTCCServiceListenEvent、kTCCServiceAccessibility
```
- 两个 TCC 库受 SIP 保护，需 root + 全盘访问。跨平台持续审计用 osquery（上游 Linux 片段同样适用）：`osqueryi "SELECT * FROM startup_items;"`、`SELECT * FROM disk_encryption;`、`SELECT * FROM managed_policies;`。
- ⚠ 上游的 `xprotect check <file>` 在不同 macOS 版本上未必存在，用前先 `xprotect -h` 确认。
## 4. 国产操作系统（麒麟 Kylin / 统信 UOS / openEuler）
**总原则**：能复用的走标准 Linux 机制（PAM/pwquality、auditd、sysctl、sshd、chmod、SELinux/kysec）；厂商专有 CLI 名称混乱且随版本变化，**先探测再执行**。
```bash
command -v kylin-security-config kylin-security-toolkit kysec-tools setstatus uos-security-center dde-security-tools uos-audit-tool isula 2>/dev/null
ls -l /sys/kernel/kysec/ /etc/kysec/ /etc/sysconfig/kysec/ 2>/dev/null   # ⚠ 路径未验证
getenforce 2>/dev/null ; sestatus 2>/dev/null                            # 部分版本 SELinux 与自研 kysec 并存
```
- 可直接复用（与 §1 相同，不重复）：口令策略走 `/etc/security/pwquality.conf` + `/etc/pam.d/common-auth` 的 `pam_faillock`（Kylin V10 / UOS V20 均为 Debian 系路径；⚠ 部分麒麟版本仍是 `pam_tally2`，先 grep 现役模块）；登录超时 `/etc/profile` 加 `TMOUT=600; export TMOUT`（⚠ 只管 bash 登录会话，图形会话与 systemd 服务不受控）；审计走 `/etc/audit/rules.d/*.rules` + `augenrules --load`，等保三级留存 ≥180 天并用 `audisp-remote`/rsyslog 送集中日志（⚠ 上游 `remote_server/port` 片段未验证）；强制访问控制用 `ps -Z` / `ls -Z` 读安全标记（⚠ 需 kysec/SELinux 生效态才有输出）。
- ⚠ **明确未验证、需现场确认的厂商专有项**（上游原文照录，勿当事实用）：`kylin-security-toolkit --set-password-policy`、`kylin-security-config --set-level high`、`/etc/sysconfig/kysec/security-level`、`kysec-tools --set-subject-label/--set-object-label/--audit-config`、`uos-security-center --set-password-policy/--status/--enable-firewall`、`dde-security-tools --mac-status/--mac-enable/--usb-storage disable`、`dde-sandbox run`、`uos-audit-tool --enable/--query`。这些名字在不同麒麟/UOS 小版本上大量不一致（有的只走图形「安全中心」）。**处理方式**：目标机上先 `command -v`，再用 `rpm -qf` / `dpkg -S` 反查归属包确认参数，最后才写脚本。
- openEuler（⚠ 未验证）：`isula` 容器引擎 `--security-opt seccomp=<profile.json>`；secGear 机密计算 `dnf install secgear-devel`。
- 等保 2.0 三级条款 → 核查项（条款序号以现行标准原文为准，这里只给「怎么查」）：身份鉴别→`pwquality.conf`/`login.defs`/`chage -l <user>`；登录失败处理→`pam_faillock` 的 deny/unlock_time、Windows 的 `LockoutBadCount/ResetLockoutCount/LockoutDuration`；审计留存→auditd+集中日志+留存期、Windows `wevtutil gl` 的 maxSize/retention；访问控制粒度→sudoers 最小化、`find / -perm -4000` 盘点、kysec/SELinux 标记。
## 5. 国密（SM2/SM3/SM4）——本机 OpenSSL ✅ 实测可用
```bash
openssl list -cipher-algorithms | grep -i sm4   # ✅ OpenSSL 3.5.5：SM4-CBC/CFB/CTR/ECB
openssl list -digest-algorithms | grep -i sm3   # ✅ SM3、RSA-SM3
openssl ecparam -list_curves | grep -i SM2      # ✅ SM2 curve over 256 bit prime field
openssl ecparam -genkey -name SM2 -out sm2.key ; openssl req -new -key sm2.key -out sm2.csr -sm3
openssl dgst -sm3 <file> ; openssl enc -sm4-cbc -in f -out f.enc -K <hex> -iv <hex>
```
- ✅ 结论：OpenSSL 3.x 自带 SM2/SM3/SM4，无需替换为国密分支。TLS 层要用 SM2 双证书套件（`ECC-SM2-SM4-SM3`）仍需国密分支（Tongsuo/BabaSSL、gmssl）+ 支持国密的网关（⚠ 未在本机验证）。
- ⚠ 上游的 `gmssl sm3sum`、`openssl ecparam ... -sm3`、Nginx 双证书重复 `ssl_certificate` 写法、`trust list | grep -i sm2`、`gmtls_server` 均未验证；国密 TLS 的证书链与套件名以网关产品文档为准，别照抄。
## 6. 通用核查清单（收尾自检）
- [ ] 「机器 → 基线版本（CIS/等保等级）+ 扫描时间 + 工具版本」有映射；结果落盘（XML/HTML/JSON），整改项有 owner 与关闭时间
- [ ] Level 2 / 等保三级项分批灰度，改前有回滚路径（策略导出、快照、配置备份）
- [ ] Linux：`sshd -t`、`augenrules --check`、`sysctl -p` 无 unknown key、SUID 差异有说明
- [ ] Windows：secedit 导出的 `[System Access]`/`[Event Audit]` 与目标值 diff 过；auditpol 用 UTF-8 代码页读；Defender ASR/CFA/Tamper 状态确认
- [ ] 日志容量与留存期覆盖合规要求；改完复扫，「新 FAIL」与「原 FAIL 未动」分开记，避免假合规