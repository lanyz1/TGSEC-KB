# Case Reference: Aime / Saturney-style Laravel Admin Decoy (2026-10)

Sanitized field notes. All credential values are redacted; do not reconstruct them.

## Surface

- Laravel 8.75 admin at `aime.saturney.io/admin/`; reachable only through a
  WARP SOCKS egress because the origin blocked the tester's direct IP.
- Real menu routes: `dashboard`, `orders`, `products`, `users`, `payment-settings`,
  `shipping-settings`, `packing-slip-settings`, `notification-settings`.
- Most other guessed routes (`settings`, `backup`, `logs`, `database`, `update`,
  `plugins`, `admins`, `roles`, `export`, `file-manager`, `terminal`) returned the
  same ~2,957-byte dashboard shell.

## Decoy evidence

1. `/.env` returned 200 and explicitly described itself as a honeypot/decoy with
   fabricated values.
2. `/.git/config` returned 200 with a `honeytoken` remote, but `HEAD`, `index`,
   `refs/*`, and `objects/*` were all 404.
3. `/storage/logs/laravel.log` returned 200 and contained a fabricated DB user and
   SMTP password matching the `.env` story; the log also reflected the tester's own
   earlier actions.
4. The apparent DB credential used an artificial prefix and never worked against the
   real MySQL service.

Conclusion: **decoy chain**, not a source/config leak. No decoy value was used.

## Mock upload evidence

- `PUT /admin/packing-slip-settings/upload` returned 200 JSON with
  `success: true` and a path under `/storage/app/public/...`.
- Benign `probe.html` and `benign.php` both returned the fixed path
  `/storage/app/public/products/up.jpg`; that URL was not retrievable from the web
  root.
- Main `POST/PUT /admin/packing-slip-settings` returned nginx 405.

Conclusion: **mock upload**, not an arbitrary-write primitive. Do not overwrite the
real Blade template.

## Useful pivot

FOFA certificate/domain pivots produced a separate, apparently real management
console on another IP. That became the next target; the decoy admin was left in
read-only state and was not modified.
