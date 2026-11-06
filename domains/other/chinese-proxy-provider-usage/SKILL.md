---
name: chinese-proxy-provider-usage
description: "Use when using Chinese proxy APIs for authorized tests."
version: 1.0.0
tags: [proxy, china, dmdaili, kuaidaili, http-proxy, socks5]
---

# Chinese Proxy Provider Usage

Use this when a task needs a mainland-China HTTP/SOCKS proxy and the user supplies a provider API link (dmdaili, kuaidaili, etc.) or a list of `ip:port` proxies.

## dmdaili API

Base endpoint: `http://api.dmdaili.com/dmgetip.asp`

Query parameters:
- `apikey` — API key from the provider panel (required)
- `pwd` — API password (required)
- `getnum` — number of IPs, max 200 (default 1)
- `httptype` — `1` HTTP, `2` HTTPS, `3` SOCKS5, `4` adaptive
- `geshi` — `1` txt, `2` JSON
- `fenge` — separator: `1` CRLF, `2` CR, `3` LF, `4` tab, `5` custom (`fengefu`)
- `operate` — region; `all` = all regions

TXT response is one `ip:port` per line. JSON response:
```json
{"code":0,"data":[{"ip":"1.2.3.4","port":15001,"endtime":"2026/10/19 12:00:00"}],"msg":"0","success":true,"num":1}
```

Provider status codes worth distinguishing: `600` too frequent, `601` plan expired, `602` bad pwd, `603` empty apikey, `604` region down, `605` auto-whitelist in progress (~1 min), `606` traffic limit.

## Whitelist rules

- dmdaili auto-whitelists the **source IP that requested the API**; allow ~1 minute before use.
- Manual whitelist API (documented by provider; `appkey` = registered phone, `sign` = API `pwd`):
  - add: `https://www.dmdaili.com/api/white/add?appkey=...&sign=...&ip=...`
  - delete: `https://www.dmdaili.com/api/white/del?appkey=...&sign=...&ip=...`
  - query: `https://www.dmdaili.com/api/white/sel?appkey=...&sign=...`
- Do not put credentials in reports, chat logs, or skill files; pass the API URL to the fetch script only.

## Geo restriction (verified 2026-10-19)

- dmdaili documentation explicitly says **overseas, Hong Kong, Macau, and Taiwan users cannot use** the service. Auto-whitelisting the API-caller IP does **not** bypass this.
- From a Hong Kong VPS, all 200 returned `ip:15001` endpoints timed out at TCP level; adding `apikey:pwd`/`pwd:apikey` auth and trying SOCKS5 made no difference. A Tor exit also failed.
- **Do not misdiagnose this as wrong password, wrong protocol, or a dead proxy list.** Test TCP reachability from the intended source first; if it fails and the provider forbids overseas/HK, the fix is a mainland landing host/jump box or a provider that allows overseas sources.

## Authenticated rotating proxy (bitip, verified 2026-10-19)

Some providers use a single gateway with per-request rotation and `host:port:username:password` credentials, e.g. `proxy-as.bitip.com:10000:user:pass`.

- Use `http://user:pass@host:port` for the HTTP exit, `socks5h://user:pass@host:port` for the SOCKS5 exit; the two exits can have **different countries** (observed HTTP = mainland China Mobile `49.131.110.191`, SOCKS5 = Hong Kong `1.65.199.166`).
- The gateway may rotate the exit per connection. Read the exit IP before each target test; do not assume a previously working exit is stable.
- `requests` `proxies={"http":..., "https":...}` works for both; for SOCKS5 use `socks5h://` so DNS is resolved at the proxy.
- **Session pins the exit IP (verified 2026-10-22)**: six consecutive `api.ipify.org` calls through one `requests.Session` all returned the same IP. One Session = one exit IP = one share of any per-IP quota; a new Session/new connection gets a new IP. Against targets with "5 attempts per IP per 15 min" locks, send one 5-attempt batch per Session, then close it and open a new one.
- **Region endpoints share the account and a small pool**: `proxy-as`, `proxy-us`, `proxy-eu` all resolve (Tencent CLB) with the same user:pass; `proxy-sg/hk/jp/uk/de` did not resolve. Treat them as one pool, not independent: after a 10k-login run against one target, **all three** returned the same lockout error.
- **Estimate pool size cheaply**: under a per-IP 5-attempt lock, a throttled 200-word batch yields roughly `done ≈ pool × 5` and `limited ≈ pool`. Observed `done 78 / lim 30` → pool ~20-30 IPs, i.e. ~100 attempts per 15-minute round. Do not plan a 100k dictionary on such a pool; a large-pool residential provider is required.
- **Proxy→China origin is slow and fragile**: 2-15 s per request through US/EU exits; 300 threads produced 1522 connection errors in 51 s with only 5 successes. Use 20-30 threads and 30-60 s timeouts for mainland origins.
- **Distinguish "proxy dead" from "target blocked the segment"**: if `api.ipify.org` still returns 200 through the proxy but the target returns `000` on every new exit, the target is dropping that proxy's IP ranges (observed after a high-concurrency burst; recovered after ~10-15 min). Cool down or switch provider instead of rotating harder.
- Verify reachability with a neutral endpoint first, then the target. Reaching the target's origin does **not** mean a separate WS/API gateway on another IP will also accept the same exit; test each host independently.

## HTTP CONNECT 200 is not proof a port is open

When using an HTTP proxy to scan non-HTTP ports with `CONNECT host:port`, some providers return `200 Connection established` for **every** port, including 22/3306/6379/9200 on hosts where those ports are actually closed. In this session a CONNECT scan reported *all* tested ports open on four different IPs — a false positive.

- Treat CONNECT 200 only as "proxy accepted the request", not as "target port is open".
- Confirm with an actual protocol handshake: `curl` to an HTTP(S) URL, `mysql` client / MySQL handshake, `redis-cli PING`, `openssl s_client`, or a TCP banner read.
- If every port returns 200, stop the scan and switch to application-level probes.

## Workflow

1. Fetch and parse the API (script below), never paste the API URL into reports.
2. Check the provider's geo policy **before** testing hundreds of IPs; one TCP test from the intended source is enough to reveal a geo/whitelist block.
3. From a valid source, test one proxy to a neutral endpoint (`http://httpbin.org/ip`), then to the real target.
4. Try auth forms in order: no auth, `apikey:pwd`, `pwd:apikey`; try HTTP CONNECT and SOCKS5 if the provider advertises both.
5. Only after a working exit is confirmed, use it for the actual authorized target; rotate only when the target blocks the exit.

## Script

`scripts/fetch_dmdaili.py` — fetch a dmdaili API URL, parse `ip:port`, dedupe, write a list, and print counts. It does not hardcode credentials.

## Related

- `ruoyi-framework-pentest` §15: Chinese RuoYi/WS gateways may be mainland-only; use this skill to choose an exit.
