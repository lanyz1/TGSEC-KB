#!/usr/bin/env python3
"""List an S3-compatible prefix, download images, md5-dedupe, OCR, keyword-filter.

Usage:
  python3 ocr_bucket_images.py https://bucket.s3.ap-southeast-1.amazonaws.com uploads/images/
  python3 ocr_bucket_images.py <base> <prefix> --lang chi_sim+eng --keywords admin,后台,密码,token

Requires: requests, and tesseract with the requested language data installed.
"""
import argparse
import hashlib
import os
import re
import subprocess
import tempfile

import requests
import xml.etree.ElementTree as ET

NS = '{http://s3.amazonaws.com/doc/2006-03-01/}'
DEFAULT_KEYWORDS = ['admin', '后台', '密码', '登录', '管理', 'token', '账号', 'password',
                    'login', '验证码', '数据库', 'mysql', 'redis', '配置', 'secret', 'key']


def list_keys(base, prefix):
    token, keys = None, []
    while True:
        params = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        if token:
            params['continuation-token'] = token
        r = requests.get(base, params=params, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        keys += [c.find(NS + 'Key').text for c in root.iter(NS + 'Contents')]
        nxt = root.find(NS + 'NextContinuationToken')
        if nxt is None:
            break
        token = nxt.text
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base', help='bucket URL, no trailing slash')
    ap.add_argument('prefix', help='key prefix, e.g. uploads/images/')
    ap.add_argument('--lang', default='chi_sim+eng')
    ap.add_argument('--keywords', default=','.join(DEFAULT_KEYWORDS))
    ap.add_argument('--psm', default='6')
    a = ap.parse_args()

    base = a.base.rstrip('/')
    kws = [k.strip() for k in a.keywords.split(',') if k.strip()]
    keys = [k for k in list_keys(base, a.prefix)
            if re.search(r'\.(png|jpe?g|webp|bmp|gif)$', k, re.I)]
    print(f'{len(keys)} image keys under {a.prefix}', flush=True)

    seen = {}
    tmp = tempfile.mkdtemp(prefix='ocr_bucket_')
    for i, key in enumerate(keys):
        fn = os.path.join(tmp, hashlib.md5(key.encode()).hexdigest())
        try:
            if not os.path.exists(fn):
                r = requests.get(f'{base}/{key}', timeout=30)
                if r.status_code != 200 or len(r.content) < 500:
                    continue
                with open(fn, 'wb') as f:
                    f.write(r.content)
            h = hashlib.md5(open(fn, 'rb').read()).hexdigest()
            if h in seen:
                continue
            seen[h] = key
            out = subprocess.run(
                ['tesseract', fn, 'stdout', '-l', a.lang, '--psm', a.psm],
                capture_output=True, text=True, timeout=60).stdout
            low = out.lower()
            hits = [w for w in kws if w in low]
            if hits:
                print('***', key, hits, '::', ' '.join(out.split())[:300], flush=True)
        except Exception as exc:  # noqa: BLE001 - keep the sweep running
            print('ERR', key, str(exc)[:80], flush=True)
        if i and i % 50 == 0:
            print('...', i, 'unique', len(seen), flush=True)

    print('unique images', len(seen))


if __name__ == '__main__':
    main()
