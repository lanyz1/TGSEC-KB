#!/usr/bin/env python3
"""ASP.NET surface: trace/elmah/ViewState/login endpoints, read-only."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
PATHS = ["/trace.axd", "/elmah.axd", "/web.config", "/Account/Login.aspx", "/login.aspx", "/api/", "/__VIEWSTATE"]


def get(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096).decode("utf-8", "replace")
            return {"status": r.status, "len": len(body), "server": r.headers.get("Server", ""),
                    "viewstate": "__VIEWSTATE" in body, "trace": "Application Trace" in body, "elmah": "Error Log" in body}
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode("utf-8", "replace")
        return {"status": e.code, "len": len(body), "viewstate": "__VIEWSTATE" in body}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="ASP.NET 面探针")
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
        (case / "artifacts/aspnet_surface.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/aspnet_surface.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
