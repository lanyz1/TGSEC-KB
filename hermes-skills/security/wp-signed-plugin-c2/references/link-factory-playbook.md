# link-factory playbook (CVE-2026-15413 class)

## Quick probes

```bash
curl -sk "https://TARGET/wp-json/link-factory/v1/health"
# {"status":"ok","version":"<hash>","protocolVersion":2|5}

curl -sk "https://TARGET/wp-json/link-factory/v1/users"
curl -sk "https://TARGET/wp-json/link-factory/v1/articles"
# v2: often 404; v5: 400 missing signed params (not unauth success)

curl -sk "https://TARGET/wp-content/plugins/link-factory/includes/"
# listing may show trait-signature.php / class-users.php / class-articles.php sizes
```

## Ghost author check

```bash
# posts by author id
curl -sk "https://TARGET/wp-json/wp/v2/posts?author=N&per_page=2"
# user object
curl -sk "https://TARGET/wp-json/wp/v2/users/N"
# empty display + invalid_user_id + spam SEO = implant residue
```

## FOFA shapes (re-validate live)

- body/health with `protocolVersion` and `link-factory`
- path/title open directory under `wp-content/plugins/link-factory`
- version hash alone is insufficient (collisions)

## Empty PHP rule

Keep body only if:

- starts with `<?php`, or
- contains `namespace LinkFactory`, or
- contains `sodium_crypto` / Ed25519 verify primitives

Discard theme 404 HTML, SPA shells, and obfuscated JS even if status 200 and path ends `.bak`.

## Origin Host rule

Same skin HTML after `--resolve` ≠ same app. Require LF health 200 JSON on that Host/IP pair before calling "same WordPress".

## Case anchor (sanitized)

OKX-channel nav farm: primary OneNav user panel taken; LF on main channel **v2 castrate**; siblings **v5 full**; listing sizes confirmed; PHP GET 0B local+offbox; WP admin/shell gated on operator Ed25519 material. Report series F31–F53 under cases tree — values redacted.
