## 八、权限提升

### 8.1 Windows 本地提权

```
信息收集：systeminfo / whoami /all / net user / wmic qfe get HotFixID
漏洞利用：WinPEAS / Watson / Windows-Exploit-Suggester
服务滥用：不安全服务权限 / 未引用服务路径（quoted path）
注册表：AlwaysInstallElevated / AutoRun / 弱 DACL
Token 操纵：SeImpersonatePrivilege（Potato 系列：Juicy/PrintSpoofer/GodPotato）
计划任务：高权限计划任务劫持（写入/替换脚本）
凭据提取：SAM / LSA / DPAPI / 浏览器密码 / RDP 缓存
2026 思路：关注每月 Patch Tuesday 新 LPE（提权漏洞时效性极强），
  结合本机补丁列表差集快速命中
```

### 8.2 Linux 提权

```
信息收集：uname -a / id / sudo -l / find / -perm -4000 2>/dev/null
内核漏洞：CVE 利用（DirtyPipe CVE-2022-0847 / PwnKit CVE-2021-4034 / 新内核链）
SUID/SGID：gtfobins.github.io 对照利用
Cron 作业：/etc/crontab / 用户 crontab / /etc/cron.d 可写
Capabilities：getcap -r / 2>/dev/null（cap_setuid 等）
Sudo 滥用：sudo -l → GTFOBins
Docker 组：docker run -v /:/mnt alpine chroot /mnt
环境变量：LD_PRELOAD / LD_LIBRARY_PATH 劫持
容器逃逸：特权容器 → nsenter / CVE 逃逸链
```

### 8.3 域内提权（从标准域用户到域管）
```
路径排序（按性价比）：
1. Kerberoast 破解（离线，无网络动作）
2. BloodHound 找 ACL 滥用 / 委派路径
3. ADCS ESC 利用（见 6.1）
4. 认证胁迫 + NTLM Relay → ADCS/LDAP（见 6.5）
5. GPO 滥用（写 GPO → 下发启动脚本/计划任务 → 域管会话反弹）
6. 明文凭据回收（网络共享脚本、配置文件、运维工具数据库）
```

