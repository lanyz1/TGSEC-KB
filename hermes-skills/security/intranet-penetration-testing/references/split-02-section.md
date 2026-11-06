## 一、本地信息收集（打点后的第一站）

> 原则：**先本地后网络，先凭证后提权**。本地信息收集决定后续所有攻击路径的可行性，10分钟的系统化收集胜过盲目扫描。

### 1.1 网络/系统/软件/服务信息
```bat
ipconfig /all                                                      :: 网卡/网关/DNS(域判断关键)
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"   :: OS版本与架构
echo %PROCESSOR_ARCHITECTURE%                                      :: 架构(影响payload选择)
wmic product get name,version                                      :: 安装软件清单(找可利用中间件)
wmic service list brief                                            :: 服务列表(找错误配置/第三方服务)
tasklist /svc                                                      :: 进程与服务关联(杀软/EDR/AV)
wmic startup get command,caption                                   :: 启动项(持久化线索/账密)
schtasks /query /fo LIST /v                                        :: 计划任务(常藏连接账号密码)
net session                                                        :: 本机与客户端的会话
netstat -anto                                                      :: 端口/连接(判断出网/服务)
```

### 1.2 用户与会话
```bat
net user                                                           :: 本机用户列表
net localgroup administrators                                      :: 本地管理员组(常含域用户)
query user                                                         :: 当前在线用户(RDP目标)
net user <username>                                                :: 用户详情(上次登录时间等)
whoami /all                                                        :: 当前权限与令牌信息(提权线索)
wmic useraccount get name,sid,disabled                             :: SID与禁用状态
```

### 1.3 补丁/防火墙/共享/路由
```bat
wmic qfe get Caption,HotFixID,InstalledOn                          :: 补丁列表(缺哪补丁→对应漏洞)
netsh advfirewall show allprofiles                                 :: 防火墙状态与规则
net share                                                          :: 本机共享(敏感共享泄露)
wmic share get name,path,status                                    :: 共享列表
route print                                                        :: 路由表(发现其他网段)
arp -a                                                             :: ARP缓存(活跃主机/网关)
```
> **高级**：`arp -a` 与 `route print` 是发现**新网段**的第一手情报——内网多网段边界机往往是跳板机的首选。

### 1.4 历史命令与登录记录
```bash
# Windows
# 每个用户的 .bash_history 类似物——PowerShell历史
type %APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
type %USERPROFILE%\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt

# Linux（含大量敏感账号密码/IP/服务配置）
history
cat ~/.bash_history
grep -iE "pass|pwd|ssh|mysql|redis|token|secret" ~/.bash_history
```
**RDP/SSH 外连记录定位运维人员**：
```
# Windows RDP外连记录（快速定位运维/管理员主机）
cmdkey /list                                     # 保存的凭据(可离线解密)
# SharpEventLog: 读取本机所有登录本机的计算机记录
# 位置: 注册表 HKCU\Software\Microsoft\Terminal Server Client\Servers
reg query "HKCU\Software\Microsoft\Terminal Server Client\Default"
reg query "HKCU\Software\Microsoft\Terminal Server Client\Servers" /s

# Linux SSH
cat ~/.ssh/authorized_keys                      # 谁曾免密登录过
cat ~/.ssh/id_rsa*                              # 私钥(可复用登录其他主机)
lastlog && last -a                              # 登录IP历史
cat ~/.ssh/config /etc/ssh/ssh_config           # 配置中的跳板/账号
```

### 1.5 杀软/EDR识别（决定免杀策略）
```
# 直接看进程
tasklist | findstr /i "360 kav avp mcshield egui safedog hws hipstray MsMpEng
  Norton symantec cccen NISUN x64 sysdiag 火绒 安天 深信服 奇安信 天擎
  QAX 微步 青藤 ossec alibaba aegis"
# 服务
wmic service get name,displayname,pathname | findstr /i "360 kav aegis"
# 驱动
driverquery /v | findstr /i "360 qutmips ysprotect sysdiag"
# PowerShell AMSI/CLM 状态
Get-MpComputerStatus 2>$null | Select RealTimeProtectionEnabled
```
> **决策链**：识别杀软 → 判断有无EDR（是否有内核驱动/行为分析）→ 决定免杀强度与上线方式（进程注入/无文件/白利用）。

### 1.6 AI辅助信息收集分析
```
# 大模型快速处理原始输出：把 ipconfig/systeminfo/tasklist/wmic 输出丢给LLM，
# 让其标注: 1)可疑的高权限进程 2)可利用的第三方软件 3)缺失的关键补丁
# 4)网段关系图 5)杀软与免杀建议。省去人工逐行翻找的耗时。
# 典型提问示例（见第十三章AI辅助红队作战）：
#  "分析以下 systeminfo 输出，列出可能存在的提权漏洞（给出CVE编号）"
#  "从这份 tasklist 中识别出所有安全软件及其类型(AV/EDR/HIPS)"
```

