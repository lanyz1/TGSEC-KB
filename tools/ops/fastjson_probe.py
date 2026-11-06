#!/usr/bin/env python3
"""Fastjson surface detection: error-signature probe, no gadget execution."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

CASES = Path("/root/cases")
PATHS = ["/", "/api", "/login", "/api/login"]


def post(url: str, body: str, timeout: float, insecure: bool) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body.encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Fastjson 面探测（错误签名，不执行 gadget）")
    ap.add_argument("action", choices=["detect"], nargs="?", default="detect")
    ap.add_argument("--base", "-u", dest="base", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    results = []
    for path in PATHS:
        url = urljoin(args.base.rstrip("/") + "/", path.lstrip("/"))
        st, body = post(url, '{"@type":"java.lang.AutoCloseable"', args.timeout, args.insecure)
        hit = any(x in body.lower() for x in ("fastjson", "autotype", "jsonexception", "syntax error"))
        results.append({"url": url, "status": st, "hit": hit, "snippet": body[:200]})
        print(f"{url} status={st} fastjson_signal={hit}")
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/fastjson.json"
        out.write_text(json.dumps({"base": args.base, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
