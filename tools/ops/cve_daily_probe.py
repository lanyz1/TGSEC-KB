#!/usr/bin/env python3
"""Daily CVE intel: CISA KEV feed filter (no API key)."""
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timedelta

KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="CVE 每日情报")
    ap.add_argument("--product", help="substring filter")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    req = urllib.request.Request(KEV, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    cutoff = datetime.utcnow() - timedelta(days=args.days)
    rows = []
    for v in data.get("vulnerabilities", []):
        try:
            added = datetime.strptime(v.get("dateAdded", ""), "%Y-%m-%d")
        except Exception:
            continue
        if added < cutoff:
            continue
        if args.product and args.product.lower() not in (v.get("product", "") + " " + v.get("vendorProject", "")).lower():
            continue
        rows.append(v)
    rows = rows[-args.limit:]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for v in rows:
            print(v.get("cveID"), "|", v.get("vendorProject"), v.get("product"), "|", v.get("dateAdded"), "|", v.get("vulnerabilityName"))
    print(f"count={len(rows)} catalog={data.get('catalogVersion')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
