---
name: c2-family-infra-mapping
description: "Use when mapping a C2 family's infra from one artifact."
---

# C2 Family Infra Mapping

From ONE artifact of an adversary C2/scam operation (a dead panel domain, a live IP, a scanner lead) produce: the family's host/service map → the panel's API surface → a triaged entry path, in that order. Steps 1–5 are passive; only step 6 touches the target.

## Procedure

### 1. Search-engine pivot
- `web_search` the exact domain/hostname and unique strings (old panel names, codenames); search the artifact's IP too.
- Why: indexes keep stale titles long after a site changes — a hit whose snippet shows a name the live page no longer has exposes the box's previous identity and leads to sibling domains; search the old name too, it recurs across the family's other hosts.
- Mine hits for: sibling domains, IP-intelligence pages, cached panel names. Code-hosting/code-search hits matter too — operators publish their webroot as public repos; loot them via `c2-infrastructure-pentest` → control-plane-mining (server source, panel auth model, committed keys/certs).
- Highest-yield query class: the KIT's own component strings (stage-file names, loader/brand names, unique API paths) — not just your target's identifiers. Commercial kits sell to many operators, so one vendor threat-intel report about ANY operator of the kit maps the whole family: host table (IP:port:role), hardcoded secrets, victim counts, per-operator splits, and IOC caveats. Treat the report as a fleet map — probe every listed host live (HTTP GET its listed port; `Directory listing for /` title = open directory), then loot exposed operator boxes per `c2-infrastructure-pentest` → control-plane-mining.
- Keep siblings distinct from the target: cross-grep any looted box for the primary target's domains/IPs; zero hits = a different operator of the same kit. Record it as a sibling — the shared kit server code still documents your target's endpoint design, and its tooling/TTPs transfer. Honor report caveats (some listed IPs are capture/staging boxes explicitly excluded from IOCs), and snapshot fast: published open boxes get cleaned within days.
- Root paths on looted/sibling boxes: beyond the web plane, scan them for network file services — NFS (2049) + rpcbind (111) with a world-exported share and `no_root_squash` gives root-identity write, and pairs with a companion HTTP dir listing for full-file read; see `nfs-rpc-exploitation`.

### 2. IP-intel services
- `https://app.huntback.io/ip/<ip>` — public HTML summary (its JSON API needs a key): tags (`c2`, `exploit`, `exposed-secret`, `forced-loot`, `malware`), open ports, service banner incl. operator-set page titles, JARM, loot-harvest stats, related infrastructure.
- `lead` (JARM-only) entries are correlation noise — stock shared JARMs false-positive easily; only `confirmed` (multi-signal: JARM+cert+pDNS+hosted files) warrants a pivot. Live-verify before attacking: scanner data goes stale (ports listed open may be closed today).

### 3. Certificate SANs = the vhost map (highest single yield)
```bash
openssl s_client -connect <IP>:443 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
openssl s_client -connect <IP>:443 -servername <any> </dev/null 2>/dev/null | openssl x509 -noout -text | grep -A5 "Subject Alternative Name"
```
- Why: IP-only operators need TLS + vhost routing, so one Let's Encrypt cert covers every service hostname; sslip.io-style entries (`admin.1-2-3-4.sslip.io`, `c2.…`, `land.…`, per-brand lines) leak the complete service map for free.
- sslip.io auto-resolves `<label>.<a-b-c-d>.sslip.io` to a.b.c.d — fetch each vhost with zero DNS setup:
```bash
curl -sk "https://admin.<dashed-ip>.sslip.io/" -D- -o /tmp/v.html
```
- Expect all hostnames to serve the same default app; diff bodies/paths per vhost, not status codes.

### 4. Domains behind the IP (and more certs)
- Reverse-IP (free): `https://api.hackertarget.com/reverseiplookup/?q=<ip>`
- Cert history (free, no key): `https://api.certspotter.com/v1/issuances?domain=<domain>&include_subdomains=true&expand=dns_names`
- crt.sh fallback (flaky — retry): `https://crt.sh/?q=%25.<domain>&output=json`
- Passive DNS: `https://otx.alienvault.com/api/v1/indicators/IPv4/<ip>/passive_dns` (often empty; low priority).

### 5. SPA bundle = the API map (before any login)
- Signal: `X-Powered-By: Express` (or similar) + every path returning the same small HTML shell that references a hashed bundle like `/assets/js/index-<hash>.js`. On catch-all SPAs status codes mean nothing — classify by body content.
```bash
curl -sk "<host>/assets/js/index-<hash>.js" -o bundle.js
grep -oE '/api/[a-zA-Z0-9/_.-]+' bundle.js | sort -u                       # endpoint map
grep -oE '.{80}(login|token|localStorage|/ws/).{100}' bundle.js | head -40 # auth flow
```
- The public bundle documents the whole backend: endpoint names classify the platform (device control / shell / data-theft / builder routes) for impact reporting, and the auth flow (endpoints, JSON fields, 2FA mechanics, WS paths, token storage keys) tells you exactly what a login wall is made of before you touch it.

### 6. Login-wall triage
- Determine rate-limit scope: your IP blocked while a fresh proxy still receives responses/challenges ⇒ limits are per-IP → rotate proxies and pace; keep your own IPs out of operator logs.
- Telegram-2FA walls: the OTP goes to the operator's chat — treat as a hard wall; timebox cheap logic probes, then pivot to sibling hosts/accounts. Never brute a random 6-digit OTP. Assume any accepted admin login alerts the operator (OTP push) — few attempts, paced, from proxies. Full triage notes: `references/auth-wall-triage.md`.

### 7. Timebox dead leads
- Ports external scanners saw open may be closed to you, to regional proxies, AND to the operators' own infrastructure. Test at most 2–3 vantage points, then drop it — the HTTPS tier on 80/443 is usually the intended door.

## Notes
- Multi-brand families run land/C2/admin lines as separate vhosts on shared boxes: enumerate ALL leaked hostnames before concluding a box is closed.
- Credentials are reused across a family's fleet — replay recovered creds against every sibling host and against every new system found later (billing fronts, gateway panels, admin UIs all tend to take the same operator password).
- Audit/login tables inside any compromised panel are a first-class host-enumeration source: attribute and scan the distinct operator IPs — operators host the family's non-C2 systems (billing portals, appliance UIs) on their own boxes; far higher yield than blind hosting-neighbor sweeps. Tactic detail: `c2-infrastructure-pentest`.
- Link artifacts into the engagement corpus: grep the case directory for new domains/codenames to connect cases.
- Multi-request probing: write a script file (inline quoting breaks) and background long sweeps with a log file.
- JARM clusters are noisier than they look (a stock shared fingerprint listed 200+ hosts): never treat a cluster page as a fleet — each pivot host needs a second signal (cert, body hash, shared token) before it counts.
- After locating one box in a hosting /24, a neighbor sweep mostly returns unrelated tenants (other teams' panels/tools): fingerprint-match candidates (title, SPA asset hash, secret constants) before attaching any neighbor to the family.

## References
- `references/auth-wall-triage.md` — panel login-wall patterns: rate-limit semantics, Telegram-2FA flow, cheap probes vs what to skip.
