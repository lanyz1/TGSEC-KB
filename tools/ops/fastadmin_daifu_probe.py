#!/usr/bin/env python3
"""FastAdmin / ThinkPHP payout surface probe: read-only endpoint discovery."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
PATHS = ["/", "/index.php", "/index.php?s=/api/demo/index", "/api/demo/index",
         "/api/demo/test", "/index.php?s=/api/index/index", "/assets/js/require.js"]


def get(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(2048).decode("utf-8", errors="replace")
            return {"status": r.status, "len": len(body), "server": r.headers.get("Server", ""),
                    "markers": [m for m in ("fastadmin", "require.js", "ThinkPHP", "demo") if m.lower() in body.lower()]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "server": e.headers.get("Server", "")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="FastAdmin/代付面探针")
    ap.add_argument("--base", "-b", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    host = (urlparse(base).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    results = {p: get(base + p, args.timeout, args.insecure) for p in PATHS}
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/fastadmin_surface.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
