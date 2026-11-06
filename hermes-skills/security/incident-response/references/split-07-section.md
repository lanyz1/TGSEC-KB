## 六、日志分析与多源关联

### 6.1 Windows日志关键EventID
| EventID | 事件 | 分析重点 |
|---------|------|---------|
| 4624 | 成功登录 | Logon Type 3(网络)/10(远程交互)；异地IP+工作时间外=重点 |
| 4625 | 失败登录 | 高频暴力破解（>10次/分钟）|
| 4672 | 特殊权限分配 | SeDebugPrivilege(提权/LSASS访问前置) |
| 4688 | 进程创建 | 可疑命令行（编码PowerShell/下载执行）|
| 4698 | 计划任务创建 | 持久化 |
| 4697/7045 | 服务安装 | 后门服务（对镜像路径做签名校验）|
| 1102 | 安全日志清除 | 反取证（发现即高价值告警）|
| 4776 | NTLM认证 | Pass The Hash 检测（工作站试图以域管认证）|
| 4768/4769 | Kerberos票据 | Golden/Silver Ticket、Kerberoast |
| 4720/4728/4732 | 用户/组创建与加组 | 新增管理员、域管组变更 |
| 4648 | 显式凭据登录 | 攻击者使用窃取凭据横向移动（配合4688）|
| 4104/4103 | PowerShell模块/脚本块日志 | 编码命令还原（PowerShell攻击核心证据）|
| 8004/8006 | PowerShell应用日志 | WMI Persistence |
| 1001/1002 | Sysmon 进程创建/进程变更 | 需部署Sysmon（推荐配置为高日志量）|

### 6.2 Linux日志分析
```bash
# 异常登录检测（高频源IP）
grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20

# 成功登录后源IP
grep "Accepted" /var/log/auth.log | awk '{print $(NF-3), $9}' | sort | uniq -c | sort -rn

# 权限提升
grep "sudo:" /var/log/auth.log
grep "su:" /var/log/auth.log

# 命令历史（重点：下载、wget/curl、ssh隧道、反弹shell）
cat ~/.bash_history | grep -E "wget|curl|nc |bash -i|python.*socket"

# Web日志分析
awk '$9 >= 400' access.log | head -100                      # 4xx/5xx
awk -F'"' '{print $6}' access.log | sort | uniq -c | sort -rn | head  # UA画像
grep -E "eval|base64|cmd=|/proc/self|\.jsp|\.php\?" access.log | head -100  # 注入特征
grep -E "passwd|shadow|\.ssh|\.git|\.env|config\.php|wp-config" access.log  # 敏感文件探测

# DNS隧道/异常DNS
# 用 tcpdump 抓DNS：tcpdump -i eth0 -nn port 53 -w dns.pcap
# 关注：超长子域名、TXT记录频繁查询（dnscat2/iodine特征）

# 反连检测（防火墙/网关侧更可靠）
# ss -antup | grep ESTAB；关注 4444/8080/53/443 等非常规反连端口
```

### 6.3 多源日志关联（时间线法+图关联法）
```
1. 时间线法：将 Windows 日志、Linux 日志、防火墙、DNS、EDR、云审计拉平到统一时间轴
   工具：Timesketch（推荐）、ELK、Splunk timeline
2. 图关联法：以"账号→主机→IP→文件"为节点画关系图（BloodHound 反向用法）
   例：域管账号在3:47登录了DB服务器，DB服务器同刻访问了外网IP X
3. 入口寻找法：先找最早的异常事件（首次恶意登录/首次C2回连），再向前找初始访问
4. 交叉验证原则：单一日志结论不成立，至少两个独立源印证（如4688+网络流）
```

### 6.4 SIEM 查询速查
```
Splunk（SPL）：
  index=windows EventCode=4624 Logon_Type=10 | stats count by src_ip, user | sort -count
  index=windows EventCode=4688 | where match(CommandLine,"(?i)(-enc|bypass|IEX|DownloadString)")
KQL（Sentinel/Defender）：
  SecurityEvent | where EventID==4688 | where CommandLine contains "powershell"
  IdentityLogonEvents | where LogonType=="RemoteInteractive"
Sigma（跨平台规则）：sigma convert -t splunk -p 通用规则（社区共享检测规则）
```

