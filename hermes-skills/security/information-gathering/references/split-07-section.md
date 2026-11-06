## 六、主动侦察与隐蔽性

### 6.1 代理池与出口 IP 轮换
```bash
# 目的：多出口 IP 分散流量特征，避免单一 IP 被封/被溯源
# 方案：商业代理池（按国家/城市选出口） / 住宅代理（更隐蔽） / 自建跳板 VPS
# 工具：proxychains / httpx -proxy / nuclei -proxy / ffuf -x

httpx -l targets.txt -proxy http://proxy:8080
nuclei -l alive.txt -proxy http://proxy:8080 -rl 5

# DNS 层隐蔽：使用公共/第三方 resolver，不直接向目标 NS 发包（dnsx -r 8.8.8.8,1.1.1.1）
```

### 6.2 指纹伪装
```bash
# HTTP 头伪装（模拟真实浏览器）
# 统一 UA 池：Chrome/Edge/Safari 常见版本轮换
httpx -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/126.0"
# 补全常见头：Accept/Accept-Language/Referer 与浏览器一致，避免畸形请求特征

# TLS 指纹（JA3）与 HTTP2 指纹（部分高级 WAF 检测）
# 使用 curl-impersonate / 浏览器自动化（无头 Chrome）规避 TLS 指纹识别

# 扫描工具本身特征（masscan/nmap 的默认 payload 可被 IDS 特征库识别）
# 重要目标改用自研/改造扫描器或降低发包特征
```

### 6.3 低频扫描与速率控制
```bash
# 原则：总量可控、速率低调、时间拉长
nmap -sS -p- -T2 --min-rate 200 target.com        # 低速率全端口
nuclei -l alive.txt -rl 10 -c 5 -pause 30s        # 每秒10请求上限
ffuf -u https://target.com/FUZZ -w wordlist.txt -rate 20   # 限速

# 扫描窗口避开业务高峰（白天上班时间流量混杂，夜晚扫描特征明显）
# 先小样本验证再全面铺开；每个目标之间随机暂停，避免机械节奏
```

### 6.4 端口扫描策略
```bash
# 两段式：masscan 快速定位开放端口 → nmap 精准识别
masscan -p1-65535 --rate=10000 target.com -oL ports.txt
ports=$(awk -F' ' '{print $3}' ports.txt | cut -d'/' -f1 | tr '\n' ',')
nmap -sV -sC -p $ports target.com -oN nmap.txt

# 常见高风险端口（直接对应漏洞面）
# 6379 Redis / 9200 ES / 27017 Mongo / 11211 Memcached / 7001 WebLogic
# 2375 Docker / 10250 kubelet / 6443 k8s / 9090 Prometheus / 2181 Zookeeper
# 5601 Kibana / 8161 ActiveMQ / 4848 GlassFish / 10000 Webmin
# UDP 重点：53/161(SNMP)/123(NTP反射)/500(IPsec)/623(IPMI)
nmap -sU -p 53,161,162,500,623 --top-ports 20 target.com

# 内网资产常映射到外网非常规端口 → 全端口扫描是红队标配（很多"少见的端口"=内网系统）
```

### 6.5 服务识别与漏洞预判
```bash
# Nmap 脚本批量（信息面优先）
nmap --script=http-title,http-headers,ssl-enum-ciphers,http-enum -sV target.com
nmap --script=dns-zone-transfer,smb-enum-shares,snmp-info target.com

# 指纹→漏洞预判：识别出版本后立即关联 CVE/EXP
# 服务版本 → nuclei 模板 / searchsploit 匹配 → 打点清单
nuclei -l alive.txt -severity critical,high -t ~/nuclei-templates/ -rl 20

# 注意：漏洞扫描阶段已属高暴露动作，务必在授权+隐蔽性评估后执行
```

