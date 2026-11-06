#!/usr/bin/env python3
"""Sensitive directory probe: scoped GET checks for exposed paths."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

DEFAULT_PATHS = [".git/config", ".env", "backup.zip", "www.zip", "db.sql", "phpinfo.php",
                 "server-status", "actuator/env", "swagger-ui.html", "druid/index.html",
                 "uploads/", "logs/", "admin/", "console/"]
CASES = Path("/root/cases")


def check(base: str, path: str, timeout: float, insecure: bool) -> dict:
    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(2048)
            return {"path": path, "status": r.status, "len": r.headers.get("Content-Length", len(body)),
                    "type": r.headers.get("Content-Type", ""), "preview": body[:120].decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        return {"path": path, "status": e.code}
    except Exception as e:
        return {"path": path, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="敏感目录/文件探针（需显式 scope）")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True, help="authorized host/domain")
    ap.add_argument("--paths", help="path list file")
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = urlparse(args.url).hostname or ""
    allowed = args.scope.replace("*.", "").lower()
    if not (host.lower() == allowed or host.lower().endswith("." + allowed)):
        print(f"[scope] DENY {host} (scope={args.scope})")
        return 2
    paths = DEFAULT_PATHS
    if args.paths:
        paths = [x.strip() for x in Path(args.paths).read_text(errors="ignore").splitlines() if x.strip()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        results = list(ex.map(lambda p: check(args.url, p, args.timeout, args.insecure), paths))
    for r in results:
        if r.get("status") in (200, 206, 301, 302, 403):
            print(f"{r.get('status')} {r['path']} len={r.get('len','-')} {r.get('type','')}")
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/sensitive_dir.json"
        out.write_text(json.dumps({"url": args.url, "scope": args.scope, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
