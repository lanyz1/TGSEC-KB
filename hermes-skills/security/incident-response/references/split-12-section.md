## 十一、威胁猎捕方法论（假设驱动）

### 11.1 猎捕 vs 响应
```
响应：事件已发生，被动处置，以"遏制止损"为目标
猎捕：主动在"没有告警"时搜索异常，以"发现未知威胁"为目标
猎捕输出：新增检测规则、IOC、环境基线修正、减少驻留时间
```

### 11.2 假设驱动猎捕流程（PTFH 模型）
```
1. 提出假设（Hypothesis）：基于威胁情报/最新攻击手法/近期事件
   例："攻击者可能通过RDP弱口令进入并在周末横向移动"
2. 确定数据源（Data Source）：假设落地到哪些日志/端点
   例：4624 Type10 + 4625 + 4688 + 防火墙日志
3. 选择技术（Technique）：查询/行为基线/机器学习异常检测
4. 验证假设（Validation）：命中→调查；未命中→记录为已排除
5. 产出（Output）：检测规则(Sigma/YARA)、IOC、故事时间线
每轮猎捕建议 2-4 小时，聚焦一个假设，避免"撒网式"低效搜索
```

### 11.3 六大高频猎捕假设模板
```
假设1-横向移动：同一账号从多台主机登录 / 新主机出现已知内网账号
假设2-持久化：近期新增的计划任务/服务/启动项（对比基线）
假设3-C2通信：低频长连接、非常规端口、DNS长域名、JA3指纹异常
假设4-凭据窃取：LSASS进程访问(4688+Sysmon EID10)、SAM/hashdump行为
假设5-数据外传：大流量突发、压缩包外传、非工作时间上传
假设6-0day信号：边缘设备(LVPN/VPN/网关)异常登录、内存注入但无已知签名
```

### 11.4 狩猎查询示例
```bash
# 假设：PowerShell 编码执行（近期钓鱼热点）
# Windows事件4688/Sysmon EID1
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational';Id=1} |
  Where-Object {$_.Message -match "-enc|encodedcommand|IEX|DownloadString"} |
  Select-Object -First 50 TimeCreated, Message | Format-List

# Linux：最近24h新增的计划任务
find /etc/cron* /var/spool/cron -type f -mtime -1 -ls 2>/dev/null

# 网络：非常规端口外连（假设C2）
# 在出口防火墙/NDR上查询：目标端口 not in (443,80,53,123) 且持续连接>5分钟
```

### 11.5 猎捕成熟度与工具
```
成熟度0：基于告警（IOC驱动，被动）
成熟度1：基于IOC+日志查询（半主动）
成熟度2：基于假设+TTP（主动，本方法论的日常形态）
成熟度3：基于行为基线+ML异常（数据驱动）
工具：Velociraptor、Elastic/OSQuery、Sigma、YARA、BloodHound（反向防御）、EDR狩猎API
```

