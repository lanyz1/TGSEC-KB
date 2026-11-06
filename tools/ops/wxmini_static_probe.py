#!/usr/bin/env python3
"""WeChat mini-program static audit: URLs, API calls, sensitive markers."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CASES = Path("/root/cases")
URL = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,300}")
MARKERS = ["wx.request", "wx.uploadFile", "tokenRequired", "rkbm", "SM2", "amount",
           "pay", "withdraw", "Authorization", "openid", "unionid"]


def main() -> int:
    ap = argparse.ArgumentParser(description="wxapkg/小程序静态审计")
    ap.add_argument("action", choices=["doctor", "run"], nargs="?", default="run")
    ap.add_argument("--dir", "-d", help="decompiled directory or .wxapkg")
    ap.add_argument("--case", "-c")
    ap.add_argument("--probe-urls", action="store_true")
    ap.add_argument("--scope")
    args = ap.parse_args()
    if args.action == "doctor":
        print("doctor: static-only; URLs are not fetched unless --probe-urls + --scope")
        return 0
    if not args.dir:
        ap.error("--dir required")
    root = Path(args.dir)
    if not root.exists():
        ap.error(f"not found: {root}")
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    urls, markers, hits = set(), {m: 0 for m in MARKERS}, []
    for p in files:
        if p.stat().st_size > 20 * 1024 * 1024:
            continue
        try:
            text = p.read_text(errors="ignore") if p.suffix.lower() not in (".wxapkg", ".bin") else p.read_bytes().decode("utf-8", errors="ignore")
        except Exception:
            continue
        urls |= set(URL.findall(text))
        local = {m: text.count(m) for m in MARKERS if m in text}
        for m, n in local.items():
            markers[m] += n
        if local:
            hits.append({"file": str(p), "markers": local})
    result = {"dir": str(root), "files": len(files), "urls": sorted(urls)[:300], "markers": markers, "hits": hits[:100]}
    print(f"files={len(files)} urls={len(urls)} markers={markers}")
    for u in result["urls"][:30]:
        print("  ", u)
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/wxmini_static.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
