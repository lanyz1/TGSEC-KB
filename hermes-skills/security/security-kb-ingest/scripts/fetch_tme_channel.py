#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch recent posts from a public Telegram channel preview (t.me/s/<ch>).

Verified 2026-10-08 on @cvebird: direct fetch OK (no proxy), ~20 posts/page,
contiguous ids, pagination via ?before=<min_id>.

Usage:
    python3 fetch_tme_channel.py <channel> [cutoff_iso] [max_pages] [out_json]
      channel   : channel slug, e.g. cvebird
      cutoff_iso: stop when a page goes older than this (default: now-7d)
      max_pages : safety cap (default 12)
      out_json  : output path (default /root/<channel>_posts.json)

Output:
    JSON list [{id, dt, text, links}] + stdout: per-day counts, id-contiguity
    check, and one line per repo link (github/gitlab/gitee).
"""
import html as htmlmod
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
LINK_RE = r"https?://(?:github\.com|gitlab\.com|gitee\.com)/[^\s\"'<>)\]]+"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def extract_text(chunk):
    """tgme_widget_message_text inner text; nesting-aware (no lazy regex)."""
    i = chunk.find("tgme_widget_message_text")
    if i < 0:
        return ""
    raw = chunk[chunk.find(">", i) + 1:]
    depth, pos, end = 1, 0, None
    while depth > 0:
        nd, nc = raw.find("<div", pos), raw.find("</div>", pos)
        if nc == -1:
            break
        if nd != -1 and nd < nc:
            depth += 1
            pos = nd + 4
        else:
            depth -= 1
            if depth == 0:
                end = nc
            pos = nc + 6
    seg = raw[:end] if end is not None else raw
    seg = re.sub(r"<br\s*/?>", "\n", seg)
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", seg)).strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ch = sys.argv[1].strip().lstrip("@").rstrip("/").split("/")[-1]
    cutoff = sys.argv[2] if len(sys.argv) > 2 else \
        (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    out = sys.argv[4] if len(sys.argv) > 4 else f"/root/{ch}_posts.json"

    base = f"https://t.me/s/{ch}"
    url, pages, seen, posts = base, 0, set(), []

    while url and pages < max_pages:
        try:
            h = fetch(url)
        except Exception as e:  # noqa: BLE001
            print(f"!! fetch failed: {url} :: {e}", file=sys.stderr)
            break
        pages += 1
        page = []
        for c in h.split(f'data-post="{ch}/')[1:]:
            m = re.match(r"(\d+)", c)
            if not m or int(m.group(1)) in seen:
                continue
            pid = int(m.group(1))
            seen.add(pid)
            tm = re.search(r'<time datetime="([^"]+)"', c)
            text = extract_text(c)
            links = {l.rstrip(").,;") for l in
                     re.findall(LINK_RE, c) + re.findall(LINK_RE, text)}
            page.append({"id": pid, "dt": tm.group(1) if tm else "",
                         "text": text, "links": sorted(links)})
        if not page:
            break
        posts.extend(page)
        dts = [p["dt"] for p in page if p["dt"]]
        if dts and min(dts) < cutoff:
            break
        url = f"{base}?before={min(p['id'] for p in page)}"
        time.sleep(1.2)

    posts.sort(key=lambda p: p["id"])
    with open(out, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=1)

    days = Counter(p["dt"][:10] for p in posts if p["dt"])
    print(f"== {len(posts)} posts / {pages} pages -> {out}")
    for d, n in sorted(days.items()):
        print(f"  {d}: {n}")
    if posts:
        ids = [p["id"] for p in posts]
        print(f"ids {min(ids)}..{max(ids)} contiguous={max(ids) - min(ids) + 1 == len(ids)}")
        print("== repo links:")
        for p in posts:
            for l in p["links"]:
                print(f"  #{p['id']} {l}")


if __name__ == "__main__":
    main()
