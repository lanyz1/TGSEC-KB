## 20. Threat Actor Investigation

### 20.1 Actor-Centric Workflow

- **Scoping** — actor hypothesis (APT28/29, Turla, Sandworm; APT10/41, Mustang Panda, Volt Typhoon). Seed reports from CERTs/vendors.
- **Indicator harvesting** — IOCs (domains, IPs, hashes, JA3/JA4, user-agents). Validate with passive DNS, CT logs, sandbox submissions.
- **Infrastructure mapping** — pivot from CT logs (SANs, issuer, serials), shared hosting, NS reuse, registrar accounts, HTML fingerprints. Enrich with ASN/WHOIS history, RPKI/ROA, geolocation.
- **Artifact profiling** — PE/ELF metadata (PDB paths, compile timestamps, Rich headers, code-signing). Cluster with SSDEEP/TLSH; YARA matches.
- **Social / procurement pivots** — developer handles, code snippets, academic theses, job posts, procurement records.
- **Falsification + reporting** — weigh each linkage; document alternatives; map TTPs to MITRE ATT&CK; cite sources with sections/pages.

### 20.2 Attribution Discipline

- Separate capability from intent and sponsorship.
- Rule of three: 3 weak OR 1 strong + 1 weak.
- Prefer durable pivots (registrar accounts, code-signing certs, build path idioms) over ephemeral (resolving IPs).
- Mark uncertainty levels; distinguish correlation from control.

### 20.3 Russia-Specific Pivots

- **Corporate / people** — EGRUL/EGRIP (captcha-gated), Rusprofile, Kontur.Focus, zakupki.gov.ru, hh.ru.
- **Infrastructure** — RU WHOIS via `whois.tcinet.ru`; Telegram for channels/admins/cross-posts.
- **Media** — VKontakte, Odnoklassniki, Rutube; search in Russian and transliterations.

### 20.4 China-Specific Pivots

- **Corporate / people** — gsxt.gov.cn (national enterprise credit); Tianyancha / Qichacha; ICP filings on beian.miit.gov.cn → USCC linkage.
- **Infrastructure** — CNNIC WHOIS; common domestic clouds (Aliyun, Tencent, Huawei).
- **Media** — Weibo, WeChat (via weixin.sogou.com), Zhihu, Bilibili, Douyin, Xiaohongshu; Chinese + Pinyin.

### 20.5 Infrastructure & Internet Measurement

- IP→ASN (HE BGP Toolkit, RIPEstat, BGPView).
- CT logs (crt.sh) for cert reuse and issuance cadence; pivot on subjects/issuers/serials.
- URLScan for HTML fingerprints, favicons (mmh3), script hashes.
- DNS over time (SecurityTrails PDNS, DNSDB) for subdomain churn and staging domains.

---

