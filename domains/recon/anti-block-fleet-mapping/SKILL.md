---
name: anti-block-fleet-mapping
description: "Use when mapping CN anti-block mirror fleets."
version: 1.0.0
tags: [recon, mirrors, anti-block, cn-web, infrastructure, origin]
related_skills: [cdn-origin-tracing, jingfaka-platform-pentest, pentest-execution]
---

# Anti-block mirror fleets & disguised infra (CN blocked ecosystems)

When the main domain is CF-locked / block-paged and the operator runs "anti-block" (反封锁) machinery:
mirror fleets, address-publisher pages, disguised storage. **The fleet leaks more than the main domain
ever will** — pivot to it early instead of hammering the one CF'd host.

## When to use

- The front domain is all-CF with challenges; footers / 404s / Telegram point at 地址发布页,
  screenshot-to-save widgets, or rotating mirror domains.
- Asset hosts resolve to "cloud-like" names (vcloudNN / qiniuyunNN / ucloudNN shapes) that don't belong
  to the real clouds, or to bare IPs answering on 443 only.

## Procedure

1. **Harvest domains** from every reachable property: main site, API pages, ERROR pages, footers.
   `grep -oE 'https?://[a-z0-9.-]+\.[a-z]{2,12}'` over saved HTML. Styled 404/error pages leak the most.
2. **Publisher pages** (地址发布页) list the mirror families; they usually load shared JS from a release
   hub (`lib.<hub>/dizhi/publish.js`). Fetch the hub JS — obfuscator.io output keeps domain literals in
   PLAINTEXT inside the `_0x` string array; grep quoted strings from the raw file (no full
   de-obfuscation needed). One array = a 50-domain sequential fleet.
3. **Resolve the fleet in one pass**, split CF vs non-CF:
   - one redirector box serving N domains (all `301 →` the CF'd current domain) = skip;
   - parked members (registrar / ParkLogic pages) = skip;
   - real app/storage boxes = scan those.
4. **Disguised storage chains**: resolve the FULL CNAME chain (intermediate CNAMEs, then the final A —
   `dig +short`). Chains like `<hash>.vcloud6.xyz → img.<brand>.in → fdc100g2b.<brand2>.cloud →
   <REAL-IP>` walk to a bare box, often NOT behind CF. Verify by replaying a known asset path at the
   origin: `curl -sk --resolve <host>:443:<IP> https://<host>/<known-path>` → 200 + real bytes =
   confirmed. DNS resolution alone is not proof — the vhost must serve.
5. **Scan and classify**: `nmap -Pn -p-` each confirmed box. Expect single-service hosts (443 static
   file server; decoy plain-nginx 8888 answering 404 to everything). Static-only = content host, not a
   shell target — record it and move on instead of forcing it.
6. **Bundles & orgs**: site JS via jsDelivr from GitHub orgs survives org deletion —
   `https://data.jsdelivr.com/v1/packages/gh/<org>/<repo>` enumerates cached versions and files even
   when github.com 404s. Grep big bundles for endpoints/domains, but check whether a bundle is a
   vendored third-party library (player/chart) before mining it.

## Pitfalls

- Wildcard `*.domain` in CT ≠ wildcard DNS; guessed sibling nodes (`fdc100g1b`…) usually NXDOMAIN —
  naming counters do not imply a reachable family.
- Multiple fake-cloud brands (vcloud / qiniuyun / ucloud + numeric suffixes) frequently all mirror ONE
  box — resolve before multiplying targets.
- The redirector box and parked domains are noise; the value is the small set of real boxes behind the
  aliases.
