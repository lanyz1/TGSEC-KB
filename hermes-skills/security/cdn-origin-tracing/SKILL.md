---
name: cdn-origin-tracing
description: "Use for CDN/WAF origin IP tracing."
version: 0.1.0
author: 思念 (狗盾思念), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cdn, waf, cloudflare, origin-ip, recon, bypass]
    related_skills: [pentest-execution, black-cat-redteam, tgsec-suite]
---

# CDN Origin Tracing

Find origin IPs behind Cloudflare/Akamai/阿里云/腾讯云/AWS CDN. Prefer layered discovery + fingerprint verification over single tricks. Full handbook: `references/full-handbook-v5.1.md`. Cost-tiered P0–P4 pipeline: `references/p0-p4-priority-playbook.md`.

## When to Use

- CDN / WAF / Cloudflare / 源站 / 真实 IP / origin IP / CDN bypass
- Target has `cf-ray`, multi-region Anycast, or rate-limit only on CDN edge
- Need direct-IP connect to bypass WAF/captcha before auth brute / xmlrpc / admin

Don't use for: Turnstile token farming alone (`pentest-execution/references/cloudflare-turnstile-bypass.md`); pure static CDN gambling nodes with no origin (`pentest-execution/references/cdn-static-gambling-recon.md`).

## Prerequisites

- `terminal` with `curl`, `dig`/`nslookup`, `python3`
- Optional: `jq`, `openssl`, SecurityTrails/VT API keys
- Scripts: `scripts/cdn_quick_trace.py`, `scripts/cdn_ranges.py` (stdlib + `requests`)

## How to Run

```bash
# quick passive+verify pipeline
python3 scripts/cdn_quick_trace.py target.com
python3 scripts/cdn_quick_trace.py target.com --passive-only
python3 scripts/cdn_quick_trace.py target.com -o /tmp/cdn_report.json

# classify / filter candidate IPs
python3 scripts/cdn_ranges.py 104.16.1.1
python3 scripts/cdn_ranges.py --filter 1.2.3.4 104.16.1.1 8.8.8.8
```

Frame all invocations via `terminal`. Use `web_search` / `web_extract` when FOFA/Shodan UI is needed.

## Procedure

1. **Identify CDN** — `curl -sI https://target` for `cf-ray`/`x-amz-cf`/`via`/`x-cache`; multi-geo ping if needed. Done when vendor known or "no CDN".
2. **Discover candidates (layer 1–2)** — run `cdn_quick_trace.py` or manually: crt.sh → subdomains (mail/dev/origin/direct) → historical DNS → MX/SPF → FOFA/Shodan `cert="target"` excluding CDN issuer. Done when ≥1 non-CDN A/AAAA exists.
3. **Filter** — `cdn_ranges.py --filter <ips>`; drop CDN ranges. Done when candidate list is non-CDN only.
4. **Verify (mandatory)** — Host-header curl to candidate: `curl -sk --resolve target:443:IP https://target/ -o /tmp/o.html -D -`. Confirm with body hash / title / TLS SAN match. Host 200 alone ≠ origin (shared host / CDN node). Decisive check: TLS cert serial exact-match vs CDN node (and different default cert). Done when hash/title/SAN align or P≥0.80 with fingerprint evidence.
5. **Exploit path** — direct IP + Host/`--resolve` for WAF-bypassed scans (xmlrpc, admin, brute). Record origin in engagement notes.

Branching by portrait: see `references/decision-tree.md`. Method ranking: `references/method-matrix.md`. Cost-tiered P0–P4 pipeline: `references/p0-p4-priority-playbook.md`.

## Quick Reference

| Goal | Command / query |
|------|-----------------|
| CT subs | `curl -s "https://crt.sh/?q=%.target.com&output=json" \| jq -r '.[].name_value' \| sort -u` |
| Passive DNS free | `curl -s "https://api.hackertarget.com/iphistory/?q=target.com"` |
| MX/SPF | `dig MX target.com +short`; `dig TXT target.com +short` |
| History DNS (CN) | `https://ipchaxun.com/target.com/` ; `https://site.ip138.com/target.com/` |
| Cert serial (decisive) | `echo \| openssl s_client -connect IP:443 -servername target.com 2>/dev/null \| openssl x509 -noout -serial` |
| Host verify | `curl -sk --resolve target.com:443:IP https://target.com/ -D- -o /tmp/b.html` |
| FOFA | `cert="target.com" && header!="cf-ray"` |
| Shodan | `ssl.cert.subject.cn:target.com` |
| CF ranges | `curl -s https://www.cloudflare.com/ips-v4` |

High-hit bypass sub labels: `mail smtp cpanel direct origin backend dev staging ftp vpn admin api`.

## Pitfalls

- Host-header 200 on shared hosting ≠ origin — require fingerprint/hash.
- Cloudflare Tunnel (`cfargotunnel.com`) has no classic origin A record — pivot config leak / Pages / Workers / sibling domains.
- Domestic 鸡哥/Anti-DDoS may reuse non-obvious ASN ranges — refresh ranges before concluding.
- Pure static CDN edge (masscan 0 app ports, all API 404) → APK/subdomain pivot, not more Host fuzz on the edge IP.
- Do not burn hours on Turnstile automation; origin bypass first, then human/browser login if needed.

## Verification

- [ ] CDN vendor identified or ruled out
- [ ] Candidates filtered through `cdn_ranges` / known CIDRs
- [ ] At least one verified origin (hash/title/SAN) **or** documented blocker (Tunnel/no public origin)
- [ ] Direct-IP request path recorded for follow-on attacks
- [ ] Report JSON or notes saved (`-o` / engagement log)

## Related

- Full 50-method handbook: `references/full-handbook-v5.1.md`
- Cost-tiered P0–P4 pipeline: `references/p0-p4-priority-playbook.md`
- Pentest early step: `pentest-execution` § CDN bypass
- Recon routing: `black-cat-redteam` → `../pentest-redteam/techniques/recon.md`


---

## 外部库增量（2026-10-11 分享包）

## 测绘引擎真源

- Skill 全文：本卡 + `references/` 16 个分册（原 4075 行 / 135K 拆分）
- 手法：`docs/playbooks/证书溯源与空间测绘引擎.md`
- 工具：`python3 tools/ops/origin_recon.py --help`
- CDN 溯源流水线：`python3 tools/ops/cdn_tracer.py <domain>`
- CDN IP 段过滤器：`python3 tools/ops/cdn_ranges.py <ip>`
- 深度 IP 段收集：`python3 tools/ops/cdn_ip_collector.py`
- 源站漂移监控：`python3 tools/ops/cdn_origin_monitor.py <domain>`
- 路由：`python3 tools/ops/hypothesis_route.py --signal "CDN溯源"`
- 源站验完若是黑洞 + 敲门 / Vue C2：交接 `c2-zero-trust-console` · `c2_zt_probe.py drive --origin-ip`
- Hermes `edgeone-origin-bypass` / `cloudflare-origin-bypass`：本卡就是对照落地，勿另开空壳卡

---

# CDN/WAF 真实 IP 溯源 — 深度实战手册 v5.1

> 50 种溯源技术 · 30+ CDN 厂商绕过 · 2025-2026 最新方法 · JA3/JA4/HTTP2 现代指纹验证 · Python 自动化 Pipeline · 贝叶斯置信度评分 · 组合拳成功率 95%+

## 核心原则：分层组合 + 现代指纹验证

**单方法成功率有限，分层组合拳成功率 95%+。** v5.0 推荐分层流水线：

```
第一层(发现)  crt.sh证书 → 子域名枚举(含AltDNS) → 历史DNS聚合 → 被动DNS多源交叉
第二层(暴露)  网络空间引擎(Shodan/Censys/FOFA) → CSP/CORS/JS端点 → 云存储桶枚举
第三层(触发)  邮件头/Pingback → 缓存投毒/请求走私 → SaaS/Serverless源站发现
第四层(验证)  Host头验证 → JA3/JA4 TLS指纹 → HTTP/2 Akamai指纹 → 页面哈希一致性
```

**关键升级**：v5.0 将"验证"独立成层，避免传统方法只发现不验证导致的误报。Host 头返回 200 ≠ 源站（可能是 CDN 节点或共享主机），必须用 JA3/JA4 + HTTP/2 指纹交叉确认。

## 分册索引（references/ · 按需加载）

> 本卡为索引主体；细节已按主题分册，避免单文件撞 100K 上限。**只读需要的分册**。

| 分册 | 内容 | 何时读 |
|------|------|--------|
| `references/methods-01-15.md` | 方法 1-15：证书透明度 / 子域名 / 历史DNS / 空间引擎 / CNAME链 / IP段反查 / SPF / MX / Host头验证 / 第三方ID / 网站功能 / ICP备案 / XML-RPC / 邮件头 / Favicon | 标准起手 |
| `references/methods-16-31.md` | 方法 16-31：ANY缓存 / IPv6 / AXFR / AltDNS / 多解析器 / CSP-CORS / 回源IP段 / JS端点 / 被动DNS聚合 / CA分析 / 重定向链 / CF Tunnel / Pages-Workers-R2 / Serverless / HTTP3 / ECH | 前段无果换现代面 |
| `references/methods-32-41.md` | 方法 32-41：K8s Ingress / CI-CD / 云存储桶 / WebSocket / 缓存投毒 / 请求走私 / GraphQL / SSE / App硬编码 / DNS Rebinding | 云原生/高防目标 |
| `references/methods-42-50.md` | 方法 42-50：缓存清除预热 / HPACK侧信道 / Anycast去匿名 / Origin Shield / 速率差分 / eBPF-XDP / 跨域计时 / IP漂移追踪 / 回源认证绕过 | 反溯源强目标 |
| `references/cdn-ip-ranges-asn.md` | CDN IP 段库（国际 / 国内 / ASN 实时反查），CIDR 可直接喂过滤脚本 | 过滤候选 IP |
| `references/vendor-bypass.md` | **30+ 厂商**专属绕过：CF 12 种 / CloudFront 8 / Akamai 6 / 阿里云 9 / 腾讯云 8 / 华为 / 火山 / Azure / Google / 鸡哥 / ArvanCloud / 通用技巧 | 已识别厂商后 |
| `references/verification-and-scoring.md` | JA3/JA4/HTTP2 四维指纹验证 + 贝叶斯加权评分 + **bash 100 分制基线** | 判胜 / 排误报 |
| `references/toolbox-cli.md` | 本技能 4 个工具完整 CLI：cdn_tracer / cdn_ranges / cdn_ip_collector / cdn_origin_monitor | 跑工具前 |
| `references/automation-bash.md` | 12 步 bash 一键脚本（无 Python 环境） | 跳板机裸环境 |
| `references/automation-python.md` | Python Pipeline 骨架（Stage 基类 / 5 阶段 / 调度 / 扩展点） | 二次开发 |
| `references/space-engine-cookbook.md` | Shodan/Censys/FOFA/Quake 进阶组合查询 + 误报过滤 | 用引擎反查 |
| `references/anti-evasion-monitoring.md` | 反规避反制（访问控制 / SNI / 地理封锁 / 蜜罐）+ 源站漂移监控 | 目标主动防御 |
| `references/cases-and-tools.md` | 4 个真实案例工作流 + 在线/开源工具速查 | 找同类案例 |
| `references/origin-landing-and-edge-evasion.md` | **v5.2 本库实战增量**：vhost 枚举 / CF 429 与 1015/cf_clearance 对抗 / 开发端口 / 换面与静默纪律 / HTTPS RR·ECH ipv4hint + 工具落地与实测记录 | 拿到候选 IP 要落地 |

## 30 秒速查

```bash
# 一键全流程(14 阶段, 推荐)
python3 tools/ops/cdn_tracer.py target.com --all

# 0. 先判有无 CDN + 是否 CF/云厂
curl -sI https://target.com | grep -iE "(cf-ray|cf-cache|x-amz-cf|x-cache|via:|server)"

# 1. 证书透明度 → 子域/兄弟域/历史 IP
curl -s "https://crt.sh/?q=%25.target.com&output=json" | jq -r '.[].name_value' | sort -u

# 2. 高命中 bypass 子域(直连类优先)
for s in direct origin backend mail ftp cpanel vpn mysql ssh dev staging; do
  dig +short $s.target.com | head -1 | sed "s/^/$s → /"; done

# 3. 候选 IP 批量排除 CDN 段(留下疑似源站)
python3 tools/ops/cdn_ranges.py --filter candidates.txt

# 4. Host 头验证 + 四维指纹确认
curl -sIk -H "Host: target.com" https://<候选IP> | head -20

# 5. 评分定案(贝叶斯 / 无 Python 时 bash 100 分制)
#    → references/verification-and-scoring.md
```

> 工具完整参数见 `references/toolbox-cli.md`；50 种方法全文见 `references/methods-*.md`。

---


## 全文导航（已拆分）

主卡保留前 13 节；其余 7 节在 `references/full.md`：

- 溯源方法完整矩阵（v5.0 深度优化 · 50 种方法）
- 第一阶段：CDN 识别（精准判定）
- 第四阶段：快速组合拳（3 分钟最高成功率）
- 常见失败原因与突破策略
- 注意事项
- 相关技能
- v5.2 本库实战增量（已拆为分册）

加载：`skill_view(name='cdn-origin-tracing', file_path='references/full.md')`
