## 23. Infrastructure OSINT

### 23.1 IP & Domain Discovery

Shodan, Censys, Onyphe, DNSDB.

### 23.2 Certificate & Passive DNS

crt.sh, SecurityTrails.

### 23.3 Malware & Artifact Analysis Workflow

- **Static triage** — SHA-256, strings, import tables, PDB path, Rich header. Don't rely solely on AV labels.
- **Dynamic / sandbox** — ANY.RUN, Hybrid Analysis, CAPE, Tria.ge.
- **Clustering** — SSDEEP/TLSH, YARA matches.
- **Reporting** — STIX 2.1 IOCs; ATT&CK technique IDs; reproduction steps.

### 23.4 Telegram / WeChat Investigation

- **Telegram** — public analytics (TGStat, Telemetr, Combot); export channels with Telegram Desktop; preserve message IDs, UTC timestamps, media hashes.
- **WeChat** — Sogou Weixin search; archive articles (PNG + WARC); capture `__biz` IDs. Expect link rot.

---

