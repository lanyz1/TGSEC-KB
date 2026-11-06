# cf-hidden-origin-tracing 全文 第 2/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Reporting discipline (this is what the user actually wants)

### 0. Brand-new domains: check the "never had a non-CF generation" case FIRST

**Step −1 — read your own case archive first (cheapest check that exists).**
`ls /root/cases/` + `grep -ril "<domain>" /root/cases/` + `session_search "<domain>"`. A prior session
may have already closed this exact target: in this engagement `/root/cases/tgasms/REPORT_tgasms.md`
held a complete verdict (246,625-request path brute, 110,158-name subdomain brute, empty PDNS/CT,
"origin structurally unobtainable") written the day before, and the re-run reproduced all of it for
nothing. If a report exists: reuse it, state the **delta**, and skip §1–§12 unless something changed.

Before running any origin hunt, spend 2 minutes on: WHOIS creation date, CT issuers,
passive DNS, subdomains, MX/TXT. If the domain was registered weeks ago and **every**
channel is empty, the origin is not hidden — it never existed publicly:

- `whois`: Creation Date ≈ Updated Date, 4-8 weeks old, registrar Dynadot, registrant
  a fake CN name + gmail (2026-08-11 case).
- CT: only same-day entries, and only **CF Universal SSL (Google Trust Services WE1)**
  + a Let's Encrypt `*.domain` wildcard — **no Chinese CA (TrustAsia) entry** = no
  generation that ever answered directly from a CN/HK box.
- CN passive DNS (ip138 / 爱站 / Chinaz) empty, `api.mnemonic.no/pdns/v3/<d>` `count:0`,
  Wayback/CommonCrawl/urlscan empty, 0 search-engine results.
- Subdomain brute (158 hand-picked + SecLists `subdomains-top1million-110000`) = 0 hits;
  MX/TXT/CAA = none.

That combination means **there is no origin IP to find** — every external vantage
(own box, `/24` sweep, IP-URL fetch) is structurally blind, and no leak channel was
ever written. Say that in the first paragraph of the report instead of burning the
session, and shift the deliverable to "what the domain actually is" (e.g. a static
impersonation shell: 3 static pages, all download links `href="#"`, zero JS).
Two cheap extras worth running on such a shell: multi-resolver geo check
(223.5.5.5 / 119.29.29.29 / 114.114.114.114 / DoH — if CN resolvers return the same
CF anycast IPs, no geo-split origin exists) and the CF error-page `cfOrigin;dur=`
header (proves an origin sits behind the edge, so "CF Pages/Workers" is ruled out).
- Every negative pairs with a **positive control**. "Dead" must be provable (CF-internal probe +
  control), not inferred from a timeout.
- Separate **externally unobtainable** from **not yet obtained**, and name the one path that can
  still produce it.
- Do not re-run ruled-out lines. Keep a running "ruled out, and why" list — see the case reference.

## Dead ends — do not spend time here again
- **Shodan/FOFA by favicon mmh3, TLS cert, hostname or HTML body** for an origin that only talks to
  CF: zero index. Expected, not a tool failure.
- **Engine-ops limits that waste a session if unknown** (weighted against the low-tier API): `fields=icon_hash`
  → `[820001] 没有权限搜索icon_hash字段` (same for `lastupdatetime`) — drop the field, don't rewrite the
  query; deep pagination **returns the same rows again** (7 pages × 100 → only 24 unique IPs), so dedupe
  by IP and never estimate coverage from `size`/page count; `[45012] 请求速度过快` means sleep `5–6 s`
  between queries in a script; and **the index is stale** — a whole `/24` of hits (`186.244.248.x`) was
  entirely unreachable, so re-verify every candidate's liveness before reporting it. Use
  `cert="<domain>" && server!="cloudflare"` as the one shape that flips a CF-only domain into a
  bare-metal farm IP, and never trust `body=` for `href`/`src` values (template paths return 0 — grep
  the fetched page locally).
- **favicon-mmh3 on a *brand* icon.** When the target impersonates a famous product, its favicon is
  that product's logo, so `icon_hash=` matches thousands of unrelated impersonators (worked case:
  Telegram's paper plane → 7,850 hits, including the real `fragment.com` and pure mmh3 collisions).
  Non-empty index ≠ usable fingerprint. Only a *custom* icon clusters a farm.
- **Custom icon_hash alone still lies.** Worked: `icon_hash=-561384241` (5644 B apple-touch) hit
  MTProto boxes and catch-all `goDl` shells that serve the same PNG on a default vhost. Require the
  **triple gate** (§16c): icon md5 + exclusive robots body + no cf-ray, plus Host md5 control (§13).
- **Shared download-shell JS (`goDl` / `openDecodedUrl`) is a template family, not an origin cluster.**
  FOFA body hits are leads for the catch-all control, not automatic same-box proof (§16d).
- **Landing 500 ≠ "no origin work left".** Check API/admin siblings for CloudFlare Origin CA (§16b)
  before declaring the engagement origin-blind — control plane may be fully exposed while the SEO
  shell is a CF-cached corpse.
- **Free Western passive-DNS** for CN-registered domains.
- **Sidebar "related IPs"** on CN IP-lookup sites (ad pollution).
- **Public CF reverse proxies as egress** (429 on live controls).
- **Re-testing historical IPs after a domain re-registration** (stale by definition).
- **Re-testing historical IPs that the cross-host test has already shown to be CF edge** — and
  never presenting such an IP to the user as "the source IP".
- **Sweeping a provider's whole /16 for the panel** (`47.76.0.0/16` + `47.91.0.0/16`: 262,136 targets,
  34,677 open hosts, CF-edge-filtered, real fingerprint => zero hits). Cheap in wall-clock, but it does
  not answer this question; the previous generation lived there, the live origin does not.
- **Escalating crypto work on a perfect replica that the server still rejects** — the gate is
  elsewhere; drive the UI instead.

## References
- `references/telegram-farm-origin-hunt-2026-10.md` — CN "Telegram download" SEO farm behind CF:
the 58,296 B aaPanel `404`, the robots/sitemap sibling leak, the md5-control clearing 59 CDN nodes +
11 bare-metal candidates, `check-host.net` retiring the top candidate, and the deliverable written
when the origin IP genuinely does not exist publicly.
- `references/telegram-farm-r4-qb117-origin-2026-10.md` — **R4 breakthrough**: CF Origin CA on
  `103.254.110.111` = `api.tron-api.top`; dual qb-117 API unauth fingerprint surface; triple-fp gate;
  goDl catch-all; OSS APK chain; what still failed for the *landing* origin.
- `references/farm-domain-pool-expansion.md` — the farm-growth playbook: link-farm mining, the
  vendor-CDN pivot, letter-level twins, the Host-reflection md5 table (§15), the deny-unknown-Host
  netblock tell (§21), and an honest note on where this class stops.
- `references/passive-dns-source-bank.md` — which history sources actually return data for
  CN-facing domains, the CF CIDR filter (miss 188.114/2a06 and you'll report CF as a new origin),
  and the ip138 parser recipe.
- `templates/cf-egress-fetcher.js` — the deployable CF-internal probe Worker (`?u=&h=`).
- `scripts/host_differential_probe.py` — the md5-control prober (§13 Trap 3/4/5) as a re-runnable
  script: sweeps a segment or an IP list, issues target-vs-control `Host` requests, repeats the same
  Host for stability, flags host-reflection, and cache-busts when pointed at a CDN-fronted URL.
- `scripts/link_farm_miner.py` — fetch N known farm pages, frequency-count their external link hosts,
  and print the pool the operator actually owns (plus each domain's resolved IPs).
- `scripts/triple_fp_verify.py` — icon md5 + robots exclusivity + no-cf-ray gate for static landers.

