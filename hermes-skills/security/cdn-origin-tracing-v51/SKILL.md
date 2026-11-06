---
name: cdn-origin-tracing-v51
description: "CDN/WAF真实IP溯源时使用。触发: CDN溯源, 找真实IP, 绕过CDN, 源站IP, origin IP。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, cdn, origin, cloudflare, tracing, surveyengine-absorbed]
    related_skills: [cloudflare-bypass, site-recon-bypass, space-mapping-engine-recon, surveyengine-knowledge-pack]
---

# CDN/WAF 真实 IP 溯源 — 深度实战手册 v5.1(测绘引擎吸收)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。**完整手册已在库内**: 读兄弟卡 `cdn-origin-tracing`(SKILL.md 索引 + `references/` 13 个分册: 50 方法详解 / 30+ 厂商绕过 / 指纹验证与评分 / IP 段库 / 工具箱 CLI / 自动化脚本 / 引擎 Cookbook / 反规避监控 / 案例工具)。

**版本谱系(勿重复吸收)**: 本卡 = 测绘引擎 v5.1(50 方法 / 30+ 厂商)。外部分享的 v4.0 手册(26 方法 / 18 厂商) 是本卡前身 — 1478 行逐行差分仅 69 行不匹配且全是格式/措辞差异,唯一实质缺口是 v4.0 的 bash 加权评分基线(已并入上方)。再收到 v4.0 报告直接跳过,只需核对厂商 IP 段/ASN 是否更新。

**结构(已重构)**: 兄弟卡 `cdn-origin-tracing` 原 4075 行 / 135K 已拆为 SKILL.md(15K 索引) + `references/` 13 分册 —— 单文件不再撞 100K 硬限。**新方法论增量直接写对应分册**(方法类→`methods-*.md`、厂商类→`vendor-bypass.md`、验证评分→`verification-and-scoring.md`)，本卡只留精炼操作面与实战教训。

来源: 测绘引擎知识包吸收。**全文已在库内**: `cdn-origin-tracing` + 其 `references/`(含 30+ CDN 厂商绕过细节、反规避、案例工作流)。本卡 = 精炼操作版。

工具(已复制到本技能 scripts/):
- `cdn_tracer.py` — 端到端溯源主程序(14 阶段流水线)
- `cdn_ranges.py` — CDN IP 段库+过滤器(51 厂商/213 静态段+自动加载深度数据,首字节桶索引)
- `cdn_ip_collector.py` — 深度 IP 段收集(8 源并发,实测 52,108 段/36 厂商)
- `cdn_origin_monitor.py` — 源站漂移监控
- `internet_wide_scanner.py`、`ja3extract.py`
- 仅依赖 `requests`+标准库;openssl 可选(TLS 指纹)

## 核心原则:分层组合 + 现代指纹验证
**单方法成功率有限,分层组合拳成功率 95%+。**
```
第一层(发现)  crt.sh证书 → 子域名枚举(含AltDNS) → 历史DNS聚合 → 被动DNS多源交叉
第二层(暴露)  网络空间引擎(Shodan/Censys/FOFA) → CSP/CORS/JS端点 → 云存储桶枚举
第三层(触发)  邮件头/Pingback → 缓存投毒/请求走私 → SaaS/Serverless源站发现
第四层(验证)  Host头验证 → JA3/JA4 TLS指纹 → HTTP/2 Akamai指纹 → 页面哈希一致性
```
**Host 头返回 200 ≠ 源站**(可能是 CDN 节点或共享主机),必须 JA3/JA4 + HTTP/2 指纹交叉确认。

## 快速启动
```bash
python3 scripts/cdn_ip_collector.py            # 先深收集 CDN 段(一次)
python3 scripts/cdn_tracer.py <domain>          # 全流程 14 阶段
python3 scripts/cdn_tracer.py <domain> --verbose
python3 scripts/cdn_ranges.py <ip>              # 查单 IP 是否 CDN
python3 scripts/cdn_ranges.py --filter 候选IP.txt  # 批量过滤排除 CDN
python3 scripts/cdn_origin_monitor.py <domain>  # 漂移监控
```

## 50 种溯源方法 Top 排名(成功率)
| 排名 | 方法 | 成功率 | 关键工具 |
|---|---|---|---|
| 1 | SSL 证书透明度日志 | 85% | crt.sh, Censys, CertSpotter |
| 2 | 子域名枚举 | 80% | Subfinder, Amass, OneForAll |
| 3 | 历史 DNS 记录 | 75% | SecurityTrails, HackerTarget, VirusTotal |
| 4 | 网络空间搜索引擎 | 70% | Shodan, FOFA, ZoomEye, Censys, Quake |
| 5 | CNAME 解析链追踪 | 70% | dig |
| 6 | CDN IP 范围反查 | 65% | cdn_ranges.py, ASN, bgp.he.net |
| 7 | SPF 邮件记录 | 60% | dig |
| 8 | MX 邮件服务器关联 | 55% | dig MX |
| 9 | Host 头验证 | 55% | curl, httpx |
| 24 | 被动 DNS 数据聚合 | 80% | 多源聚合 |
| 20 | 多 DNS 解析器交叉验证 | 60% | dnsx, massdns |
| 22 | CDN 回源 IP 段利用 | 55% | CDN 文档, nmap |
| 28 | Cloudflare Pages/Workers/R2 源站暴露 | 45% | crt.sh, *.pages.dev 枚举 |
| 34 | 云存储桶枚举 | 50% | lazarus, bucket_finder |
| 40 | 移动 App/小程序硬编码 IP | 45% | jadx, apktool |
| 41 | DNS Rebinding → SSRF 源站发现 | 40% | singularity, rbndr |
| 17 | IPv6 解析 | 25% | nslookup -type=AAAA |
| 18 | DNS 区域传送 | 15% | dig AXFR |

## 第一阶段:CDN 识别(先判定有没有 CDN)
1. 多地 Ping(ping.chinaz.com / check-host.net):不同地区不同 IP → 有 CDN
2. 响应头: cf-ray→Cloudflare; x-amz-cf-id→AWS; x-cache→Akamai/Fastly; via→代理
3. `nslookup` 多 IP 段 → CDN;单 IP → 可能无 CDN 或 Anycast
4. CDNPlanet: cdnplanet.com/tools/cdnfinder/

## 第二~五阶段:溯源→验证→评分(精炼)
- **crt.sh 秒级拿证书**: `curl -s "https://crt.sh/?q=%25.<domain>&output=json"` 提取 common_name/name_value → 解析唯一 IP 段
- **CNAME 链**: `dig +short <sub> CNAME` 追到非 CDN 域名 → 解析即源站
- **历史 DNS**: SecurityTrails API / HackerTarget `https://api.hackertarget.com/hostsearch/?q=<domain>` / VirusTotal
- **IPv6**: `nslookup -type=AAAA <domain>` 很多站 AAAA 直连源站
- **SPF/MX**: `dig TXT <domain> | grep spf` — include: 里的域可能不套 CDN;MX 服务器常同机房
- **Favicon 哈希**: mmh3 哈希 → Shodan `http.favicon.hash:<hash>` / FOFA `icon_hash="<hash>"`
- **被动 DNS 多源**: SecurityTrails / PassiveTotal / Censys / FOFA 交叉
- **Host 头验证**: 候选 IP 上 `curl -H "Host: <domain>" https://<ip>/` — 返回与 CDN 同内容 → 疑似源站;再用 JA3/JA4 指纹确认
- **页面哈希一致性**: 比对候选源站页面 HTML hash 与线上(排除动态块)
- **贝叶斯评分**: 多方法命中同一 IP 加权,得分高者 = 源站(工具内已实现)。>20 个候选才用它(去相关,避免同源证书证据重复加权虚高)
- **轻量降级(bash 100 分制 · 无 Python 跳板机专用)**: 各维度命中的 IP 落盘后手算,满分 100:

```bash
score_ip() {  # 前置: crtsh_ips.txt / historical_dns.txt / subdomain_ips.txt / spf_ips.txt / mx_ips.txt
  local ip="$1" target="$2" score=0
  grep -q "$ip" crtsh_ips.txt      2>/dev/null && score=$((score+25))  # crt.sh 证书
  grep -q "$ip" historical_dns.txt 2>/dev/null && score=$((score+20))  # 历史/被动 DNS
  grep -q "$ip" subdomain_ips.txt  2>/dev/null && score=$((score+15))  # 子域名解析
  grep -q "$ip" spf_ips.txt        2>/dev/null && score=$((score+10))  # SPF ip4:
  grep -q "$ip" mx_ips.txt         2>/dev/null && score=$((score+10))  # MX 同机
  local code=$(curl -s -o /dev/null -w "%{http_code}" -k -H "Host: $target" "https://$ip" --connect-timeout 3)
  case $code in 200|301|302|403) score=$((score+20));; esac            # Host 头验通
  echo "$ip: 置信度 $score/100"
}
```

分档: **80+ 几乎确定是源站 · 60-79 很有可能 · 40-59 有可能 · <40 需再验证**。
> 注意: bash +20 / 贝叶斯 E 组 +4.0 都会高估「Host 头 200」的信号强度——**两套评分都必须叠加 JA4S/HTTP2 指纹才能结案**

## 各厂商快速绕过要点(完整 30+ 厂商 → `cdn-origin-tracing` 的 `references/vendor-bypass.md`)
- **Cloudflare**: 历史 DNS/子域/邮件头/证书透明度;cloudflared tunnel 无源站(打 tunnel 服务本身);Pages/Workers 找 `*.pages.dev` 绑定前旧源
- **阿里云/腾讯云**: ICP 备案反查(beian.miit.gov.cn)同主体其他域名常不套 CDN;对象存储 OSS/COS 直接解析
- **Akamai**: HTTP/2 指纹(响应头顺序);Origin Shield 中间源 IP 段
- 更多厂商细节(30+): 读 `cdn-origin-tracing` 的 `references/vendor-bypass.md`「各 CDN 厂商特定绕过技巧」

## 网络空间引擎高级查询(节省额度)
- Censys: `services.tls.certificates.leaf.names: "<domain>"`(新平台语法)
- Shodan: `ssl.cert.subject.cn:<domain>` / `hostname:<domain>`(网页版登录不耗 credits)
- FOFA: `cert="<domain>"` / `domain="<domain>"`(中文站覆盖强)

## 常见失败原因与突破
- 全查完无果 → 站用了 **cloudflared Tunnel / 纯 Serverless**,没有传统源站(换打应用层)
- 候选全是 CDN 段 → 用 cdn_ranges.py --filter 排除后再验证
- Host 头 200 但指纹不符 → 是共享主机/同机房邻居,继续找
- **IP 白名单型源站**(只放行平台域名,403 静默)→ 从请求特征/端口面换路,别硬绕(见 wps-casino / edgeone-origin-bypass 实战)

## 「不可溯源」快速判定(先花 10 分钟排除，别空转)
六条同时成立 ⇒ **直接结案为「源站不可被动取得」**，不要再去扫 CDN Anycast IP:
1. 被动 DNS(robtex/多源)**首条记录就是 CDN** → 从未暴露过裸 IP
2. crt.sh/certspotter **只有 CDN 通用证书**，无源站自有证书 → 走 Flexible SSL，`cert=` 引擎检索失效
3. 子域枚举 150+ 字典**全部 NXDOMAIN** → zone 扁平，无旁路
4. TXT/SPF/MX 全空 → 无 `ip4:` 泄漏
5. robots.txt / sitemap.xml 内**无绝对源站 URL**
6. CF 侧报 522/530-1016 或 200 返回面板默认页 → 见下方错误码语义
> 补第 7 条: 若源站是 **aaPanel/宝塔** 默认 vhost，用 IP 或无关键 Host 扫描只会得到默认页 ⇒ **任何测绘引擎都索引不到 vhost 内容**，`body=` 检索对本目标天然失效。别再耗引擎额度。

**扫 CDN Anycast IP 是无效动作**: 如 Cloudflare `172.67.x`/`104.21.x` 的「开放端口」只有 13 个回源白名单端口(80,443,2052,2053,2082,2083,2086,2087,2095,2096,8080,8443,8880)且**全部 403**，直连 TLS 无 SNI 直接握手失败。汇报时要把这点讲明，否则用户会被「IP 情报」误导向扫描。

**CF 错误码 = 源站存活探针**(不用碰源站就能判断):
- `200` + 「Site is created successfully!」/ `Power by aaPanel` ⇒ 源站**活**，该域名未配 vhost
- `500` + `cfOrigin;dur=<小值>` 空体 ⇒ 源站**活**，PHP/索引坏了
- `522` ⇒ CF 连不上源站(TCP 超时)
- `530` / `Error 1016 Origin DNS error` ⇒ 源站记录是解析不到的 CNAME(常见于 **已删除的 cloudflared tunnel**)
- 若多域名都呈现上述组合 ⇒ 极可能 **Cloudflare Tunnel**(不存在可寻址源站，改打应用层/木马样本)

**关联域名金矿**: 目标的 `robots.txt` / `sitemap.xml` 常把**工具站/品牌站**写成绝对 URL(本次靠 `Sitemap: https://<vendor>/sitemap.xml` 挖出运营方另 2 个域名)。抓到后逐一测 CF 错误码，从中挑「源站活」的那个做基建指纹比对。

**基建同源判定**: 比对 404/错误页**字节数 + 品牌特征**(aaPanel 定制 404 约 58663 字节、含 `aapanel.com/...invite_code=`)。字节数一致 ⇒ 同一套基建。

**引擎登录态**: Chrome 127+ cookie 为 **v20 app-bound** 加密，DPAPI + AES-GCM **解不了**(v10/v11 才可以)，`Local Storage/leveldb` 也读不到 session ⇒ 只能「**复制 profile(Local State + Default/{Network,Local Storage,IndexedDB,Preferences}) → headless Chrome + `--remote-debugging-port` → CDP 带登录态**」。判据先查 leveldb 里有无该域名字符串，无则基本未登录，别白跑。

## 输出与结案
- 工具输出: 终端彩色排名表 + report_target_<时间戳>.json
- 判胜: 找到 IP → JA3/JA4+页面哈希确认 → 记录证据(证书/响应头/页面哈希)
