---
name: admin-panel-link-hijack
description: "Hijack admin-panel links to one redirect URL."
version: 1.0.0
tags: [pentest, admin-panel, link-hijack, redirect, h5, gambling, cdn]
---

# Admin-Panel Link Hijack

Use when an authorized admin panel controls product/channel/landing URLs and the operator wants all clicks to one target URL. The goal is a verified data-layer redirect, not a domain-level setting change.

## 1. Inventory link surfaces before changing anything
- Pull the admin OpenAPI/Swagger and the panel JS; grep for `url`, `link`, `href`, `redirect`, `download`, `channelLink`, `icon`, `domain`.
- Dump one full object from each list endpoint. Never assume a field is editable because it appears in the response.
- Audit product list (the real click target), ads/classification records (often only `pid`, no own URL), channels (`channelLink`, `entryPath`, `apkPath`), and system settings (`WEB_DOMAIN`, `LANDING_DOMAIN`, `IMG_DOMAIN`, download domains).
- Fetch one entry page and count target occurrences; inspect the front-end for `window.open`, `location.href`, and the object field it reads. The click may read a product `url`, not the channel link.
- Read `references/link-surface-audit.md` for the field matrix and commands.

## 2. Change data-level fields, not host/domain settings
- Prefer the product batch-update endpoint for `url`; send only ids/url. If extra URL fields exist, use the single edit endpoint with the request DTO, not the full response object; read-only fields in the full object commonly cause a 500.
- Ads usually resolve through `pid` to a product; changing the product URL covers them. Do not invent an ad URL field.
- `channelLink` is commonly stored or derived and labelled bot-maintained. The single edit may return 200 while ignoring it; batch edit may reject it. Verify the exact field before claiming a change.
- Before trying to drive a bot-maintained field, check the bot control plane: webhook health and authorized users. A webhook that is down (`Connection refused`) or an empty auth table means the field cannot be updated from the panel; an unrelated bot API success is not proof the link can be changed.
- Never set `WEB_DOMAIN`/`LANDING_DOMAIN` to the redirect target as a shortcut. H5 entry pages often enforce a host/domain whitelist; a mismatch renders a maintenance page. This breaks the live site and does not fix stored channel links.
- If the operator asks for "all links", state which surfaces are data-editable and which are derived/bot-maintained; do not silently substitute a domain change.

## 3. Write and verify one item first
- Back up exact original values (settings, product rows, channel rows) before writing.
- Change one product/channel; read the list back and compare the exact field. A `code:0`/`data:1` response is not proof.
- For bulk update, batch and then count exact matches: target URL count and old-URL count.
- Fetch entry pages (`/entry/<cid>`) and count target and old-host occurrences. Include `backRedirectConfig.targetUrl` where present.
- For static pages/generators, compare before/after MD5, size, and `Last-Modified`. A `200` with `data:0` means no write; do not report success. `references/link-surface-audit.md` has the commands.

## 4. Handle legacy and cached pages separately
- A static landing page can be a legacy artifact whose generator is dead (`gen_html`/`landing_inject` return `data:0`). Do not loop on it; verify the live entry route and report the legacy page/CDN state.
- Fetch the origin and CDN separately; CDN TTLs can serve the old page for days after the origin changes. Add a cache-buster for verification; a CDN purge is a separate operation.
- Do not overwrite an existing executable or template with a page generator's output to force a link change; that breaks the host service and is not a link-hijack step.

## 5. Verify page assets after the change
- Links can be correct while images are broken. Extract image hosts from the entry page and test them.
- If an image domain NXDOMAINs, distinguish DNS from origin/CDN: direct origin GET, then CDN edge with `curl --resolve <img-host>:443:<edge-ip> https://<img-host>/<path>`, then check the cert SAN. If the edge returns the image, fix DNS, not `IMG_DOMAIN`.
- Keep HTTPS pages on HTTPS assets; do not point them at an HTTP MinIO/S3 endpoint (mixed content).
- Full recipe: `references/media-cdn-failure-triage.md`.

## 6. Restore and report
- Restore every test setting and test row; leave only the changes the operator requested. Re-check the settings list after restore.
- Report exact counts per surface, the target URL, and the surfaces that remain unchanged with the mechanism (derived, bot-maintained, legacy, CDN-cached).
- Do not ask repeatedly for infrastructure tokens after the operator has declined. Exhaust application-layer paths; if blocked, state the specific missing artifact or field and the observed evidence.
- Never fabricate a successful change from an API 200. Read the exact target back.

## Working agreements
- Production changes are one-item-first, backed up, and read back.
- A global setting is not a bulk-edit shortcut; it is a shared dependency.
- Prefer a verified subset with a clear residual list over a site-breaking "all".
