# SPA / wildcard-vhost estates: response-class discrimination

Purpose: on estates (many vhosts, SPA fronts, gateways) raw status codes lie in BOTH directions — "200 everywhere" (false positives) and "404/closed everywhere" (false negatives). Classify every response by WHICH layer answered before believing it.

## Layered 404s / 200s — read the class, not the code
- **Same byte-size body on every GET path** = SPA catch-all fallback → NOT a hit. Test: fetch `/` vs `/a/b/c`; identical length + content-type = shell. (2026-10: audit frontend returned an identical 6873B shell for everything.)
- **Tiny HTML 404 (<200B, nginx signature)** = gateway/nginx: route not proxied at all.
- **Framework JSON/HTML 404** (e.g. Yii2 `Unable to resolve the request`, Chinese error page) = backend reached, route wrong → you just proved a proxied backend exists.
- **Static path + POST → 405 (nginx)** = method blocked at gateway; GET-only probing misses the door. Nginx `;`-truncation quirks can route GET and POST to different layers.
- **Route ladder**: 404(static) → 404(framework) → 401/403/500 = module prefix RESOLVED. The 404→401/500 transition is how hidden module prefixes are found (2026-10: `/api/` → Yii2 404, `/api/v1/` → route hit; `ding-login` → 500 = route resolved + handler executing).
- **Auth-error semantics**: distinguish "missing credential" errors from "invalid credential" errors — different code paths. A missing-credential error still proves the route and its middleware exist. Enumerate a whole API group with a no-token call and record each endpoint's error class.

## Estimate the estate honestly (dedupe before claiming numbers)
- Wildcard-vhost estates collapse: many exposed hosts → often ONE backend file.
- Procedure: group hits by body size → download one representative per group → md5 → then count. Measured 2026-10: 798-host scan → 392 "hits" → 61 unique logs; second wave 159 fetched → 61 unique / 98 dups.
- Report BOTH numbers ("392 hits across 324 hosts, 61 unique artifacts") — inflating unique counts is how findings get retracted.

## Cloud storage classes
- OSS/COS/S3 `AccessDenied` on LIST ≠ objects private — try direct object reads / known prefixes.
- `The bucket you access does not belong to you` = wrong account or wrong region endpoint, NOT a broken ACL. Multi-account estates split frontend assets and data into different accounts.

## Probe-validation recipe (before believing any negative)
1. On the same base, request one path that MUST 404 and one known-good path.
2. Compare body size & class (shell / gateway / framework / app).
3. Only then interpret the target probe.

Worked example case files: `/root/cases/rpfds.com/probe_audit2-6.sh`, `audit_ctx.txt`, `audit_api_extract.txt`.
