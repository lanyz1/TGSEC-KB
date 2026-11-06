#!/usr/bin/env python3
"""Link-farm miner: given N known SEO-farm pages, find the domain pool the same buyer owns.

Why: farm templates insert the buyer's whole domain set into every page's footer, so domains
appearing on ~all pages are HIS, while 1x domains are ordinary farm filler.

Usage:
    python3 link_farm_miner.py site1.cyou site2.cyou site3.cyou ... [--threshold 0.6] [--top 60]

Notes:
  * Fetch happens through `curl` with --noproxy '*' and a fixed UA so a Tor/proxy env in the
    environment cannot silently change results (see recon-negative-validation section on UA/proxy traps).
  * Prints the frequency table plus, for domains above threshold, their resolved A records.
"""
import argparse
import collections
import concurrent.futures
import re
import subprocess
import sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
HREF = re.compile(r'href=["\']https?://([a-zA-Z0-9._-]+)', re.I)

# Farm filler you never want ranked as the operator's own property.
NOISE = re.compile(
    r'(^|\.)(w3\.org|schema\.org|googleapis\.com|gstatic\.com|gravatar\.com|wordpress\.org|'
    r'google\.com|bing\.com|baidu\.com|twitter\.com|facebook\.com|youtube\.com|pinterest\.com|'
    r'instagram\.com|linkedin\.com|telegram\.org|t\.me|apkpure\.com|softonic\.cn|uptodown\.com|'
    r'cloudflare\.com|cloudflareinsights\.com|tailwindcss\.com|51\.la)$', re.I)


def fetch(site):
    """Return (site, html). Never raises; a dead farm page is just skipped."""
    url = site if site.startswith("http") else f"https://{site}/"
    try:
        out = subprocess.run(
            ["curl", "-sL", "-k", "-m", "25", "--noproxy", "*", "-A", UA, url],
            capture_output=True, text=True, timeout=32, errors="ignore",
        ).stdout
        return site, out or ""
    except Exception:
        return site, ""


def resolve(domain):
    try:
        out = subprocess.run(["dig", "+short", "A", domain, "@8.8.8.8"],
                             capture_output=True, text=True, timeout=10).stdout
        return [l.strip() for l in out.splitlines() if l.strip() and ":" not in l]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", nargs="+")
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="fraction of pages a domain must appear on to count as the pool (default 0.6)")
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--no-resolve", action="store_true")
    args = ap.parse_args()

    counter = collections.Counter()
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for site, html in ex.map(fetch, args.sites):
            if not html:
                print(f"  [skip] {site}", file=sys.stderr)
                continue
            ok += 1
            hosts = {h.lower() for h in HREF.findall(html) if not NOISE.search(h.lower())}
            counter.update(hosts)
            print(f"  [{site}] {len(hosts)} external hosts, {len(html)}B", file=sys.stderr)

    if not ok:
        print("no pages fetched -- check the site list / egress", file=sys.stderr)
        return 1

    cutoff = max(2, int(ok * args.threshold))
    print(f"\n===== source pool (>= {cutoff}/{ok} pages) =====")
    pool = [(d, n) for d, n in counter.most_common() if n >= cutoff]
    if not pool:
        print("  (none -- lower --threshold, or the farm is not template-based)")
    for d, n in pool:
        line = f"  {n:3d}x  {d}"
        if not args.no_resolve:
            ips = resolve(d)
            line += "  -> " + (", ".join(ips) if ips else "NO-A")
        print(line)

    others = [(d, n) for d, n in counter.most_common() if n < cutoff][: args.top]
    if others:
        print(f"\n===== rest (top {len(others)}; treat as farm filler) =====")
        for d, n in others:
            print(f"  {n:3d}x  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
