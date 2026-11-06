# Growing the domain pool of a hidden-origin site farm

Companion to `cf-hidden-origin-tracing` §18–§21. All techniques below produced **verified** findings
(each domain/IP was independently resolved and re-probed); the boundary is stated at the end.

## 1. Link-farm mining — the highest-yield pool expander

The operator buys links on AI-generated spam farms. The farm is a machine-readable list of his
property because the template inserts **his whole domain set** into every farm page's footer.

Recipe:
1. One member is enough to start — in the worked case `FOFA body="tlgramhq.com"` returned 763 rows
   (mostly `.cyou` casino/SEO spam; the operator's own domains are a small minority).
2. Fetch 15–20 members concurrently, pull `href="https?://([^"']+)"` from the raw HTML, and
   `collections.Counter` the hosts across **all** pages.
3. Read the distribution, not the top of it. Batch-inserted footer links land at **N/N** (every page);
   organic farm filler lands at 1–17× but on unrelated topics (casino brands, hotels, `.edu` sites).

Worked output (18 pages):

| hits | domain | verdict |
|---|---|---|
| 17× | `tlgramhq.com` | the target |
| 17× | `tlgr.tw` | confirmed sibling (separate traditional-Chinese nav site, static) |
| 17× | `telegramaf.com` | confirmed sibling (behind 「公用666」CDN, origin 502) |
| 17× | `www.telegramtlg.com` | confirmed sibling (CF, title “Telegram - Telegram下载”) |
| 9× | `tlgrmzh.com` | confirmed sibling (aaPanel “site stopped”) |
| 17× | `132.148.216.191` | **shared-host artifact** (GoDaddy `secureserver.net`) — not the operator |

Cross-check every candidate before admitting it: `telegramhq.com` looked like a sibling by name and
turned out to be an unrelated gambling site on `45.38.148.110`.

Then: resolve the pool, flag the non-CDN members (direct-connect candidates), and run `cert="<domain>" &&
server!="cloudflare"` on each (§16).

## 2. Vendor-CDN pivot

CF-fronted hostnames leak their CDN vendor through the CNAME of a `www`/sub record, and CF does not
hide CNAME targets on the zone you can query:

| seen | CNAME target | vendor |
|---|---|---|
| `www.telegramaf.com` | `k24n8dax.d8n2kls8.gongyong666.com` | 「公用666」 (8 node IPs via `domain=`) |
| `tlgramhk.com` | `526yj4g9.2027facai.com` | 「2027发财」 (Alibaba DNS NS) |
| node error page | `530 Domain Not Configured · 不死鸟CDN` | 「不死鸟CDN」 |

These are **commercial** station-farm CDNs, not the operator's own — treat them as vantage/inventory,
not as attribution.

## 3. The generic unbound page is an *existence oracle* (and a length trap)

Vendor CDN nodes serve one generic 「当前访问域名未绑定 / Domain Not Configured」 page that **echoes the
request Host**, so the byte length moves with the Host string alone:

| request | length |
|---|---|
| `Host: tlgramhq.com` `/` | 12427 |
| `Host: tlgramhq.com` `/static/assets/apple-touch-icon.png` | 12461 |
| `Host: telegramaf.com` `/` | 12429 |
| `Host: zzznotexist777.com` `/` | 12433 |

So length deltas are noise, and "the page mentions my target" is meaningless. Use the inverse signal:
**a node answering anything other than the generic page for `Host: <target>` has that vhost
configured.** Binding still needs the §13 Trap 3 md5 control.

## 4. Host reflection: the table that disproved a "binding"

Same box (`206.238.77.139`), same path (`/users/login`), only `Host:` varied:

| Host | `app-url` meta | md5 |
|---|---|---|
| `tlgramhq.com` | `//tlgramhq.com/` | `dab067e6` |
| `zzznotexist999.com` | `//zzznotexist999.com/` | `9fa8d367` |
| `www.baidu.com` | `//www.baidu.com/` | `603cf342` |
| `anymall-test123.com` | `//anymall-test123.com/` | `5d0a4f2b` |

The 302 `Location`, the `file-base-url` meta, and the absolute CSS hrefs all tracked it too. This is a
catch-all Laravel/AizMall deployment: **it proves nothing about the target.** (This table exists
because the claim was written up first and had to be retracted — run the control *before* claiming.)

## 5. Letter-level twins and theme-path clusters

- `tlgramhq.com` ↔ `tlgramhk.com` (`hq`↔`hk`) — live, non-CF, same WordPress theme, host
  `222.167.35.135` inside a **39-machine /24** running that theme.
- `body="themes/telegram03"` → **6 rows** → `tlgramhk.com` (`222.167.35.135`), `men-zifeiji.com`
  (`222.167.35.31`, `200/27099`), `zhtelegram.top` (`45.78.43.183`). `51.la` analytics on the page
  marks the operator as Chinese.
- Operator's impersonation breadth (from reverse-IP on his own boxes): VPN (仿 Zoom/Panda/Proton/绿茶/
  快连/iKuuu), wallets (仿 MetaMask/Ledger/非小号), office (仿 WPS), porn, plus his own admin panels
  (`chaojiseo.cloud`, `goapi.mom`). Useful for recognising the same operator later.

## 6. The deny-unknown-Host netblock (stop, don't sweep)

`222.167.35.0/24`: 39 live boxes. Every one returns `000` (TCP accepted, no HTTP reply) for
`Host: tlgramhq.com` and for a random control, while serving its own domains normally. Also observed on
`94.154.43.0/24` and the 「公用666」 node IPs. This is a deliberate vhost whitelist; Host-injection
scanning sees **nothing** there by construction. Detect it on two boxes and pivot.

## 7. Where this class stops (honest boundary)

On this target the CF origin IP was **not** obtained, and the reasons are structural rather than a
missed trick:

- CF-only ingress, true A-record origin (CF authoritative NS returned a plain `A`, not a
  `cfargotunnel` CNAME), so an origin exists but is invisible from outside CF.
- The origin drops unknown Hosts, and every candidate range in the operator's pool behaves that way.
- The domain is weeks old: PDNS, CT-beyond-CF-Universal-SSL, Wayback, Common Crawl (504/no rows),
  subdomain brute, MX/TXT/CAA are all empty — there is no "before CF" generation to leak.

What *was* delivered instead, and what to reframe toward when asked for "the source IP": the
operator's identity as a large SEO station-farm operation, his CDN stack, his domain pool (with the
non-CF members named), and the twin domain that maps his netblock. Write those up as the answer and
state the CF-origin limit explicitly rather than implying more scanning will close it.
