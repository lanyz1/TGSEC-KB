## 四、子域名枚举（被动+主动全维度）

### 4.1 被动数据源与聚合
```bash
# 主流被动源
# VirusTotal / SecurityTrails / Censys / Shodan / ThreatCrowd / AlienVault OTX
# 国内：FOFA / Hunter(奇安信) / Quake(360) / 微步 / ZoomEye
# ProjectDiscovery Chaos（聚合数千赏金项目数据，含独有域名）

# 工具（多源聚合）
subfinder -d target.com -silent | anew subs.txt          # 40+ 被动源
amass enum -passive -d target.com -o amass.txt           # 最全面（含图谱输出）
assetfinder target.com
findomain -t target.com
# 新一代：subdominator（73 个被动源，Python3.13+，异步高性能）
subdominator -d target.com -o subs.txt

# 空间引擎语法（国内目标必备）
# FOFA: domain="target.com" || cert="target.com" || icp="目标备案号"
# Hunter: domain="target.com" && web.title="目标"
# Quake: domain: "target.com"
# 空间引擎还能直接给出：IP、端口、指纹、国家、ASN → 一步到位
```

### 4.2 字典爆破（主动）
```bash
# 高质量词表
# seclists/Discovery/DNS/（best-dns-wordlist.txt、deepmagic 等）
# bitquark-subdomains-top100000.txt
# 六位数/行业定制：按目标行业生成（dev/staging/test/uat/oa/vpn/mail/sso）

dnsx 解析验证：
puredns bruteforce subdomains-top100000.txt target.com -r resolvers.txt

gobuster dns -d target.com -w subdomains.txt
dnsrecon -d target.com -D subdomains.txt -t brt
```

### 4.3 变体生成（Permutation）
基于已知子域自动衍生新词（红队效率倍增器）：
```bash
# alterx（ProjectDiscovery）：根据已有子域生成排列变体
cat subs.txt | alterx -silent | dnsx -silent | anew final-subs.txt

# 语义变体：api→api-dev→api-test→api-uat→api-staging
# 品牌变体：公司英文名/拼音/缩写 + dev/test/内网 等后缀
```

### 4.4 解析验证与资产归一
```bash
# 全部候选 → 解析 → 探活 → 去重
cat subs.txt | dnsx -silent -a -resp -cdn | tee resolved.txt
cat resolved.txt | awk '{print $1}' | httpx -silent -title -tech-detect -status-code -cdn -json | tee alive.json

# 通配符过滤：*.target.com 解析到同一 IP 时需过滤泛解析噪音
dnsx -w wildcard-check.txt 对比解析结果

# 注意：先验证再扫描，避免对 CNAME 指向第三方（GitHub Pages/云存储）的域名做无意义扫描
```

