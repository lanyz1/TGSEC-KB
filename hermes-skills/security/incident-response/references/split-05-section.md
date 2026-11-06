## 四、现场取证与易失性数据采集

### 4.1 取证优先级原则（易失性递减）
```
内存 > 网络连接 > 进程 > 磁盘 > 日志
先采"关机会丢"的数据；顺序错了证据就没了
取证前禁止：重启、杀毒扫描、删除文件、关闭服务（除非是遏制必须）
```

### 4.2 Windows取证
```bash
# 1. 内存dump（最先）
winpmem.exe --load driver --output RAMDump.raw
DumpIt.exe / DumpIt_x64.exe
Magnet RAM Capture（GUI）

# 2. 网络连接
netstat -ano > netstat.txt
Get-NetTCPConnection | Where-Object {$_.State -eq "Established"} | Export-Csv connections.csv

# 3. 进程信息
tasklist /svc /v > processes.txt
wmic process get ProcessId,Name,ExecutablePath,CommandLine,ParentProcessId > wmic_process.txt
Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | Format-List

# 4. 网络连接+进程关联
netstat -anob > net_process.txt

# 5. 服务与计划任务
sc query type= service state= all > services.txt
schtasks /query /fo LIST /v > scheduled_tasks.txt
wmic startup get Caption,Command,Location > startup.txt

# 6. 注册表（持久化）
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"

# 7. 用户与登录
net user > users.txt
net localgroup administrators > admins.txt
wevtutil qe Security /q:"*[System[EventID=4624]]" /c:200 /f:text > logins.txt
wevtutil qe Security /q:"*[System[(EventID=4625)]]" /c:200 /f:text > failed_logins.txt

# 8. 最近修改的文件（时间线）
forfiles /P C:\ /S /D +2026-06-27 /C "cmd /c echo @path @fdate @ftime" > recent_files.txt

# 9. 浏览器与远程桌面痕迹（作为补充）
reg query "HKCU\Software\Microsoft\Terminal Server Client\Servers" /s > rdp_servers.txt
```

### 4.3 Linux取证
```bash
# 1. 内存
cat /proc/meminfo
# LiME：insmod lime-$(uname -r).ko "path=memdump.mem format=raw"

# 2. 网络连接
ss -antup > connections.txt
netstat -antup > netstat.txt

# 3. 进程
ps auxef > processes.txt
ls -la /proc/*/exe 2>/dev/null > proc_exe.txt
for p in /proc/[0-9]*; do echo "== $p =="; cat $p/cmdline 2>/dev/null | tr '\0' ' '; echo; done > proc_cmdline.txt

# 4. 用户与登录
last -20 > last_login.txt
lastb -20 > failed_login.txt
cat /etc/passwd > passwd.txt
cat /etc/shadow > shadow.txt
who > who.txt
ls -la /home/*/.ssh/ > ssh_keys.txt
cat /root/.bash_history > root_history.txt

# 5. 计划任务
crontab -l > crontab.txt
cat /etc/crontab >> crontab.txt
ls -la /etc/cron.* >> crontab.txt

# 6. 启动项
systemctl list-unit-files --type=service > services.txt
cat /etc/systemd/system/*.service > systemd_services.txt
cat /etc/init.d/* > init_scripts.txt
cat /etc/rc.local 2>/dev/null

# 7. 日志
cp /var/log/auth.log ./ 2>/dev/null
cp /var/log/secure ./ 2>/dev/null
cp /var/log/syslog ./ 2>/dev/null
cp /var/log/nginx/access.log ./ 2>/dev/null
cp /var/log/apache2/access.log ./ 2>/dev/null
journalctl --since "2026-06-27" > journal.txt 2>/dev/null

# 8. 文件系统时间线
find / -mtime -2 -type f -ls > recent_files.txt 2>/dev/null
find /tmp /var/tmp /dev/shm /var/www -type f -ls > suspicious_dirs.txt 2>/dev/null

# 9. SUID/Capabilities
find / -perm -4000 -type f -ls > suid.txt 2>/dev/null
getcap -r / > capabilities.txt 2>/dev/null

# 10. Rootkit检测
rkhunter --check --skip-keypress
chkrootkit

# 11. 内核模块与隐藏进程
lsmod > kernel_modules.txt
cat /proc/modules >> kernel_modules.txt
```
**所有采集文件完成后立即计算 SHA-256 并记录到证据清单（见4.4）**

### 4.4 证据保全与证据链
```
1. 每份采集文件：记录采集时间/主机/采集人/工具/命令
2. 全部计算 SHA-256：Get-FileHash file -Algorithm SHA256
3. 证据介质：只读挂载或写保护（Windows写保护块/ Linux mount -o ro）
4. 时间统一：以协调世界时(UTC)记录，避免时区歧义
5. 采集过程对系统的最小改动也要记录（本身也是"污染证据"）
6. 如涉司法取证：使用 EnCase/FTK 做镜像与校验，建立完整 Chain of Custody
```

### 4.5 远程取证（规模化）
```
KAPE（Kroll Artifact Parser & Extractor）：Windows 自动化取证，Targets批量提取工件
  kape.exe --tsource C:\ --tdest D:\output --target !SANS_Triage --tlog
UAC（Linux Artifact Collector）：Linux 自动化采集
Velociraptor：大规模远程取证与狩猎（DFIR/IR 一体化）
  velociraptor --config client.config.yaml artifacts collect Windows.Sys.Processes
GRR Rapid Response：Google 开源远程取证平台
F-Response/EnCase Enterprise：远程镜像
原则：能自动化就不手工，能并行就不串行，先采集再分析
```

