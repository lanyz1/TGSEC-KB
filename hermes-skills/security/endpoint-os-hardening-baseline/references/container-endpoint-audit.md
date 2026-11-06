# 容器与端点审计参考（container-endpoint-audit）

> 定位：**审计/基线核查**侧命令（发现 + 核查 + 检测点）。利用面与逃逸手法见 docker-security / cloud-k8s / linux-privilege-escalation。
> 验证标记：✅=本机实测（Docker 29.6.2 + Docker Desktop/WSL2、trivy 0.74.0、kube-bench v0.16.0、dockle、kubectl）；⚠=上游或官方文档，未在本机复现。

## 1. Docker 守护进程与运行时审计

```bash
docker info                                     # ✅实测字段：Server Version/Storage Driver/Cgroup Driver/Cgroup Version/
                                                #   Security Options/Runtimes/Default Runtime/Live Restore Enabled/Docker Root Dir
docker version --format '{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}'
ls -l /etc/docker/daemon.json; cat /etc/docker/daemon.json   # Linux 宿主；Docker Desktop 在 C:\ProgramData\docker\config\daemon.json ✅实测
```
✅ 本机 `docker info | grep -i "Security Options"` 输出为空 + `Cgroup Version: 2` + `Live Restore Enabled: false` + `Default Runtime: runc`：这就是可核查项（seccomp/AppArmor/USerns 未生效、live-restore 未开）。

```bash
# 全容器体检（✅ 本机实测模板可用）
docker ps -q | xargs docker inspect --format '{{.Id}}: Privileged={{.HostConfig.Privileged}} User={{.Config.User}}'
docker ps -q | xargs docker inspect --format '{{.Id}}: Mounts={{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}'
docker ps -q | xargs docker inspect --format '{{.Id}}: Memory={{.HostConfig.Memory}} CpuShares={{.HostConfig.CpuShares}}'
docker ps -q | xargs docker inspect --format '{{.Name}} CapAdd={{.HostConfig.CapAdd}} CapDrop={{.HostConfig.CapDrop}} Pid={{.HostConfig.PidMode}} Net={{.HostConfig.NetworkMode}}'
docker ps -q | xargs docker inspect --format '{{.Name}} UsernsMode={{.HostConfig.UsernsMode}} Readonly={{.HostConfig.ReadonlyRootfs}} SecOpt={{.HostConfig.SecurityOpt}}'
docker volume ls ; docker network ls            # 数据面/网络面盘点
```
⚠ 判读要点：`Privileged=true`、`PidMode=host`、`NetworkMode=host`、`Mounts` 含 `/var/run/docker.sock`、`/`、`/etc`、`ReadonlyRootfs=false`、`CapAdd` 含 `SYS_ADMIN/SYS_PTRACE` → 逐条记录为风险项。
✅ 容器内自查能力集（本机实测 `debian:bookworm-slim` 返回 `CapEff/CapBnd=00000000a80425fb`）：
```bash
docker run --rm <image> sh -c 'id; grep -E "^Cap(Eff|Bnd|Prm)" /proc/self/status; cat /proc/1/cgroup'
```

`daemon.json` 加固项（⚠ 键名逐一核对，上游给的一份里混入了非法键）：
- ✅/⚠ 常见有效键：`"icc": false`、`"userns-remap": "default"`、`"live-restore": true`、`"userland-proxy": false`、`"log-driver":"json-file"`、`"log-opts":{"max-size":"10m","max-file":"3"}`、`"no-new-privileges"`（⚠ 该键**不是** daemon.json 合法项，真实形态是 `docker run --security-opt no-new-privileges`，✅`docker run --help` 确认存在 `--security-opt`）、`"seccomp-profile"`（⚠ 需与 dockerd 版本匹配）
- ⚠ 改完必须 `systemctl restart docker`；`userns-remap` 会让已有容器卷权限变化，需先评估。

## 2. 镜像与主机基线扫描（本机实测结果）

```bash
# dockle：CIS Docker Image 检查（本机实测可用）
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock goodwithtech/dockle:latest <image>
```
✅ 实测输出格式：`WARN - CIS-DI-0001: Create a user for the container`、`INFO - CIS-DI-0005: Enable Content trust`、`INFO - CIS-DI-0006: Add HEALTHCHECK`、`INFO - CIS-DI-0008: Confirm safety of setuid/setgid files`（会逐个列出镜像内 setuid/setgid 文件，如 `/usr/bin/chsh`、`/usr/bin/passwd`）。`--exit-code 1` 可接 CI。

```bash
# trivy
trivy image --severity CRITICAL,HIGH <image>      # ⚠ 需下载漏洞库
trivy fs /path/to/project ; trivy repo <url> ; trivy image --input alpine.tar
trivy config <DIR_or_Dockerfile>                  # ✅ 本机实测离线可用（检查捆绑在二进制内，拉不到远端会 fallback）
trivy image --format json -o out.json ; trivy image --exit-code 1 --severity CRITICAL,HIGH <image>
```
✅ 实测：`trivy config /scan` 对示例 Dockerfile 报 `Tests: 27 (SUCCESSES: 22, FAILURES: 5)`，规则 ID 形如 `DS-0001 (MEDIUM): Specify a tag in the 'FROM' statement`（可查 avd.aquasec.com/misconfig/ds-XXXX）。
⚠ 实测坑：`trivy image` 需联网下载漏洞库，本机因代理未启动失败（`failed to download vulnerability DB ... proxyconnect tcp: 127.0.0.1:10808`）；气隙环境需预置 DB（`TRIVY_OFFLINE_SCAN=true` + 落好的 db 仓库，⚠ 未验证）。`trivy config` 不接受 `--no-progress`（会报 unknown flag）。

```bash
# docker-bench-security（CIS Docker Benchmark 主机侧）
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=0 -v /var/lib:/var/lib:ro -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc:/etc:ro --label docker_bench_security docker/docker-bench-security
```
⚠ **本机实测失败**：`Error connecting to docker daemon (does docker ps work?)`。原因是 Docker Desktop 的端点是 `npipe:////./pipe/dockerDesktopLinuxEngine`（`docker context ls` ✅）、宿主根本没有 `/var/run/docker.sock`，把 socket 挂进去也连不上。**变通**：在 Linux 宿主或 WSL2 发行版内（有真实 `/var/run/docker.sock`）执行；Windows 上做基线核查改用 dockle + trivy config + `docker inspect` 三件套。
⚠ `grype`/`syft`/`cosign`/`docker scout`（`docker scout quickview` 需登录）本机均未安装，未验证；`DOCKER_CONTENT_TRUST=1` 只对支持 Notary 的 registry 生效。

## 3. Kubernetes 审计

```bash
# kube-bench（✅ 本机实测 v0.16.0）
docker run --rm --pid=host -v /etc:/etc:ro -v /var/lib:/var/lib:ro aquasec/kube-bench:latest run --targets node
docker run --rm aquasec/kube-bench:latest version          # ✅ 正确用法是 version 子命令；`--version` 会报 flag needs an argument
kube-bench run --targets master|node|controlplane|policies|etcd|all
kube-bench run --json > results.json ; kube-bench run --check 1.1.1,1.1.2 ; kube-bench run --config-dir ./cfg
```
✅ 实测输出形如 `[FAIL] 4.1.1 Ensure that the kubelet service file permissions are set to 644 or more restrictive (Automated)`、`[PASS]/[WARN]` 分级，含 `4.1.x Worker Node Configuration Files`、`4.2.x Kubelet`。
⚠ 实测行为：kubectl 连不上集群时它 `Assuming default version 1.18` —— 版本猜错会导致检查项错配，务必让 kube-bench 能读 kubeconfig（挂载 `/root/.kube` 或设 `KUBECONFIG`）。

```bash
kubectl auth can-i --list --as=system:serviceaccount:ns:sa      # 以 SA 身份枚举权限
kubectl auth can-i delete pods --as=system:serviceaccount:ns:sa
kubectl get clusterrolebindings -o wide ; kubectl describe clusterrolebinding cluster-admin
kubectl get clusterroles -o json | jq '.items[] | select(.rules[].resources[]? | contains("*"))'
kubectl get serviceaccounts,rolebindings --all-namespaces
kubectl get networkpolicies --all-namespaces ; kubectl describe networkpolicy -n default deny-all
kubectl who-can create pods        # ⚠ 需 kubectl-who-can 插件，本机未装
```
- Pod Security Admission（PSA）：给 Namespace 打标签强制级别（`baseline` / `restricted`），三档 `Privileged → Baseline → Restricted`：
  ```yaml
  metadata:
    labels:
      pod-security.kubernetes.io/enforce: restricted
      pod-security.kubernetes.io/audit: restricted
      pod-security.kubernetes.io/warn: restricted
  ```
  Restricted 合规 Pod 要点：`runAsNonRoot: true`、`seccompProfile.type: RuntimeDefault`、`allowPrivilegeEscalation: false`、`capabilities.drop: ["ALL"]`、`readOnlyRootFilesystem: true`、设 `resources.limits`。
  ⚠ 上游 RBAC 卡片里的 `security.kubernetes.io/podsecuritypolicies` ClusterRole 示例是旧 API（PSP 在 k8s 1.25 已移除，API 组为 `policy`，别再给 PSP 授权）。
- 策略即代码：Gatekeeper（ConstraintTemplate + Constraint，示例 `K8sPSPPrivilegedContainer`）或 Kyverno（`ClusterPolicy` + `validationFailureAction: enforce|audit`，示例禁 `:latest` 标签、要求 readOnlyRootFilesystem）⚠ 未在本机验证，但资源结构是官方示例格式。
- 持续运行时检测：Falco（Helm `falcosecurity/falco`，`--set falco.driver.kind=modern_ebpf`；单机 `docker run --privileged` 挂 `/proc`、`/boot`、`/lib/modules`）、tracee、Cilium Tetragon（`tetra getevents -o compact --process|--network`）⚠ 未验证。
  ⚠ 上游 Falco 规则片段有结构性错误：它把 list 命名为 `str_miner_procs` 又写了同名 macro 且 `condition: proc.name in (str_miner_procs)` **自引用**（会循环报错）。正确形态是 `- list: miners` + `items: [...]`，规则里写 `proc.name in (miners)`。判读要点：容器内起 shell、挂载宿主机敏感路径、挖矿进程（xmrig 等）、异常外联、`kubectl`/`docker` 出现在容器内。

## 4. 端点检测：Sysmon / LOLBins / EDR

```powershell
sysmon64.exe -accepteula -i sysmon-config.xml          # ⚠ 本机未装 Sysmon，未验证
Get-Service Sysmon,Sysmon64 -ErrorAction SilentlyContinue   # ⚠ 服务名取决于安装用的二进制（sysmon64.exe→Sysmon64）
Get-WinEvent -FilterHashtable @{LogName="Microsoft-Windows-Sysmon/Operational"; StartTime=(Get-Date).AddHours(-1)} |
  Group-Object Id | Sort Count -Descending
```
Sysmon 事件 ID（上游 + 官方语义）：1 进程创建、3 网络连接、7 镜像加载、8 CreateRemoteThread、10 ProcessAccess（LSASS 访问）、11 文件创建、15 FileCreateStreamHash（Zone.Identifier/下载来源）、17/18 命名管道、22 DNS 查询。
- 高频狩猎组合：`Id=10` 且 `TargetImage=lsass.exe` 且 `SourceImage` 非系统进程；`Id=8` 从 `powershell.exe` 注入；`Id=11` 落 `AppData\...\Temp` 的可执行文件；`Id=1` 里 Office → `cmd/powershell/mshta/regsvr32/rundll32` 的父子链。

```powershell
# PowerShell 侧遥测（先按 os-hardening-baseline.md §2.6 开日志）
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 200 |
  Where-Object Id -in 4103,4104 | Select TimeCreated,Id,Message
# Defender XDR / Sentinel 高级狩猎（⚠ 需 MDE 许可，本机无）
# DeviceEvents | where ActionType == "AmsiScriptDetected" | summarize count() by DeviceName, InitiatingProcessFileName
```
LOLBins 检测要点（上游清单 + 判读）：`powershell.exe`（`-enc`/`-EncodedCommand`、`DownloadString`、`IEX`、`FromBase64String`、`-w hidden`、`-nop/-ExecutionPolicy Bypass`）、`cmd.exe /c`、`wscript/cscript` 跑 `.vbs/.js`、`mshta`、`regsvr32 /s /u /i:<url> scrobj.dll`、`rundll32`、`certutil -urlcache/-decode`、`bitsadmin /transfer`、`installutil`、`msbuild`。检测落点优先选「命令行内容 + 父进程 + 是否从 Temp/Downloads/UNC 执行」，不要只做文件名黑名单（一条 `IEX` 正则 ≠ 检测能力，容易假阳/假阴）。

EDR 遥测与调查：
- Defender：✅ 实测 `Get-MpComputerStatus`（`AMServiceEnabled`/`AntispywareEnabled`/`RealTimeProtectionEnabled`/`BehaviorMonitorEnabled`/`IsTamperProtected`/`AMRunningMode`）、`Get-MpPreference`；取证包 ✅ `MpCmdRun.exe -GetFiles`（真实命令，另有 `-Scan`、`-Trace`、`-RemoveDefinitions`）。云侧 `DeviceProcessEvents`/`DeviceNetworkEvents`/`DeviceFileEvents` 等表需 MDE，⚠ 未验证。
- Velociraptor / KAPE / CrowdStrike RTR：⚠ 本机均未安装，命令未验证。通用做法：Velociraptor 用 server 下发 artifact 采集（`Windows.KapeFiles.Targets` 等）+ notebook 做时间线；KAPE 用 `kape.exe --tsource C: --tdest D:\out --target <TargetName> --module <ModuleName>` 形态的目标/模块名从 `Modules/`、`Targets/` 目录现取；CrowdStrike 走 Falcon 控制台的 RTR/`falconctl`（Linux 传感器）——**都别写死参数，先在管理台/安装目录确认版本对应的命令**。

## 5. 端点合规基线核查清单（可直接当检查表）

| 面 | 核查命令/证据 | 通过判据 |
|---|---|---|
| 补丁与版本 | Linux `uname -r`、`apt list --upgradable`；Win `Get-HotFix`、`Get-CimInstance Win32_OperatingSystem` | 无已知高危未修，记录基线版本 |
| 本地账户 | `net accounts` ✅、`Get-LocalGroupMember Administrators` ✅、`passwd -S`、`awk -F: '($3==0)' /etc/passwd` | 无多余管理员/uid0，口令策略达标 |
| 口令策略 | secedit 导出 `[System Access]` ✅、`pwquality.conf` | 长度/历史/锁定/有效期达标 |
| 审计开关 | `auditpol /get /category:*`（先 `chcp 65001`）✅、`auditctl -l`/`augenrules --check` | 关键子类别成功+失败；规则已加载 |
| 日志留存 | `wevtutil gl Security` ✅、`ls /var/log`、远程日志连通性 | 容量/留存覆盖合规期，异地留存 |
| 加密 | `Get-BitLockerVolume` ✅、`fdesetup status`（mac）、`lsblk`+`cryptsetup status` | 系统盘/数据盘加密 |
| 主机防火墙 | `Get-NetFirewallProfile` ✅（本机 Domain/Private/Public 全 True）、`nft list ruleset`/`iptables -S` | 默认拒绝入站，例外有清单 |
| 暴露面 | `ss -tlnp`、`Get-NetTCPConnection -State Listen`、`systemctl list-unit-files --type=service \| grep enabled` | 端口/服务与台账一致 |
| SUID/提权面 | `find / -xdev -perm -4000 -type f -ls`、`sudo -l`、`Get-LocalUser` 的 UAC 限制 | 差异项有说明 |
| 容器面 | `docker info` ✅、`docker ps -q \| xargs docker inspect ...` ✅、dockle ✅、trivy config ✅ | 无 privileged/host 网络/socket 挂载，无 root 用户运行 |
| 检测面 | Sysmon 服务与事件量、4104 事件、Falco 告警、EDR 传感器在线率 | 遥测有数据且被消费（不是装了没人看） |
| 自动化 | Ansible `--check --diff`、DSC `-WhatIf`、策略导出备份 | 变更可回滚、有审批记录 |
