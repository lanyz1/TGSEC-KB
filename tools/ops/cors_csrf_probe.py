#!/usr/bin/env python3
"""CORS and CSRF surface probe (read-only unless --post is supplied)."""
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
FORM = re.compile(r"<form\b.*?</form>", re.I | re.S)
INPUT = re.compile(r"<input\b[^>]*>", re.I)


def req(url: str, method: str = "GET", headers: dict | None = None, data: bytes | None = None,
        timeout: float = 8, insecure: bool = False) -> dict:
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
            return {"status": resp.status, "headers": dict(resp.headers), "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": dict(e.headers), "body": e.read(2048).decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="CORS/CSRF 面探针")
    ap.add_argument("action", choices=["cors", "csrf"], nargs="?", default="cors")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--origin", default="https://evil.example")
    ap.add_argument("--post", help="CSRF target URL to test without token")
    ap.add_argument("--cookie")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    if args.action == "cors":
        r = req(args.url, headers={"Origin": args.origin}, timeout=args.timeout, insecure=args.insecure)
        h = {k.lower(): v for k, v in r.get("headers", {}).items()}
        out = {"status": r.get("status"), "acao": h.get("access-control-allow-origin"),
               "acac": h.get("access-control-allow-credentials"), "acah": h.get("access-control-allow-headers"),
               "acam": h.get("access-control-allow-methods"), "reflected": h.get("access-control-allow-origin") == args.origin}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        r = req(args.url, timeout=args.timeout, insecure=args.insecure)
        forms = FORM.findall(r.get("body", ""))
        tokens = [i for f in forms for i in INPUT.findall(f) if re.search(r"csrf|token|nonce", i, re.I)]
        setcookie = r.get("headers", {}).get("Set-Cookie", "")
        out = {"url": args.url, "status": r.get("status"), "forms": len(forms), "token_inputs": tokens[:10],
               "samesite": "SameSite" in setcookie, "httponly": "HttpOnly" in setcookie,
               "post_test": None}
        if args.post:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if args.cookie:
                headers["Cookie"] = args.cookie
            pr = req(args.post, method="POST", headers=headers, data=b"", timeout=args.timeout, insecure=args.insecure)
            out["post_test"] = {"status": pr.get("status"), "len": len(pr.get("body", "")), "error": pr.get("error")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        p = case / "artifacts/cors_csrf.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
