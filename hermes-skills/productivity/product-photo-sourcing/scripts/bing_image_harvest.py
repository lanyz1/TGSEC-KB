#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bing 图库批量抓取 -> 下载 -> md5 去重 -> 出总览图册 (stdlib only).

用法:
  python bing_image_harvest.py --out "C:/Users/x/Desktop/shipai" --query "gold M1911 diamond" --query "纯金 M1911 镶钻"
  python bing_image_harvest.py --out DIR --query-file queries.txt --domain-filter goldguns,blackrose --budget 180

纪律: 每请求 8s 超时 + 循环墙钟硬止损(防不可达主机拖死执行单元); 下载后 md5 去重(超时重跑会留重复)。
"""

import argparse, hashlib, html, json, os, re, socket, ssl, time
import urllib.parse, urllib.request

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
    "Referer": "https://www.bing.com/",
}
ASYNC = "https://www.bing.com/images/async?q={q}&first=1&count={n}&mmasync=1"
M_ATTR = re.compile(r'm="(\{[^"]*?\})"')
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def get(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def harvest(query, count, timeout):
    """一条 query -> [{url, page, title}]"""
    url = ASYNC.format(q=urllib.parse.quote(query), n=count)
    try:
        body = get(url, timeout).decode("utf-8", "ignore")
    except Exception as e:
        print("  [harvest fail] %s: %s" % (query, type(e).__name__))
        return []
    out, seen = [], set()
    for m in M_ATTR.finditer(body):
        try:
            o = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        u = o.get("murl")
        if u and u not in seen:
            seen.add(u)
            out.append({"url": u, "page": o.get("purl", ""),
                        "title": (o.get("t") or "").strip()})
    print("  %-40s -> %d urls" % (query[:40], len(out)))
    return out


def safe_name(title, idx, prefix):
    stem = re.sub(r"[^A-Za-z0-9]+", "_", (title or "img"))[:34].strip("_") or "img"
    return "%s%s_%02d.jpg" % (prefix, stem, idx)


def download(items, outdir, timeout, deadline, prefix, min_bytes=4000):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    n = 0
    for o in items:
        if time.time() > deadline:
            print("  [budget reached] stop downloading")
            break
        path = os.path.join(outdir, safe_name(o["title"], n, prefix))
        try:
            req = urllib.request.Request(o["url"], headers=UA)
            data = urllib.request.urlopen(req, timeout=timeout, context=ctx).read()
        except Exception as e:
            print("  skip %-34s %s" % (o["url"][:34], type(e).__name__))
            continue
        if len(data) < min_bytes:
            continue
        with open(path, "wb") as f:
            f.write(data)
        print("  OK %9d  %s" % (len(data), os.path.basename(path)))
        n += 1
    return n


def dedupe(outdir):
    seen, dropped = {}, []
    for f in sorted(os.listdir(outdir)):
        if not f.lower().endswith(IMG_EXT):
            continue
        p = os.path.join(outdir, f)
        with open(p, "rb") as fh:
            h = hashlib.md5(fh.read()).hexdigest()
        if h in seen:
            os.remove(p)
            dropped.append(f)
        else:
            seen[h] = f
    if dropped:
        print("  dedupe removed %d: %s" % (len(dropped), ", ".join(dropped)))
    return dropped


def contact_sheet(outdir, title="contact sheet"):
    imgs = sorted(f for f in os.listdir(outdir) if f.lower().endswith(IMG_EXT))
    groups = {}
    for f in imgs:
        head = f.split("_")[0]
        groups.setdefault(head if 0 < len(head) <= 12 else "ungrouped", []).append(f)
    parts = ["<!doctype html><meta charset='utf-8'><title>%s</title>" % title,
             "<style>body{font-family:inherit;color:var(--foreground);margin:0;padding:4px}"
             "h2{font-size:15px;margin:18px 0 8px;border-left:3px solid var(--accent);padding-left:8px}"
             ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}"
             "figure{margin:0;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--card)}"
             "img{width:100%;height:165px;object-fit:contain;display:block;background:rgba(127,127,127,.08)}"
             "figcaption{font-size:11px;color:var(--muted-foreground);padding:5px 7px}</style>"]
    for g, fs in groups.items():
        parts.append("<h2>%s (%d)</h2><div class='grid'>" % (g, len(fs)))
        for f in fs:
            parts.append("<figure><img src='%s' loading='lazy'><figcaption>%s</figcaption></figure>"
                         % (urllib.parse.quote(f), os.path.splitext(f)[0]))
        parts.append("</div>")
    p = os.path.join(outdir, "00_gallery.html")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))
    print("  contact sheet -> %s (%d imgs)" % (p, len(imgs)))
    return p


def main():
    ap = argparse.ArgumentParser(description="Bing image harvest for real product photos")
    ap.add_argument("--out", required=True, help="delivery dir (desktop recommended)")
    ap.add_argument("--query", action="append", default=[], help="repeatable")
    ap.add_argument("--query-file", help="one query per line, # skipped")
    ap.add_argument("--count", type=int, default=35, help="results per query")
    ap.add_argument("--limit", type=int, default=40, help="max images downloaded")
    ap.add_argument("--timeout", type=float, default=8.0, help="per-request timeout seconds")
    ap.add_argument("--budget", type=float, default=180.0, help="wall-clock budget for download phase")
    ap.add_argument("--domain-filter", default="", help="comma list; keep only urls containing one of these")
    ap.add_argument("--group-prefix", default="", help="filename prefix, e.g. 1 or A")
    args = ap.parse_args()

    socket.setdefaulttimeout(args.timeout)
    os.makedirs(args.out, exist_ok=True)

    queries = list(args.query)
    if args.query_file:
        with open(args.query_file, encoding="utf-8") as fh:
            queries += [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    if not queries:
        ap.error("need --query or --query-file")

    keys = [k.strip().lower() for k in args.domain_filter.split(",") if k.strip()]
    t0 = time.time()
    items, seen = [], set()
    for q in queries:
        for o in harvest(q, args.count, args.timeout):
            if keys and not any(k in o["url"].lower() for k in keys):
                continue
            if o["url"] not in seen:
                seen.add(o["url"])
                items.append(o)
    print("candidates: %d (after dedupe/filter)" % len(items))
    download(items[:args.limit], args.out, args.timeout, t0 + args.budget, args.group_prefix)
    dedupe(args.out)
    contact_sheet(args.out)


if __name__ == "__main__":
    main()
