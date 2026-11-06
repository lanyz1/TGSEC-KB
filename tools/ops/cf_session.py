#!/usr/bin/env python3
"""Cloudflare session fetcher: cookie header -> status/html save."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="CF 会话抓取")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--cookie", default="")
    ap.add_argument("--ua", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
    ap.add_argument("--case")
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    req = urllib.request.Request(args.url, headers={"User-Agent": args.ua, "Cookie": args.cookie})
    ctx = ssl._create_unverified_context() if args.insecure else None
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            body = r.read(2 * 1024 * 1024)
            out = {"status": r.status, "bytes": len(body), "cf_ray": r.headers.get("cf-ray", ""),
                   "challenge": b"Just a moment" in body or b"cf-chl" in body}
    except urllib.error.HTTPError as e:
        body = e.read(2 * 1024 * 1024)
        out = {"status": e.code, "bytes": len(body), "cf_ray": e.headers.get("cf-ray", ""),
               "challenge": b"Just a moment" in body or b"cf-chl" in body}
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/cf_page.html").write_bytes(body)
        out["saved"] = str(case / "artifacts/cf_page.html")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
