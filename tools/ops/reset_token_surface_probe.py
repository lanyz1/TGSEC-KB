#!/usr/bin/env python3
"""Password-reset token surface: request/validate differential, no account change."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse

CASES = Path("/root/cases")


def req(url: str, data: bytes | None, timeout: float, insecure: bool) -> dict:
    r = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0",
                                                        "Content-Type": "application/x-www-form-urlencoded"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            body = resp.read(2048).decode("utf-8", "replace")
            return {"status": resp.status, "len": len(body), "body": body[:300]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "body": e.read(300).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="重置密码 token 面")
    ap.add_argument("--url", "-u", required=True, help="reset/validate endpoint")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--token", default="invalid-probe-token")
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    tests = {
        "invalid_token": req(args.url + "?" + urlencode({"token": args.token}), None, args.timeout, args.insecure),
        "empty_token": req(args.url + "?token=", None, args.timeout, args.insecure),
    }
    out = {"url": args.url, "tests": tests}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/reset_token.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/reset_token.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
