#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量扫描赌场站点的 USDT/加密支付支持(并行快速版)。

用法:
  python usdt_payment_scan.py                # 扫描内置站点列表
  python usdt_payment_scan.py site1.com site2.com   # 自定义站点

原理:
  1. 主页 HTML + 前 6 个 JS + 常见支付路径(/banking /cashier /payment-methods
     /deposit /crypto /withdraw)并行抓取
  2. 按币种关键词字典(PAT)扫描命中数
  3. 结果存 usdt_scan_results.json

关键教训:
  - 关键词出现 ≠ 支持(可能是 "We do NOT support crypto" 否认句)!
    命中后必须二次提取上下文(print_contexts)验证
  - 支付 logo 图片(tether.png / bitcoin.png / bitcoin_cash.png)是最强证据
  - 压缩 JS 里 grep 会被 eCode/eContext 淹没,必须用精确正则
"""
import re, json, urllib.request, ssl, sys
from concurrent.futures import ThreadPoolExecutor

SITES = [
    ("fairgocasino.com", "https://www.fairgocasino.com/"),
    ("slotswincasino.com", "https://www.slotswincasino.com/"),
    ("ozwincasino.com", "https://www.ozwincasino.com/"),
    ("freespinz.com", "https://freespinz.com/"),
    ("reddog-games.com", "https://reddog-games.com/"),
    ("crypto-games.io", "https://crypto-games.io/"),
    ("luxury.casino", "https://luxury.casino/en/"),
    ("whamoo.com", "https://whamoo.com/"),
    ("lyracasino.com", "https://www.lyracasino.com/"),
]

PAT = {
    "USDT": r'(?i)\busdt\b|tether|trc-?20|erc-?20',
    "BTC": r'(?i)\bbitcoin\b|\bbtc\b',
    "CRYPTO": r'(?i)\bcrypto(?:currency)?\b|blockchain',
    "ETH": r'(?i)\bether(eum)?\b',
    "加密支付商": r'(?i)bitpay|coinbase|cryptopay|nowpayments|plisio|coingate|changelly|guardarian',
}
PAY_PATHS = ["/banking", "/cashier", "/payment-methods", "/deposit", "/crypto", "/withdraw"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=7):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    })
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return r.read(), r.status, r.geturl()
    except Exception as e:
        return None, 0, str(e)[:60]


def scan_site(item):
    name, url = item
    entry = {"keywords": {}, "pages": {}}
    html, code, final = fetch(url)
    base = final or url
    if html:
        text = html.decode('utf-8', errors='ignore')
        for kw, pat in PAT.items():
            ms = re.findall(pat, text)
            if ms:
                entry["keywords"]["home_" + kw] = len(ms)
        js_refs = [j if j.startswith('http') else base.rstrip('/') + '/' + j.lstrip('/')
                   for j in re.findall(r'<script[^>]*src="([^"]+\.js[^"]*)"', text)][:6]
        for j in js_refs:
            try:
                jh, jc, _ = fetch(j, timeout=5)
                if jh:
                    jt = jh.decode('utf-8', errors='ignore')
                    for kw, pat in PAT.items():
                        ms = re.findall(pat, jt)
                        if ms:
                            entry["keywords"]["js_" + kw] = entry["keywords"].get("js_" + kw, 0) + len(ms)
            except Exception:
                pass
    for p in PAY_PATHS:
        try:
            ph, pc, pf = fetch(base.rstrip('/') + p, timeout=5)
            if ph and pc == 200 and len(ph) > 300:
                pt = ph.decode('utf-8', errors='ignore')
                title = re.search(r'<title[^>]*>([^<]*)</title>', pt)
                entry["pages"][p] = title.group(1)[:50] if title else "?"
                for kw, pat in PAT.items():
                    ms = re.findall(pat, pt)
                    if ms:
                        entry["keywords"]["page_" + p + "_" + kw] = entry["keywords"].get("page_" + p + "_" + kw, 0) + len(ms)
        except Exception:
            pass
    return name, entry


def print_contexts(url, timeout=10):
    """二次验证:打印关键词命中上下文(区分支持/否认)"""
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}), timeout=timeout, context=ctx)
        t = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  ERR: {str(e)[:60]}")
        return
    ms = list(re.finditer(r'(?i)(usdt|tether|bitcoin|crypto)[^<>]{0,120}', t))
    seen, count = set(), 0
    for m in ms[:8]:
        c = m.group(0).strip()
        if c[:40] not in seen and count < 6:
            seen.add(c[:40])
            print(f"  [{m.group(1)}] ...{c[:130]}...")
            count += 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        SITES = [(a, f"https://{a}/") for a in sys.argv[1:]]
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for name, entry in ex.map(scan_site, SITES):
            results[name] = entry
    for n, e in results.items():
        kws = {k: v for k, v in e["keywords"].items() if v}
        print(f"\n=== {n} ===\n  关键词: {kws if kws else '无'}\n  支付页: {e['pages'] if e['pages'] else '无'}")
    json.dump(results, open("usdt_scan_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 完成。对命中站点运行 print_contexts(站点, 支付页URL) 二次验证")
