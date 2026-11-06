# Passive-DNS / history source bank (origin tracing)

Tested 2026-09 against a CF-backed, CN-facing target (`*.opensms.cc`, `*.opensms.xin`).

## Returns real data
- **mnemonic PDNS** — `https://api.mnemonic.no/pdns/v3/<domain>` (free, no key). Returns
  `{answer, rrtype, rdata, timesFirstSeen, timesLastSeen}`; carries records the site no longer
  publishes. Also `https://api.mnemonic.no/pdns/v3/<ip>` for reverse history.
- **ip138 (CN)** — `https://site.ip138.com/<host>/`. The **only** source that held non-CF A records
  for these CN-facing domains (previous-generation hosting, with dates). Reach it from a CN/HK egress.
  Parse the history block — ad-hoc table scraping returns 0 rows and wastes a whole run. Working
  shape: `id="J_ip_history"`, rows `<span class="date">DATE</span><a …>IP</a>`. Reuse the existing
  parser (`ip138_batch.py`, emits `IP138_ALL.json` as `{host: [[date, ip], …]}`) instead of rewriting.
- **hackertarget hostsearch** — `https://api.hackertarget.com/hostsearch/?q=<domain>`: current
  resolution per hostname; fastest way to enumerate the live subdomain set.

## Empty / unusable for this class
- AlienVault OTX `…/passive_dns` — 0 records.
- ThreatMiner `v2/domain.php?q=<d>&rt=2` — 522.
- rapiddns / viewdns / unauthenticated urlscan — 0 or blocked.
- **CT logs (crt.sh JSON) carry hostnames, never IPs** — use them to *name* new subdomains to resolve.

## CF range filter (apply before celebrating a "non-CF" hit)
`172.64.0.0/13`, `172.66.0.0/16`, `172.67.0.0/16`, `104.16.0.0/13`, `104.24.0.0/14`,
`162.159.0.0/16`, `188.114.96.0/20`, `173.245.48.0/20`, `141.101.64.0/18`, `108.162.192.0/18`,
`190.93.240.0/20`, `103.21.244.0/22`, `103.22.200.0/22`, `103.31.4.0/22`, `31.13.24.0/21`,
IPv6 `2a06:98c1::/32`, `2606:4700::/32`, `2803:f800::/32`.
Missing `188.114.x` / `2a06:98c1::` made CF's own WARP ranges look like a fresh origin.

## Order of operations
1. `whois` creation date — a re-registration days ago stales **all** history by definition.
2. mnemonic + hackertarget — current state and foreign history.
3. ip138 — CN history, the only non-CF records for CN-facing targets.
4. Filter CF ranges. Every surviving IP is a **candidate**, never a confirmed origin, until it
   answers a Host/SNI-correct request from inside CF (SKILL.md section 3).
