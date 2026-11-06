#!/usr/bin/env python3
"""Frontend auth crypto surface: bundle fetch + key/algorithm markers."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

CASES = Path("/root/cases")
MARK = ["CryptoJS", "AES", "RSA", "SM2", "SM4", "publicKey", "encrypt", "JSEncrypt",
        "md5", "sha256", "login", "captcha", "sign"]


def fetch(url: str, timeout: float, insecure: bool) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read(2 * 1024 * 1024).decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser(description="前端认证加密面")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    base = args.url
    host = (urlparse(base).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    html = fetch(base, args.timeout, args.insecure)
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', html, re.I)
    scripts = {}
    for src in srcs[:30]:
        u = urljoin(base, src)
        if (urlparse(u).hostname or "").lower() != host:
            continue
        try:
            body = fetch(u, args.timeout, args.insecure)
            hits = {m: body.count(m) for m in MARK if m in body}
            if hits:
                scripts[u] = hits
        except Exception as e:
            scripts[u] = {"error": str(e)}
    out = {"url": base, "scripts": len(srcs), "hits": scripts}
    print(json.dumps(out, ensure_ascii=False, indent=2)[:10000])
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/frontend_auth.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/frontend_auth.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
