# CF 源站打空 → 兄弟白标枢轴

When Host-fingerprint masscan across BD/MM/SG/HK/EU/KH/VN/cloud ranges yields **only CF-RAY false positives or 0 GBKPay**, stop widening CIDR.

## Pivot sequence

1. **Fingerprint false-positive filter**: any probe body with business marker (`PlatformName`/`GBKPay`) that still has `CF-RAY` / `server: cloudflare` / `cf-cache-status` = ISP transparent cache or CF edge — **not origin**. Discard before claiming origin.
2. **Collect sibling brands**: cert SAN list, TLS CN on Aliyun hits (`*.lucky3357.com`, `*.xepay1.com`, …), frontend Host rewrites (`lucky1pay` → `admin.lucky1pay.com`), webpack product name (`worldpaypp`).
3. **Resolve admin hosts** via DoH/DNS: prefer `admin.` / `panel.` / brand apex. ALB CNAMEs (`*.alb.aliyuncsslbintl.com`) are high-value — they often terminate the **management** plane even when the cashier stays on CF.
4. **Confirm stack coexistence**: same IP may answer worldpaypp `GET /api/getSetting` (StarPay/GBKPay JSON) **and** yudao `/admin-api/...` (encrypt-key). Different products, same ops family.
5. **Mine tenant/IP APIs** on the admin stack (see `yudao-encrypt-tenant-whitelist.md`) instead of another country masscan.
6. **CF Registrar RDAP** (`rdap.cloudflare.com/.../domain/X`) may leak registrant country/city for scan prioritization only.

## When masscan is still useful

- You have a non-CDN A/AAAA / ALB IP to expand /24 neighbors
- You have a verified non-CF fingerprint without CF-RAY
- Country hint from RDAP + no admin ALB yet

Otherwise: sibling admin > more CIDR.

## Prefer business-plane origin capture (verified)

If you already own a manager JWT on the worldpaypp family, **skip further CIDR** and use `ShopInformUrl` + `informOrders` to make the origin call out — see `shopinformurl-origin-capture.md`. That path landed a real GCP origin after ~1.5M IPs of Host fingerprint returned 0.
