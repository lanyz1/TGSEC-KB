---
name: web-ssrf
description: "SSRF attack techniques — internal port scanning, cloud metadata access, gopher/redis exploitation, blind SSRF, DNS rebinding. Trigger: ssrf, server-side request…"
---

# Web Ssrf

SSRF attack techniques — internal port scanning, cloud metadata access, gopher/redis exploitation, blind SSRF, DNS rebinding. Trigger: ssrf, server-side request forgery, internal scan, metadata, aws metadata.

## SSRF 防护绕过 — deny-list/IP 校验必漏地址库(2026-09 增量)
- 场景: 目标有 SSRF 防护(IsInternalIP/deny list/内网校验),直打 127.0.0.1/10.x 被拦 → 换下面"校验器漏网"地址
- **Azure 专用**: `168.63.129.16`(Azure WireServer/IMDS,非 169.254 系)——Mailpit IsInternalIP 就漏它(CVE-2026-84697,link check API + proxy 端点可打内网)
- **IPv4-translated IPv6 前缀**(RFC 2765/6145 `64:ff9b::/96` 及 SIIT 翻译): 校验器只查 IPv4 或只查纯 IPv6 内网段时,`http://[::ffff:10.0.0.1]/` / `[64:ff9b::a00:1]` 可达内网 IPv4 ——同样被 Mailpit 漏掉
- 完整云元数据地址表: AWS `169.254.169.254` / GCP `metadata.google.internal` / Azure `168.63.129.16` + 各家 IPv6 元数据(阿里云 `100.100.100.200`、腾讯云 `metadata.tencentyun.com`)
- 组合绕过: 十进制/八进制 IP(`2130706433`/`0177.0.0.1`)、短域名(`localtest.me`)、DNS rebinding、`http://169.254.169.254@evil`、URL 解析差异(空格/`#`/`@`/unicode)
- 参考: https://www.vulncheck.com/advisories/mailpit-ssrf-deny-list-bypass-via-azure-metadata-and-ipv6-prefix

## SSRF 内网打点速查(老路径,常用)
- gopher://redis(写 crontab/ssh key)→ RCE;gopher://mysql 认证绕过
- 云 metadata: `http://169.254.169.254/latest/meta-data/iam/security-credentials/`(AWS)→ AK;Azure IMDS `168.63.129.16/metadata/...`
- 盲 SSRF 判定: dnslog / 响应时间差 / 图片加载器
- 扫描脚本: scripts/ssrf_scanner.py
