#!/usr/bin/env python3
"""Captcha router: local ddddocr first, API providers only with keys."""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="验证码路由")
    ap.add_argument("--image", "-i")
    ap.add_argument("--provider", default="auto", choices=["auto", "ddddocr", "2captcha", "capmonster"])
    ap.add_argument("--key")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.image:
        ap.error("--image required")
    if args.provider in ("auto", "ddddocr"):
        cmd = [sys.executable, "/root/TGSEC-Qtzuu/tools/ops/captcha_auto.py", "ocr", "--image", args.image]
        return subprocess.call(cmd)
    if not args.key:
        print(f"[err] {args.provider} requires --key (not stored)")
        return 2
    print(f"[plan] provider={args.provider} image={args.image}; API submission not implemented without provider SDK")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
