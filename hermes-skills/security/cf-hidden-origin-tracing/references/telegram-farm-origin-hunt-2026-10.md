# Worked case — CN "Telegram download" SEO farm behind Cloudflare (2026-10)

Target: `tlgramhq.com` — an impersonation of Telegram's download page, part of a large CN grey-industry
SEO farm. **Verdict delivered: origin IP not externally obtainable**, with the origin *stack* fully
characterized and the operator's fleet attributed. Read this when you meet the same shape (CF +
brand-new domain + strict vhost whitelist + all passive channels empty) — it is the reference for
"spend 20 minutes, then say so plainly".

Two rounds ran back-to-back: round 1 closed the external-origin line honestly; round 2 ("继续深挖")
turned the same target into a full fleet map. **Round 2 is the part worth reading for technique** —
it produced the app-attribution route (§ Round 2 → A) and the non-CF twin (§ Round 2 → B).

---

# Round 1 — the target and the negative result

## What the target looked like

```
GET /            -> 500, 0 B   (content-type: text/html; charset=UTF-8 — PHP default)
GET /index.html  -> 404, 58296 B  (aaPanel default page; body links aapanel.com/new/download.html?invite_code=aapanele)
GET /login /api  -> 404, 58296 B  (same aaPanel default page)
GET /robots.txt  -> 200 -> "Sitemap: https://telegramset.com/sitemap.xml"
GET /sitemap.xml -> 200 -> "<loc>https://telegramkit.com/</loc>"
```

Two conclusions fell straight out of those five requests: the **origin stack is aaPanel/宝塔 + PHP**,
and the target's own files disclose **two sibling domains**.

## Network layer (all CF — no signal to harvest)

| Field | Value |
|---|---|
| A | `104.21.44.21` / `172.67.193.244` (CF anycast) |
| AAAA | `2606:4700:3037::ac43:c1f4` / `2606:4700:3031::6815:2c15` |
| NS | `zita.ns.cloudflare.com` / `newt.ns.cloudflare.com` |
| CF authoritative NS `dig A` | plain `A` record → **not** a `cfargotunnel.com` CNAME → real origin exists |
| Edge cert | CN=tlgramhq.com, issuer **Google Trust Services WE1** (CF Universal SSL), serial `48604AE834EC2E2E0E21816A1C08FAF4` |
| Cert validity | 2026-09-06 → 2026-12-05 (**domain went live in Sept 2026**) |
| Registrar | trustname.com (handle 4318) |
| MX / TXT / CAA | none |
| favicon.ico | 4286 B, **md5 identical to telegram.org's own favicon** → zero discrimination |

## Why no origin IP: all three locks at once

1. **CF fronts everything** — every resolver agrees.
2. **Origin runs a strict vhost whitelist** — `Host: <target>` to any sibling bare-metal box gives `403`
   or a catch-all default site, so the Host-spray反证法 yields nothing.
3. **The domain is weeks old** — 8 passive-DNS sources (OTX, Mnemonic pdns v3, ThreatMiner, bufferover,
   hackertarget, rapiddns, urlscan, VirusTotal UI) were **all empty**; there is no "generation before
   CF" to leak. crt.sh/certspotter show only the CF GTS cert + a Sectigo cert for `tlgrmweb.com`.

## Ruled out, with the evidence (so nobody re-runs them)

- **favicon mmh3 `-469815234`** → 7,850 FOFA hits, but the hash is *Telegram's own paper-plane icon*,
  so it matches every Telegram site on earth plus mmh3 collisions (even `nft.fragment.com`).
  Useless as a farm fingerprint. Same for `cert=` / `domain=` in round 1 — CF IPs only.
- **Subdomains** → none (30-word brute, then an **807-name** brute across 3 domains, crt.sh,
  subdomain.center, anubis, wildcard check — all empty).
- **`154.12.21.0/24` / `154.26.238.0/24` / `186.244.248.0/24`** (512 IPs × 80/443, swept, then Host-sprayed)
  → zero matches.
- **A 59-node CN "CDN 3.0" cluster** (FOFA `body="当前访问域名未绑定"`, 32,634 records) → cleared by the
  **md5 control**: every node returned byte-identical `503`/`530` for *every* Host including `baidu.com`.
  Note the panel is a **public commercial product** (30 万+ rows) — matching it proves nothing about
  *this* operator.
- **A `500`-signature candidate** → cleared by the same control (it was a default site).
- **`186.244.248.17`** — the single most promising candidate (title matched the target *verbatim*,
  `Telegram下载-电报下载官网`; aaPanel-ish port 888; camouflage domain `hamiltonintakes.com`) —
  **check-host.net: 8/8 nodes timed out** ⇒ genuinely decommissioned, not blocked from my egress.
  Its two neighbours `.10` / `.11` carried the same title and were equally dead.

---

# Round 2 — same target, fleet fully mapped

## A. App-level attribution (the strongest deliverable of the whole engagement)

The CF edge does **not** point at these boxes — and they still belong to the target's deployment,
proven by the application's own configuration:

| IP | Evidence |
|---|---|
| `206.238.77.139` (HK, AS399077 Tcloudnet) | `/` → `302` → `https://tlgramhq.com/users/login`; `/users/login` → `200`, 67,919 B |
| `154.82.68.132` (HK) | same app, same `app-url`; cert SAN `tlkdheuaa.com,tlkdujkah.com,tlkdkukshe.com` **all resolve here** |
| `154.82.67.245` | same app, same cert |

```html
<meta name="app-url" content="//tlgramhq.com/">
<meta name="file-base-url" content="//tlgramhq.com/public/">
<link href="https://tlgramhq.com/public/assets/css/aiz-core.css">
<title>Any Mall | Marketplace</title>   cookie: any_mall_session
```

- App = **AizMall / Active eCommerce** lineage (Laravel marketplace), `any_mall_session` cookie,
  `/users/login`, multi-language storefront.
- FOFA app-signature ladder: `body="Any Mall | Marketplace"` → **11 rows**; `body="aiz-core.css"` →
  **26,634 rows** (too generic). Use the *rendered* string.
- **Cache-bust settled the question**: through CF, `/static/assets/apple-touch-icon.png` was a
  `cf-cache-status: HIT` (`age: 169316`); with `?cb=<rand>` the **origin** answered `200/5644` for the
  icon but `404` for `/public/assets/css/aiz-core.css`. So the AizMall boxes are **not** the CF origin —
  but they are the target's app fleet. Both statements went in the report.

## B. Non-CF twin + the farm's bare-metal server

- `cert="telegramkit.com" && server!="cloudflare"` → exactly one row:
  **`kit-telegramkit.com` → `206.238.197.239`** — the CF domain's direct twin, on the farm's own box.
- That box: **28 impersonation domains**, all non-CF — `kit-telegramkit.com`, `youdao-hpcfton.com`,
  `seupdeelpefanyi.com`, `linestuprg.com`, `hkgoogelteuest.com`, `safwcattaklio.com`,
  `gootgsuatxiazai.com`, `singalxiazaitr.com`, `chaotwerk/chaetwerk/chaoiwerk.com`,
  `letstalktupsekl-hk.com`, `todestuoxi.com`, `yifanyixiaos.com`, `hellogptonou.com` …
  (brand set: Telegram / 有道 / LINE / Google / WhatsApp / TokenIM / generic "下载").
- Ports: `80`(**400 to every Host, incl. HTTP/1.0 with no Host** — an HTTPS-only vhost config),
  `443` (closed from my egress **and** from check-host nodes), `888`(403), `8888` **aaPanel
  「安全入口校验失败」**, `21`, `22`.
- Two of its domains CNAME to the operator's own CDN: `dfec1b0e.688cdn.xyz`, `9d37ac02.688cdn.xyz`,
  `e9c1c19b.688cdn.xyz`.

## C. Domain pool (one-domain-one-CF-account discipline)

`tlgramhq.com` (NS `zita/newt`) and **`tlgrmhq.com`** (NS `kayleigh/maciej`) — different CF accounts,
**byte-identical origin**: same `500` + headers, same `robots.txt` text, same custom `5644 B` icon.
⇒ one origin. Sibling set also includes `telegramkit.com`, `telegramset.com` (aaPanel "Site is created
successfully!"), `tlgrmkit.com`, `tlgrmweb.com`(521), `tlgrmdb.com`(522), `tlgrmblog.com`,
`telegraapp.com`, `telegwam.com`, `telegramtgch.com`, `telegram-com.com`, `telegram-jvip.com.cn`,
`telegramtgtgtgtg.com.cn`.

## D. Operator's wider infrastructure (all reached from the farm's own links)

- **Short-URL / jump system** `202616888.com`「易记网址」— FOFA `body="202616888.com"` → **7,497 rows**;
  nodes `154.204.238.107/108/109`, `154.220.120.75/77/91/102/113/120`, `154.220.121-123.x`,
  `156.241.71/113.x`, `156.245.40-46.x`, `154.204.253/254.x`. `154.220.120.77` serves 7 operator SEO
  domains (`aqrzhl.com` mother-domain + `jyhojo/yeshengele/zhilixx/tuhuanggroup/gzyunmi/wcbyy0451`),
  and `/index.php` (128,494 B) is a 中国广电辽宁 impersonation with the brand swapped to `pg.vip`.
  Pattern: mother-domain + bulk numeric subdomains (`679.aqrzhl.com`, `262.wzgm0577.com`).
- **Self-built CDN** `688cdn.xyz` (NS `vip7/vip8.alidns.com`) with server tag **`668cdn`**
  (`server="668cdn"` → 4,281 rows, mostly 六合彩). Nodes `103.171.35.54/.94/.179`,
  `103.214.175.183/.253`, `45.201.241.70` — all catch-all, cleared by md5 control.
- **SEO content sub-farm**: `telegwam.com` / `tlgrmblog.com` = WordPress + **`ripro-v5`** theme
  (names "Telegram官网下载" / "Telegram官网"); `wp-json/wp/v2/users` leaks author slug + gravatar hash.
- **"纸飞机" farm** on `154.12.21.45` (cognetcloud AS401696): 13 vhosts all `200` (list in SKILL §15),
  template crest `/template/zfj_20260903/static/…` (dated 09-03 vs target cert 09-06).
- **SEO provider** `154.26.238.190` default site = 「星瀚SEO｜网站搭建｜必应快排｜谷歌GEO优化」
  (own domain `bingkuaipai.cn`); same racks host 代开医院证明 / 本地制作证书 / 医保卡套现 / 苹果 ID 贷 /
  伴游招聘 — one provider serving a grey-industry portfolio.
- **ASNs involved**: AS399077 Tcloudnet / AS135097 LUOGELANG / AS401696 cognetcloud / AS400619 AROSSCLOUD /
  AS8796 fastnet (all bulk grey-industry hosting, million-plus assets each — an ASN alone is not a boundary).
- **Vowel-dropped twin search is worth a batch**: `tlgrmhq.com` hit; `tlgramhq.cn/net`, `tlgramhq.top/xyz`,
  `hqtlgram.com`, `hktlgram.com`, `tlgramhq-kit.com` all do not exist.
- **Name collision to ignore**: `telegramhq.com` → `45.38.148.110` is an unrelated gambling site (泰达平台).

## E. Round-2 sweep results (≈8000 IPs, zero hits — do not re-run)

`154.220.120.0/24` (whole /24 answers `403/146` ⇒ one operator's private box pool),
`154.204.238.0/24` (K1体育 gambling catch-all; Host-reflects `wap./www.<host>` links),
`154.204.242.0/24`, `154.220.16.0/24` (94 B 「当前域名或者端口未绑定」 panel), `154.220.121-123.0/24`,
`156.241.71/113.0/24`, `156.245.40-46.0/24`, `38.12.79-81.0/24`, `137.220.211.0/24`, `154.39.82.0/24`,
`206.238.196-199.0/24`, `154.82.66-69.0/24`, and the 401 FOFA-listed IPs of **AS399077** — all swept on
80/443 with `Host: <target>` + the icon-path probe, then md5-controlled. Also confirmed dead:
`77.37.48.240` (quickq.dev, Hostinger SG), `186.244.248.10/.11/.17`.

## F. False positives that cost time in round 2

- `156.248.73.237/.99`, `206.238.198.62` — a single `404/258` containing the target hostname, never
  reproducible (stable `404/138` after) ⇒ LB backends / Host-reflecting Apache error page.
- `186.244.248.22/.26/.65` — `grep <target>` hits, all **Host reflection** (ZBlog canonical hrefs,
  「会员中心」 links, CDN "域名未绑定" pages that also print *my own egress IP*).
- `154.204.238.56:443` — a K1体育 page whose length varied with the Host; stable per-Host but the delta
  was just the Host string echoed into `wap.<host>` / `www.<host>` links. **Reflection, not a vhost.**
- `154.12.21.25/.27/.28` — Vite SPA catch-all default sites.

## Follow-up paths handed to the user

1. **Watch `206.238.77.139` / `154.82.68.132` / `154.82.67.245`** — the boxes bound to the target by app
   config. If the operator points CF back at them, the icon-path probe (`Host: <target>` +
   `/static/assets/apple-touch-icon.png`) flips to `200/5644`.
2. Watch `186.244.248.0/24` and `154.82.68.0/24` for reuse (operator resource pools).
3. Poll the sibling domains' A records for a non-CF generation (§16 twin hunt).
4. The only clean path remains CF-account access, or the origin's own aaPanel.

*Case artifacts: `/root/cases/tlgramhq/REPORT.md` (round 1), `REPORT-R2.md` (round 2).*
