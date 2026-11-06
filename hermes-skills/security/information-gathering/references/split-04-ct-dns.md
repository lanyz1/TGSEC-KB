## 三、证书透明度（CT）与 DNS 历史

### 3.1 CT 日志原理与新数据源
证书透明度（RFC 6962/9162）要求所有公开可信 CA 将签发的每张证书写入公开可验证日志。**证书的 SAN 字段列出全部覆盖域名**，等于目标自己"投喂"子域名清单，且零触达。

**2025-2026 新趋势：**
- 自 2013 年以来已累计记录 **25 亿+ 张证书**，Let's Encrypt 每天签发约 1000 万张
- Chrome（2018）、Apple（系统级）、**Firefox 135（2025-02）** 三大浏览器全部强制 CT
- 蜜罐研究：证书签发后平均 **73 秒** 内即被扫描流量触达——CT 是攻击者发现新资产的第一时效来源
- 证书内嵌邮箱（CA 邮箱）可用于反查同一申请者

**核心查询源：**
```bash
# crt.sh（Sectigo 维护，PostgreSQL 全文索引，最常用）
curl -s "https://crt.sh/?q=%25.target.com&output=json" | jq -r '.[].name_value' | sort -u

# Censys 证书搜索（支持更精确字段过滤）
# https://search.censys.io/certificates?q=names%3A+target.com

# Entrust CT 搜索 / Google Transparency Report / certspotter
curl -s "https://api.certspotter.com/v1/issuances?domain=target.com&include_subdomains=true&expand=dns_names" | jq -r '.[].dns_names[]' | sort -u
```

### 3.2 CT 聚合与监控工具
```bash
# CTFR（纯 CT 收集，秒级）
python3 ctfr.py -d target.com -o subs.txt

# Sublert（CT 持续监控：新签发域名 → Slack 推送，抢占新资产第一落点）
python3 sublert.py --domains target.com --slack_api_token xxx
# 实战价值：目标刚部署的 staging/内测环境，未加固且未暴露，是高危打点入口

# 与主动枚举互补：CT 发现的是"真实使用过"的域名，字典爆破发现的是"可能使用"的域名
```

### 3.3 DNS 历史记录
```bash
# 历史解析记录（CDN 上线前的真实 IP、旧服务器）
# SecurityTrails / DNSDB（Farsight）/ ViewDNS.info / 微步在线(威胁情报社区)
# 场景：某域名解析到 Cloudflare 之前直连源站 IP → 该 IP 可绕过 CDN

# 微步在线 API（国内数据全）
curl -s "https://api.threatbook.cn/v3/domain/query?apikey=<REDACTED>" | jq .

# passive DNS（被动 DNS 数据，覆盖历史解析对）
# RiskIQ PassiveTotal / 微步 PDNS / DNSGrep
curl -s "https://dns.bufferover.run/dns?q=.target.com" | jq -r '.FDNS_A[]' | head
```

### 3.4 DNS 记录深度解析
```bash
# 全记录类型（每个都可能是攻击入口）
dig target.com A AAAA MX NS TXT CNAME SOA SRV CAA
dig _autodiscover._tcp.target.com SRV     # 邮件自动发现
dig _ldap._tcp.target.com SRV             # 域控线索
dig _sip._tcp.target.com SRV              # VoIP
dig _vlmcs._tcp.target.com SRV            # KMS激活服务器（可刷授权）

# TXT 记录高风险点
# SPF/DKIM 泄露邮件基础设施；verification token（Google/Apple/Bing）可用于冒充验证
# "v=spf1 include:spf.xxx.com" 反查第三方邮件服务商

# CNAME 指向云服务 = 子域名接管候选
dig cname staging.target.com
# 返回 .s3.amazonaws.com / .blob.core.windows.net / .cloudfront.net / .herokuapp.com 等 → 见第五章

# AXFR 区域传送（老而有效）
dig axfr target.com @ns1.target.com
dnsrecon -d target.com -t axfr
```

