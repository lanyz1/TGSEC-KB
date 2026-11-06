#!/usr/bin/env python3
"""Admin entry surface: status/redirect/title for common admin paths."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

PATHS = ["admin", "admin/", "admin/login", "login", "manage", "manager", "console",
         "dashboard", "backend", "system", "api/admin", "wp-admin/", "user/login"]
CASES = Path("/root/cases")


def get(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096).decode("utf-8", errors="replace")
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            return {"url": r.geturl(), "status": r.status, "title": (title.group(1).strip()[:120] if title else ""),
                    "server": r.headers.get("Server", ""), "len": len(body)}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "location": e.headers.get("Location", "")}
    except Exception as e:
        return {"url": url, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Admin 入口面探测")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    results = [get(urljoin(args.url.rstrip("/") + "/", p), args.timeout, args.insecure) for p in PATHS]
    for r in results:
        if r.get("status") in (200, 301, 302, 401, 403):
            print(f"{r['status']} {r['url']} {r.get('title','')} {r.get('location','')}")
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/admin_access.json"
        out.write_text(json.dumps({"base": args.url, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
