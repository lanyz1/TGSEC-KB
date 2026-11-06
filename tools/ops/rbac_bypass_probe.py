#!/usr/bin/env python3
"""RBAC differential: same path with/without a token, status+size compare."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def get(url: str, token: str | None, timeout: float, insecure: bool) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096)
            return {"status": r.status, "len": len(body)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="RBAC 前后端鉴权差分")
    ap.add_argument("--url", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--token")
    ap.add_argument("--paths", default="/api/user/info,/api/admin/users,/api/admin/config,/api/agent/users")
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
    out = {}
    for p in [x.strip() for x in args.paths.split(",") if x.strip()]:
        anon = get(base + p, None, args.timeout, args.insecure)
        auth = get(base + p, args.token, args.timeout, args.insecure) if args.token else None
        out[p] = {"anon": anon, "auth": auth,
                  "suspicious": bool(auth and auth.get("status") == 200 and anon.get("status") in (200, 401, 403)
                                     and auth.get("len", 0) > 200)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/rbac_diff.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/rbac_diff.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
