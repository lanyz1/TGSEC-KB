## 五、内存取证与主机取证深度

### 5.1 内存采集工具
```
Windows：winpmem、DumpIt、Magnet RAM Capture、FTK Imager(内存)
Linux：LiME（内核模块）、avml（Linux内存采集，速度快）
macOS：osxpmem
云端VM：部分云厂商提供内存快照能力；无法直接采集时依赖进程/日志替代
K8s容器内进程：在宿主机上 avml --pid <容器内进程在宿主机的PID>（容器PID在宿主机可见）
```

### 5.2 Volatility 3 深度分析
```bash
# 系统信息与内核基址
vol -f memdump.raw windows.info

# 进程分析（核心三连）
vol -f memdump.raw windows.pslist      # 常规进程列表（对比EDR确认基线）
vol -f memdump.raw windows.pstree      # 父子进程树（发现可疑派生关系）
vol -f memdump.raw windows.psscan      # 扫描隐藏/已退出进程（反取证对抗）
vol -f memdump.raw windows.pstree --pid <PID>   # 单进程族谱

# 网络连接（内存中的socket）
vol -f memdump.raw windows.netscan     # 包括已断开但仍在内存中的连接
vol -f memdump.raw windows.netstat

# 注入与隐蔽代码（无文件攻击核心证据）
vol -f memdump.raw windows.dlllist     # 进程加载的DLL（异常路径/未签名）
vol -f memdump.raw windows.malfind     # 可疑可执行内存段（经典注入检测）
vol -f memdump.raw windows.ldrmodules  # 检查DLL是否从内存中被隐藏（反射注入）
vol -f memdump.raw windows.svcscan     # 服务（隐藏服务检测）

# 凭据与hash
vol -f memdump.raw windows.hashdump    # 本地账户hash
vol -f memdump.raw windows.lsadump     # LSA secrets（含服务账号明文）

# 命令与文件
vol -f memdump.raw windows.cmdline     # 进程命令行（LOLBins滥用证据）
vol -f memdump.raw windows.filescan    # 扫描内存中文件对象
vol -f memdump.raw windows.dumpfiles --pid PID   # 从内存提取文件
vol -f memdump.raw windows.memmap --pid PID > pid_map.txt  # 内存段映射

# Linux 对应插件
vol -f linuxmem.raw linux.pslist linux.bash linux.environ linux.malfind linux.dump_map
```

### 5.3 KAPE 自动化取证
```
KAPE = 集合器(kcollect)+处理器(kpsparse)，分钟级完成 Windows 关键工件采集
常用 Targets：
  !SANS_Triage        # SANS 三线采集（核心推荐）
  !EZ_Triage          # Eric Zimmerman 全家桶格式
  $MFT / Prefetch / ShimCache / AmCache / RecentDocs
  SRUM（应用资源使用，定位执行时间）
  EventLogs / Sysmon
KAPE 输出自动生成时间线，配合 EZ 工具（Timeline Explorer/EvtxECmd/Everything）
```

### 5.4 无文件攻击追查（Fileless 专项）
无文件攻击不落地二进制，或仅存在于内存/注册表/系统组件中，**传统杀软可能零检测**：
```
追查路径：
1. 内存证据：Volatility malfind/ldrmodules 找注入；提取内存样本做YARA匹配
2. 注册表负载：RunKeys/服务ImagePath指向powershell脚本、WMI EventSubscription持久化
   reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\WMI" /s
   Get-WmiObject -Namespace root\subscription -Class __EventConsumer  # 查看WMI消费器
3. 计划任务内嵌脚本：schtasks /query /fo LIST /v | findstr /i "powershell"
4. LOLBins 滥用：powershell.exe -enc、mshta、regsvr32、rundll32 启动链
   （对 4688/Sysmon EID1 做命令行规则检测是关键防线）
5. .NET CLR 劫持：AppDomainManager 注入（内存中托管代码）
6. 无文件勒索：直接在内存中加密或仅用系统工具（如部分 BlackCat/Medusa 变种行为）
判活确认后：内存样本+YARA规则留档，禁止直接杀掉重启（证据丢失）
```

### 5.5 反取证检测
```
Timestomping（篡改时间戳）：对比 MFT/PreFetch/日志时间，使用 MFTECmd 检查
日志清除：1102(安全日志清空)/104(系统日志清空)本身就是告警信号
ADS（NTFS 备用数据流）：dir /r 检测，可疑文件藏于隐藏流
卷影副本删除：vssadmin list shadows 对比记录
进程名欺骗/伪装：镜像路径与签名校验（sigcheck -a）
禁用安全工具：EDR/AV被停用的服务状态变化日志（7045/7036）
```

