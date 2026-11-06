#!/usr/bin/env python3
"""Batch HTTP probe: status, title, server, redirect target."""
from __future__ import annotations

import argparse
import concurrent.futures
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def probe(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(8192).decode("utf-8", errors="replace")
            m = TITLE.search(body)
            return {"url": url, "status": r.status, "title": m.group(1).strip()[:100] if m else "",
                    "server": r.headers.get("Server", ""), "final": r.geturl()}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "location": e.headers.get("Location", "")}
    except Exception as e:
        return {"url": url, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="批量 HTTP 探针")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", "-u")
    src.add_argument("--urls", "-U", help="file with one URL per line")
    ap.add_argument("--threads", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    urls = [args.url] if args.url else [x.strip() for x in Path(args.urls).read_text(errors="ignore").splitlines() if x.strip()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        results = list(ex.map(lambda u: probe(u, args.timeout, args.insecure), urls))
    for r in results:
        print(f"{r.get('status','ERR')} {r['url']} {r.get('title','')} {r.get('server','')} {r.get('location','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
