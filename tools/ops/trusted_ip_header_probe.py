#!/usr/bin/env python3
"""Trusted-IP header differential probe: does XFF/Real-IP change access?"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
HEADERS = {"X-Forwarded-For": "127.0.0.1", "X-Real-IP": "127.0.0.1",
           "True-Client-IP": "127.0.0.1", "X-Client-IP": "127.0.0.1",
           "X-Originating-IP": "127.0.0.1"}


def get(url: str, extra: dict, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **extra})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(8192)
            return {"status": r.status, "len": len(body), "sha": hashlib.sha256(body).hexdigest()[:12]}
    except urllib.error.HTTPError as e:
        body = e.read(2048)
        return {"status": e.code, "len": len(body), "sha": hashlib.sha256(body).hexdigest()[:12]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="信任 IP 头差分探针")
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
    base = get(args.url, {}, args.timeout, args.insecure)
    print("baseline", base)
    results = []
    for name, value in HEADERS.items():
        r = get(args.url, {name: value}, args.timeout, args.insecure)
        changed = r.get("status") != base.get("status") or r.get("sha") != base.get("sha")
        print(f"{name:16} {r} changed={changed}")
        results.append({"header": name, "value": value, "result": r, "changed": changed})
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/trusted_ip.json"
        out.write_text(json.dumps({"url": args.url, "baseline": base, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
