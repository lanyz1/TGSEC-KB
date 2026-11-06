#!/usr/bin/env python3
"""Playwright headless: capture XHR/fetch/WS traffic for API surface mapping.

Usage: python3 capture_net.py <url> [wait_seconds]
Prints one JSON line per unique request/response. Requires: pip install playwright && playwright install chromium
"""
import sys, json
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
wait_s = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0

hits = []

def on_request(req):
    rt = req.resource_type
    if rt in ("xhr", "fetch", "websocket") or req.url.startswith("ws"):
        hits.append({"t": "req", "rt": rt, "method": req.method, "url": req.url})

def on_response(resp):
    try:
        rt = resp.request.resource_type
    except Exception:
        return
    if rt in ("xhr", "fetch"):
        ct = (resp.headers or {}).get("content-type", "")
        hits.append({"t": "resp", "status": resp.status, "ct": ct[:40], "url": resp.url})

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36")
    page = ctx.new_page()
    page.on("request", on_request)
    page.on("response", on_response)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print("[goto]", e, file=sys.stderr)
    page.wait_for_timeout(int(wait_s * 1000))
    try:  # scroll to trigger lazy loads
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(800)
    except Exception:
        pass
    b.close()

seen = set()
for h in hits:
    key = json.dumps(h, sort_keys=True)
    if key in seen:
        continue
    seen.add(key)
    print(json.dumps(h, ensure_ascii=False))
