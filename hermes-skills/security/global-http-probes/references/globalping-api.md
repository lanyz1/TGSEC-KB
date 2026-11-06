# Globalping API — practical reference

Base: `https://api.globalping.io`

## Create HTTP measurement

```bash
curl -sS -X POST https://api.globalping.io/v1/measurements \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "http",
    "target": "api.example.com",
    "locations": [
      {"country": "CN"},
      {"country": "HK"},
      {"country": "JP"},
      {"country": "US"}
    ],
    "limit": 15,
    "measurementOptions": {
      "protocol": "HTTPS",
      "request": {
        "method": "GET",
        "path": "/",
        "host": "api.example.com"
      }
    }
  }'
```

For an IP target behind a vhost:

```json
{
  "type": "http",
  "target": "203.0.113.10",
  "locations": [{"country": "CN"}, {"country": "HK"}],
  "limit": 10,
  "measurementOptions": {
    "protocol": "HTTPS",
    "request": {"method": "GET", "path": "/", "host": "target.example.com"}
  }
}
```

The probe sends TLS SNI/Host from `request.host`, so this tests the virtual host on that IP rather than the bare IP certificate.

## Poll

```bash
curl -sS https://api.globalping.io/v1/measurements/<id>
```

Repeat until `status` is `finished`; typical fields:

```json
{
  "id": "...",
  "type": "http",
  "status": "finished",
  "results": [
    {
      "probe": {"continent":"AS","country":"CN","city":"Beijing","network":"...","asn":12345},
      "result": {
        "status": "finished",
        "statusCode": 200,
        "headers": {"content-type": "text/html"},
        "rawBody": "...",
        "timings": {"total": 123}
      }
    }
  ]
}
```

On connection failure, `statusCode` may be absent and `result.status`/error fields show the timeout. Do not assume a 0 status is an HTTP 0; inspect the result object.

## Location filters

- `{"country":"CN"}` — mainland China probes
- `{"country":"HK"}`, `{"country":"TW"}`, `{"country":"SG"}`, `{"country":"JP"}` — Asian controls
- `{"city":"Frankfurt"}`, `{"asn":12345}` — narrower probes
- `limit` caps how many probes run; keep 5–15 for diagnosis, not hundreds.

## Worked example: classify a hard timeout

Target: an origin IP that FOFA/InternetDB says is alive (Ubuntu + nginx + SSH), but direct connections from the local host and eight SOCKS5 proxies all time out.

- Globalping HTTP probes from CN, HK, TW, SG, JP, plus US/EU: all TCP connect timeouts.
- Independent InternetDB: ports 22/80/443/7000 open, host up.
- Conclusion: **strict IP allowlist / network ACL**, not a China geo-block and not a dead host. A generic proxy pool is useless; use an allowlisted egress or pivot.

Contrast: if CN probes time out but US/EU probes get 200, suspect geo/CDN policy; if all probes get 200 while local egress gets 403, suspect local IP reputation or a WAF rule keyed to your source.

## Caveats

- Globalping probes are measurement agents, not a browsing proxy; no cookies/client certs/internal DNS.
- The probe's resolver may see a different CDN edge than yours; test both hostname and origin IP + `request.host`.
- Anonymous use is rate-limited. If a token is available, send `Authorization: Bearer <token>`; otherwise reuse one measurement and poll instead of re-creating.
- `rawBody` can be large/truncated; use it for markers/titles, not full data dumps.
