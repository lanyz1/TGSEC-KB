#!/usr/bin/env python3
"""Tor-fronted POST helper: hunt a clean exit, then retry-until-JSON.

Why: WAF-fronted APIs ban/challenge most egress; a JSON body is the only proof
the origin answered. Same --proxy-user == same Tor exit, so a credential that
worked once keeps working for the whole run.
"""
import json
import os
import random
import subprocess
import tempfile
import time

TARGET = 'https://example.com'
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
SOCKS = '127.0.0.1:9050'


def cred():
    return f'u{random.randint(1, 10**9)}:p{random.randint(1, 10**9)}'


def post(path, body=None, proxy_user=None, method='POST', tries=6, tout=25, headers=None):
    """POST and return the body only if the ORIGIN answered (body starts with '{')."""
    for _ in range(tries):
        hf, bf = tempfile.mktemp(), tempfile.mktemp()
        cmd = ['curl', '-s', '-k', '-D', hf, '-o', bf,
               '--socks5-hostname', SOCKS, '--proxy-user', proxy_user or cred(),
               '-A', UA, '-m', str(tout), '-X', method,
               '-H', 'Content-Type: application/json',
               '-H', f'Origin: {TARGET}', '-H', f'Referer: {TARGET}/']
        for h in (headers or []):
            cmd += ['-H', h]
        if body is not None:
            cmd += ['--data', json.dumps(body)]
        cmd += [TARGET + path]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=tout + 10)
            bod = open(bf, errors='replace').read()
        except Exception:
            bod = ''
        finally:
            for f in (hf, bf):
                try:
                    os.unlink(f)
                except OSError:
                    pass
        if (bod or '').lstrip().startswith('{'):
            return bod
    return None


def find_clean_exit(path, body=None, max_tries=20):
    """Return a Tor credential whose exit reaches the origin."""
    for i in range(max_tries):
        c = cred()
        r = post(path, body, proxy_user=c, tries=1)
        print(f'[exit {i}] {"ORIGIN" if r else "blocked/challenged"}', flush=True)
        if r:
            return c
        time.sleep(1)
    return None


if __name__ == '__main__':
    c = find_clean_exit('/csapi/serverTime', None)
    if not c:
        raise SystemExit('no clean exit found')
    print('clean exit credential:', c)
    print(post('/csapi/login', {'username': 'admin', 'password': 'x', 'theme': 'default'}, proxy_user=c))
