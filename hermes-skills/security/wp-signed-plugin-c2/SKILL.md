---
name: wp-signed-plugin-c2
description: "Use when WP link-factory/signed REST malware C2 or mapping its infection network."
version: 1.0.0
tags: [wordpress, malware, backdoor, seo, ed25519, rest, c2]
---

# WordPress Signed Plugin C2 (link-factory class)

Authorized assessment of **signed REST backdoors** shipped as WP plugins (SEO spam / remote content / remote user ops). Primary family: **`link-factory`** under `/wp-content/plugins/link-factory/` (CVE-2026-15413 class). Treat as **operator C2**, not a normal public plugin CVE spray.

## When to use

- `/wp-json/link-factory/v1/health` returns JSON with `protocolVersion`
- Path `/wp-content/plugins/link-factory/` or open includes listing
- Homepage SEO spam + hidden outbound `go.php?key=` sibling jumps
- Posts with empty author display / REST user id invalid while posts exist
- FOFA hits on `link-factory` body/path or health JSON hashes

## Fingerprint (all three when possible)

1. **REST health (unauth):** `GET /wp-json/link-factory/v1/health` → `status` / `version` (hash) / `protocolVersion`
2. **Path:** `/wp-content/plugins/link-factory/` (+ `includes/`, `readme`)
3. **Side effect:** spam posts, empty ghost authors, sibling `go.php` jump hosts

Always re-hit live health after FOFA — version hashes can collide with unrelated plugins (e.g. Elementor false positives).

## protocolVersion cut (do not assume full routes)

| Ver | Routes typically live | Meaning |
|-----|----------------------|--------|
| **2** | `health` + `sentences` | **Castrated** implant — `/users` `/articles` often **404** |
| **5** | + `users` + `users/check` + `articles` | Full remote user/content C2 — full route table: health(GET, unsigned) / articles(POST, GET; `{id}` GET, POST, DELETE) / sentences(POST; `{id}` DELETE) / users(POST) / users/check(POST) / users/{login}(DELETE) |

Signed headers (names only; values never in chat): Signature / Timestamp / Nonce / Protocol-Version family (`X-Link-Factory-*` or mirror of live error text).

| Response | Meaning |
|----------|--------|
| **400** missing params | Param validation runs **before** crypto — not "open write"; add real params → still 403 |
| **500** bad signature | Route exists; crypto failed — on debug stations the fatal handler leaks file:line (see below) |
| **404** on `/users` | Often **v2 castrate**, not WAF |

## Error-differential fingerprinting (keystone)

Feed wrong-shaped probes, record which gate fires first — the order maps the validation chain, exact strings + crash behavior identify the implementation:

| Probe (all four `X-Link-Factory-*` headers) | Response | Reads off |
|--------------------------------------------|----------|-----------|
| no headers | 403 `Required signature headers missing` | gate 1 = header presence |
| ts = now−3600 | 403 `Timestamp outside tolerance window` | window **< 1h** |
| fresh ts + reused nonce | 403 `Nonce replay detected` | nonce store → replay dead |
| fresh ts + 64B garbage sig | 403 `Invalid request signature` | gate 4 = crypto verify |
| fresh ts + **63/65B** sig | **500** uncaught `SodiumException`; debug stations return full stack + **file:line** | `sodium_crypto_sign_verify_detached()` @ `trait-signature.php:74`; **no length precheck, no try/catch** → native libsodium, not hand-rolled |

**Stack-leak sweep:** send the wrong-length probe once to every station — `WP_DEBUG_DISPLAY=true` sites answer with the WP fatal-handler body: `Class "LinkFactory\Repository" not found`, boot chain `plugins_loaded → LinkFactory\Plugin::boot('') → class-plugin.php:21`, absolute paths + server layout. Highest-yield single request against the family.

**No-bypass discipline (verified 2026-10 — do not loop):** native libsodium Ed25519 (no forgery), no valid sig samples, <1h window + nonce store (no replay), every non-health route signed. The private key is a hard gate — pivot to source/backup/key acquisition or adjacent surfaces instead of re-fuzzing the crypto.

## Ghost author residue (v5 tell)

- `wp/v2/posts?author=N` has posts
- `wp/v2/users/N` → `rest_user_invalid_id`
- HTML / JSON-LD author `name` and `@id` empty
- Login oracle often random `lf_*` — short dict usually misses

Use as **implant fingerprint**, not primary ATO path.

## Sibling / FOFA pivot

When victim is **v2-only**:

1. FOFA / space-map for open `link-factory` listing or `"protocolVersion":5` health
2. Prefer hosts with **directory listing** (byte sizes on `trait-signature.php`, `class-users.php`, `class-articles.php`)
3. Harvest **non-executed** source for Ed25519 verify material (pubkey in signature trait)
4. Sign full-surface `/users` only after real key material — do **not** assume operator keys are shared across every cluster

## Network census — dorks, beacons, sitemap quantification (2026-10, validated)

**Infection census (search dorks):** every station that completed the claim step leaves a verification page; search indexes them — one sweep surfaced 30+ (incl. government domains).
- `"Link Factory verification"` / `inurl:link-factory-verification`
- Template (v3, test domain never replaced): `# Link Factory verification` + `[verification](https://link-factory.test/verification-anchor)`; slug suffix `-2`…`-19` = Nth duplicate = generation count for that station.
- Page byline = network-wide signature, two classes: `By: lf_XXXXXXXX` (backdoor account, e.g. `lf_sVSIeHc0qEem`) or an existing site-admin name (`backupadmin`, `root`, real staff names) — matches WPScan "posts authored by a site administrator".
- Random-word clone hosts (`<randomword>.<tld>/<path>?key=<32hex>` behind CDNs, e.g. StackPath) + verification links pointing at them = operator's parasite-mirror layer.

**Station state triage (health beacon):**

| health response | State |
|---|---|
| 200 `{status,version,protocolVersion}` | Active (v5 = full C2) |
| 404, ~114 B `rest_no_route` | **Cleaned** — plugin removed post-CVE; verification page/posts residue remains |
| 200 but multi-KB HTML (not JSON) | wp-json intercepted/guarded — inconclusive |

**Quantify a donation site (sitemap mining):** WP ≥5.5 `/wp-sitemap.xml` → `/wp-sitemap-posts-post-N.xml`, 2000 URLs/shard. `<loc>` → brand keyword frequency (customer rankings); `<lastmod>` → campaign timeline; slug language mix → market coverage. Reference case thethinkagency.com: 14 099 posts / 11 717 casino (83%), 30+ brands (stake 232, nv-casino 161, energy 150, jugabet 149…), sparse 2025-06 → **2026-03/04/05 burst (~75%)** → ongoing Oct 2026, 11+ languages. Same customer links across stations (casinoly cluster) = shared campaign material.

**Output-side mapping (what the operator actually pushes — 2026-10 validated):**

- Rendered anchors sit in hidden donor containers — grep saved HTML for `aria-hidden` / `display:none` / off-screen wrappers; camouflage reuses theme-native classes (live sample: `<a class="wpex-promoted-link" href="…">non GamStop betting</a>`).
- Full external-href inventory of ONE donor page = the operator's live delivery list → archive as loot. Two tracks visible: gambling clients + gray "non GamStop" affiliate bridge pages.
- Clone nodes: same `?key=<32hex>` on multiple donors = one node reused network-wide; cross-ref via urlscan.io search API (no key needed: `https://urlscan.io/api/v1/search/?q=domain:<d>`) + stack-lookup/search snapshots; WP oEmbed embeds of node URLs are a common donor-page injection form.
- Attribution: rdap.org proxy unreliable → query registry RDAP directly (`.com`/`.net`: `https://rdap.verisign.com/com/v1/domain/<d>`) then `dig NS` separately (NS → cheap shared hosting = burnable node); Gridinsoft/Sucuri-style trust reports supply age + blacklist count.
- Classify each linked domain with ONE follow-redirect fetch (`curl -skL`): CF answers a bare 301 to health/REST without `-L` — don't misread as "no plugin"; footer brand text identifies what the site is; static asset paths (`/res/js/*`, `/public/js/*`) = non-WP → client/bridge, not donor.

## Source grab — verified empty vs still open

| Observation | Conclusion |
|-------------|------------|
| Listing shows real sizes (~3.1K trait-signature, ~4.5K class-users, ~10K class-articles) | Files on disk |
| GET `.php` → 200 **0-byte** body | Interpreter executes; empty response |
| Same 0B from alternate egress | Origin empties PHP — not only local WAF |
| `.bak` / `::$DATA` / null-byte → HTML or obfuscated JS | **False positive** — keep only `<?php` / `namespace LinkFactory` / `sodium_crypto` |
| Wayback empty | No free historical source |
| `readme.txt` 200 (~2.7KB) on every station | **Read it FIRST** — architecture, version history, protocol changelog, ops notes ("C2 reinstalls outdated installs, SITE-16") |
| Listing shows 8-file inventory | class-{articles,footer,health,plugin,repository,sentences,users}.php + trait-signature.php |
| Backup-plugin dirs exist (jetbackup `backups-*`/`db-*`/`downloads-*`, ai1wm, updraft, wpvivid, `upgrade/`, `upgrade-temp-backup/`) | Dir shells only — contents 404/emptied; documented so nobody re-runs the sweep daily |

**Unresolved (do not encode as workflow):** recovering operator **private** key from empty PHP alone. Only record fingerprints + pivot order until a real static/backup/LFI copy appears.

## Host / origin traps (nav + mirror farms)

- Channel domain on EdgeOne/CF; sibling nav may be **LE direct** → true origin IP usable for panel/SSH **banner** only (no long spray).
- `--resolve ORIGIN` + foreign Host may serve same skin while **LF health 404** → catch-all vhost, **not same WP app**. Prove sameness with LF health / REST namespace / plugin path.
- Open registration / subscriber AppPass / media upload ≠ WP admin shell.

## Escalation order

1. Classify `protocolVersion` from health.
2. v2 → FOFA v5 + listing siblings; avoid burning admin lockouts.
3. v5 → map `/users` `/articles` error grammar + ghost authors; still need key or source leak.
4. Parallel short WP surfaces (abilities, XML-RPC, pending XSS) under lockout discipline.

## Related

- Plugin discovery umbrella: `wordpress-plugin-hunt` / `hunt-wordpress` (if adopted)
- Farm / multi-vhost: `multi-app-farm-pentest`
- Execution discipline: `pentest-execution`

## Support

- `references/link-factory-playbook.md` — detection commands, FOFA shapes, ghost-author checks, empty-PHP rules
- `references/lf-cve-2026-15413-dissection.md` — 2026-10 field dissection: 8-station fleet matrix, stack-leak transcript, exhaustive source-hunt log, CVE intel closure
- `references/lf-network-mapping.md` — census + quantification: station lists + states, verification-page mechanics, quant numbers, byline signatures, clone-mirror layer with key-reuse + RDAP node profiles, donor output capture (sentences render) + client taxonomy, public-research cross-ref
- `scripts/fingerprint_signed_rest.py` — runnable error-differential probe (health + gate-order + 63/64/65B sig cases)
