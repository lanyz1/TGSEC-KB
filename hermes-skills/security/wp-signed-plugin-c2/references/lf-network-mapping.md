# LF network mapping — second/third-wave sweep (2026-10-06, k0 case)

Companion to `lf-cve-2026-15413-dissection.md` (first-wave 8 stations). Covers: censusing the whole network, classifying station states, quantifying a donation site, the operator's clone layer, and donor output capture + attribution (2026-10-06 addenda).

## 1. Census dorks (find infected stations en masse)

- `"Link Factory verification"` / `inurl:link-factory-verification` — the claim/verification page each compromised station gets; search-indexed → live census (30+ surfaced in one sweep, incl. government sites).
- Template (v3 build, test domain never replaced):
  ```
  # Link Factory verification
  [verification](https://link-factory.test/verification-anchor)
  ```
- Slug `link-factory-verification-N` (`-2` … `-19`): duplicate counter = generation count on that station.
- Page bylines, two signature classes:
  - `By: lf_XXXXXXXX` — backdoor account (samples: `lf_sVSIeHc0qEem`, `lf_DmZoUNi765ab`, `lf_MVrwtt0zoZCS`)
  - existing site-admin names — `backupadmin`, `mwebesa johnson`, `Cassandra`, `root`, `admin` (matches WPScan: "posts authored by a site administrator")
- Some verification links point at operator clone hosts instead of the `.test` placeholder — see §4.

## 2. Station state triage (health beacon)

| Probe | State |
|---|---|
| `GET /wp-json/link-factory/v1/health` → 200 JSON | Active |
| 404, ~114 B `rest_no_route` | Cleaned — plugin removed post-CVE; verification page/posts residue remain |
| 200 but multi-KB HTML | wp-json intercepted/guarded — inconclusive |
| 000 | Dead / WAF |

## 3. Quantify a donation site (sitemap mining)

- WP ≥5.5 sitemaps: `/wp-sitemap.xml` → `/wp-sitemap-posts-post-N.xml`, 2000 URLs/shard (7-8+ shards on big farms).
- `<loc>` → brand keyword frequency = customer ranking; `<lastmod>` → campaign timeline; language mix from slugs.
- Reference case — thethinkagency.com (active v5, disguised as a real agency):
  - 14 099 posts / 11 717 casino-bet (83%)
  - Top brands: stake 232 · nv-casino 161 · energy-casino 150 · jugabet 149 · spinbet 139 · 22bet 76 · betfair 70 · betcity 65 · vavada 62 · mostbet 56 · dragonia 53 · betsafe 45 · ggbet 44 · eurobet 42 · 1bet 35 · yukon 32 · marathonbet 29 · casinoly 15 … (30+)
  - Timeline: sparse from 2025-06 → **2026-03/04/05 burst = 10 540 (75%)** → 500-650/month ongoing → latest 2026-10-02 (live)
  - Languages: EN DE FR NL IT ES DA NO PL CS EL (11+)
- Real-company backplate (normal about/team/portfolio pages) + industrial-scale casino posts = rented/hijacked donation host profile.

## 4. Operator clone layer (parasite mirrors)

- Sample: legit site geekyhumans → content mirrored at `violationsyllable.com/jatm5da51g?key=<32hex>` (StackPath CDN segment 172.240/12).
- Pattern: `<random-word domain>/<short path>?key=<32hex>` — tracking key ties mirror to campaign.
- **Key reuse = network-wide node identity (2026-10-06):** `jatm5da51g?key=a083d1574757d06b0cc74d2bcbe17daf` cited by ≥3 donors — geekyhumans · futuremediatrix.com (dead) · raleighwakewssunaa.org (page carries WP oEmbed embeds of the node URL + `/about-us/`, `/abus/` subpaths). Second node `e66929gn9e?key=e365df8403dfdcd4758a2c5409dba7f6` cited from ivfgenesis.gr/author under weight-anchor post title "Authoritative Web site". Cross-ref channels: urlscan.io search API (`https://urlscan.io/api/v1/search/?q=domain:<d>&size=10`, no key), stack-lookup snapshots (techleads.fyi), plain web_search of the domain.
- **Node profile (RDAP + dig):** violationsyllable.com = registered 2025-11-14 via eNom → NS `sharehostsns.com` (cheap shared hosting) + StackPath; Gridinsoft report: trust 1/100, 5 blacklist detections (phishing) → burnable PBN node. Contrast casinoly.com = 2019-12 (PDR/URL Solutions) + Cloudflare = established commercial client.
- Mirror pages carry their own `link-factory-verification.htm` backlinks.

## 5. Station lists (k0 case file — REPORT.md K/K7)

- Wave 1 (source/stack-leak sources): softwarechimps.com · hejmo · tarvos · cemilozerblog · pbbny · typesofeverything · sfrrehab · sizeandsymmetry.cz
- Wave 2: thethinkagency.com (active flagship) · sabineparishlibrary.org · reports.americanprinciplesproject.org · dcde.gov.et (gov) · visionarygroup.com.pk · webaddesign.net · vamediabox.com · blog.agribazaar.com · lbchallenge.com · management.pefy-consulting.com · techvilly.com · antoniomarromusic.com
- Wave 3: kwa.kerala.gov.in (India gov) · bajajcreations.in · webbuild.acciorg.com · thegoatrace.org · apedr.org · equalitymaryland.org · ontariodailynews.ca · healthyagingbody.com · taylorfamilyenterprisesllc.com · fofralo.org
- Sector spread: gov, libraries, NGOs, clinics, small business, news — no vertical preference; all are SEO-donor hosts.
- Cleaned stations observed (plugin gone, residues remain): techvilly · lbchallenge · agribazaar.

## 6. Donor output capture (sentences render) + client taxonomy — 2026-10-06

- Sentences render into the donor frontend. Grep saved homepage HTML for hidden containers (`aria-hidden` / `display:none` / off-screen / `position:absolute;left:-`) — operator camouflages with theme-native classes. Live sample (thethinkagency.com): `<div>Many players seek out <a class="wpex-promoted-link" href="https://limenchilli.co.uk/">non GamStop betting</a> platforms …` (`wpex-promoted-link` = WPExplorer Total theme class).
- **Full external-href inventory of one donor page = operator's delivery list.** k0 archive: `loot/bq_src/lf_network_ext_links_tta.txt` (76 unique links). Tracks: gambling clients (casino.guru/TonyBet ×2 · woo-spin-casino-au.com · winwinbetapk-eg.com · winbet.com.nl · wild-chance.com.de · vipluckdeutschland.de.com · unique-casino.ch · toxi-casino-de.de) + gray affiliate bridges (dekomount, limenchilli, …).
- **Spot-check classification (one `curl -skL` fetch each):** dekomount.co.uk = affiliate bridge ("© 2026 Non GamStop Betting Sites", static non-WP); toxi-casino-de.de = Toxi Casino official site (static, pure client); steponsafety.co.uk = 404 dead. Always `-L` — CF answers a bare 301 to health/REST without it; non-WP shows `/res/js/core.*.js` or `/public/js/app.*.js` asset paths.
- tta verification series: v1=404 (never generated); v2–v7=200, identical template, ~59.5 KB each — expect uniform sizes across the series.
- readme.txt v3.0.0 addenda: install = WP admin zip upload or `POST /wp/v2/plugins` multipart; "single trusted public key embedded in the source"; sentences table `wp_link_factory_sentences` (homepage-scoped default vs `sitewide` flag).

## 7. Published research cross-reference

- Security Point Break (2026-08-13): "wasn't vulnerable, it was a backdoor"; found complete plugin dirs search-indexed; open questions: operator identity / distribution / fleet size.
- WPScan entry `4cad269d-0146-4ca9-a1ae-55f02c8e5433` (2026-08-11, CVSS 10.0); PoC public 2026-08-25: `LinkFactory\Users::handle_create_user()` → `wp_insert_user(role=administrator, lf_ random)`; `Footer::render()` echoes operator HTML UNESCAPED into hidden off-screen footer container. PoC still requires the private key — no no-key bypass.
- This case's increments over public research: live quantification (14k posts / brand ranking / timeline), byline-signature chain, verification-page mechanics, clone-mirror layer, cleaned-station evidence, stack-level implementation fingerprint.

## 8. Open questions (as of 2026-10-06)

- Operator identity & plugin distribution channel — still open publicly.
- Fleet size: 30+ stations from one dork sweep; per-station volume up to ~14k posts → conservative floor = 100k+ injected articles.
