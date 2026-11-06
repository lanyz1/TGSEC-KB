## 三、内网网络信息收集

### 3.1 存活主机探测
```bat
:: 内置命令(不出网/无工具环境)
for /L %I in (1,1,254) DO @ping -w 1 -n 1 192.168.1.%I | findstr "TTL="
:: NetBIOS(可拿到主机名/用户名/MAC)
nbtscan.exe 192.168.1.0/24
:: ARP扫描(本机同网段,快且不易被发现)
arp-scan -l / Invoke-ARPScan.ps1 -CIDR 192.168.1.0/20
:: nmap存活探测(大并发)
nmap -sP --min-hostgroup 1024 --min-parallelism 1024 -iL ip.txt -oG alive.txt
:: UDP关键口(53/137/161)扫存活
nmap -sU -p 53,137,161 192.168.1.0/24
```

### 3.2 端口扫描与服务识别
```bash
# 全端口快速(通过代理)
proxychains nmap -sT -Pn -p- --min-rate 2000 10.10.10.0/24 -oN full.txt
# 关键端口定向
nmap -sT -Pn -p 21,22,23,53,80,135,139,445,443,1433,1521,3306,3389,
  5432,5900,6379,7001,8080,8443,9200,11211,2181,27017,5000,11434,19530 10.10.10.0/24
# 服务指纹
nmap -sT -Pn -sV -p 445,1433,3306,6379 10.10.10.10
# UDP服务(SNMP/Syslog等)
nmap -sU -sV -p 53,161,137,139,500,1617,1900 10.10.10.10
```

### 3.3 常见端口高危服务速查（内网横向重点）
| 端口 | 服务 | 攻击面 |
|------|------|--------|
| 445/139 | SMB | MS17-010/SMBGhost、弱口令、未授权共享、PTH |
| 3389 | RDP | 弱口令、BlueKeep(CVE-2019-0708)、NLA绕过 |
| 22 | SSH | 弱口令、私钥复用、隧道代理 |
| 1433 | MSSQL | sa弱口令、xp_cmdshell提权、链接服务器 |
| 3306 | MySQL | 弱口令、UDF提权、未授权 |
| 6379 | Redis | 未授权RCE(写公钥/计划任务/主从复制) |
| 27017 | MongoDB | 未授权访问 |
| 9200 | Elasticsearch | 未授权、RCE(CVE-2015-1427) |
| 11211 | Memcached | 未授权、DRDoS反射 |
| 2181 | ZooKeeper | 未授权访问(配置/会话泄露) |
| 7001/7002 | WebLogic | 反序列化(T3/IIOP)、弱口令 |
| 8080/8089 | Tomcat/JBoss/Jenkins | 弱口令、反序列化、后台部署 |
| 1099 | Java RMI | 反序列化 |
| 873 | Rsync | 匿名访问、文件读取 |
| 50000 | SAP | 远程代码执行 |
| 8069 | Zabbix | 弱口令、监控命令执行 |
| 2181/9092 | Kafka | 未授权、消息窃取 |
| **11434** | **Ollama** | **LLM服务未授权（见12.1）** |
| **19530/8000** | **向量库/推理服务** | **AI服务未授权（见12.1/12.2）** |

### 3.4 综合扫描工具（内网渗透标配）
```bash
# fscan（最常用：存活+端口+弱口令+Web漏洞+MS17-010一站式）
fscan.exe -h 10.10.10.0/24                          # 全模块
fscan.exe -h 10.10.10.0/24 -nobr -nopoc             # 静默模式(减少流量)
fscan.exe -h 10.10.10.0/24 -m smb -pwd password     # 指定模块/密码碰撞
fscan.exe -h 10.10.10.0/24 -rf id_rsa.pub           # redis写公钥
fscan.exe -hf ip.txt -o result.txt                  # 批量导入+结果输出
# LadonGo（一键C/B/A段：存活/指纹/爆破/高危漏洞/远程执行）
Ladon 10.10.10.8/24 MS17010 ; Ladon 10.10.10.8/24 PortScan
# netspy（网段发现,适合大内网横向扩张）
netspy is                       # icmp全自动探测 10/172.16/192.168 段
netspy ts -p 22 -p 3389         # tcp探测
# Yasso（红队辅助工具集,含代理与并发）
Yasso.exe all -H 10.10.10.1/24
```

### 3.5 网段发现与扩张（高级）
```
# 网段来源：路由表、ARP缓存、DHCP分配、DNS记录(domain controllers)、
# 服务器多网卡、云VPC网段、容器网络(172.17.0.x/10.244.x.x)
# 多网段主机 = 跳板机首选
# 大内网：按 网关存活→B段/C段 逐层推进,先打管理网段(运维/堡垒机/监控)再打业务网段
# AI辅助：把路由表/ARP/探测结果给LLM生成网段拓扑图与推进顺序建议
```

