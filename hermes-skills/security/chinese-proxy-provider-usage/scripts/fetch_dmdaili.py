#!/usr/bin/env python3
"""Fetch and normalize a dmdaili proxy API response.

Usage:
  python3 fetch_dmdaili.py --api-url 'http://api.dmdaili.com/dmgetip.asp?...' --out proxies.txt

Keep the API URL secret; it contains apikey/pwd.
"""
import argparse
import json
import re
import sys

import requests


def parse(text):
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        out = []
        for item in data.get("data", []):
            if isinstance(item, dict) and item.get("ip") and item.get("port"):
                out.append(f"{item['ip']}:{item['port']}")
        return out
    except Exception:
        pass
    out = []
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"[0-9A-Fa-f:.]+:\d+", line):
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", required=True)
    ap.add_argument("--out", default="proxies.txt")
    ap.add_argument("--timeout", type=float, default=30)
    args = ap.parse_args()

    r = requests.get(args.api_url, timeout=args.timeout)
    print(f"HTTP {r.status_code}, {len(r.content)} bytes")
    proxies = list(dict.fromkeys(parse(r.text)))
    with open(args.out, "w") as f:
        f.write("\n".join(proxies))
    print(f"parsed {len(proxies)} proxies -> {args.out}")
    if not proxies:
        print("No proxies parsed; inspect provider status/response body.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
