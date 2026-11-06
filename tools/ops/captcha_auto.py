#!/usr/bin/env python3
"""Captcha OCR: ddddocr on a local image or fetched image URL."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from pathlib import Path

CASES = Path("/root/cases")


def read_image(args) -> bytes:
    if args.image:
        return Path(args.image).read_bytes()
    req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0",
                                                    **({"Cookie": args.cookie} if args.cookie else {})})
    ctx = ssl._create_unverified_context() if args.insecure else None
    with urllib.request.urlopen(req, timeout=args.timeout, context=ctx) as r:
        return r.read(2 * 1024 * 1024)


def main() -> int:
    ap = argparse.ArgumentParser(description="图形验证码 OCR（ddddocr）")
    ap.add_argument("action", choices=["ocr"], nargs="?", default="ocr")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", "-i", help="local captcha image")
    src.add_argument("--url", "-u", help="captcha image URL")
    ap.add_argument("--cookie")
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    try:
        import ddddocr
    except ImportError:
        ap.error("ddddocr not installed; pip install ddddocr")
    ocr = ddddocr.DdddOcr(show_ad=False)
    img = read_image(args)
    text = ocr.classification(img)
    result = {"source": args.image or args.url, "text": text, "bytes": len(img)}
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/captcha_ocr.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
