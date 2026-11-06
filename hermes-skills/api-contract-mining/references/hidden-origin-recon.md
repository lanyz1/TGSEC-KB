# Hidden origin recon (finding the IP behind a CDN/WAF)

Use when the public name resolves only to a CDN and the origin silently drops everything
outside the CDN's ranges. Authoritative umbrella for this class in this library:
`security/cdn-origin-tracing` (user-owned).

## Chinese DNS-history sources — the gap-filler when Western PDNS is empty
- `https://site.ip138.com/<domain>/` (plus the `/www.<domain>/` variant) publishes a dated
  A-record history table. Parse the history block, not the sidebar.
  Reference case: a CF-fronted target showed direct A records on 2026-06-20 to three
  Alibaba-Cloud-Hong-Kong IPs (matching the operator's own "3 datacenters" marketing), an
  older AWS-Frankfurt IP, and the pre-2025 CF-only era — while every Western free service
  returned nothing usable.
- Fetch these with a China/HK-friendly egress and a browser User-Agent.
- Western free PDNS can be dead or gutted for the same target (viewdns, bufferover,
  threatminer, rapiddns; mnemonic may only hold recent CF rows; crt.sh intermittently 502 —
  retry via the JSON endpoint `https://crt.sh/?q=%25.<domain>&output=json`).

## Liveness tests for a candidate origin
- Direct TCP on 80/443/8080/8443/8888/22 with correct `Host`/SNI. "Connection refused" is
  information; "timeout / 100% packet loss" smells like a CDN-only allowlist.
- Fetch it through a CF-side relay (`api.allorigins.win/raw?url=`, `api.codetabs.com/v1/proxy?quest=`).
  A timeout/5xx there means Cloudflare itself cannot reach the origin either.
- `https://<name>/cdn-cgi/trace` prints `ip=` — confirms which egress IP Cloudflare sees
  (also the fastest way to prove a chained proxy is actually pinned).
- Under CF "Full (strict)" the origin must serve a certificate for the hostname, so a cert
  index search (e.g. Shodan `ssl.cert.subject.cn:"<domain>"`, excluding Cloudflare ASNs) can
  surface the real host.
- Hostnames recovered from CT logs are frequently dead (NXDOMAIN) on a mature target —
  resolve the whole set anyway, but expect a mostly empty result.

## Deciding "dead" vs "CF-only allowlist" (validated)
- Fetch the candidate through a service that **itself runs on Cloudflare's network** (a
  CF-Worker-hosted fetcher, e.g. Microlink `api.microlink.io/?url=<url-or-ip>`). An origin merely
  firewalled to CF ranges answers; a decommissioned host returns `statusCode: null`.
  **Always fetch a known-live control URL in the same run** — a null result with no control proves nothing.
- A `/24 neighbourhood sweep` (80/443/8080/8443/8888) with a per-IP spoofed `Host: <target>` is the
  cheapest way to answer "did it move next door?". A live subnet with no matching service = it left
  that provider entirely.

## Check the domain's registration dates FIRST
- `whois` Creation/Updated Date can invalidate an otherwise convincing trail: in the reference case the
  domain had been **re-registered the previous day**, so the months-old direct A records belonged to the
  *previous* registration and every one of them was dead. Read the creation date before spending hours
  on historical IPs — "the origin moved" is not the same as "the origin is hidden".

## Don't be fooled
- A 200 with the "right" product title can still be a Chinese anti-DDoS/WAF front (e.g.
  `Server: ADM/2.1.1`) or a reseller page, not the origin.
- IP-history "same-IP peers" sidebars are polluted by shared high-defense ranges: several
  unrelated sites sharing a same-day IP set means shared edge, not a single origin.
- A registrar/parking IP (GoDaddy parking) is not an origin.

## Reaching China-facing services (CONNECT chaining)
Onshore proxies fronted by nginx/Tengine (ports 8080/3128) often answer a bare
`CONNECT host:443` with HTTP 500 and return 200 once a normal browser `User-Agent` is sent on
the CONNECT request. If a chained proxy works for curl but fails for the browser, test the
provider's other ports and expect upstream slowness rather than a protocol error.
