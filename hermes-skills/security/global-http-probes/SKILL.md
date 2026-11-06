---
name: global-http-probes
description: "Use when testing geo-blocking or origin reachability."
version: 1.0.0
tags: [recon, reachability, geo-blocking, globalping, cdn]
---

# Global HTTP Probes

Use when you need to answer “is this host reachable from country X?”, “is this a geo-block or an IP allowlist?”, or “is the origin down or only blocking my egress?” without owning a proxy in every region. Globalping runs measurements from distributed probes and returns status codes, timings, headers, and sometimes the body.

This is **measurement**, not a proxy: you cannot use it to send authenticated requests or browse a target. Use it to characterize reachability, then pick a real egress path (WARP, SOCKS5, regional VPS, or an allowlisted pivot).

## Quick procedure

1. Create an HTTP measurement with explicit probe locations.
2. Poll the measurement ID until `status` is `finished` (or timeout).
3. Read per-probe results: `result.status`, `statusCode`, `timings`, `headers`, `rawBody`.
4. Compare regions. Combine with an independent liveness source (InternetDB, FOFA, Shodan) before concluding the host is down.

## Create a measurement

```bash
curl -sS -X POST https://api.globalping.io/v1/measurements \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "http",
    "target": "203.0.113.10",
    "locations": [{"country": "CN"}, {"country": "HK"}, {"country": "JP"}],
    "limit": 10,
    "measurementOptions": {
      "protocol": "HTTPS",
      "request": {
        "method": "GET",
        "path": "/",
        "host": "target.example.com"
      }
    }
  }'
```

`target` can be a hostname or IP. `request.host` overrides the HTTP Host header/SNI name when probing an IP directly. `locations` accepts `country`, `city`, `asn`, or `magic`; keep the list small and set `limit` to cap probes. Anonymous requests work but are rate-limited; a token can be supplied via `Authorization: Bearer $GLOBALPING_TOKEN` if configured.

## Poll

```bash
curl -sS https://api.globalping.io/v1/measurements/<id>
```

Poll every 1–2 s until `status` is `finished`; do not hammer. Each result includes a `probe` object (country/city/network/asn) and a `result` object. On success you normally get `statusCode`, `headers`, `rawBody` and timings; on connect timeout `statusCode` is absent/null and `status` is failed/timed out.

## Interpretation

| Pattern | Meaning | Next move |
|---|---|---|
| All probes time out, but InternetDB/FOFA shows the host up | Strict IP allowlist or network ACL, not geo-block | Use an allowlisted egress/pivot; stop hunting generic proxies |
| CN probes fail, US/EU probes succeed | Geo/CDN policy or China-side filtering | Try an in-country egress or a CDN edge that serves CN |
| All probes get 200 but your host gets 403/timeout | Your egress IP is blocked, not the target down | Rotate egress; verify with WARP/SOCKS |
| Some probes 200, some 403 | WAF/CDN rule varies by PoP or source reputation | Compare headers/body per probe; test the same PoP path |
| All probes fail and independent liveness also fails | Host/service is down or firewall drops everyone | Re-check ports and DNS before more probing |

## Why not check-host alone

`check-host.net` is useful for a quick multi-node check, but its node list is not a controlled country sample and it has no reliable mainland-China probes. Do not use “check-host timed out” as proof of a China geo-block. Use Globalping locations with explicit `country: CN` (plus HK/TW/SG/JP controls) when that distinction matters; use check-host only as a second opinion.

## Pitfalls

- The probe resolves the target from its own network; CDN/geo-DNS answers can differ from your resolver. Test the exact hostname and, separately, the origin IP with `request.host`.
- A timeout is not proof the service is dead. Cross-check with a passive liveness source and a second region.
- Do not treat Globalping as an authenticated client or proxy; it cannot carry your cookies, client certs, or internal DNS.
- Keep `limit` small and reuse a measurement; repeated large anonymous requests hit rate limits.
- For HTTP measurements, set `protocol` explicitly (`HTTP`/`HTTPS`); the default may not match the service.

## Verification checklist

- [ ] Measurement created with explicit countries and small limit
- [ ] Polled to `finished`; per-probe status/timing captured
- [ ] Independent liveness source checked before calling a host down
- [ ] Geo-block vs IP-allowlist conclusion matches the region matrix
- [ ] Egress/pivot chosen from the conclusion, not from a generic proxy list

## References

- `references/globalping-api.md` — exact request/poll payloads, response fields, location filters, and a worked CN/HK/JP allowlist example.
