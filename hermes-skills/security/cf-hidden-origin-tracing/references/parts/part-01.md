# cf-hidden-origin-tracing 全文 第 1/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Verified techniques (each produced a real finding)

### 1. Historical A records come from Chinese PDNS, not Western ones
Free Western passive-DNS (and `.cn/.cc/.xin` names in general) return zero. `ip138`-family CN
services **do** carry history — reach them from a CN/HK egress and parse the history table for the A
records with dates. That is how an operator's previous generation of servers is discovered.
**Never take sidebar "related IPs" as data**: on these sites the sidebar is ad/SEO pollution.

### 2. WHOIS Creation Date first, history second
Check `whois <domain>` **before** believing any IP history. A domain **re-registered days ago**
means the entire previous infrastructure is stale by definition (different registrant, different
NS) — say so and stop re-testing those old IPs. A `Creation Date` + `Updated Date` minutes apart is
a fresh deployment, mid-migration.

### 3. CF-network egress probe — and why a `null` is NOT proof of death
A candidate origin that ignores you may just be allowlisting CF source IPs — so ask **from inside
Cloudflare**. Any public fetch service that runs on CF Workers (e.g. `https://api.microlink.io/?url=…`)
is a CF-internal vantage. But a vantage only counts if the request actually reaches the origin's
vhost, and **`fetch("https://<ip>/")` sends SNI = the bare IP**, which a vhost-based nginx rejects at
the TLS layer — the fetch fails no matter how alive the box is. That failure surfaces as
`statusCode: null` / connection error, i.e. **the exact signature people read as "dead"**.
So a `null` from an IP-URL fetch is **uninterpretable on its own**. Treat "dead" as UNPROVEN until the
probe controls **Host and SNI** and the control goes through the *same* code path:
- Primary liveness test: **HTTP :80 with an explicit `Host: <site>`** — no SNI involved, nginx still
  routes on the Host header.
- For HTTPS you need a client that sets Host (and ideally SNI) — your own Worker (section 10) or any
  proxy that forwards your `Host` header. Microlink/`fetch("https://ip/")` cannot.
- Pair every candidate with a known-alive control **fetched the same way**; a control that only
  succeeds *without* a Host override does not validate the candidate's negative.
- **Validate the control itself on both ends: is it *listening*, and is it *reachable from the
  prober's network*?** A whole batch of "all candidates dead (522)" was pure noise because the
  control listener sat behind a host firewall (`ufw` default `INPUT DROP`, one port open) — nothing
  outside could reach it, so the batch said nothing about the targets. Check `ss -ltnp` for the
  listener **and** probe the control from an external, non-CF vantage before trusting any negative
  from that batch.
- Only then: `null` => dead or firewalled-to-all, an answer => alive — then prove identity by
  fingerprint.
**Consequence to state out loud:** every "dead" verdict reached from a non-CF vantage (own box
curl, `/24` sweep, IP-URL fetch) is provisional. A CF-only allowlist makes a live origin invisible to
all of them — so "all candidates are dead" does NOT mean the origin is off these IPs.
Do not bother with generic public CORS/CF reverse proxies (`cors.workers.dev` etc.) as your egress:
validated as useless — they rate-limit hard (429) even for known-alive IPs, so no usable control.

### 4. Neighbourhood sweep — cheap, but only trust a fingerprint match
Re-numbered origins hide in the old range. Sweep the historical `/24` on 80/443/8080/8443, then
re-issue with the target `Host:` header and compare the response shape (title, favicon hash, error
body). Shared 高防/CDN/WAF ranges answer everywhere — **a bare 200 is not a hit**; no fingerprint
match means no answer, and the honest conclusion is "origin is not in this range".

### 4b. Anycast-edge vs origin — the decisive test (run it before you write "origin")
Candidates handed to you by IP-history sources are very often **Cloudflare's own anycast edge**, and
an edge answers for *any* CF customer. Three tells, cheapest first:
- **Cross-host test (decisive, one command).** Ask the candidate IP for a *different* CF-hosted
  hostname: `curl -sk --resolve example.com:443:<ip> https://example.com/`. If the box serves
  **example.com's** page, it is a generic CF edge node, not your origin. Same idea in a raw
  socket/TLS probe: swap the SNI.
- **Certificate issuer.** `openssl s_client -connect <ip>:443 -servername <site>` returning a
  public-CA cert that covers *your* hostname (Cloudflare Universal SSL; seen in the wild as
  **Google Trust Services WE1**) is the **edge's** certificate. An origin normally serves its own.
- **Headers on a fingerprint match.** `server: cloudflare` / `cf-ray: …-<IATA>` means you hit the
  edge. Filter these out of every bulk sweep, or each CF-anycast IP becomes a false hit.
**Consequence: CN-PDNS "historical A records" can themselves be CF edge IPs** (CF announces out of
Alibaba-HK space among others), so a dated A record is *not* origin evidence until the cross-host
test clears it. In the worked case this demoted three long-standing "origin candidates" to edge nodes
and let the external line be closed honestly.

### 5. CT logs: the issuing CA dates the infrastructure
Pull recent certs per FQDN (crt.sh family, searching hostnames you discover in later CT entries).
A **Chinese CA (e.g. TrustAsia)** issuing for a hostname that now sits behind CF proves that
hostname was served **directly from a CN/HK box at that time** — a different generation from today's
CF-only deployment. Sub-domains found only in CT and already `NXDOMAIN` are migration debris worth
noting, not targets.

### 6. The gateway labels its own gates — read the headers
Custom Worker/site gateways leak their control layers in response headers, e.g.
`access-control-expose-headers: X-Whitelist-Block, X-Turnstile-Block, X-RateLimit-Block, X-Handshake-Block, X-Origin-Block`.
Then confirm each one: **probe a nonsense path** -> `x-path-block: 1` (the Worker has its own path
whitelist); probe an authenticated endpoint unauthenticated -> `x-whitelist-block: 1` plus
`{"code":403,"msg":"请先登录"}`. Now you know exactly which layer refused you and that config
endpoints need a real session — not that the endpoint is missing.
- **The exposed list is a *declaration*, not an observation.** Grep'ing a header name out of
  `access-control-expose-headers` will "find" gates that were never sent (`x-origin-block` was pure
  self-deception — it only matched the expose line itself). Trust only a header read on its own
  `x-…:` line.
- **`x-path-block` on a 200 is not a bypass.** A path that escapes the Worker's prefix gets
  normalised and served the SPA fallback (`index.html`, a few hundred bytes): you hit the edge, not
  the origin. Dot-segment tricks only "work" when normalisation lands the path **back inside the
  proxied prefix** — `/<prefix>/%2e%2e/<prefix>/<route>` reaches the origin (and the auth gate then
  stops you, which is the useful signal), while `/<prefix>/%2e%2e/<other-route>` is just index.html.
  Always compare `content-length` against the known SPA shell size before calling anything a bypass.
- **Determining "edge or origin?"** — a path that returns the SPA shell is edge-generated; one that
  returns the origin's JSON error envelope (`{"code":…,"msg":…}`) was proxied. That distinction is
  how you map which prefixes the Worker forwards without any credentials.
- **The front end's own error copy is an architecture oracle.** A bundle containing
  「源站超时，请稍后重试」 ("origin timed out, retry later") is announcing that it is a proxy layer in
  front of an origin — i.e. the origin is not on the public internet at all and the hunt belongs
  in-app. One grep over the user-facing strings, before any scanning.

### 7. Decode the session cookie, then verify your own egress against it
Session cookies often bind the client IP. Example seen: `__hs = base64( "hs|" + clientIP + "|" + ts + ":" + HMAC )`
with a 300 s Max-Age. Before concluding "session invalid": fetch `/cdn-cgi/trace` **through the same
egress** and compare its `ip=` with the IP the origin recorded in the cookie. If they match, the IP
layer is innocent — move on instead of re-engineering the protocol.

### 8. Stable egress is a prerequisite (Tor HTTPTunnelPort pinning)
IP-bound sessions and single-use captcha tokens make rotating exits useless. Pin one circuit:
`HTTPTunnelPort 8118` in `torrc` + a **fixed** proxy user:pass (the credentials act as the circuit
isolation key) => the same exit IP for the browser and for `curl` across processes. Verify with
`/cdn-cgi/trace` before and after. Notes:
- Firefox/Playwright **cannot** use SOCKS5 with authentication; give it the HTTP tunnel
  (`http://user:pass@127.0.0.1:8118`) and point `curl` at the same one — one exit, two clients.
- Plain `SocksPort 9050` is stable per destination for a while but **will rotate** — tokens minted
  on one exit fail on another, so tag every token/config batch with its exit IP.
- Datacentre HK exits generally cannot pass Turnstile; Tor can.

### 9. Know the boundary: pivot to in-app config
When the front end is CF Pages + a Worker proxying to the origin, **external discovery is bounded**.
The origin's coordinates live in the operator's own panel:
`/monitor/server` (hostname, OS, cloud vendor), `/system/config/list` (endpoint URLs, IP allowlists),
`/phone/config/list` or device/card-pool lists (device IPs), `/api/*/list` for agent/site records.
Those need an authenticated account of sufficient privilege, so the real work becomes *getting that
account* (see `password-spray-lockout-bypass`) — say that to the user explicitly rather than
reporting "still scanning".
**This path does pay, and it is worth saying so.** In the worked case, in-session spraying landed a
main-panel account; with its `sa-token`: `/vim/server/config` 200, `/vim/server/notices` 200,
`/vim/server/users/my` 200, `/vim/server/chat/list` 200 (objects carrying card/device ids),
`/csapi/wsOnline` 200. The operators' own notice named **three physical 机房 and their card inventory**
— the asset the origin-IP hunt existed as a proxy for. When the user keeps demanding "the source IP",
this is the deliverable to reframe toward.

### 10. Own the egress: deploy a fetcher Worker on a throwaway account
A tiny Worker on **any** free account (never the operator's) is the only probe that gives you
CF-network egress *and* an explicit `h=` host override — the two things public fetch services cannot.
Shape: `GET /?u=<url>&h=<host>` -> `fetch(u, {headers: {Host: h}})` -> return
`{status, ms, server, ct, len, body.slice(0,800)}`; template `templates/cf-egress-fetcher.js`.
If the runtime refuses the `Host` override it returns the error verbatim — then fall back to
`http://<ip>/` (no SNI) and read it as liveness + fingerprint only.
**Get a deployable token — verify scope before promising the user anything:**
- `cfat_` tokens are purpose-built. An **R2-scoped** token can manage buckets and nothing else.
  Check with `GET /client/v4/user/tokens/verify`, then actually attempt the capability you need
  (`GET /client/v4/accounts/<id>/workers/scripts` => `Authentication error` when unscoped).
- A token carrying a future **`not_before`** is inert until that instant. Read the timestamp and
  diff it against `date -u` *before* reporting "your credentials don't work" — the honest line is
  "inert for another 3h49m, and scoped away from Workers anyway".
- **R2 S3 credentials (Access Key ID / Secret / endpoint) are not API tokens.** They cannot deploy a
  Worker or read zone config; holding them unblocks nothing in this workflow.
- Ask for: Custom Token -> **Account -> Workers Scripts -> Edit** (+ Account Settings -> Read),
  account-scoped, **TTL and Start date left EMPTY**. Fastest of all: have the user paste the Worker
  into the dashboard and hand back the `*.workers.dev` URL — zero credential exchange.
- One Worker, several wins in one batch: re-test every historical candidate IP **and** the second
  CF-fronted host in the case (admin/control panel), each with its own `h=`.
- **Upgrade the Worker to a raw-TCP prober (`cloudflare:sockets`) — it buys what `fetch` cannot.**
  Shape: `?op=tcp&l=<ip:port>,<ip:port>,…` -> `connect()` each and return `{open, ms}` (millisecond
  liveness from inside CF, batch-scannable); `?op=http&ip=&port=&h=` -> write a raw HTTP/1.1 request
  with an explicit `Host:` and read the first bytes back (the Host-controlled :80 probe §3 needs).
  Verified limits: `connect()` **refuses raw TLS** (`secureTransport:on` -> errors with *"consider
  using fetch"*), so HTTPS still goes through `fetch` + `<ip>.nip.io`; naked-IP `fetch` -> `error
  1003`; CF's own IPs are rejected by the runtime; a silent target just burns the ~30 s edge timeout
  and looks like `{}`/522. Keep `Protect with Cloudflare Access` **off** or every probe 302s to a
  login page.

### 11. Make the origin dial YOU — the outbound-callback leak

When every passive channel is empty, stop looking for a *record* of the origin and start
**asking the origin to open the connection**. Any user- or admin-controllable outbound target
behind the CDN will dial an IP you own:

| Feature on the edge-served app | Field you control | What comes back |
|---|---|---|
| PHP/Java installer step 2 («数据库配置») | `db_host` / `db_port` | MySQL client handshake **from the origin's real IP** |
| Webhook / callback / notify URL | URL | HTTP request from the origin IP |
| SMTP / 短信 / 推送 configuration | host:port | TCP connect from the origin IP |
| Image import / 远程下载 / RSS 采集 | URL | outbound fetch from the origin IP |
| 运维 agent (`linux-ops-agent`, RMM, Sentinel-style) | its `-state`/config + server URL | proves the fleet's control plane, see below |

Recipe (verified, 2026-09): raise a listener on your own box (`nc -lvnp <port>` is enough for the
first proof — you only need the peer IP), open the port in **your own** firewall (`ufw allow
<port>/tcp`; default `INPUT DROP` silently eats the callback and you will blame the target), verify
inbound reachability from a third-party port checker, then submit the form with `db_host=<your ip>`
and read the source IP off the connection. **That IP is the origin**; it is also the fastest way to
turn a blind origin hunt into a working attack surface (the same request can often complete the
exploit — see `card-merchant-platform-pentest` §八).

Then **prove which vhosts live on that machine before touching them**:
```bash
for h in target.example sibling.example <other candidate hosts>; do
  curl -sk --resolve "$h:443:<origin-ip>" -o /tmp/o -w "$h %{http_code} %{size_download}\n" "https://$h/"
done
```
Answers that match the CDN-fronted content = that vhost is served from this box = same machine =
in scope. A `502`/`error code: 502` means that host's backend is elsewhere. This one loop is what
separates "the operator's other property" from "the same server", and it is the evidence to quote
when the user asks why you did or did not keep going.

### 12. `_guard` / JS-PoW CDN nodes: the edge itself is a target
Small CN CDNs (seen: 不死鸟CDN `bsncdn.ai`) ship a `/_guard/html.js?js=click_html` + `/_guard/pow.js`
+ `/_guard/click.js` (data-pow-bits) click-and-PoW challenge, plus `x-cache-status: MISS from L1:263`
/ `via: L1:263` node headers, and a 504/530 page that **prints the node IP and the origin's
reachability state** ("节点IP … 回源请求超时 / 域名未配置"). Read those error pages for free
architecture. A burst (>100 fast requests) or a full nmap gets your egress null-routed by the guard
(TCP dead, everything `000`, no RST) — rotate to Tor and keep the rate civil; the ban is on the
edge, not the origin, so the origin stays reachable through another node/exit.

### 13. Origin fingerprints — and the two probe traps that manufacture a false hit

- **CF passes the origin's `Last-Modified` through** (`cf-cache-status: DYNAMIC`), so it is a free
  *file-level* fingerprint of the origin. Use it to (a) test whether a candidate IP serves the
  target's vhost and (b) **cluster a whole site farm by shared origin file**: fetch
  `https://<domain>/index.html`, keep `Last-Modified`; identical stamps = same box/deploy. In the
  worked case this separated our own farm box (`2026-09-02 16:30`) from the target (`2026-08-11
  09:10`) in one pass, and killed the "it's on our box" hypothesis.
- **Marker-file test (decisive in both directions).** Write a uniquely-named file into the docroot of
  a box you control (`/www/wwwroot/<site>/<rand>.txt`), then fetch
  `https://<target-through-CF>/<rand>.txt`. `404` through the edge **proves that box is not this
  hostname's origin**; `200` with your token proves it is. A `Host:`-header `200` from the candidate
  box proves nothing — that is usually the catch-all default vhost answering.
- **Trap 4 — a CDN-cached response is not origin evidence, so cache-bust before fingerprinting.**
  `cf-cache-status: HIT` (with an `age:`) means the bytes came out of **Cloudflare's** cache — the
  origin may not serve that file at all. In the worked case the "origin fingerprint" icon arrived as
  `HIT, age: 169316`; re-requesting it with a throwaway query (`?cb=$RANDOM`) forced a MISS and made
  the origin answer for real — it **did** serve the icon (`200/5644`) but **404'd** the fleet's own
  `aiz-core.css`, which *disproved* the "these boxes are the origin" hypothesis that had just been
  built on the cached read. **Rule: every request used as an origin fingerprint goes through a
  cache-buster**; the un-busted one is a *cache* reading, not a *server* reading. (The opposite
  direction is fine — `last-modified` and the nginx ETag `W/"<hex(mtime)>-<hex(size)>"` do pass
  through from the origin and give a free file-level fingerprint.)
- **Trap 1 — HTTPS vhosts are selected by SNI, not by `Host`.** `curl -H "Host: <site>" https://<ip>/`
  hits the *default* vhost and cheerfully returns the wrong site (and the wrong `Last-Modified`).
  Force SNI: `curl --resolve <site>:443:<ip> https://<site>/`.
- **Trap 2 — a proxy env var silently discards `--resolve` and every self-IP check.** With
  `ALL_PROXY`/`HTTPS_PROXY` set (Tor in this environment) the *proxy* does the DNS, so `--resolve`
  never applies — the "candidate origin" answers with Cloudflare's own block page. The same trap makes
  `api.ipify.org` return the **Tor exit**, not your IP. Always
  `env -u ALL_PROXY -u all_proxy -u HTTPS_PROXY curl --noproxy '*' …` for both.
- **Trap 3 — `grep <target-domain>` over a Host-spray response is NOT a hit test. Host reflection
  manufactures hits out of nothing.** Plenty of apps echo the request's `Host` back into the body:
  ZBlog/CMS emit `<link rel="canonical" href="http://<host>:443/">` and nav links like
  `<a href="https://<host>/index/user/index">会员中心</a>`; small CDN error pages print the Host in
  `<span class="info-value">{host}</span>` right next to **your own egress IP**. Every one of those
  yields a body containing your target hostname with **zero** relationship to the origin.
  **The decisive control — run it on EVERY candidate, it is one command:** request the same candidate
  twice with `Host: <target>` and `Host: <random-nonexistent-zzz>` and compare the **md5 of the body**,
  never the status and never a substring. Same md5 ⇒ vhost-agnostic *default* vhost ⇒ the candidate is
  irrelevant, whatever the body appears to say. Different md5 ⇒ a real vhost match ⇒ *then* fingerprint
  (title / favicon / `Last-Modified`). In the worked case this cleared 11/11 apparently-promising `200`
  responses, a whole 59-node CN CDN cluster, and a `500`-signature candidate in one pass — and it
  caught the one near-miss where a **~5-byte length delta** (a dynamic timestamp on the page) had
  masqueraded as a per-host vhost. Treat a few-bytes length difference as noise, not a match.
- **A one-off "contains <target>" that will not reproduce is an LB artifact.** `156.248.73.237/.99`
  and `206.238.198.62` each returned a `404/258` containing the target hostname exactly once, then a
  stable `404/138` on every later request — different backends behind a load balancer, or a
  Host-reflecting Apache error page. **Re-request the same candidate with the *same* Host 3-5× and
  require stability** before treating any difference as a vhost; instability of a single Host is
  itself the tell that the body is dynamic.
- **Bulk-identical `503`/`530` across many IPs is a generic port response, not a binding.** The same
  md5 control settles it instantly: if every Host — including `baidu.com` — returns the byte-identical
  page, those nodes know nothing about your target. Never report "the CDN nodes are bound to the
  target" off a status code.
- **Know your own address before hunting anyone else's**: `ip -4 addr`. A "candidate origin"
  (reverse-IP, CNAME, PDNS) that equals your own base means you are about to attack yourself —
  see `pentest-execution` §0b for the full self-target guard.

### 14. Fingerprinting the origin stack when the IP itself is unobtainable

The IP can be ungettable and the **stack still fully characterizable** — and that is usually what lets
you deliver something useful instead of "unknown":

- **The origin's default error page names its own panel.** A `404` of one very specific size (worked
  case: **58,296 B**) whose body links
  `https://www.aapanel.com/new/download.html?invite_code=aapanele` is **aaPanel / 宝塔**'s default
  vhost page. That single page told us the hidden origin is a Linux box running aaPanel — which also
  *explains* the strict vhost whitelist (`403` to every unknown Host) and redirects the follow-up at
  the panel itself (8888 / randomised safe-entry path).
- **Tell an origin-generated `500` from a CF-generated one by the header, not the body.** An
  empty-bodied `500` carrying `content-type: text/html; charset=UTF-8` — **note the space**, a PHP
  default — came from the origin's PHP-FPM, not from Cloudflare (CF's error pages have their own
  shape). That proves *the origin answers and its app is broken*, i.e. a live-origin signal at a
  moment when you have no IP.
- **`robots.txt` / `sitemap.xml` are self-declared sibling-domain leaks.** Pull both even when the
  site is otherwise a broken shell: in the worked case `robots.txt` named
  `Sitemap: https://telegramset.com/sitemap.xml` and `sitemap.xml` named
  `<loc>https://telegramkit.com/</loc>` — two siblings disclosed by the target's own files. Both were
  CF-fronted as well, but they became the anchor for enumerating the whole farm.
- **A farm's template path is its family crest.** `/template/<name>_<YYYYMMDD>/static/…` in the page
  source cluster-fingerprints every site built by the same operator, and the date often brackets the
  target's own cert date (worked case: template `zfj_20260903` vs target cert issued `2026-09-06`).
  Caveat: FOFA `body=` does **not** index `href`/`src` attribute values, so searching a template path
  there returns 0 — reach the page (yours or a sibling's) and grep locally.
- **`check-host.net` is the free multi-node vantage that separates "the box is dead" from "my egress
  is blocked".** `GET https://check-host.net/check-tcp?host=<ip>:<port>&max_nodes=8`, then poll
  `/check-result/<request_id>`: ≥5 nodes `Connection timed out` = globally down, not a local firewall.
  This is what retired a "most promising candidate" honestly instead of leaving it dangling as a
  maybe. Its lone "reachable in 0.001 s" node answers are single-node artifacts — ignore them.
- **Pair it with a CF-authoritative-NS query to rule CF Tunnel in or out.**
  `dig @<zone>.ns.cloudflare.com <domain> A` returning a plain `A` record (not a
  `*.cfargotunnel.com` CNAME) means a real origin sits behind the edge and the hunt is legitimate;
  a tunnel answer means there is no origin IP to find and you should say so immediately.

### 15. Attribute by *application* when the IP is unobtainable

The IP being out of reach does not force the answer "unknown" — you can usually deliver **"these N
machines are provably part of this deployment"**, which is what the user actually needs.

- **⚠ CORRECTED (2026-10-01) — a page that echoes the target domain is HOST REFLECTION, not fleet
  evidence. This bullet previously claimed the opposite and was wrong.** AizMall / `Active eCommerce`-
  lineage apps (catch-all Laravel SaaS templates generally) emit `<meta name="app-url" content="//<request-host>/">`,
  `<meta name="file-base-url" content="//<request-host>/public/">`, absolute asset hrefs
  (`https://<request-host>/public/assets/css/aiz-core.css`) and `302 -> https://<request-host>/users/login`
  — **every one of them generated from the `Host:` you send.** Verified on one box (`206.238.77.139`),
  same path `/users/login`, only the Host varied:

  | `Host:` sent | `app-url` in body | body md5 |
  |---|---|---|
  | `tlgramhq.com` | `//tlgramhq.com/` | `dab067e6` |
  | `zzznotexist999.com` | `//zzznotexist999.com/` | `9fa8d367` |
  | `www.baidu.com` | `//www.baidu.com/` | `603cf342` |
  | `anymall-test123.com` | `//anymall-test123.com/` | `5d0a4f2b` |

  An `app-url` that happens to name your target therefore proves **nothing**. What such a box *does*
  establish is weaker and must be labelled as such — it is one of the operator's app deployments
  (here evidenced independently: FOFA `body="Any Mall | Marketplace"` = 11 rows / 3 hosts, plus a
  shared Let's Encrypt SAN `tlkdheuaa.com`/`tlkdujkah.com`/`tlkdukshe.com` all resolving to
  `154.82.68.132`). **The binding test is always the repeat-Host md5 control (§13 Trap 3), run before
  any claim is written** — this section is the cautionary tale for skipping it.
- **Fingerprint the *rendered app string*, not the library name and not the title.**
  `body="Any Mall | Marketplace"` → **11 rows / 3 hosts**; the framework asset `body="aiz-core.css"`
  → **26,634 rows** (useless). Pick the template's exact rendered sentence.
- **When the target's own page is a `500`, the search-engine snippet is your copy of it.** Take the
  distinctive sentence out of the indexed description and use it as an exact-phrase query — it is a
  fingerprint of *one deployment*, not of a product:
  `body="一键Telegram下载安装，3分钟搞定中文设置和注册"` → 16 rows;
  `body="Telegram下载2026最新版，提供安卓APK直装包"` → 7 rows. Both lists confirmed the farm boundary
  (the three dead `186.244.248.x` boxes + the 521/522 siblings) and nothing else — cheap and decisive,
  and the only channel that works while the target's app is broken.
- **A name-collision is not a sibling.** `telegramhq.com` (`45.38.148.110`) is an unrelated gambling
  site (泰达平台). Resolve-and-check before admitting a domain to the pool.
- **Enumerating one box's vhosts proves which farm it belongs to.** `154.12.21.45` answered `200` for
  13 "纸飞机" domains (`shpg168.com`, `njhengya.com`, `babyplanet.net.cn`, `zhengqi-group.cn`,
  `bugme.top`, `zhxinlian.com.cn`, `qdzhcb.cn`, `pinequant.cn`, `zhouguanjia.vip`, `wxgamess.cn`,
  `shouyangren.cn`, `yuyo8h.cn`, `zhifeiji-app.top`) and `403` for the target — a cheap, quotable
  "same operator, different box" statement either way.

### 16. The non-CF twin: `cert=`-filter first, then generate variants

Farm operators keep a *direct* hostname beside every CF-fronted one, and the twin resolves straight to
the farm box. Worked case: **`telegramkit.com` (CF) ↔ `kit-telegramkit.com` → `206.238.197.239`** — a
box carrying 28 impersonation domains (Telegram / 有道 / LINE / Google / WhatsApp / TokenIM …), aaPanel
`8888` answering 「安全入口校验失败」, `888`/`21`/`22` open, and **`400` on :80 for every Host** (an
HTTPS-only vhost config; :443 closed from two independent vantages).

- **Cheapest finder — this is the one query shape that converts a CF-only domain into a farm IP:**
  `cert="<cf-fronted-domain>" && server!="cloudflare"`.
- **Then generate variants** in one batch and resolve them: prefixes `kit- hq- hk- us- m- go- app- cdn-
  api-` × base; suffixes `-kit -hq -hk -cdn -app -go` on the stem; and **vowel-dropped forms**
  (`tlgramhq.com` ↔ `tlgrmhq.com`, which really exists — different CF account, same origin). ~100
  names costs seconds.
- **A twin that resolves proves the farm's edge of the map; it is a probe target, not automatically
  the answer.** Say which one it is in the report.

### 16b. CloudFlare Origin CA on a bare IP = definitive origin (API/admin path)

When the **landing domain** stays CF-hidden, the operator often still parks a **management / API
sibling** with a real Origin Certificate. That cert is the single strongest external origin proof:

```bash
# openssl on a non-CF candidate
timeout 10 openssl s_client -connect <IP>:443 -servername <api-or-admin-host> </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -ext subjectAltName
# HIT shape:
#   issuer=... O="CloudFlare, Inc." OU="CloudFlare Origin SSL Certificate Authority"
#   SAN=DNS:*.tron-api.top, DNS:tron-api.top
# + response has NO cf-ray
```

Worked case (tlgramhq R4, 2026-10-01):
| IP | Cert | Role |
|---|---|---|
| **103.254.110.111** | CF Origin CA, SAN `*.tron-api.top` | `api.tron-api.top` true origin |
| **192.253.228.147** | LE CN=`admin.tpwallet.fun` | qb-117 SPA + `api.tpwallet.fun` |

**Host routing on the same box is decisive** — SPA catch-all vs real API:
```bash
# SPA shell (useless): Host: tron-api.top  -> 200 text/html ~484B "qb-117 管理后台"
# Real API:            Host: api.tron-api.top + Accept: application/json
curl -sk -H 'Host: api.tron-api.top' -H 'Accept: application/json' https://103.254.110.111/health
curl -sk -H 'Host: api.tron-api.top' -H 'Accept: application/json' \
  https://103.254.110.111/api/v1/fingerprint/logs   # often unauth read
```
Dual instances (tron-api vs tpwallet) do **not** cross-serve: wrong Host returns the SPA HTML, not
the sibling's JSON. Enumerate every `api.` / `admin.` sibling from the SPA JS `baseURL` before
concluding "no origin".

FOFA shapes that surface these:
- `title="qb-117"` / `title="qb-117 管理后台"` → management SPA IPs
- `ip="<candidate>"` then openssl for Origin CA
- `cert="admin.<sibling>"` (LE) and Origin-CA rows on the same ASN (here AS152194 CTG HK)

Do **not** confuse this with "frontend landing origin found". The landing (`tlgramhq.com`) can still
be independent / deny-unknown-Host while the **control plane** is fully exposed on another IP.

### 16c. Triple fingerprint gate (static SEO shells)

For brand-impersonation static landers, a candidate is **origin-class** only when **all three** hold:

1. **Custom icon md5** (not the brand logo) — worked: `/static/assets/apple-touch-icon.png` =
   `295ccdb03006b8dfef45090dafbd46ac` (5644 B). FOFA `icon_hash="-561384241"` (mmh3 of
   `base64.encodebytes(icon)`). Brand favicon (`telegram.org` paper plane, hash `-469815234`) is
   noise (§ Dead ends).
2. **Exclusive robots body** — worked: **exactly 68 B** containing
   `Sitemap: https://telegramset.com/sitemap.xml` (sibling leak). Generic `Disallow: /` or nginx 404
   HTML is not a hit.
3. **No `cf-ray`** on the response (and preferably not `server: cloudflare`).

Script: `scripts/triple_fp_verify.py`. Any two of three without the third = **not** origin.

### 16d. Shared JS template ≠ same origin (`goDl` / `openDecodedUrl`)

Many CN Telegram-download shells share the same inline `goDl` + base64 APK decoder. FOFA
`body="goDl" && body="openDecodedUrl"` returns multiple **non-CF** IPs that still fail the triple
gate. Mandatory control (same as §13 Trap 3):

```bash
# any Host returns identical homepage md5 => catch-all default vhost, drop it
for h in telegramm.mom tlgramhq.com zzz-not-exist-999.com www.baidu.com; do
  curl -sk --resolve "$h:443:<IP>" "https://$h/" | md5sum
done
```

Worked false positive: `38.76.150.162` (cert CN=`telegramm.mom`, icon md5 **matches**, robots **404**,
every Host same 20817 B page). Also pulled a second APK chain (`kdhtisekkk.s3.ap-southeast-1…` /
`hktuesakk.com` → Aliyun OSS private bucket) — useful supply-chain intel, **not** landing origin.

### 16e. Landing 500 + CF-cached statics

When `/` is `500/0B` (origin PHP dead) but `/robots.txt`, `/sitemap.xml`, and icons still `200`:

- Cache-bust every fingerprint asset (`?cb=$RANDOM`) and read `cf-cache-status` (§13 Trap 4).
- Decode inline/base64 download URLs in `app.js` / homepage — often third-party OSS/S3, not the web
  origin.
- Do not burn the session re-proving "origin is down"; pivot to **API/admin siblings** (§16b) and
  farm pool expansion (§18–§21).

### 17. Domain-pool proof: different CF accounts, byte-identical origin ⇒ one box

Two domains on *different* Cloudflare accounts (different NS pairs) returning the **same origin bytes**
are served by one machine. Compare *originating* assets — a custom icon, the exact `robots.txt` /
`sitemap.xml` text, the `500`+header shape — never a CF-cached asset (§13 Trap 4). Worked case:
`tlgramhq.com` (NS `zita/newt`) and `tlgrmhq.com` (NS `kayleigh/maciej`) matched on all three. Two
payoffs: it proves the one-domain-one-CF-account deploy discipline, **and** it hands you a second
domain to hunt the twin of (§16).

### 18. Expanding the farm's domain pool — mine the SEO link farm

When the target sits inside a **link farm** (hundreds of AI-generated spam sites all linking the
operator's domains), that farm is effectively a directory of the operator's property. Verified:

1. Find one member — FOFA `body="<target-domain>"` (worked case: 763 rows, mostly `.cyou` spam).
2. Fetch N of them concurrently, extract **all** external `href` hosts, `Counter` them.
   **Domains appearing on ~all N sites are batch-inserted template links = the buyer's own pool**;
   a domain appearing once is ordinary farm filler. Worked case: `tlgramhq.com`, `tlgr.tw`,
   `telegramaf.com`, `www.telegramtlg.com` (17×/18) and `tlgrmzh.com` (9×) — four new same-family
   domains, verified individually, zero false leads.
3. Resolve every pool domain and **flag the non-CDN ones** — those are direct-connect server
   candidates. Then follow each one's `www.`/sub CNAME to name its vendor CDN (§19).
4. A **bare-IP link** in the pool (`132.148.216.191`, 17×) is almost always a shared-host artifact
   (GoDaddy/Namecheap shared IP) — resolve-and-check before promoting it.

Script: `scripts/link_farm_miner.py`.

### 19. Vendor-CDN pivot — the CNAME names the CDN, FOFA lists its nodes

A CF-fronted domain's `www.`/sub often CNAMEs to the **vendor CDN's node naming**, which names the
product outright: `www.telegramaf.com` → `k24n8dax.d8n2kls8.gongyong666.com` (「公用666」CDN),
`tlgramhk.com` → `526yj4g9.2027facai.com`, and one node's own error page self-identified as 「不死鸟CDN」.
Then one query — `domain="<vendor-cdn-domain>"` — enumerates the product's node IPs (公用666 → 8 IPs).
Also grep the vendor's error page: the 「未绑定」 pages print the node and the origin's state.
**Sample the node range once and stop** — on this class every node answers `000`/`530` for arbitrary
Hosts, so a /24 sweep returns nothing but the generic page.

**Read that generic page as an *existence oracle*, never as a hit.** It echoes the request Host, so the
body length tracks the Host string exactly — `tlgramhq.com` → **12427 B**, same Host on
`/static/assets/apple-touch-icon.png` → **12461 B**, `telegramaf.com` → **12429 B**, random control →
**12433 B**. Length deltas there are *proven* noise (§13 Trap 3). The usable direction is the
**inverse**: if a node answers anything *other* than the generic unbound page for `Host: <target>`,
that node has the vhost configured. The md5 control still decides binding.

### 20. Letter-level twins, not just vowel drops

§16 covers prefixes/suffixes/vowel drops. Add **suffix letter swaps** — `tlgramhq.com` ↔
`tlgramhk.com` (`hq` ↔ `hk`) — which really existed: non-CF, same WordPress theme, and its host
`222.167.35.135` sat inside a **39-machine /24 all running that same theme**. One twin can therefore
hand you an entire farm netblock. Same idea via a theme path as a cluster query:
`body="themes/telegram03"` → **6 rows** → the operator's three Telegram stations; the page's `51.la`
analytics tag also tells you the operator is Chinese. Pick the **exact rendered string / theme path**,
not the framework name (§15).

### 21. Recognise the "drops unknown Hosts" farm netblock early, then stop sweeping

A farm range may answer **`000` — TCP accepted, no HTTP response — for any Host it does not know**,
while answering normally for its own domains. Worked case: `222.167.35.0/24`, 39 live boxes, every one
returning `000` for `Host: tlgramhq.com` and for a random control, yet `200` for its own stations.
That is an intentional vhost whitelist, **not** a dead host, and it makes Host-injection scanning
structurally useless across the entire range — no number of IPs will ever produce a hit. Detect it
once (two boxes × {target Host, random control}) and pivot to the application / vendor-CDN channels
instead. Do **not** write such a sweep up as "the origin is provably not in this netblock"; the
honest statement is only "this range drops unknown hosts, so this technique cannot see anything here".

