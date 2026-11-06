#!/usr/bin/env python3
"""Hosting/admin panel surface probe: detect common panels by path + marker."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
PATHS = ["/admin", "/admin/login", "/login", "/wp-login.php", "/wp-admin/", "/1panel/", "/panel/",
         "/bt/", "/druid/index.html", "/actuator", "/admin/index.php", "/index.php?s=/admin"]
MARKERS = ["wordpress", "1panel", "宝塔", "baota", "druid", "spring", "ruoyi", "若依", "login"]


def get(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096).decode("utf-8", "replace")
            title = (re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S) or [None, ""])[1].strip()
            return {"status": r.status, "len": len(body), "title": title[:100],
                    "markers": [m for m in MARKERS if m in body.lower()]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "markers": []}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="面板入口面探针")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    host = (urlparse(base).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    out = {p: get(base + p, args.timeout, args.insecure) for p in PATHS}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/panel_surface.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/panel_surface.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
