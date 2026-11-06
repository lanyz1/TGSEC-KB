# Laravel Admin Case Notes (field notes, redacted)

Session detail for a Laravel 8 / PHP 8.0.28 commerce admin panel behind Cloudflare, reached by reusing credentials from a sibling app. Keep credentials out of this file; use `<operator-email>` / `[REDACTED]` in notes.

## Entry

- Sibling app A had a read-only/mock admin: 8 menu items, all sub-pages ~2–3 KB dashboard shell, every POST/PUT 405, `/admin/products/upload` returned fixed `products/up.jpg`.
- Sibling app B (`travelsim.<operator-domain>`) is a real Laravel 8 commerce panel. `/admin` with the same email/password returned 200, title `仪表盘 - Saturney Telecom`; session cookie name `saturney_telecom_session`.
- A self-registered buyer could log in but `/admin` returned 403 — authenticated, no role. Mass-assigning `is_admin=1` / `role=admin` was rejected.
- Origin found by Host matrix: `Host: travelsim.<operator-domain>` against known IPs returned 200/11 KB on the same IP as app A. Cloudflare was in front; `--resolve` + WARP SOCKS reached origin.

## Admin menu

Orders, products, users, coupons, payment methods, shipping, packing-slip settings; product create/import routes present. Users page showed 20 rows; export only counts/field names, never PII in chat.

## Upgrade attempts and decisive results

| Test | Result |
|---|---|
| Product image `.php` | 302 back to create; extension rejected |
| Valid JPEG bytes + `.php` name | still rejected → extension whitelist, not MIME |
| Plain `.jpg` | stored as hashed `.jpg`; content intact but not executed |
| `.phtml` / `.phar` / `.php.jpg` | rejected; `.phar.jpg` stored as `.jpg` |
| Path-info `/uploads/x.jpg/x.php` | 404 |
| `<annotation file="/etc/passwd">` in footer | HTML-escaped; PDF text shows literal tag |
| `<b>R22BOLD</b>` product name in PDF | literal tag; mPDF injection dead |
| Order packing-slip PDF | 17 KB, `pdfdetach -list` 0 attachments, `strings` no `root:` |
| Admin search/filter SQLi (`q`, `role`, `type`, `status`) | no time delay |
| `/admin/products/import` | POST 405 / no form |
| Origin `.env*`, `storage/logs/*`, `_ignition/*` | 404; `_ignition/execute-solution` 405 |
| SSH to origin (`root`/`aime`/`travelsim` × reused password) | all denied; key-only |
| Target MySQL (`travelsim`/`saturney`/`telecom` × defaults) | 6 attempts, all 1045 |

## Business-logic PoC

- Admin-created 100% fixed coupon (`R22FREE`, `R22FREE2`, value ¥120) → orders `20261019114100L4OX3P` and `20261019114339DDTNXF` at ¥0.00.
- Only ¥0 orders; no real payment. Both set to `cancelled` during cleanup.
- Frame as **admin-configurable coupon/pricing risk**; not an unauth vuln unless a normal user can obtain the coupon.

## Cleanup sequence that actually worked

1. Test products 4/5 deleted; product 1 name/price/stock restored; footer cleared.
2. Coupons: first pass deleted IDs 1/2 but the list still showed `R22FREE` / `R22FREE2` — the delete had not taken effect despite 302. Re-fetched the page, parsed each row's form action, printed IDs, deleted IDs 1/2 again, re-fetched: 0 hits. **302 is not proof.**
3. Virtual items `R22CODE` ×2: route was `/admin/virtual-items/{id}`, not a product route; deleted by row action and verified.
4. Address 3 deleted; cart emptied; orders 1/2 set `cancelled`.
5. Product 1 `description` and footer original text were not captured before overwrite → reported as “not restored — original not captured”, set empty.
6. Test buyer account (`r22334...@...`) had no delete route; left in place and reported. Product test images may remain in storage; no delete API; reported.

## Lessons

- The mock sibling is not the target; the same credential on the next sibling may be a full admin. Keep the sibling list short and test once per app.
- Use a harmless HTML marker before any file-read payload in PDFs.
- Always verify deletes by re-fetch; parse row-specific actions, never infer IDs.
