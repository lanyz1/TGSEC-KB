#!/usr/bin/env python3
"""Yudao/TMA front-end surface: JS bundles, /app-api, encryption markers."""
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
MARKERS = ["/app-api", "/admin-api", "sk_encrypt", "initData", "telegramBot/autoLogin",
           "tenant", "AES", "CryptoJS", "sign", "randbet", "game/list", "pay"]
SCRIPT_RE = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)


def fetch(url: str, timeout: float, insecure: bool) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", errors="replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return 0, "", url


def main() -> int:
    ap = argparse.ArgumentParser(description="芋道/TMA 前端攻击面探针")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=12)
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--max-js", type=int, default=20)
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    status, html, final = fetch(args.url, args.timeout, args.insecure)
    scripts = [urljoin(final, s) for s in SCRIPT_RE.findall(html)]
    findings = []
    bundles = []
    for js in scripts[: args.max_js]:
        js_url = urljoin(final, js)
        st, body, _ = fetch(js_url, args.timeout, args.insecure)
        if st != 200:
            continue
        hits = sorted({m for m in MARKERS if m in body})
        bundles.append({"url": js_url, "bytes": len(body), "markers": hits})
        if hits:
            findings.append({"url": js_url, "markers": hits})
    result = {"base": args.url, "status": status, "scripts": scripts, "bundles": bundles,
              "findings": findings, "tma": "initData" in html or any("initData" in b["markers"] for b in bundles)}
    for f in findings:
        print(f"[js] {f['url']} markers={f['markers']}")
    print(f"[yudao] scripts={len(scripts)} scanned={len(bundles)} findings={len(findings)} tma={result['tma']}")
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/yudao_appapi.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
