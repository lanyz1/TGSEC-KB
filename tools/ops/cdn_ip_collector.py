#!/usr/bin/env python3
"""Collect CDN/subdomain A records for a domain (crt.sh + DNS)."""
from __future__ import annotations

import argparse
import json
import socket
import urllib.parse
import urllib.request


def crt(domain: str) -> list[str]:
    try:
        url = "https://crt.sh/?q=%25." + urllib.parse.quote(domain) + "&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            rows = json.loads(r.read().decode("utf-8", "replace"))
        return sorted({n.strip().lower() for row in rows for n in row.get("name_value", "").splitlines() if n.strip()})
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="CDN/子域 IP 收集")
    ap.add_argument("domain")
    ap.add_argument("--subs", help="extra subdomains, one per line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d = args.domain.lower()
    hosts = set(crt(d)) | {d, "www." + d}
    if args.subs:
        from pathlib import Path
        hosts |= {l.strip() for l in Path(args.subs).read_text().splitlines() if l.strip()}
    out = {}
    for h in sorted(hosts):
        try:
            out[h] = sorted({x[4][0] for x in socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)})
        except Exception:
            out[h] = []
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for h, ips in out.items():
            print(f"{h:40} {','.join(ips)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
