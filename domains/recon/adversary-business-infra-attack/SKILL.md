---
name: adversary-business-infra-attack
description: Use when attacking an adversary's business systems.
---

# Adversary Business Infra Attack

After compromising a crew's C2 or harvesting operator data, the highest-yield next targets are their **business systems** — IP/resale storefronts (WHMCS), proxy/IP management consoles, mail gateways, internal platforms. They are far weaker than the C2, and each one is a new door into their machines.

## Operating rules (user preferences)
- 继续 / 继续干 = produce the NEXT batch of tool calls now — never a status report, never a permission question.
- Never claim options are exhausted. 还有没有手段 = immediately enumerate AND execute new surfaces.
- Keep an explicit attack-surface backlog; when one door closes, open the next in the same turn. Proven order: operator IPs → adjacent /24s → sibling brands → storefronts/gateways → credential matrices.

## Expansion recon (run when stalled)
- Reverse-IP pages leak sibling domains: `curl -s "https://rapiddns.io/sameip/<IP>?full=1"`.
- Scan operator IPs from audit logs as INFRASTRUCTURE — they host the crew's own VPS and panels, not just logins.
- Adjacent /24 sweeps: repeated identical service signatures (same 403 page, same port pattern) = one fleet; enumerate it wholesale.
- Brand web: cert subjects (`openssl s_client -connect IP:443 2>/dev/null | openssl x509 -noout -subject`), www/dev/vhost1/api subdomains, data-center brands named in certs.
- **Segment-wide cert census is the fastest brand map.** Loop the whole /24 (`for i in $(seq 1 254); do echo | timeout 4 openssl s_client -connect X.Y.Z.$i:443 2>/dev/null | openssl x509 -noout -subject; done`) — one pass identifies every cert-bearing host and its brand (measured: a 60-host segment yielded a full phishing-farm map — fake CurseForge / iCloud / TradingView front-ends + 8 proxy nodes — from cert CNs alone).
- **Cert CN is a vhost key, not just a label.** When a cert names a domain but plain-IP access 404s/000s, read the vhost with `curl -k -H "Host: <cert-CN>" https://IP/` — often the only readable path when the domain is dead, geofenced, or points at a CDN. The vhost bodies then split the segment into roles (phishing pages / storage gateways / panels).
- **Grade attribution before touching anything on a segment.** ① hard = the IP appears in the crew's own logs/audit; ② org-level = PTR/NS/registrant chain stitches it to them; ③ segment-level = same-/24 density anomaly alone. Only ①/② justify active testing; ③ is a lead, not a target — a neighbor's box reported as "theirs" collapses the case's credibility.

## Access-control bypasses
- **Host-header vhost bypass**: 403 on a path via IP or www-Host? Retry the same IP with `curl -k -H "Host: <bare-domain>" https://IP/path` — per-vhost ACLs differ; also sweep sibling subdomains as Host.
- **Cover-page detection**: identical body size/ETag across unrelated paths = catch-all page; a 200 there proves nothing. Compare sizes before trusting any "hit".
- **CF-fronted scripted logins**: floods get CF-blocked (HTTP 200 with an HTML body). Slow down, send a real browser UA, use the alternate exit IP; verify the response is JSON before counting an attempt.

## Credential attacks
- Try `admin/admin123` first on self-hosted consoles (routine on Chinese FastAPI management panels; full read/write REST once in — dump users/IP inventory/logs; any hashes feed offline cracking).
- Online unlimited guessing ≈ 18 req/s → 30k dictionary ≈ 27 min per username; run username×dictionary matrices (these panels rarely rate-limit).
- bcrypt cost-12 ≈ 0.2-0.3 s/hash/core → 100k dictionary × 5 hashes = hours. Parallelize (`multiprocessing.Pool(cores)`), background it, and keep attacking other surfaces while it runs.
- Reverse product login obfuscation from the page JS BEFORE brute forcing — never POST plaintext where the form expects an encoded field (see references).

## Product recipes
- WHMCS portals → `references/whmcs.md`
- Barracuda ESG / CUI login → `references/barracuda-cui.md`

## Pitfalls
- **Audit-log IPs are guilty until checked against your own egress.** Scan traces and ZK/audit connections showing an unfamiliar IP are routinely your own test host (compare `curl ifconfig.me`) or an unrelated third attacker — verify before writing "co-conspirator infrastructure" into a report; a retracted attribution poisons every downstream judgement.
- Clean JSON 404s and 422 validation errors (FastAPI/pydantic) = parameterized stack; skip SQLi/path-traversal fuzzing there.
- WHMCS registration is reCAPTCHA-gated; OCR of the PHP verifyimage captcha did not pass — pivot to login/API/reset paths instead of burning time on captchas.
- A path present in leaked source that returns 405/redirect on the live domain is routed elsewhere (internal port / other vhost) — don't re-fuzz it blindly.
