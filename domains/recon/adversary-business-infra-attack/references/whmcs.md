# WHMCS notes (reseller storefronts)

## Fingerprint
- `x-powered-by: PHP/8.3.x` + Apache; theme CSS header "WHMCS Twenty-One Theme" → modern 8.x line.
- API endpoint: `/whmcs/includes/api.php` (POST `action=...`, e.g. `GetActivityLog`, `ValidateLogin`).

## Portal paths (with correct Host header)
- `/whmcs/` portal home; `register.php`; `login.php`; `cart.php`; client area `clientarea.php` (302 to login when no session; sets a `WHMCSxxxx` cookie).
- Content routes: `index.php?rp=/knowledgebase|/announcements|/download|/store/<product>|/login`.
- Store products expose the business line (e.g. `?rp=/store/arin-ipv4`, `ripe-ipv4` → IPv4 address resale).

## Access quirks
- Blanket 403 via IP or www Host can coexist with 200 via bare-domain Host — always try `-H "Host: <bare-domain>"`.
- Registration form fields: token, firstname, lastname, email, password, password2, address1, city, state, postcode, country, phonenumber, accepttos, captcha, register.
- Registration is behind Google reCAPTCHA (siteKey in page JS); OCR of the PHP `includes/verifyimage.php` captcha did not pass validation — prefer login, API, or reset paths over captcha automation.
- API when IP-restricted: `result=error;message=Invalid IP <your-ip>` — the allowlist is the wall; route through an allowed machine instead of more guessing.

## Harvest
- Knowledgebase / downloads pages leak support emails and tos.pdf links.
