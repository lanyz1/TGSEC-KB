## SSRF 内网打点速查(老路径,常用)
- gopher://redis(写 crontab/ssh key)→ RCE;gopher://mysql 认证绕过
- 云 metadata: `http://169.254.169.254/latest/meta-data/iam/security-credentials/`(AWS)→ AK;Azure IMDS `168.63.129.16/metadata/...`
- 盲 SSRF 判定: dnslog / 响应时间差 / 图片加载器
- 扫描脚本: scripts/ssrf_scanner.py
