## 6. Client-side server list = alternate, often weaker, entry points

Decode the class that builds the client's base URL (`baseUrl(X.y())` -> storage getter -> a
hardcoded obfuscated literal) and decode the whole server list. Clients ship 3-6 entries: CDN
domain, one or more direct `IP:port` backends, and an ops/relay host.

- Probe every entry with the same route set. An alternate edge frequently has **no edge WAF rule**,
so administrative paths answer normally.
- **The rule sets differ *per path*, not per entry.** An origin is not simply "an edge with the rules
turned off": it applies its **own** blocklist. Expect a split — the edge blocks the whole business
surface while the origin serves it, and both block the token-minting/admin paths. So build a
**path × ingress matrix** (CDN domain; each origin `IP:port` over BOTH HTTP and HTTPS) against a
real recovered endpoint list, and classify every cell: WAF page / business JSON / `404` (route
reached the app) / timeout. Only a path blocked in **every** cell is genuinely closed.
- **Re-test blocked paths with a valid session header.** Some rules match the request *shape*, not
the URL: a path that returns the WAF page for an anonymous `{}` body answers normally once
`Authorization` and the app's own token header are set. Cheap — do it before writing a path off.
- **A resolved per-path edge rule is a standalone finding, not a nuisance.** It means the CDN's URL
rules are the de-facto access control for that surface. The campaign consequence outranks the bypass
itself: **every endpoint previously recorded as "blocked/closed" must be re-tested through the
origin**, because that verdict was only ever true at the edge.
- `404` = route not configured there; `504` = route configured but upstream dead. Both are useful
and distinguishable from the WAF 403 page.
- Resolve each entry's PTR: a dynamic residential ISP hostname marks operator infrastructure (a relay), not a CDN edge.
- **`--resolve` over Tor reaches origins that IP-whitelist their CDN.** `curl -sk --socks5-hostname 127.0.0.1:9050 --resolve domain:443:ORIGIN_IP https://domain/path` makes the origin see a whitelisted (CDN/Tor) source and answer directly. This shows responses the edge never gives: real nginx/Go 404 where the edge returned an SPA-fallback 200, and route-existence (308 redirect / raw framework 404) for paths the edge disguised. Use for path-existence probes — and treat any gateway block page from ONE ingress as unproven for the route.
- **Origin vhost matrix**: same IP with different `Host:` values (`www.domain`, bare `domain`, `admin.domain`, `api.domain`) splits services; combine with BOTH HTTP and HTTPS ports. 404 (nginx default server) vs 308 vs real app HTML tells you which vhost is which. The origin applies its own rules — a path blocked at the edge can answer from the origin and vice versa.
relay), not a CDN edge.

