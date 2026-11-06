#!/usr/bin/env python3
"""Admin credential probe: tiny lockout-aware list, capped by --max."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
USERS = ["admin", "administrator", "root"]
PASSES = ["admin", "admin123", "123456", "password", "admin888"]


def attempt(url: str, user: str, pwd: str, user_field: str, pass_field: str,
            timeout: float, insecure: bool) -> dict:
    data = urllib.parse.urlencode({user_field: user, pass_field: pwd}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0",
                                                           "Content-Type": "application/x-www-form-urlencoded"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(2048).decode("utf-8", "replace").lower()
            return {"status": r.status, "len": len(body), "success": any(x in body for x in ("dashboard", "欢迎", "logout", "退出"))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "success": False}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Admin 小字典凭据探测")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--user-field", default="username")
    ap.add_argument("--pass-field", default="password")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    attempts = []
    for u in USERS:
        for p in PASSES:
            if len(attempts) >= min(args.max, 20):
                break
            attempts.append((u, p))
    out = []
    for u, p in attempts:
        r = attempt(args.url, u, p, args.user_field, args.pass_field, args.timeout, args.insecure)
        out.append({"user": u, "pass_len": len(p), **r})
        if r.get("success"):
            break
    print(json.dumps({"url": args.url, "attempts": len(out), "results": out}, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/admin_creds.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/admin_creds.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
