#!/usr/bin/env python3
"""Front-end source/endpoint extraction from a page and same-origin scripts."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

CASES = Path("/root/cases")
SRC = re.compile(r"""(?:src|href)=["']([^"']+\.(?:js|mjs|json|map)(?:\?[^"']*)?)["']""", re.I)
EP = re.compile(r"""["'](/[A-Za-z0-9_./-]*(?:api|admin|login|user|upload|pay|config)[A-Za-z0-9_./?=&-]*)["']""", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description="前端源码/端点提取")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--max-js", type=int, default=15)
    ap.add_argument("--timeout", type=float, default=12)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    ctx = ssl._create_unverified_context() if args.insecure else None
    req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=args.timeout, context=ctx) as r:
        html = r.read().decode("utf-8", errors="replace")
        final = r.geturl()
    scripts = sorted({urljoin(final, s) for s in SRC.findall(html)})
    endpoints = sorted(set(EP.findall(html)))
    bundles = []
    host = urlparse(final).netloc
    for js in scripts[: args.max_js]:
        if urlparse(js).netloc != host:
            continue
        try:
            req = urllib.request.Request(js, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=args.timeout, context=ctx) as r:
                body = r.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            bundles.append({"url": js, "bytes": len(body), "endpoints": sorted(set(EP.findall(body)))[:200]})
        except Exception:
            pass
    result = {"url": args.url, "final": final, "scripts": scripts, "endpoints": endpoints[:300], "bundles": bundles}
    print(f"scripts={len(scripts)} endpoints={len(endpoints)} bundles={len(bundles)}")
    for e in endpoints[:40]:
        print("  ", e)
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/source_extract.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
