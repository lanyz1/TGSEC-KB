---
name: subdomain-enum-takeover
description: "子域名枚举与DNS接管检测时使用。触发: 子域名枚举, 子域爆破, subdomain, DNS接管。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, recon, subdomain, dns, takeover, surveyengine-absorbed]
    related_skills: [site-recon-bypass, space-mapping-engine-recon, cdn-origin-tracing-v51, surveyengine-knowledge-pack]
---

# 子域名枚举与 DNS 接管

来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\subdomain-enum\SKILL.md`)。

## 触发条件
- 子域名枚举/爆破/发现、Subfinder/Amass/OneForAll/Sublist3r
- DNS 接管(subdomain takeover)、证书透明度(CT/crt.sh)
- DNS 历史(MX/TXT/NS)、旁站发现/同 IP 站

## 1. 被动枚举(不发 DNS 请求)
```bash
# Subfinder
subfinder -d target.com -o subdomains.txt
subfinder -d target.com -all -o subdomains.txt -v   # 多数据源(填 API key 更全)
# 配置文件 ~/.config/subfinder/provider-config.yaml: Shodan/Censys/SecurityTrails/VirusTotal/GitHub key

# Amass(最全面较慢)
amass enum -passive -d target.com -o subs.txt
amass enum -d target.com -r 8.8.8.8,1.1.1.1

# OneForAll(中文功能全)
git clone https://github.com/shmilylty/OneForAll.git && cd OneForAll
pip install -r requirements.txt
python3 oneforall.py --target target.com run   # 结果 results/target.com.csv

# crt.sh 证书透明度(零依赖首选)
curl -s "https://crt.sh/?q=%.target.com&output=json" | \
  jq -r '.[].name_value' | sort -u | grep -v '[*]' > ct_subdomains.txt
```

## 2. 主动 DNS 爆破
```bash
dnsx -l wordlist.txt -d target.com -o dnsx_results.txt -r 8.8.8.8 -rl 500
# massdns: massdns -r resolvers.txt -t A -o S -w out.txt brute_list.txt
# ffuf: ffuf -w subdomains-top1million-5000.txt -u http://FUZZ.target.com -mc 200,301,302,403
# 常用字典: SecLists /Discovery/DNS/: subdomains-top1million-110000.txt / -5000.txt / dns-Jhaddix.txt
```

## 3. DNS 历史与旁站
```bash
# SecurityTrails(API key)
curl -s "https://api.securitytrails.com/v1/domain/target.com/subdomains" -H "APIKEY: <key>" | jq '.subdomains[]'
# VirusTotal
curl "https://www.virustotal.com/vtapi/v2/domain/report?apikey=<REDACTED>" | jq '.subdomains[]'
# 同 IP 旁站
curl "https://api.hackertarget.com/reverseiplookup/?q=1.2.3.4"
```

## 4. 存活探测与指纹
```bash
cat subdomains.txt | httpx -silent -o live_hosts.txt -threads 50 -timeout 5
cat subdomains.txt | httpx -silent -title -tech-detect -status-code -o live_full.txt
# httprobe: cat subdomains.txt | httprobe | sort -u > live.txt
```

## 5. DNS 接管检测(Subdomain Takeover)
**原理**: 子域 CNAME 指向已注销/未认领第三方服务(GitHub Pages/Heroku/S3/Shopify/Fastly)。
```bash
subjack -w subdomains.txt -t 100 -timeout 30 -o takeover.txt -ssl
subzy run --targets subdomains.txt --verify-ssl
nuclei -l subdomains.txt -t ~/nuclei-templates/takeovers/ -o takeover_nuclei.txt
```
**手工确认**:
```bash
dig CNAME sub.target.com   # 看是否指向第三方
```
- GitHub Pages: "There isn't a GitHub Pages site here."
- Heroku: "No such app";Fastly: "Fastly error: unknown domain";S3: "NoSuchBucket"
- 认领验证(GitHub Pages → fork 仓库 → Settings → Pages → 绑定该域名)

## 6. 完整流程串联(一键)
```bash
domain="target.com"
subfinder -d $domain -o subs_sf.txt -all -silent
amass enum -passive -d $domain -o subs_amass.txt 2>/dev/null
curl -s "https://crt.sh/?q=%.${domain}&output=json" | jq -r '.[].name_value' | grep -v '[*]' | sort -u > subs_ct.txt
cat subs_sf.txt subs_amass.txt subs_ct.txt | sort -u > all_subs.txt
cat all_subs.txt | httpx -silent -status-code -title -tech-detect -o live_hosts.txt
subjack -w all_subs.txt -t 50 -timeout 30 -o takeover.txt -ssl
```

## Pitfalls
- **泛解析过滤**: 目标域名泛解析 *.domain 全回同 IP → DNS 爆破结果全是假的,必须过滤
- 证书 SAN 常暴露隐藏 vhost: `openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -text | grep -A3 "Subject Alternative Name"`
- 本机 v2rayN TUN 时 socket 直连全端口假 OPEN → 存活判定以 httpx 业务响应/Censys 为准
- FOFA/Shodan 额度省着用: 先被动(零成本)再主动爆破
- 旁站≠同库同业务,验证 HTTP 行为是否独立应用
