---
name: endpoint-os-hardening-baseline
description: "Use when 加固/基线核查:CIS、Lynis、oscap、kube-bench、国产OS。"
---

# 端点与操作系统加固基线

按 CIS / 等保 2.0 做「扫描 → 差异 → 整改 → 复扫」，输出可交付的加固与合规证据。攻击面利用交给 linux-privilege-escalation / windows-lpe / active-directory / docker-security / cloud-k8s。

## 触发场景
- 「按基线加固 / 合规核查 / CIS / 等保三级 / 安全加固报告」——Linux、Windows、macOS、国产 OS（麒麟、统信 UOS）
- 要跑 Lynis / OpenSCAP(oscap xccdf eval) / Chef InSpec / Ansible / kube-bench / dockle / trivy 出扫描结果
- Windows 安全策略与审计策略核对（secedit、auditpol、wevtutil、Defender ASR）
- 容器与 K8s 基线审计（daemon.json、PSS/PSA、NetworkPolicy、RBAC）
- 端点检测落地（Sysmon、LOLBins、Defender/Velociraptor/KAPE 遥测与调查）
- 国密（SM2/SM3/SM4）与国产化改造相关核查

## 工作流
1. 定范围与基线版本：机器清单 → 每台对应的 CIS Benchmark 版本 / 等保等级；记录扫描工具与版本（结论要能复现）。
2. **只读扫描**：Linux 上 `lynis audit system` + `oscap xccdf eval --profile ... --results-arf r.xml --report r.html`；Windows 上 `secedit /export /cfg` + `auditpol /get /category:*`；容器 `docker info` + `docker inspect` 模板 + `dockle`/`trivy config`；K8s `kube-bench run --targets node`。
3. 出差异清单：只列「目标值 vs 实测值」，逐条标 owner、影响面、回滚方式。Level 2 / 等保三级项单独一档。
4. 分批整改：能自动化的走 Ansible（`--check --diff`）/ DSC（`-WhatIf`）/ GPO(LGPO)，先灰度 1–2 台验证服务与日志影响。
5. 复扫回归 + 交付：结果文件（XML/HTML/JSON）+ 差异表 + 未整改项风险说明。把「新 FAIL」与「原 FAIL 未动」分开记。
6. 顺手沉淀：把该环境的基线版本、profile id、翻车项写进本 skill 的参考文件，别只留在临时笔记里。

## 命令速查
```bash
# Linux：体检 + 合规
sudo lynis audit system
oscap info /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml     # 先列 profile，再 eval
sudo oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  --results-arf r.xml --report r.html /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml
sudo sysctl -p /etc/sysctl.d/99-security.conf ; sshd -t && systemctl restart sshd
sudo augenrules --check && sudo augenrules --load ; sudo ausearch -k identity -ts today
chmod 600 /etc/shadow ; find / -xdev -perm -4000 -type f -ls
```
```powershell
# Windows
secedit /export /cfg C:\Temp\secpol.cfg
Get-Content C:\Temp\secpol.cfg -Encoding Unicode | Select-String "PasswordComplexity|LockoutBadCount"
chcp 65001 ; auditpol /get /category:*          # 中文 Windows 先切 UTF-8，否则乱码
wevtutil gl Security ; net accounts ; Get-MpPreference ; Get-MpComputerStatus
Get-Content C:\Temp\secpol.cfg -Encoding Unicode | Select-String "EnableGuestAccount"   # 导出后逐项 diff
```
```bash
# 容器 / K8s / 端点
docker info ; docker ps -q | xargs docker inspect --format '{{.Id}}: {{.HostConfig.Privileged}} {{.Config.User}}'
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock goodwithtech/dockle:latest <image>
trivy config <DIR> ; docker run --rm --pid=host -v /etc:/etc:ro -v /var/lib:/var/lib:ro aquasec/kube-bench:latest run --targets node
Get-WinEvent -FilterHashtable @{LogName="Microsoft-Windows-Sysmon/Operational"; StartTime=(Get-Date).AddHours(-1)} | Group-Object Id
```
国产 OS 与国密：`command -v` 探测厂商 CLI 后再用；OpenSSL 3.x 自带 SM2/SM3/SM4（`openssl enc -sm4-cbc`、`openssl dgst -sm3`）。

## Pitfalls
- `secedit /export` 的结果**不写 stdout**且文件是 **UTF-16LE**：`secedit ... | Select-String` 永远匹配不到，必须 `Get-Content -Encoding Unicode`（或 `iconv -f UTF-16LE`）。
- 上游/网上大量片段把 `MinimumPasswordLength`、`LockoutBadCount` 当注册表项写 —— 它们来自 secedit 策略导出，注册表里查不到。
- 中文 Windows 的 `auditpol`、`net accounts` 输出是 GBK，bash 里读会乱码；先 `chcp 65001`。脚本里 `auditpol` 优先用子类别 GUID，别用本地化名称。
- Defender：真实参数是 `-LowThreatDefaultAction`、`-AttackSurfaceReductionRules_Ids/_Actions`（带下划线）；网上/上游常写成 `-LowfiThreatLevel`、`-AttackSurfaceReductionRulesIds`，会直接报错。ASR 的 GUID↔名称映射错位极常见，以 Microsoft Learn 为准，或直接 `Get-MpPreference` 枚举本机现有规则。
- `get-service Sysmon` 常常找不到：`Sysmon64.exe -i` 装的服务是 `Sysmon64`。
- `kernel.exec-shield` 在主流内核不存在，Ansible `sysctl` 模块会因 unknown key 整任务失败；`ClientAliveCountMax 0` 不是「超时」而是「不断开」；`Protocol 2` 在 OpenSSH 7.6+ 已废弃。
- auditd：`ausearch -ts` 只认 `today|yesterday|this-week|...|recent|boot`，不认「24小时前」；规则别写进会被包升级覆盖的文件名。
- `docker-bench-security` 在 Docker Desktop/Windows 上连不上守护进程（端点是 npipe，没有 `/var/run/docker.sock`）——在 Linux/WSL2 内跑，Windows 上用 `docker info` + `docker inspect` + dockle + `trivy config` 替代。
- `trivy image` 需联网下载漏洞库（气隙环境要预置）；`trivy config` 离线可用且不接受 `--no-progress`。
- 关 `ip_forward`/`rp_filter`、开 `AllowUsers`、Level 2 批量落地（SMB 签名、NTLM 级别、审计策略）都可能直接断业务或把安全日志打爆：先灰度 + 留回滚。
- 国产 OS 的厂商专有 CLI 名称随小版本漂移（`kylin-security-*`、`kysec-tools`、`uos-security-center`、`dde-security-tools`），先 `command -v` / `rpm -qf` 确认，别照抄脚本。
- 常见输出退化：dockle 只报 CIS-DI 编号、kube-bench 猜错 K8s 版本会错配检查项 —— 落地前确认版本来源。

## 参考文件
- `references/os-hardening-baseline.md`：CIS 落地流程、Linux（Lynis/OpenSCAP/InSpec/Ansible、sysctl、sshd、PAM、auditd、权限）、Windows（secedit/auditpol/注册表实测点位/Defender+ASR/PowerShell 日志/策略工具）、macOS、国产 OS 与等保映射、国密。
- `references/container-endpoint-audit.md`：Docker 守护进程与运行时审计、dockle/trivy/kube-bench 实测结果、K8s PSA/NetworkPolicy/RBAC、Falco、Sysmon/LOLBins、EDR 遥测与端点合规核查清单。
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
