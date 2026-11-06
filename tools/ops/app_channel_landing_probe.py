#!/usr/bin/env python3
"""APP channel landing-page probe: download URLs, base64 chunks, redirects."""
from __future__ import annotations

import argparse
import base64
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

CASES = Path("/root/cases")
EXT = re.compile(r"https?://[^\s\"'<>]+?\.(?:apk|ipa|plist|mobileconfig)(?:\?[^\s\"'<>]*)?", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description="APP 渠道落地页探针")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=10)
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
            body = r.read(2 * 1024 * 1024).decode("utf-8", "replace")
            final = r.geturl()
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    links = sorted(set(EXT.findall(body)))
    b64 = [m for m in re.findall(r"[A-Za-z0-9+/]{80,}={0,2}", body) if len(m) > 100]
    out = {"url": args.url, "final": final, "links": links, "base64_chunks": len(b64), "bytes": len(body)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/app_landing.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/app_landing.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
