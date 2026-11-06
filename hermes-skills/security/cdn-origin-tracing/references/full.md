# cdn-origin-tracing — 全文续篇

> 主卡保留前 13 节；本文件从第 14 节起。原文件：`/root/.hermes/skills/security/cdn-origin-tracing/SKILL.md`

## 溯源方法完整矩阵（v5.0 深度优化 · 50 种方法）

| 排名 | 方法 | 成功率 | 速度 | 自动化 | 关键工具 |
|------|------|--------|------|--------|----------|
| 1 | SSL 证书透明度日志 | 85% | 秒级 | 是 | crt.sh, Censys, CertSpotter |
| 2 | 子域名枚举 | 80% | 分钟级 | 是 | Subfinder, Amass, OneForAll |
| 3 | 历史 DNS 记录 | 75% | 秒级 | 是 | SecurityTrails, HackerTarget, VirusTotal |
| 4 | 网络空间搜索引擎 | 70% | 秒级 | 是 | Shodan, FOFA, ZoomEye, Censys, Quake |
| 5 | CNAME 解析链追踪 | 70% | 秒级 | 是 | dig |
| 6 | CDN IP 范围反查 | 65% | 分钟级 | 部分 | cdn_ranges.py, ASN, bgp.he.net |
| 7 | SPF 邮件记录 | 60% | 秒级 | 是 | dig |
| 8 | MX 邮件服务器关联 | 55% | 秒级 | 是 | dig MX |
| 9 | Host 头验证 | 55% | 分钟级 | 是 | curl, httpx, cdn_tracer.py |
| 10 | 第三方服务 ID 关联 | 50% | 分钟级 | 否 | Google Analytics, 百度统计 |
| 11 | 网站功能泄露 | 50% | 分钟级 | 否 | RSS, robots.txt, sitemap |
| 12 | ICP 备案查询 | 45% | 秒级 | 否 | beian.miit.gov.cn |
| 13 | XML-RPC Pingback 泄露 | 40% | 秒级 | 是 | curl, nc |
| 14 | 邮件头分析 | 45% | 分钟级 | 否 | 邮件客户端, eml_parser |
| 15 | Favicon 哈希匹配 | 40% | 分钟级 | 部分 | Shodan, FOFA, mmh3 |
| 16 | DNS ANY / 搜索引擎缓存 | 35% | 秒级 | 部分 | dig ANY, Wayback Machine |
| 17 | IPv6 解析 | 25% | 秒级 | 是 | nslookup -type=AAAA |
| 18 | DNS 区域传送 | 15% | 秒级 | 是 | dig AXFR |
| 19 | AltDNS 排列 + 泛解析过滤 | 45% | 分钟级 | 是 | altdns, dnsgen |
| 20 | 多 DNS 解析器交叉验证 | 60% | 秒级 | 是 | dnsx, massdns |
| 21 | CSP / CORS 头泄露 | 40% | 秒级 | 是 | curl |
| 22 | CDN 回源 IP 段利用 | 55% | 分钟级 | 是 | CDN 文档, nmap |
| 23 | JavaScript / API 端点泄露 | 45% | 分钟级 | 半自动 | curl, grep, JS 解析 |
| 24 | 被动 DNS 数据聚合 | 80% | 秒级 | 是 | 多源聚合 |
| 25 | 证书颁发机构 (CA) 分析 | 50% | 秒级 | 是 | crt.sh, openssl |
| 26 | HTTP 重定向链分析 | 35% | 秒级 | 是 | curl -L |
| **27** | **Cloudflare Tunnel/cloudflared 绕过** | **35%** | 分钟级 | 半自动 | dig, cloudflared 配置泄露 |
| **28** | **Cloudflare Pages/Workers/R2 源站暴露** | **45%** | 秒级 | 是 | crt.sh, *.pages.dev 枚举 |
| **29** | **Serverless / Lambda@Edge 源站泄露** | **40%** | 分钟级 | 半自动 | 日志触发, 错误页 |
| **30** | **HTTP/3 (QUIC) 源站发现** | **30%** | 秒级 | 是 | curl --http3, nmap |
| **31** | **TLS 1.3 ECH / SNI 操纵** | **25%** | 秒级 | 是 | openssl, curl --doh-url |
| **32** | **容器 / K8s Ingress 暴露** | **40%** | 分钟级 | 半自动 | Shodan, FOFA, Ingress 端口 |
| **33** | **CI/CD 管道泄露 (.git/Actions)** | **35%** | 分钟级 | 是 | .git 泄露, GitHub dork |
| **34** | **云存储桶枚举 (S3/OSS/COS/OBS)** | **50%** | 分钟级 | 是 | lazarus, bucket_finder |
| **35** | **WebSocket 长连接源站** | **30%** | 分钟级 | 是 | wscat, websocat |
| **36** | **缓存投毒/欺骗取源站** | **25%** | 分钟级 | 半自动 | 路径操纵, Header 注入 |
| **37** | **HTTP 请求走私 (CDN↔源站)** | **20%** | 分钟级 | 半自动 | smuggler, CL.TE/TE.CL |
| **38** | **GraphQL Introspection 泄露** | **35%** | 秒级 | 是 | curl, graphw00f |
| **39** | **SSE / Server-Sent Events 源站** | **25%** | 分钟级 | 是 | curl, EventSource |
| **40** | **移动 App / 小程序硬编码 IP** | **45%** | 分钟级 | 是 | jadx, apktool, Frida |
| **41** | **DNS Rebinding → SSRF 源站发现** | **40%** | 分钟级 | 半自动 | singularity, rbndr |
| **42** | **CDN 缓存清除/预热回源泄露** | **35%** | 分钟级 | 是 | CDN 管理面板, API |
| **43** | **HTTP/2 HPACK 压缩侧信道** | **25%** | 分钟级 | 半自动 | h2load, h2spec |
| **44** | **Anycast IP 去匿名化** | **30%** | 分钟级 | 是 | 多地 ping, 全球 VPS |
| **45** | **CDN Origin Shield / 中间源绕过** | **35%** | 分钟级 | 半自动 | 请求路由操纵 |
| **46** | **速率限制差分分析** | **30%** | 分钟级 | 半自动 | ffuf, 并发脚本 |
| **47** | **eBPF/XDP 源站旁路检测** | **20%** | 分钟级 | 否 | bpftrace, cilium |
| **48** | **跨域资源计时侧信道** | **25%** | 分钟级 | 半自动 | 浏览器 Performance API |
| **49** | **源站 IP 漂移实时追踪** | **50%** | 分钟级 | 是 | cdn_ranges monitor, cron |
| **50** | **CDN 回源认证绕过 (Signed URL/Token)** | **30%** | 分钟级 | 半自动 | Hashcat, 签名分析 |

---

---

## 第一阶段：CDN 识别（精准判定）

### 判断方法

```bash
# 1. 多地 Ping（最可靠）
# 国内: https://ping.chinaz.com/
# 国际: https://check-host.net/
# 判断标准: 不同地区返回不同 IP → 有 CDN

# 2. 在线 CDN 检测
# IPIP: https://tools.ipip.net/cdn.php
# Get-Site-IP: https://get-site-ip.com/
# CDNPlanet: https://www.cdnplanet.com/tools/cdnfinder/

# 3. 命令行检测
nslookup target.com
# 多个 IP 段 → 可能 CDN；单 IP → 可能无 CDN 或 Anycast

# 4. 响应头检测
curl -sI https://target.com | grep -iE "(cf-ray|cf-cache|x-cache|via:|x-amz-cf|server: cloudflare|x-sucuri|x-akamai)"
# cf-ray → Cloudflare; x-amz-cf-id → AWS CloudFront; x-cache → Akamai/Fastly
# via: → 通用代理; x-sucuri → Sucuri; x-akamai → Akamai
```

> **完整 CDN IP 段库（国际 / 国内 / ASN 实时反查 · CIDR 格式）** → `references/cdn-ip-ranges-asn.md`
> 本技能工具已内置 51 厂商 / 213 静态段并自动加载深度数据（实测 52,108 段），无需手抄。

---

## 第四阶段：快速组合拳（3 分钟最高成功率）

```bash
#!/bin/bash
# 快速溯源 - 3 分钟高成功率流程
TARGET=${1:?Usage: $0 target.com}

echo "[*] 快速溯源: $TARGET"
echo ""

# 步骤1: crt.sh 证书查询（30秒）
echo "[1/5] crt.sh 证书查询..."
IPS=$(curl -s "https://crt.sh/?q=${TARGET}&output=json" 2>/dev/null | jq -r '.[] | .name_value, .common_name' 2>/dev/null | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | sort -u)
echo "  发现 $(echo "$IPS" | wc -l) 个候选 IP"

# 步骤2: 子域名枚举（60秒）
echo "[2/5] 子域名枚举..."
for sub in mail ftp smtp pop3 imap webmail cpanel whm admin dev staging test direct origin backend vpn mysql ssh static img upload api m mobile; do
  ip=$(dig A "${sub}.${TARGET}" +short 2>/dev/null | grep -E '^[0-9]' | head -1)
  [ -n "$ip" ] && IPS="$IPS"$'\n'"$ip"
done
echo "  累计 $(echo "$IPS" | sort -u | wc -l) 个候选 IP"

# 步骤3: 历史 DNS（30秒）
echo "[3/5] 历史 DNS 查询..."
HIST_IPS=$(curl -s "https://api.hackertarget.com/hostsearch/?q=${TARGET}" 2>/dev/null | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}')
IPS="$IPS"$'\n'"$HIST_IPS"
echo "  累计 $(echo "$IPS" | sort -u | wc -l) 个候选 IP"

# 步骤4: SPF + MX（15秒）
echo "[4/5] SPF/MX 查询..."
IPS="$IPS"$'\n'$(dig TXT "$TARGET" +short | grep -oP 'ip4:\K[^\s]+')
IPS="$IPS"$'\n'$(dig MX "$TARGET" +short | awk '{print $NF}' | while read mx; do dig A "$mx" +short; done)

# 过滤内网IP和去重
IPS=$(echo "$IPS" | sort -u | grep -vE '^(0\.|127\.|10\.|172\.1[6-9]|172\.2[0-9]|172\.3[0-1]|192\.168\.)')

# 步骤5: 批量验证（60秒）
echo "[5/5] Host 头验证 $(echo "$IPS" | wc -l) 个候选..."
VERIFIED=""
for ip in $IPS; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -k -H "Host: $TARGET" "https://$ip" --connect-timeout 3 2>/dev/null)
  [ "$code" != "000" ] && VERIFIED="$VERIFIED"$'\n'"$ip → HTTP $code"
done

echo ""
echo "=== 结果 ==="
echo "$VERIFIED" | sort -u | grep -v '^$'
echo ""
echo "[*] 完成！对已验证 IP 进行 TLS 指纹对比确认源站"
```

---

---

## 常见失败原因与突破策略

| 失败原因 | 表现 | 突破策略 |
|----------|------|----------|
| 证书全部由 CDN 签发 | crt.sh 无候选 IP | 使用子域名枚举 + 历史 DNS |
| 所有子域名都走 CDN | 枚举无结果 | 查 MX/SPF + 第三方服务关联 |
| 历史 DNS 无记录 | 域名一直用 CDN | 网络空间引擎 + 证书序列号关联 |
| 源站仅允许 CDN IP 访问 | 直接 IP 访问被拒绝 | 伪造 X-Forwarded-For + CDN 回源 IP（方法22） |
| 源站使用 SNI 过滤 | curl 返回 421/400 | 使用正确的 SNI（域名）+ 尝试不同路径（方法31） |
| Cloudflare Authenticated Origin Pulls | 直接 IP 返回 403 | 需客户端证书，改用被动方法（Censys/Shodan 证书反查） |
| 源站 IP 频繁变更 | IP 验证后失效 | 持续监控 + 定期重新溯源（见监控章节） |
| 容器/K8s 环境 | 源站 IP 是动态的 | 查 Ingress/LB IP + Traefik dashboard（方法32） |
| **Cloudflare Tunnel 接入** | 无公网源站 IP | 方法27（配置泄露）+ 同账户兄弟域名 + 方法28 |
| **Serverless 架构** | 无固定源站 | 方法29（Lambda@Edge ARN）+ 方法28（pages.dev） |
| **证书钉刺 (Pinning)** | 直连 TLS 失败 | 提取 App 钉刺哈希反查 + 被动方法（指纹4） |
| **Host 头返回 200 但疑似误报** | 可能是 CDN 节点/共享主机 | JA4S + HTTP/2 指纹交叉验证（现代指纹章节） |
| **ECH 加密 SNI** | SNI 不可见 | dig HTTPS 取 ipv4hint + ECH retry_configs（方法31） |
| **蜜罐陷阱** | 源站异常宽松/行为不一致 | 蜜罐识别清单 + 多源交叉 + 降权处理 |
| **IPv6 源站** | 仅查 IPv4 漏掉 | dig AAAA + 方法17 + IPv6 Nmap |

---

---

## 注意事项

1. **合法性**：仅用于授权测试、自有资产验证或安全研究
2. **组合使用**：单方法可能误报，建议 3 种以上方法交叉验证
3. **Host 头**：验证时务必设置正确的 Host 头
4. **HTTPS 优先**：优先使用 HTTPS 连接候选 IP
5. **CDN 范围过滤**：先排除 CDN 节点 IP，再验证
6. **源站访问控制**：有些源站仅允许 CDN 回源 IP 访问，需伪造来源
7. **持续监控**：源站 IP 可能变更，建议定期重新溯源
8. **(v5.0) 必做指纹验证**：Host 头返回 200 不等于源站，必须叠加 JA4S/HTTP2 指纹
9. **(v5.0) 警惕蜜罐**：异常宽松的源站需交叉验证，避免落入蜜罐
10. **(v5.0) 贝叶斯评分优先**：用 P≥0.95 阈值替代经验判断，降低主观误判

---

> **评分分工补充（v4.0 吸收）**：bash 100 分制基线（crt.sh +25 / 历史DNS +20 / 子域名 +15 / SPF +10 / MX +10 / Host头验通 +20；**80+ 几乎确定 · 60-79 很可能 · 40-59 有可能 · <40 再验证**）用于无 Python 环境 / 单目标快速判定；>20 个候选或要排序出报告时改用贝叶斯（`references/verification-and-scoring.md`），避免 crt.sh+Censys 同源证据重复加权虚高。两者都必须叠加 JA4S/HTTP2 指纹才可结案。

---

## 相关技能

- **recon-and-methodology** — 信息收集方法论
- **subdomain-takeover** — 子域名接管
- **waf-bypass-techniques** — WAF 绕过技术
- **ssrf-server-side-request-forgery** — SSRF 可配合 CDN 溯源（命中 cloudflared metrics）
- **dns-rebinding-attacks** — DNS 重绑定绕过 CDN
- **http-request-smuggling** — 请求走私配合 CDN↔源站边界
- **cloud-security** — 云存储桶 / Serverless / K8s 暴露面
- **tls-fingerprinting** — JA3/JA4 与反指纹
- **mobile-app-pentest** — APK/IPA 逆向取硬编码 IP
- **hack** — 主路由入口

<!-- 数据源：CT Logs, Shodan, Censys, FOFA, ZoomEye, Quake, SecurityTrails, VirusTotal, AlienVault, kaeferjaeger, BGP.HE, urlscan, DNSlytics, 实战经验 · 方法论 v5.0 · 50 种方法 · 30+ 厂商绕过 · JA4/HTTP2 现代指纹验证 · 贝叶斯置信度 · Python Pipeline · 反规避 + 持续监控 · DNS Rebinding · HPACK侧信道 · Anycast去匿名化 · Origin Shield绕过 · 速率限制差分 · 源站IP漂移追踪 -->

<!-- 原文件 3895-4000 行内嵌了一份与本库 cdn-origin-tracing-v51 重复的精炼版全文，拆分时去重删除。 -->

## v5.2 本库实战增量（已拆为分册）

> 源站落地 · vhost 枚举 · CF 429/1015/cf_clearance 对抗 · 开发端口 · 换面与静默纪律 · HTTPS RR/ECH ipv4hint
> **按需读取**: [references/origin-landing-and-edge-evasion.md](references/origin-landing-and-edge-evasion.md)
> **新增工具**: `cf_evasion.py` (detect / ct429 / origin / backoff) · `cdn_tracer.py` 阶段 4b (HTTPS RR / ECH ipv4hint)

