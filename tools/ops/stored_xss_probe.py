#!/usr/bin/env python3
"""Stored XSS probe: submit a unique marker, then read back the sink."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def send(url: str, data: bytes | None, method: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return {"status": r.status, "len": len(r.read(4096))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="存储型 XSS 探针")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--param", default="content")
    ap.add_argument("--method", default="POST")
    ap.add_argument("--check-url")
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    marker = "xssprobe" + uuid.uuid4().hex[:10]
    payload = f"<script>/*{marker}*/</script>"
    data = urllib.parse.urlencode({args.param: payload}).encode()
    submit = send(args.url, data, args.method, args.timeout, args.insecure)
    check_url = args.check_url or args.url
    req = urllib.request.Request(check_url, headers={"User-Agent": "Mozilla/5.0"})
    reflected = False
    status = None
    try:
        with urllib.request.urlopen(req, timeout=args.timeout, context=ssl._create_unverified_context() if args.insecure else None) as r:
            status = r.status
            reflected = marker in r.read(2 * 1024 * 1024).decode("utf-8", "replace")
    except Exception:
        pass
    out = {"submit": submit, "check_status": status, "marker": marker, "reflected": reflected,
           "note": "reflected only proves storage/sink; execute in a browser for DOM context"}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/stored_xss.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/stored_xss.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
