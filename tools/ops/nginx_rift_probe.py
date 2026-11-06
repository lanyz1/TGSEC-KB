#!/usr/bin/env python3
"""NGINX Rift (CVE-2026-42945) surface check: version + config clues, no exploit."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description="NGINX Rift 面检查")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if args.insecure else None
    try:
        with urllib.request.urlopen(req, timeout=args.timeout, context=ctx) as r:
            server = r.headers.get("Server", "")
            status = r.status
    except urllib.error.HTTPError as e:
        server = e.headers.get("Server", "")
        status = e.code
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    m = re.search(r"nginx/([0-9.]+)", server, re.I)
    out = {"url": args.url, "status": status, "server": server, "nginx": bool(m),
           "version": m.group(1) if m else None, "affected_hint": bool(m and tuple(map(int, m.group(1).split(".")[:2])) < (1, 27))}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/nginx_rift.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/nginx_rift.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
