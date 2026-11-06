#!/usr/bin/env python3
"""Grab TWA initData from an open Mini-App iframe (Web K + chromium CDP).

Usage:  python3 grab_twa_initdata.py [out_file]

Prereqs:
  - chromium launched: chromium --headless=new --no-sandbox --remote-debugging-port=9222 --user-data-dir=/tmp/prof
  - Web K logged in; target bot's webview button clicked; LAUNCH popup passed.
Why: playwright page.frames/querySelectorAll cannot see the cross-process (OOPIF)
mini-app iframe -- only raw CDP Target.getTargets exposes it.
"""
import sys, urllib.parse
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else 'initdata.txt'

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    bs = browser.new_browser_cdp_session()
    targets = bs.send('Target.getTargets').get('targetInfos', [])
    found = []
    for ti in targets:
        u = ti.get('url', '')
        if 'tgwebappdata' in u.lower():
            frag = urllib.parse.urlparse(u).fragment or urllib.parse.urlparse(u).query
            q = urllib.parse.parse_qs(frag)
            idata = q.get('tgWebAppData', [None])[0]
            if idata:
                found.append((ti.get('type'), u[:120], idata))
    if not found:
        print('no tgWebAppData target found -- is the mini app actually open with LAUNCH passed?')
        for ti in targets:
            if ti.get('type') in ('page', 'iframe'):
                print('  target:', ti.get('type'), ti.get('url', '')[:130])
        sys.exit(1)
    kind, url, idata = found[-1]
    open(OUT, 'w').write(idata)
    print(f'saved initData ({len(idata)} chars) -> {OUT}')
    print('target:', kind, url)
    print('head:', idata[:120])
    print('NOTE: auth_date has a TTL (commonly 1h-24h) -- use it immediately.')
